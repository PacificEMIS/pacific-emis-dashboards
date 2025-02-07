import os
import json
import logging
import requests
import pandas as pd
import plotly.express as px

from .config import USERNAME, PASSWORD, BASE_URL, LOGIN_URL, LOOKUPS_URL, ENROL_URL, TABLEENROLX_URL, LOOKUPS_URL_CACHE_FILE, ENROL_URL_CACHE_FILE, TABLEENROLX_URL_CACHE_FILE

# Global variables
df_enrol = pd.DataFrame()
df_tableenrolx = pd.DataFrame()
lookup_dict = {}  # <-- ⚡ Lookup values stored in a dictionary instead of DataFrame

auth_status = "❌ Not authenticated"
data_status = "❌ No data loaded"

# 📡 Function to Authenticate and Get Token
def get_auth_token():
    payload = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    response = requests.post(LOGIN_URL, data=payload, headers=headers)
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token"), "✅ Authentication Successful!"
    else:
        return None, "❌ Authentication Failed! Check credentials."

# 🔄 Function to Fetch Data from API with Bearer Token (Runs Once)
def fetch_data(url, is_lookup=False, cache_file=None):
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
    response = requests.get(url, headers=headers)
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

# ✅ **Fetch and store data at startup**
lookup_dict = fetch_data(LOOKUPS_URL, is_lookup=True, cache_file=LOOKUPS_URL_CACHE_FILE)  # ✅ Stored as dictionary
df_enrol = fetch_data(ENROL_URL, is_lookup=False, cache_file=ENROL_URL_CACHE_FILE)  # ✅ Stored as DataFrame
df_tableenrolx = fetch_data(TABLEENROLX_URL, is_lookup=False, cache_file=TABLEENROLX_URL_CACHE_FILE)  # ✅ Stored as DataFrame

# ✅ Debugging logs
if True:  # Replace with a condition if needed
    print("lookup_dict (first keys):", list(lookup_dict.keys())[:5])  # Display first few keys
    print("df_enrol (head):", df_enrol.head())
    print("df_tableenrolx (head):", df_tableenrolx.head())

# --- Data Processing and Visualization ---
if not df_enrol.empty:
    df_grouped = df_enrol.groupby("ClassLevel")["Enrol"].sum().reset_index()
    fig_enrol = px.bar(
        df_grouped, x="ClassLevel", y="Enrol",
        title="Total Enrollment by Class Level",
        labels={"ClassLevel": "Class Level", "Enrol": "Total Enrollment"},
        color="ClassLevel"
    )

    df_gender = df_enrol.groupby(["ClassLevel", "GenderCode"])["Enrol"].sum().reset_index()
    fig_gender = px.bar(
        df_gender, x="ClassLevel", y="Enrol", color="GenderCode",
        barmode="group", title="Enrollment by Class Level and Gender",
        labels={"ClassLevel": "Class Level", "Enrol": "Total Enrollment", "GenderCode": "Gender"}
    )

    if "SurveyYear" in df_enrol and df_enrol["SurveyYear"].nunique() > 1:
        recent_years = sorted(df_enrol["SurveyYear"].unique(), reverse=True)[:5]
        df_yearly = df_enrol[df_enrol["SurveyYear"].isin(recent_years)]
        df_yearly = df_yearly.groupby(["SurveyYear", "ClassLevel"])["Enrol"].sum().reset_index()
        fig_yearly = px.line(
            df_yearly, x="SurveyYear", y="Enrol", color="ClassLevel",
            title="Enrollment Trends Over Time (Last 5 Years)",
            labels={"SurveyYear": "Year", "Enrol": "Total Enrollment", "ClassLevel": "Class Level"}
        )
    else:
        df_yearly = pd.DataFrame()
        fig_yearly = None
