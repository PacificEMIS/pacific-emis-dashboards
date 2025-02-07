import dash
from dash import html
import dash_bootstrap_components as dbc

# Register this page as the Dashboard page
dash.register_page(__name__, path="/", name="Dashboard")

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3("At A Glance Dashboard")),
    ], className="m-1"),

    dbc.Row([
        dbc.Col(html.P("Coming soon...")),
    ], className="m-1"),
], fluid=True)
