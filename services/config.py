import os

# Credentials
# It’s a good idea to also allow environment variable overrides.
USERNAME = os.getenv("KEMIS_USERNAME", "example@pacific-emis.org")
PASSWORD = os.getenv("KEMIS_PASSWORD", "password")

# Base API URL
BASE_URL = os.getenv("KEMIS_BASE_URL", "https://kemis-test.pacific-emis.org")

# Login endpoint
LOGIN_URL = f"{BASE_URL}/api/token"

# REST API endpoints
LOOKUPS_URL = f"{BASE_URL}/api/lookups/collection/core"
ENROL_URL = f"{BASE_URL}/api/warehouse/enrol/school"
TABLEENROLX_URL = f"{BASE_URL}/api/warehouse/tableEnrolX/r"

# Cache file paths
LOOKUPS_URL_CACHE_FILE = os.getenv("LOOKUPS_URL_CACHE_FILE", "cached_lookups_data.json")
ENROL_URL_CACHE_FILE = os.getenv("ENROL_URL_CACHE_FILE", "cached_enrol_data.json")
TABLEENROLX_URL_CACHE_FILE = os.getenv("TABLEENROLX_URL_CACHE_FILE", "cached_tableenrolx_data.json")
