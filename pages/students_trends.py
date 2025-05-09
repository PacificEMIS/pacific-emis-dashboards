import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
import pandas as pd
import plotly.express as px

# Import data and figures from the API module
from services.api import df_enrol, auth_status, data_status

# Register this page as the Trends page
dash.register_page(__name__, path="/students/trends", name="Students Trends")

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Students Trends")),
    ], className="m-1"),

    dbc.Row([
        dbc.Col(html.P("Coming next...")),
    ], className="m-1"),
], fluid=True)