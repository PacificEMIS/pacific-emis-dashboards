import pandas as pd
from pprint import pprint
from urllib.parse import quote_plus
from sqlalchemy import create_engine

from config import DEBUG, SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD, SQL_DRIVER

# SQLAlchemy engine (recommended by pandas)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        conn_str = (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
        _engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(conn_str)}")
    return _engine


# Core fetch function
def fetch_survey_submission_data():
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
    df = pd.read_sql(query, get_engine())
    return df


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
