import logging
import pandas as pd
from pprint import pprint
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from config import DEBUG, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD, SQL_DRIVER
from services.connection_status import connection_registry

# SQLAlchemy engine (recommended by pandas)
_engine = None


def get_engine():
    """
    Get or create the SQLAlchemy engine for SQL Server connections.

    Returns None if the connection fails, allowing graceful degradation.
    """
    global _engine
    if _engine is None:
        try:
            conn_str = (
                f"DRIVER={{{SQL_DRIVER}}};"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"UID={SQL_USER};"
                f"PWD={SQL_PASSWORD};"
                f"TrustServerCertificate=yes;"
            )
            _engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={quote_plus(conn_str)}"
            )
            # Test the connection
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            connection_registry.set_success("SQL Server")
        except Exception as e:
            error_msg = _format_sql_error(e)
            logging.error(f"SQL Server connection failed: {error_msg}")
            connection_registry.set_error("SQL Server", error_msg)
            _engine = None
    return _engine


def _format_sql_error(e: Exception) -> str:
    """Format SQL errors into user-friendly messages."""
    error_str = str(e)

    # Check for common error patterns
    if "Login failed" in error_str:
        return f"SQL Server authentication failed. Please check credentials. (Server: {SQL_SERVER}, Database: {SQL_DATABASE})"
    elif "Cannot open database" in error_str:
        return f"Cannot open database '{SQL_DATABASE}'. Please verify the database name exists."
    elif "server was not found" in error_str or "Could not open a connection" in error_str:
        return f"Cannot connect to SQL Server '{SQL_SERVER}'. Please verify the server is accessible."
    elif "ODBC Driver" in error_str:
        return f"ODBC Driver issue: {SQL_DRIVER} may not be installed or configured correctly."
    else:
        return f"SQL Server error: {error_str[:200]}"


# Core fetch function
def fetch_survey_submission_data():
    """
    Fetch survey submission data from the SQL Server.

    Returns an empty DataFrame if the connection fails.
    """
    engine = get_engine()
    if engine is None:
        logging.warning("SQL Server not available - returning empty DataFrame")
        return pd.DataFrame()

    query = """
    WITH BaseData AS (
        SELECT
            sy.svyYear,
            S.schNo,
            S.schName,
		    S.schLat,
		    S.schLong,
            I.iName AS Island,
            D.dName AS District,
            R.codeDescription AS Region,
            SS.ssMissingData,
            SS.ssMissingDataNotSupplied,
            SSX.pCreateDateTime,
            SSX.pCreateUser,
            SSX.pEditDateTime,
            SSX.pEditUser,
            CASE
                WHEN SS.ssID IS NOT NULL THEN 1 ELSE 0
            END AS Submitted
        FROM (
            SELECT DISTINCT svyYear FROM SchoolSurvey WHERE svyYear >= 2020
        ) sy
        CROSS JOIN Schools S
        LEFT JOIN Islands I ON S.iCode = I.iCode
        LEFT JOIN Districts D ON I.iGroup = D.dID
        LEFT JOIN lkpRegion R ON I.iOuter = R.codeCode
        LEFT JOIN SchoolSurvey SS ON SS.schNo = S.schNo AND SS.svyYear = sy.svyYear
        LEFT JOIN SchoolSurveyXml_ SSX ON SS.ssID = SSX.ssID
        WHERE
            (S.schClosed = 0 OR S.schClosed > sy.svyYear)
            AND S.schType != 'EC'
    )
    SELECT * FROM BaseData;
    """
    try:
        df = pd.read_sql(query, engine)
        connection_registry.set_success("SQL Server")
        return df
    except SQLAlchemyError as e:
        error_msg = _format_sql_error(e)
        logging.error(f"SQL query failed: {error_msg}")
        connection_registry.set_error("SQL Server", error_msg)
        return pd.DataFrame()
    except Exception as e:
        error_msg = f"Unexpected error fetching SQL data: {str(e)[:200]}"
        logging.error(error_msg)
        connection_registry.set_error("SQL Server", error_msg)
        return pd.DataFrame()


###############################################################################
# Fetch and store data at startup
###############################################################################
df_submission = fetch_survey_submission_data()

###############################################################################
# Debugging logs
###############################################################################
if DEBUG:
    # print("✅ df_submission (head):")
    # pprint(df_submission.head(3).to_dict(orient="records"))
    # print("\nℹ️ df_submission (info):")
    # print(df_submission.info())
    # print("\nℹ️ df_submission (sample):")
    # print(df_submission.head(5))
    # print("End of sql.py debug output")
    pass
