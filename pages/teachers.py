import dash
from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/teachers", name="Teachers")

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3("Teachers Dashboard")),
    ], className="m-1"),

    dbc.Row([
        dbc.Col(html.P("Coming soon...")),
    ], className="m-1"),
], fluid=True)
