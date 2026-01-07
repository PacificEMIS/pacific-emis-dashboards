import dash
from dash import html
import dash_bootstrap_components as dbc

from config import CONTEXT
from services.connection_status import connection_registry

# Register this page as the Dashboard page
dash.register_page(__name__, path="/", name="Home")


def build_connection_alerts():
    """Build alert components for any connection errors."""
    errors = connection_registry.get_all_errors()
    if not errors:
        return None

    alert_items = []
    for error in errors:
        icon = "bi bi-database-x" if error.source_type == "sql" else "bi bi-cloud-slash"
        alert_items.append(
            html.Li([
                html.I(className=f"{icon} me-2"),
                html.Strong(f"{error.name}: "),
                error.error_message or "Connection failed",
            ])
        )

    return dbc.Alert(
        [
            html.H5([
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                "Data Connection Issues"
            ], className="alert-heading"),
            html.P(
                "The following data connections are currently unavailable. "
                "Some dashboard features may be limited or show incomplete data."
            ),
            html.Hr(),
            html.Ul(alert_items, className="mb-0"),
        ],
        color="warning",
        className="mb-4",
    )


def layout():
    """Generate layout dynamically to reflect current connection status."""
    connection_alert = build_connection_alerts()

    content = [
        dbc.Row([
            dbc.Col(html.H1(f"Welcome to the {CONTEXT.upper()} Data Portal")),
        ], className="m-1"),
    ]

    # Add connection alert if there are errors
    if connection_alert:
        content.append(dbc.Row([dbc.Col(connection_alert)], className="m-1"))

    content.extend([
        dbc.Row([
            dbc.Col(html.P(f"""Welcome to our new online dashboard application! Designed with the needs
                            of our stakeholders in mind, this comprehensive analysis platform allows you to
                            effortlessly view and monitor key metrics of interest. While the Pacific EMIS
                            (of which {CONTEXT.upper()} is based on) offers
                            a range of pre-defined, flexible dashboards, we understand that adding new charts
                            and analyses can sometimes be complex and time consuming. This new data portal
                            serves as the go-to location for real time data, collaboration on the required types of
                            analysis by various stakeholders.
                            We are excited for you to explore the capabilities of this powerful tool!""")),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.H5("Key Highlights:")),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.Ul([
                html.Li("Access interactive dashboards based on a rapid application development framework. In other words, you have an idea, let's explore it quickly!"),
                html.Li("Visualize trends in enrollment, staffing, performance, and infrastructure."),
                html.Li("Download tables and charts for reporting and presentations."),
                html.Li("Explore timely data from the most recent school census."),
                html.Li("Access easily from anywhere, no login required."),
                html.Li("More dashboard features are being added over time."),
            ])),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.H5("Key Highlights Coming Soon:")),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.Ul([
                html.Li("Downloadable live Excel workbooks (that can refresh with latest data) containing the data for further data analysis."),
                html.Li("Links to data related documentation (e.g. User Guides, Policicy, Standards and Procedures)."),
                html.Li("Data Publications."),
            ])),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.H5("Notes:")),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.Ul([
                html.Li("This platform is still under active development. Some features may be rough around the edges or occasionally break — thank you for your patience."),
                html.Li("Maps rely on accurate GPS coordinates to function properly. Schools without known coordinates will appear at a default location (usually centered in the main lagoon) until updated."),
            ])),
        ], className="m-1"),
    ])

    return dbc.Container(content, fluid=True)
