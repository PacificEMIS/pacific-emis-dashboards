import os

DEBUG = True

# Credentials
# It’s a good idea to also allow environment variable overrides.
USERNAME = os.getenv("EMIS_USERNAME", "user@pacific-emis.org")
PASSWORD = os.getenv("EMIS_PASSWORD", "password")
CONTEXT = "pacemis" # Need to be inline with the BASE_URL below

# Base API URL
BASE_URL = os.getenv("EMIS_BASE_URL", "https://some-emis-url.pacific-emis.org")

# Login endpoint
LOGIN_URL = f"{BASE_URL}/api/token"

# REST API endpoints
LOOKUPS_URL = f"{BASE_URL}/api/lookups/collection/core"
ENROL_URL = f"{BASE_URL}/api/warehouse/enrol/school"
TABLEENROLX_URL = f"{BASE_URL}/api/warehouse/tableEnrolX/r"
TEACHERCOUNT_URL = f"{BASE_URL}/api/warehouse/teachercountx"
TEACHERCPDX_URL = f"{BASE_URL}/api/warehouse/teachercpd/x"

# Cache file paths
LOOKUPS_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_lookups_data.json"
ENROL_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_enrol_data.json"
TABLEENROLX_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_tableenrolx_data.json"
TEACHERCOUNT_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_teachercount_data.json"
TEACHERCPDX_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_teachercpdx_data.json"