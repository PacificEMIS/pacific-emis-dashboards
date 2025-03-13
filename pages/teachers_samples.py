import numpy as np
import math
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from dash import dash_table
import pandas as pd
import plotly.express as px

# Import data and lookup dictionary from the API module
from services.api import (
    df_teachercount, 
    lookup_dict, 
    district_lookup, 
    region_lookup, 
    schooltypes_lookup,
    vocab_region, 
    vocab_district,
    vocab_schooltype
)

# Register this page as the Samples page under Teachers
dash.register_page(__name__, path="/teachers/samples", name="Teachers Samples")

# Filters
# Extract survey years from lookup dictionary (assuming it contains a "surveyYears" key)
survey_years = lookup_dict.get("surveyYears", [])

print("survey_years", survey_years)

# Create dropdown options using 'N' for display and 'C' for value
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]

# Determine the default value: the highest available year
default_year = max([int(item['C']) for item in survey_years], default=2024) 

# --- Layout ---
def teachers_sample_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers Samples (Experiment here)")),
        ], className="m-1"),

        dbc.Row([
            dbc.Col(html.P("A page meant mostly for experimenting.")),
        ], className="m-1"),
        
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="year-filter",
                    options=year_options,
                    value=default_year,
                    clearable=False,
                    style={'width': '200px'}
                ),
                className="m-1"
            )
        ], className="m-1"),
        
        dbc.Row([
            dbc.Col(dcc.Graph(id="sample-chart"), md=6, xs=12, className="p-3"),
        ], className="m-1"),
                
        dbc.Row([
            dbc.Col(dash_table.DataTable(
                id="teacher-data-table",
                columns=[{"name": col, "id": col} for col in df_teachercount.columns],
                data=df_teachercount.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left"},
            ), md=12, xs=12, className="p-3")
        ], className="m-1"),
    ], fluid=True)

@callback(
    Output(component_id="sample-chart", component_property="figure"),
    Input(component_id="year-filter", component_property="value")
)
def update_charts(selected_year):
    if selected_year is None:
        return {}

    # Filter data for the selected survey year
    filtered = df_teachercount[df_teachercount['SurveyYear'] == selected_year].copy()

    ###########################################################################
    # Teacher Count by Age Groups (Diverging Horizontal Bar Chart)
    # Female bars extend to the left (negative) and Male bars extend to the right (positive)
    ###########################################################################
    grouped_age = filtered.groupby('AgeGroup')[['NumTeachersF', 'NumTeachersM']].sum().reset_index()
    grouped_age = grouped_age.rename(columns={'NumTeachersF': 'Female', 'NumTeachersM': 'Male'})
    grouped_age['Female'] = -grouped_age['Female']  # Negative for diverging bar chart

    # Create the diverging bar chart as before.
    fig_age = px.bar(
        grouped_age,
        y="AgeGroup",
        x=["Female", "Male"],
        orientation='h',
        title=f"Teacher Count by Age Groups for {selected_year}",
        labels={"AgeGroup": "Age Group", "value": "Teacher Count", "variable": "Gender"}
    )

    # Determine the maximum absolute value to set symmetric ticks.
    max_val = max(grouped_age['Male'].max(), abs(grouped_age['Female'].min()))
    rounded_max = math.ceil(max_val / 50) * 50

    # Set the desired number of ticks (more ticks for finer granularity)
    num_ticks = 11

    # Generate tick positions using the rounded maximum value
    tick_vals = np.linspace(-rounded_max, rounded_max, num=num_ticks)
    tick_text = [str(int(abs(val))) for val in tick_vals]

    # Update the chart with a symmetric x-axis and custom ticks
    fig_age.update_layout(xaxis=dict(range=[-rounded_max, rounded_max]))
    fig_age.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

    
    return fig_age

layout = teachers_sample_layout()
