import os

DEBUG = True

# Deployment mode: use environment variable `EMIS_MODE` to override.
# Accepted values: "Production" (default) or "Testing"
MODE = os.getenv("EMIS_MODE", "Production")

# Credentials
# It’s a good idea to also allow environment variable overrides.
USERNAME = os.getenv("EMIS_USERNAME", "user@pacific-emis.org")
PASSWORD = os.getenv("EMIS_PASSWORD", "password")
CONTEXT = "pacemis"  # Need to be inline with the BASE_URL below

# Base API URL
BASE_URL = os.getenv("EMIS_BASE_URL", "https://some-emis-url.pacific-emis.org")

# Login endpoint
LOGIN_URL = f"{BASE_URL}/api/token"

# REST API endpoints
WAREHOUSE_VERSION_URL = f"{BASE_URL}/api/warehouse/version"
LOOKUPS_URL = f"{BASE_URL}/api/lookups/collection/core"
ENROL_URL = f"{BASE_URL}/api/warehouse/enrol/school"
TABLEENROLX_URL = f"{BASE_URL}/api/warehouse/tableEnrolX/r"
TEACHERCOUNT_URL = f"{BASE_URL}/api/warehouse/teachercount/school?report"
TEACHERPD_URL = f"{BASE_URL}/api/warehouse/teacherpd/school"
TEACHERPDATTENDANCE_URL = f"{BASE_URL}/api/warehouse/teacherpdattendance/school"
SCHOOLCOUNT_URL = f"{BASE_URL}/api/warehouse/schoolcount"
SPECIALED_URL = f"{BASE_URL}/api/warehouse/specialeducation"
ACCREDITATION_URL = f"{BASE_URL}/api/warehouse/accreditations"
ACCREDITATION_BYSTANDARD_URL = (
    f"{BASE_URL}/api/warehouse/accreditations/nation?byStandard=true"
)
EXAMS_URL = f"{BASE_URL}/api/warehouse/exams/tabledimension"

# Cache file paths
LOOKUPS_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_lookups_data.json"
ENROL_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_enrol_data.json"
TABLEENROLX_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_tableenrolx_data.json"
TEACHERCOUNT_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_teachercount_data.json"
TEACHERPD_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_teacherpd_data.json"
TEACHERPDATTENDANCE_URL_CACHE_FILE = (
    f"data\\{CONTEXT}-cached_teacherpdattendance_data.json"
)
SCHOOLCOUNT_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_schoolcount_data.json"
SPECIALED_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_specialed_data.json"
ACCREDITATION_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_accreditation_data.json"
ACCREDITATION_BYSTANDARD_URL_CACHE_FILE = (
    f"data\\{CONTEXT}-cached_accreditation_bystandard_data.json"
)
EXAMS_URL_CACHE_FILE = f"data\\{CONTEXT}-cached_exams_data.json"

# Direct SQL server access configuration
SQL_SERVER = os.getenv("SQL_SERVER", "SERVERNAME")
SQL_DATABASE = os.getenv("SQL_DATABASE", "DBNAME")
SQL_USER = os.getenv("SQL_USER", "user")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "password")
SQL_DRIVER = "ODBC Driver 18 for SQL Server"

# Dashboard modules configuration
# Set enabled to True/False to show/hide menu sections and items
# Each country deployment can customize this based on available data
DASHBOARDS = {
    "exams": {
        "enabled": True,
        "label": "Exams",
        "items": {
            "exams": {"enabled": True, "label": "Exams", "path": "/exams/exams"},
            "standards": {
                "enabled": True,
                "label": "Standards",
                "path": "/exams/standards",
            },
            "benchmarks": {
                "enabled": True,
                "label": "Benchmarks",
                "path": "/exams/benchmarks",
            },
            "indicators": {
                "enabled": True,
                "label": "Indicators",
                "path": "/exams/indicators",
            },
        },
    },
    "schools": {
        "enabled": True,
        "label": "Schools",
        "items": {
            "overview": {
                "enabled": True,
                "label": "Overview",
                "path": "/schools/overview",
            },
        },
    },
    "students": {
        "enabled": True,
        "label": "Students",
        "items": {
            "overview": {
                "enabled": True,
                "label": "Overview",
                "path": "/students/overview",
            },
        },
    },
    "specialed": {
        "enabled": True,
        "label": "Special Education",
        "items": {
            "overview": {
                "enabled": True,
                "label": "Overview",
                "path": "/specialed/overview",
            },
        },
    },
    "teachers": {
        "enabled": True,
        "label": "Teachers",
        "items": {
            "overview": {
                "enabled": True,
                "label": "Overview",
                "path": "/teachers/overview",
            },
        },
    },
    "teacherpd": {
        "enabled": True,
        "label": "Teacher PD",
        "items": {
            "overview": {
                "enabled": True,
                "label": "Overview",
                "path": "/teacherpd/overview",
            },
            "attendants": {
                "enabled": True,
                "label": "Attendants",
                "path": "/teacherpd/attendants",
            },
            "attendance": {
                "enabled": True,
                "label": "Attendance",
                "path": "/teacherpd/attendance",
            },
        },
    },
    "schoolaccreditation": {
        "enabled": True,
        "label": "School Accreditation",
        "items": {
            "overview": {
                "enabled": True,
                "label": "Overview",
                "path": "/schoolaccreditation/overview",
            },
        },
    },
    "audit": {
        "enabled": True,
        "label": "Audit",
        "items": {
            "annual-census": {
                "enabled": True,
                "label": "Annual Census",
                "path": "/audit/annual-census",
            },
        },
    },
}
