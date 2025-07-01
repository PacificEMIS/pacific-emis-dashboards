import os
import json
import logging
import requests
import pandas as pd
import plotly.express as px
from pprint import pprint

from config import (
    DEBUG, USERNAME, PASSWORD, BASE_URL, LOGIN_URL, 
    LOOKUPS_URL, ENROL_URL, TABLEENROLX_URL, 
    TEACHERCOUNT_URL, TEACHERCPDX_URL, 
    LOOKUPS_URL_CACHE_FILE, ENROL_URL_CACHE_FILE, TABLEENROLX_URL_CACHE_FILE, 
    TEACHERCOUNT_URL_CACHE_FILE, TEACHERCPDX_URL_CACHE_FILE
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
    payload = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    try:
        response = requests.post(LOGIN_URL, data=payload, headers=headers, verify=verify_ssl)
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
    """
    global auth_status, data_status  # Use global cache system

    # ✅ Use cache if available
    if cache_file and os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        data_status = "✅ Loaded from cache (no API call)"
        auth_status = "✅ Using previous authentication (no new login)"
        logging.info(f"Using cached data for {url}")
        return cached_data if is_lookup else pd.DataFrame(cached_data)

    token, new_auth_status = get_auth_token()
    auth_status = new_auth_status  # ✅ Update authentication status

    if not token:
        data_status = "❌ No valid token!"
        return {} if is_lookup else pd.DataFrame()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Origin": f"https://{BASE_URL}"
    }
    response = requests.get(url, headers=headers, verify=verify_ssl)
    logging.debug(f"Response Code: {response.status_code}")
    logging.debug(f"Response Text: {response.text}")

    if response.status_code == 200:
        try:
            data = response.json()
            if cache_file:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)  # ✅ Save data to cache
            data_status = "✅ Data retrieved successfully!"
            return data if is_lookup else pd.DataFrame(data)
        except ValueError as e:
            logging.error(f"JSON Parsing Error: {e}")
            data_status = "❌ JSON Parsing Error!"
            return {} if is_lookup else pd.DataFrame()
    else:
        data_status = f"❌ Data fetch failed! {response.status_code}"
        return {} if is_lookup else pd.DataFrame()

###############################################################################
# Fetch and store data at startup
###############################################################################
lookup_dict = fetch_data(LOOKUPS_URL, is_lookup=True, cache_file=LOOKUPS_URL_CACHE_FILE)
df_enrol = fetch_data(ENROL_URL, is_lookup=False, cache_file=ENROL_URL_CACHE_FILE)
df_tableenrolx = fetch_data(TABLEENROLX_URL, is_lookup=False, cache_file=TABLEENROLX_URL_CACHE_FILE)

df_teachercount = fetch_data(TEACHERCOUNT_URL, is_lookup=False, cache_file=TEACHERCOUNT_URL_CACHE_FILE)
# --- Data Processing ---
if not df_teachercount.empty:
    # Ensure teacher count columns are numeric
    df_teachercount['NumTeachersM'] = pd.to_numeric(df_teachercount['NumTeachersM'], errors='coerce')
    df_teachercount['NumTeachersF'] = pd.to_numeric(df_teachercount['NumTeachersF'], errors='coerce')
    df_teachercount['NumTeachersNA'] = pd.to_numeric(df_teachercount['NumTeachersNA'], errors='coerce')
    # Create a total teacher count column (if needed for other charts)
    df_teachercount['TotalTeachers'] = df_teachercount['NumTeachersM'].fillna(0) + df_teachercount['NumTeachersF'].fillna(0) + df_teachercount['NumTeachersNA'].fillna(0)

df_teachercpdx = fetch_data(TEACHERCPDX_URL, is_lookup=False, cache_file=TEACHERCPDX_URL_CACHE_FILE)

###############################################################################
# Setup lookups
###############################################################################
# Expected format for lookup_dict["districts"]:
# [{"C": "XYZ", "N": "Friendly Name"}, ...]
district_lookup = {item["C"]: item["N"] for item in lookup_dict.get("districts", [])}
region_lookup = {item["C"]: item["N"] for item in lookup_dict.get("regions", [])}
authorities_lookup = {item["C"]: item["N"] for item in lookup_dict.get("authorities", [])}
authoritygovts_lookup = {item["C"]: item["N"] for item in lookup_dict.get("authorityGovts", [])}
schooltypes_lookup = {item["C"]: item["N"] for item in lookup_dict.get("schoolTypes", [])}
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
if True:  # Replace with a condition if needed
    print("lookup_dict keys preview:")
    for k in list(lookup_dict.keys())[:3]:
        values = lookup_dict[k]
        print(f"  {k}: {len(values)} items")
        if isinstance(values, list):
            pprint(values[:2])  # Show first 2 entries only
        else:
            pprint(values)
    #pprint(dict(list(lookup_dict.items())[:3]))
    print("authorityGovt lookups:", authoritygovts_lookup)
    print("df_enrol (head):", df_enrol.head())
    print("df_tableenrolx (head):", df_tableenrolx.head())
    print("df_teachercount (head):", df_teachercount.head())
    print("df_teachercount (info):", df_teachercount.info())
    print("End of api.py debug output")