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
                        and analyses can sometimes be complex and time consuming. Our goal is to simplify this process, 
                        providing you with an intuitive and user-friendly interface that empowers you 
                        to customize your data visualizations and gain valuable insights at a glance. 
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
        dbc.Col(html.H5("Notes:")),
    ], className="m-1"),

    dbc.Row([
        dbc.Col(html.Ul([
            html.Li("This platform is still under active development. Some features may be rough around the edges or occasionally break — thank you for your patience."),
            html.Li("Maps rely on accurate GPS coordinates to function properly. Schools without known coordinates will appear at a default location (usually centered in the main lagoon) until updated."),
        ])),
    ], className="m-1"),

], fluid=True)
