import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table

# Import data and figures from the API module
from services.api import df_enrol, df_yearly, df_gender, auth_status, data_status, fig_enrol, fig_gender, fig_yearly

# Register this page as the Trends page
dash.register_page(__name__, path="/samples", name="Samples")

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H3("Sample Dashboard Components")),
    ], className="m-1"),

    dbc.Row([
        dbc.Col(html.P("A page meant mostly for experimenting.")),
    ], className="m-1"),
    
    dbc.Row([    
        dbc.Col(dcc.Graph(id="enrollment-graph", figure=fig_enrol), md=4, xs=12, className="p-3"),
        dbc.Col(dcc.Graph(id="enrollment-gender-graph", figure=fig_gender), md=4, xs=12, className="p-3"),
        dbc.Col(dcc.Graph(id="enrollment-yearly-graph", figure=fig_yearly), md=4, xs=12, className="p-3"),
    ], className="m-1"),

    dbc.Row([
        
        # 📊 Display Data Table (Pretty Like Jupyter)
        dbc.Col(dash_table.DataTable(
            id="enrollment-data-table",
            columns=[{"name": col, "id": col} for col in df_enrol.columns],
            data=df_enrol.to_dict("records"),  # Convert DataFrame to Dash format
            page_size=10,
            style_table={"overflowX": "auto"},  # Allow horizontal scrolling
            style_cell={"textAlign": "left"},
        ), md=6, xs=12, className="p-3"),

        dbc.Col(dash_table.DataTable(
            id="enrollment-gender-table",
            columns=[{"name": col, "id": col} for col in df_gender.columns],
            data=df_enrol.to_dict("records"),  # Convert DataFrame to Dash format
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        ), md=6, xs=12, className="p-3"),

        dbc.Col(dash_table.DataTable(
            id="enrollment-yearly-table",
            columns=[{"name": col, "id": col} for col in df_yearly.columns],
            data=df_enrol.to_dict("records"),  # Convert DataFrame to Dash format
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        ), md=6, xs=12, className="p-3")

    ], className="m-1"),

    # Some status stuff
    dbc.Row([
        dbc.Col(html.P(auth_status, style={"font-weight": "bold"}), md=6, xs=12, className="p-3"),
        dbc.Col(html.P(data_status, style={"font-weight": "bold"}), md=6, xs=12, className="p-3"),
    ], className="m-1")
], fluid=True)