import numpy as np
import math
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from tabulate import tabulate
from dash.dependencies import Input, Output

# Import data and lookup dictionary from the API module
from services.api import (
    get_df_teachercount,
    district_lookup,
    region_lookup,
    authorities_lookup,
    authoritygovts_lookup,
    schooltypes_lookup,
    vocab_district,
    vocab_region,
    vocab_authority,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,    
)
df_teachercount = get_df_teachercount()

dash.register_page(__name__, path="/teachers/overview", name="Teachers Overview")

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024) 

# ✅ Define Layout inside a Function
def teachers_overview_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers Overview"), width=12, className="m-1"),
        ]),        
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
        ]),
        # No data message + spinner host centered in a reserved spacer (prevents footer jump)
        dcc.Loading(
            id="teachers-overview-top-loading",
            type="default",
            children=html.Div(
                id="teachers-overview-loading-spacer",
                style={"minHeight": "50vh"},
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="teachers-overview-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),
        # Charts hidden by default; shown by callback when ready
        html.Div(id="teachers-overview-content", style={"display": "none"}, children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id="teachers-district-gender-bar-chart"), md=12, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="teachers-region-gender-bar-chart"), md=4, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="teachers-authgovt-pie-chart"), md=4, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="teachers-auth-bar-chart"), md=4, xs=12, className="p-3"),            
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="teachers-schooltype-pie-chart"), md=4, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="teachers-age-group-gender-bar-chart"), md=8, xs=12, className="p-3"),
            ], className="m-1"),
        ]),
    ], fluid=True)

# Data processing
@dash.callback(
    Output("teachers-district-gender-bar-chart", "figure"),
    Output("teachers-region-gender-bar-chart", "figure"),
    Output("teachers-authgovt-pie-chart", "figure"),
    Output("teachers-auth-bar-chart", "figure"),
    Output("teachers-schooltype-pie-chart", "figure"),
    Output("teachers-age-group-gender-bar-chart", "figure"),
    # No data UX
    Output("teachers-overview-nodata-msg", "children"),
    Output("teachers-overview-nodata-msg", "is_open"),
    Output("teachers-overview-loading-spacer", "style"),  # hide spacer when done; keep while loading/no-data
    Output("teachers-overview-content", "style"),         # show charts when done
    Input("year-filter", "value"),
    Input("warehouse-version-store", "data"),   # <— triggers when warehouse version changes
)
def update_dashboard(selected_year, _warehouse_version):
    if selected_year is None:
        empty = ({}, {}, {}, {}, {}, {})
        return (*empty, "No data", True, {}, {"display": "none"})

    # Re-fetch and guard against None/empty
    df = get_df_teachercount()
    if df is None or df.empty:
        empty = ({}, {}, {}, {}, {}, {})
        return (*empty, "No data available.", True, {}, {"display": "none"})

    # Filter data for the selected survey year
    filtered = df[df['SurveyYear'] == selected_year].copy()
    if filtered.empty:
        empty = ({}, {}, {}, {}, {}, {})
        return (*empty, f"No data available for {selected_year}.", True, {}, {"display": "none"})

    ###########################################################################
    # District Bar Chart (Stacked Bars)
    ###########################################################################
    grouped_district = filtered.groupby('DistrictCode')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_district['DistrictName'] = grouped_district['DistrictCode'].apply(
        lambda code: district_lookup.get(code, code)
    )
    grouped_district = grouped_district.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })
    fig_district = px.bar(
        grouped_district,
        x="DistrictName",
        y=["Male", "Female", "Not Available"],
        barmode="stack",
        title=f"Teachers by {vocab_district} in {selected_year}",
        labels={"DistrictName": vocab_district, "value": "Teacher Count", "variable": "Teacher Category"}
    )
    fig_district.update_layout(xaxis_tickangle=90)

    ###########################################################################
    # Teacher Count by Region (Stacked Bar Chart)
    ###########################################################################
    filtered['RegionName'] = filtered['RegionCode'].apply(lambda code: region_lookup.get(code, code))
    grouped_region = filtered.groupby('RegionName')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_region = grouped_region.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })
    fig_teachers_by_region_gender = px.bar(
        grouped_region,
        x="RegionName",
        y=["Male", "Female", "Not Available"],
        barmode="stack",
        title=f"Teacher Count by {vocab_region} and Gender for {selected_year}",
        labels={"RegionName": vocab_region, "value": "Teacher Count", "variable": "Gender"}
    )

    ###########################################################################
    # Teacher Count by Authority Govt (Pie Chart)
    ###########################################################################
    filtered['AuthorityGovtName'] = filtered['AuthorityGovtCode'].apply(lambda code: authoritygovts_lookup.get(code, code))
    grouped_school_authgovt = filtered.groupby('AuthorityGovtName')['TotalTeachers'].sum().reset_index()
    fig_teachers_authoritygovt = px.pie(
        grouped_school_authgovt,
        color_discrete_sequence=px.colors.qualitative.D3,
        names="AuthorityGovtName",
        values="TotalTeachers",
        title=f"Teacher Count by {vocab_authoritygovt} for {selected_year}",
        labels={"AuthorityGovtName": vocab_authoritygovt, "TotalTeachers": "Teacher Count"}
    )

    ###########################################################################
    # Teacher Count by Authority (Horizontal Stacked Bar Chart)
    ###########################################################################
    filtered['AuthorityName'] = filtered['AuthorityCode'].apply(lambda code: authorities_lookup.get(code, code))
    grouped_auth = filtered.groupby('AuthorityName')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_auth = grouped_auth.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })
    fig_teachers_authorities_gender = px.bar(
        grouped_auth,
        y="AuthorityName",
        x=["Male", "Female", "Not Available"],
        barmode="stack",
        orientation="h",
        title=f"Teacher Count by {vocab_authority} and Gender for {selected_year}",
        labels={"AuthorityName": vocab_authority, "value": "Teacher Count", "variable": "Gender"}
    ) 

    ###########################################################################
    # Teacher Count by School Type (Pie Chart)
    ###########################################################################
    filtered['SchoolTypeName'] = filtered['SchoolTypeCode'].apply(lambda code: schooltypes_lookup.get(code, code))
    grouped_schooltype = filtered.groupby('SchoolTypeName')['TotalTeachers'].sum().reset_index()
    fig_teachers_by_school_type = px.pie(
        grouped_schooltype,
        color_discrete_sequence=px.colors.qualitative.D3,
        names="SchoolTypeName",
        values="TotalTeachers",
        title=f"Teacher Count by {vocab_schooltype} for {selected_year}",
        labels={"SchoolTypeName": vocab_schooltype, "TotalTeachers": "Teacher Count"}
    )

    ###########################################################################
    # Teacher Count by Age Groups (Diverging Horizontal Bar Chart)
    ###########################################################################
    grouped_age = filtered.groupby('AgeGroup')[['NumTeachersF', 'NumTeachersM']].sum().reset_index()
    grouped_age = grouped_age.rename(columns={'NumTeachersF': 'Female', 'NumTeachersM': 'Male'})
    grouped_age['Female'] = -grouped_age['Female']  # Negative for diverging bar chart

    fig_teachers_agegroup_gender = px.bar(
        grouped_age,
        y="AgeGroup",
        x=["Female", "Male"],
        orientation='h',
        title=f"Teacher Count by Age Groups for {selected_year}",
        labels={"AgeGroup": "Age Group", "value": "Teacher Count", "variable": "Gender"}
    )

    # Symmetric axis based on max absolute
    max_val = max(grouped_age['Male'].max(), abs(grouped_age['Female'].min())) if not grouped_age.empty else 0
    rounded_max = math.ceil(max_val / 50) * 50 if max_val else 50
    num_ticks = 11
    tick_vals = np.linspace(-rounded_max, rounded_max, num=num_ticks)
    tick_text = [str(int(abs(val))) for val in tick_vals]
    fig_teachers_agegroup_gender.update_layout(xaxis=dict(range=[-rounded_max, rounded_max]))
    fig_teachers_agegroup_gender.update_xaxes(tickvals=tick_vals, ticktext=tick_text)
    
    # success: hide alert, hide spacer, show content
    return (
        fig_district, 
        fig_teachers_by_region_gender, 
        fig_teachers_authoritygovt, 
        fig_teachers_authorities_gender, 
        fig_teachers_by_school_type, 
        fig_teachers_agegroup_gender,
        "", False, {"display": "none"}, {}
    )

layout = teachers_overview_layout()
