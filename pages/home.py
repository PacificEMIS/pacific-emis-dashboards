import dash
from dash import html
import dash_bootstrap_components as dbc

from config import CONTEXT

# Register this page as the Dashboard page
dash.register_page(__name__, path="/", name="Home")

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1(f"Welcome to the {CONTEXT.upper()} Online Dashboards")),
    ], className="m-1"),

    dbc.Row([
        dbc.Col(html.P(f"""Welcome to our new online dashboard application! Designed with the needs
                        of our stakeholders in mind, this comprehensive analysis platform allows you to 
                       effortlessly view and monitor key metrics of interest. While the Pacific EMIS 
                       (of which {CONTEXT.upper()} is based on) offers
                        a range of pre-defined, flexible dashboards, we understand that adding new charts 
                       and analyses can sometimes be complex. Our goal is to simplify this process, 
                       providing you with an intuitive and user-friendly interface that empowers you 
                       to customize your data visualizations and gain valuable insights at a glance. 
                       We are excited for you to explore the capabilities of this powerful tool!""")),
    ], className="m-1"),
], fluid=True)
