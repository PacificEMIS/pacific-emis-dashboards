import os
import json
import logging
import requests
import pandas as pd
import plotly.express as px
from pprint import pprint
import xml.etree.ElementTree as ET
import time

from config import (
    DEBUG,
    USERNAME,
    PASSWORD,
    BASE_URL,
    LOGIN_URL,
    WAREHOUSE_VERSION_URL,
    LOOKUPS_URL,
    ENROL_URL,
    TABLEENROLX_URL,
    TEACHERCOUNT_URL,
    TEACHERPD_URL,
    TEACHERPDATTENDANCE_URL,
    SCHOOLCOUNT_URL,
    SPECIALED_URL,
    ACCREDITATION_URL,
    ACCREDITATION_BYSTANDARD_URL,
    EXAMS_URL,
    LOOKUPS_URL_CACHE_FILE,
    ENROL_URL_CACHE_FILE,
    TABLEENROLX_URL_CACHE_FILE,
    TEACHERCOUNT_URL_CACHE_FILE,
    TEACHERPD_URL_CACHE_FILE,
    TEACHERPDATTENDANCE_URL_CACHE_FILE,
    SCHOOLCOUNT_URL_CACHE_FILE,
    SPECIALED_URL_CACHE_FILE,
    ACCREDITATION_URL_CACHE_FILE,
    ACCREDITATION_BYSTANDARD_URL_CACHE_FILE,
    EXAMS_URL_CACHE_FILE,
)

# Global variables
df_enrol = pd.DataFrame()
df_tableenrolx = pd.DataFrame()
lookup_dict = {}  # <-- ⚡ Lookup values stored in a dictionary instead of DataFrame

auth_status = "❌ Not authenticated"
data_status = "❌ No data loaded"
verify_ssl = not DEBUG


def get_auth_token():
    """
    Retrieve an authentication token for accessing secure API endpoints.

    This function obtains an authentication token by interacting with an external
    authentication service. The token is required to authenticate subsequent API
    requests and should be cached for its valid duration to reduce redundant calls.

    Returns
    -------
    str
        A string representing the authentication token.

    Raises
    ------
    Exception
        If there is an error during the authentication process, such as network issues
        or invalid credentials.
    """
    payload = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    try:
        response = requests.post(
            LOGIN_URL, data=payload, headers=headers, verify=verify_ssl
        )
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token"), "✅ Authentication Successful!"
        else:
            return None, f"❌ Authentication Failed! Status {response.status_code}"
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def fetch_data(url, is_lookup=False, cache_file=None):
    """
    Fetch data from a specified URL with optional lookup and caching functionality.
    Now supports ETag-based conditional requests to minimize unnecessary downloads.

    Parameters
    ----------
    url : str
        The URL from which to retrieve the data.
    is_lookup : bool, optional
        If True, the data is expected to be a lookup table and will be processed accordingly.
        Default is False.
    cache_file : str or None, optional
        The file path to cache the retrieved data. If provided, the function will use
        the cache to avoid repeated downloads. Default is None.

    Returns
    -------
    data : pandas.DataFrame or dict
        The fetched data. If `is_lookup` is False, the data is returned as a pandas DataFrame.
        If `is_lookup` is True, the data is returned as a dictionary.

    Raises
    ------
    Exception
        Raises an exception if there is an error fetching the data from the URL or if caching fails.

    Notes
    -----
    This function supports caching to improve performance when the same data is requested multiple times.
    If an ETag is provided by the server, it is saved alongside the cache and used in an
    `If-None-Match` header on subsequent requests. If the server returns a 304 Not Modified,
    the cached data is used without re-downloading.
    """
    global auth_status, data_status  # Use global cache system

    token, new_auth_status = get_auth_token()
    auth_status = new_auth_status  # ✅ Update authentication status

    if not token:
        data_status = "❌ No valid token!"
        return {} if is_lookup else pd.DataFrame()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Origin": f"https://{BASE_URL}",
    }

    # ✅ Prepare ETag file path if cache_file is given
    etag_file = f"{cache_file}.etag" if cache_file else None
    cached_etag = None

    # ✅ If we have a cache and ETag saved, send it as If-None-Match
    if (
        cache_file
        and os.path.exists(cache_file)
        and etag_file
        and os.path.exists(etag_file)
    ):
        try:
            with open(etag_file, "r", encoding="utf-8") as f:
                cached_etag = f.read().strip() or None
        except Exception:
            cached_etag = None
        if cached_etag:
            headers["If-None-Match"] = cached_etag

    # --- Fetch from API ---
    response = requests.get(url, headers=headers, verify=verify_ssl)
    logging.debug(f"Response Code: {response.status_code}")
    logging.debug(f"Response Text (truncated): {response.text[:500]}")

    # ✅ If the server indicates no changes, load from cache
    if response.status_code == 304 and cache_file and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            data_status = "✅ 304 Not Modified — loaded from cache"
            return cached_data if is_lookup else pd.DataFrame(cached_data)
        except Exception as e:
            logging.error(f"Cache read error after 304: {e}")
            data_status = "❌ Cache read error after 304!"
            return {} if is_lookup else pd.DataFrame()

    # ✅ If data is fresh (HTTP 200), save to cache and update ETag if available
    if response.status_code == 200:
        try:
            data = response.json()
            if cache_file:
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    if etag_file:
                        new_etag = response.headers.get("ETag")
                        if new_etag:
                            with open(etag_file, "w", encoding="utf-8") as f:
                                f.write(new_etag)
                except Exception as e:
                    logging.warning(f"Cache write warning: {e}")
            data_status = "✅ Data retrieved successfully!"
            return data if is_lookup else pd.DataFrame(data)
        except ValueError as e:
            logging.error(f"JSON Parsing Error: {e}")
            data_status = "❌ JSON Parsing Error!"
            return {} if is_lookup else pd.DataFrame()

    # ⚠️ If fetch failed but cache exists, load stale data
    if cache_file and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            data_status = f"⚠️ {response.status_code} from server — loaded stale cache"
            return cached_data if is_lookup else pd.DataFrame(cached_data)
        except Exception as e:
            logging.error(f"Fallback cache read error: {e}")

    # ❌ No usable data
    data_status = f"❌ Data fetch failed! {response.status_code}"
    return {} if is_lookup else pd.DataFrame()


def get_warehouse_version():
    url = WAREHOUSE_VERSION_URL
    resp = requests.get(url, verify=verify_ssl)
    resp.raise_for_status()

    data = resp.json()
    if isinstance(data, list) and data:
        row = data[0]
    elif isinstance(data, dict):
        row = data
    else:
        return None

    return {"id": row.get("ID"), "datetime": row.get("versionDateTime")}


###############################################################################
# Lightweight, ETag-aware in-memory cache with accessors (background-friendly)
###############################################################################
class DataResource:
    """
    Maintain an in-memory DataFrame (or dict) that refreshes via ETag-aware fetches.

    Parameters
    ----------
    url : str
        Endpoint URL to fetch.
    cache_file : str
        JSON cache file path used by fetch_data (and its .etag sidecar).
    is_lookup : bool
        If True, this represents a lookup dict; otherwise a DataFrame.
    name : str
        Friendly name for logs.
    """

    def __init__(self, url, cache_file, is_lookup=False, name=""):
        self.url = url
        self.cache_file = cache_file
        self.is_lookup = is_lookup
        self.name = name or url
        self._obj = None

    def get(self):
        obj = fetch_data(self.url, is_lookup=self.is_lookup, cache_file=self.cache_file)
        # Only replace in-memory copy if we actually got something usable
        if self.is_lookup:
            if isinstance(obj, dict) and obj:
                self._obj = obj
        else:
            if isinstance(obj, pd.DataFrame) and not obj.empty:
                self._obj = obj
        return self._obj


###############################################################################
# Register resources and expose accessors
###############################################################################
res_lookup = DataResource(
    LOOKUPS_URL, LOOKUPS_URL_CACHE_FILE, is_lookup=True, name="lookups"
)
res_enrol = DataResource(ENROL_URL, ENROL_URL_CACHE_FILE, name="enrol")
res_tableenrolx = DataResource(
    TABLEENROLX_URL, TABLEENROLX_URL_CACHE_FILE, name="tableenrolx"
)
res_teachercount = DataResource(
    TEACHERCOUNT_URL, TEACHERCOUNT_URL_CACHE_FILE, name="teachercount"
)
res_teacherpdx = DataResource(
    TEACHERPD_URL, TEACHERPD_URL_CACHE_FILE, name="teacherpdx"
)
res_teacherpdattendancex = DataResource(
    TEACHERPDATTENDANCE_URL,
    TEACHERPDATTENDANCE_URL_CACHE_FILE,
    name="teacherpdattendancex",
)
res_schoolcount = DataResource(
    SCHOOLCOUNT_URL, SCHOOLCOUNT_URL_CACHE_FILE, name="schoolcount"
)
res_specialed = DataResource(
    SPECIALED_URL, SPECIALED_URL_CACHE_FILE, name="specialed"
)
res_accreditation = DataResource(
    ACCREDITATION_URL, ACCREDITATION_URL_CACHE_FILE, name="accreditation"
)
res_accreditation_bystandard = DataResource(
    ACCREDITATION_BYSTANDARD_URL, ACCREDITATION_BYSTANDARD_URL_CACHE_FILE, name="accreditation_bystandard"
)
res_exams = DataResource(
    EXAMS_URL, EXAMS_URL_CACHE_FILE, name="exams"
)


def get_lookup_dict():
    return res_lookup.get()


def get_df_enrol():
    return res_enrol.get()


def get_df_tableenrolx():
    return res_tableenrolx.get()


def get_df_teachercount() -> pd.DataFrame:
    df = res_teachercount.get()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not df.empty:
        # Ensure teacher count columns are numeric
        if "NumTeachersM" in df.columns:
            df["NumTeachersM"] = pd.to_numeric(df["NumTeachersM"], errors="coerce")
        if "NumTeachersF" in df.columns:
            df["NumTeachersF"] = pd.to_numeric(df["NumTeachersF"], errors="coerce")
        if "NumTeachersNA" in df.columns:
            df["NumTeachersNA"] = pd.to_numeric(df["NumTeachersNA"], errors="coerce")
        # Create a total teacher count column (if needed for other charts)
        if "TotalTeachers" not in df.columns:
            cols = [
                c
                for c in ["NumTeachersM", "NumTeachersF", "NumTeachersNA"]
                if c in df.columns
            ]
            if cols:
                df["TotalTeachers"] = df[cols].fillna(0).sum(axis=1)
    return df


def get_df_teacherpdx():
    return res_teacherpdx.get()


def get_df_teacherpdattendancex():
    return res_teacherpdattendancex.get()


def get_df_schoolcount() -> pd.DataFrame:
    df = res_schoolcount.get()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not df.empty:
        # Ensure NumSchools is numeric
        if "NumSchools" in df.columns:
            df["NumSchools"] = pd.to_numeric(df["NumSchools"], errors="coerce")
    return df


def get_df_specialed() -> pd.DataFrame:
    df = res_specialed.get()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not df.empty:
        # Ensure count columns are numeric (M, F for male/female counts)
        for col in ["M", "F", "Num"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_df_accreditation() -> pd.DataFrame:
    df = res_accreditation.get()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not df.empty:
        # Ensure Num column is numeric
        if "Num" in df.columns:
            df["Num"] = pd.to_numeric(df["Num"], errors="coerce")
    return df


def get_df_accreditation_bystandard() -> pd.DataFrame:
    df = res_accreditation_bystandard.get()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not df.empty:
        # Ensure Num column is numeric
        if "Num" in df.columns:
            df["Num"] = pd.to_numeric(df["Num"], errors="coerce")
        if "NumInYear" in df.columns:
            df["NumInYear"] = pd.to_numeric(df["NumInYear"], errors="coerce")
    return df


def get_df_exams() -> pd.DataFrame:
    df = res_exams.get()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not df.empty:
        # Ensure candidateCount column is numeric
        if "candidateCount" in df.columns:
            df["candidateCount"] = pd.to_numeric(df["candidateCount"], errors="coerce")
    return df


###############################################################################
# Background refresh (used by app.py interval)
###############################################################################
def background_refresh_all():
    """
    Trigger ETag-aware refresh of all resources. Safe to call frequently.
    """
    try:
        print("Refreshing data in the background...")
        _ = res_lookup.get()
        _ = res_enrol.get()
        _ = res_tableenrolx.get()
        _ = get_df_teachercount()
        _ = res_teacherpdx.get()
        _ = res_teacherpdattendancex.get()
        _ = get_df_schoolcount()
        _ = get_df_specialed()
        _ = get_df_accreditation()
        _ = get_df_accreditation_bystandard()
        _ = get_df_exams()
    except Exception as e:
        logging.warning(f"Background refresh warning: {e}")


###############################################################################
# Helper: get latest year with data
###############################################################################
def get_latest_year_with_data(df, year_column="SurveyYear", fallback_year=2024):
    """
    Find the most recent year that has data in the given DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to check for data.
    year_column : str
        The column name containing year values.
    fallback_year : int
        The year to return if no data is found.

    Returns
    -------
    int
        The latest year that has data, or fallback_year if no data exists.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return fallback_year
    if year_column not in df.columns:
        return fallback_year
    years = df[year_column].dropna().unique()
    if len(years) == 0:
        return fallback_year
    return int(max(years))


###############################################################################
# Warm-up: ensure lookups and vocab are available as module-level constants
###############################################################################
# Fetch and store lookups once so that vocab_* constants are defined at import time
lookup_dict = get_lookup_dict() or {}

# Setup lookups
# Expected format for lookup_dict["districts"]:
# [{"C": "XYZ", "N": "Friendly Name"}, ...]
district_lookup = {item["C"]: item["N"] for item in lookup_dict.get("districts", [])}
region_lookup = {item["C"]: item["N"] for item in lookup_dict.get("regions", [])}
authorities_lookup = {
    item["C"]: item["N"] for item in lookup_dict.get("authorities", [])
}
authoritygovts_lookup = {
    item["C"]: item["N"] for item in lookup_dict.get("authorityGovts", [])
}
schooltypes_lookup = {
    item["C"]: item["N"] for item in lookup_dict.get("schoolTypes", [])
}
vocab_lookup = {item["C"]: item["N"] for item in lookup_dict.get("vocab", [])}

# Get the localized terms for convenience
vocab_district = vocab_lookup.get("District", "District")
vocab_region = vocab_lookup.get("Region", "Region")
vocab_authority = vocab_lookup.get("Authority", "Authority")
vocab_authoritygovt = vocab_lookup.get("Authority Govt", "Authority Group")
vocab_schooltype = vocab_lookup.get("School Type", "School Type")

###############################################################################
# Debugging logs
###############################################################################
if DEBUG:
    # print("lookup_dict keys preview:")
    # for k in list(lookup_dict.keys())[:3]:
    #    values = lookup_dict[k]
    #    print(f"  {k}: {len(values) if isinstance(values, list) else 'n/a'} items")
    #    if isinstance(values, list):
    #        pprint(values[:2])  # Show first 2 entries only
    #    else:
    #        pprint(values)
    # print("authorityGovt lookups:", authoritygovts_lookup)

    # Show heads for a quick sanity check
    # _enrol = get_df_enrol()
    # _table = get_df_tableenrolx()
    # _tc = get_df_teachercount()
    # _tpdx = get_df_teacherpdx()
    # _tpda = get_df_teacherpdattendancex()

    # print("df_enrol (head):", None if _enrol is None else _enrol.head())
    # print("df_tableenrolx (head):", None if _table is None else _table.head())
    # print("df_teachercount (head):", None if _tc is None else _tc.head())
    # if _tc is not None:
    #     print("df_teachercount (info):", None if _tc is None else _tc.info())
    # print("df_teacherpdx (head):", None if _tpdx is None else _tpdx.head())
    # print("df_teacherpdattendancex (head):", None if _tpda is None else _tpda.head())
    # print("End of api.py debug output")
    pass
