import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
import pandas as pd
import plotly.express as px

# Import data and figures from the API module
from services.api import get_df_enrol, auth_status, data_status
df_enrol = get_df_enrol()

# Register this page as the Trends page
dash.register_page(__name__, path="/students/samples", name="Students Samples")

# --- Data Processing and Visualization ---
if not df_enrol.empty:
    df_grouped = df_enrol.groupby("ClassLevel")["Enrol"].sum().reset_index()
    fig_enrol = px.bar(
        df_grouped, x="ClassLevel", y="Enrol",
        title="Total Enrollment by Class Level",
        labels={"ClassLevel": "Class Level", "Enrol": "Total Enrollment"},
        color="ClassLevel"
    )

    df_gender = df_enrol.groupby(["ClassLevel", "GenderCode"])["Enrol"].sum().reset_index()
    fig_gender = px.bar(
        df_gender, x="ClassLevel", y="Enrol", color="GenderCode",
        barmode="group", title="Enrollment by Class Level and Gender",
        labels={"ClassLevel": "Class Level", "Enrol": "Total Enrollment", "GenderCode": "Gender"}
    )

    if "SurveyYear" in df_enrol and df_enrol["SurveyYear"].nunique() > 1:
        recent_years = sorted(df_enrol["SurveyYear"].unique(), reverse=True)[:5]
        df_yearly = df_enrol[df_enrol["SurveyYear"].isin(recent_years)]
        df_yearly = df_yearly.groupby(["SurveyYear", "ClassLevel"])["Enrol"].sum().reset_index()
        fig_yearly = px.line(
            df_yearly, x="SurveyYear", y="Enrol", color="ClassLevel",
            title="Enrollment Trends Over Time (Last 5 Years)",
            labels={"SurveyYear": "Year", "Enrol": "Total Enrollment", "ClassLevel": "Class Level"}
        )
    else:
        df_yearly = pd.DataFrame()
        fig_yearly = None

layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Students Samples (Experiment here)")),
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