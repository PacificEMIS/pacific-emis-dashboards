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
    df_teachercount,
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

dash.register_page(__name__, path="/teachers/overview", name="Teachers Overview")

# Filters
# Extract survey years from lookup dictionary (assuming it contains a "surveyYears" key)
survey_years = lookup_dict.get("surveyYears", [])

print("survey_years", survey_years)

# Create dropdown options using 'N' for display and 'C' for value
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]

# Determine the default value: the highest available year
default_year = max([int(item['C']) for item in survey_years], default=2024) 

# ✅ **Define Layout inside a Function**
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
    ], fluid=True)

# Data processing
@dash.callback(
    Output(component_id="teachers-district-gender-bar-chart", component_property="figure"),
    Output(component_id="teachers-region-gender-bar-chart", component_property="figure"),
    Output(component_id="teachers-authgovt-pie-chart", component_property="figure"),
    Output(component_id="teachers-auth-bar-chart", component_property="figure"),
    Output(component_id="teachers-schooltype-pie-chart", component_property="figure"),
    Output(component_id="teachers-age-group-gender-bar-chart", component_property="figure"),
    Input(component_id="year-filter", component_property="value")
)
def update_dashboard(selected_year):
    if selected_year is None:
        return {}, {}, {}
    
    # Filter data for the selected survey year
    filtered = df_teachercount[df_teachercount['SurveyYear'] == selected_year]    
    
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
    filtered['RegionName'] = filtered['RegionCode'].apply(
        lambda code: region_lookup.get(code, code)
    )

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
    filtered['AuthorityGovtName'] = filtered['AuthorityGovtCode'].apply(
        lambda code: authoritygovts_lookup.get(code, code)
    )
    grouped_school = filtered.groupby('AuthorityGovtName')['TotalTeachers'].sum().reset_index()

    fig_teachers_authoritygovt = px.pie(
         grouped_school,
         color_discrete_sequence=px.colors.qualitative.D3, # For some reason pie requires an override...
         names="AuthorityGovtName",
         values="TotalTeachers",
         title=f"Teacher Count by {vocab_authoritygovt} for {selected_year}",
         labels={"AuthorityGovtName": vocab_authoritygovt, "TotalTeachers": "Teacher Count"}
    )

    ###########################################################################
    # Teacher Count by Authority (Horizontal Stacked Bar Chart)
    ###########################################################################        
    filtered['AuthorityName'] = filtered['AuthorityCode'].apply(
        lambda code: authorities_lookup.get(code, code)
    )

    grouped_auth = filtered.groupby('AuthorityName')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_auth = grouped_auth.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })

    fig_teachers_authorities_gender = px.bar(
        grouped_auth,
        y="AuthorityName",                       # now the category goes on the y-axis
        x=["Male", "Female", "Not Available"],   # numeric values go on the x-axis
        barmode="stack",
        orientation="h",                         # set the orientation to horizontal
        title=f"Teacher Count by {vocab_authority} and Gender for {selected_year}",
        labels={"AuthorityName": vocab_authority, "value": "Teacher Count", "variable": "Gender"}
    ) 

    ###########################################################################
    # Teacher Count by School Type (Pie Chart)
    ###########################################################################        
    filtered['SchoolTypeName'] = filtered['SchoolTypeCode'].apply(
        lambda code: schooltypes_lookup.get(code, code)
    )
    grouped_school = filtered.groupby('SchoolTypeName')['TotalTeachers'].sum().reset_index()

    fig_teachers_by_school_type = px.pie(
         grouped_school,
         color_discrete_sequence=px.colors.qualitative.D3, # For some reason pie requires an override...
         names="SchoolTypeName",
         values="TotalTeachers",
         title=f"Teacher Count by {vocab_schooltype} for {selected_year}",
         labels={"SchoolTypeName": vocab_schooltype, "TotalTeachers": "Teacher Count"}
    )

    ###########################################################################
    # Teacher Count by Age Groups (Diverging Horizontal Bar Chart)
    # Female bars extend to the left (negative) and Male bars extend to the right (positive)
    ###########################################################################
    grouped_age = filtered.groupby('AgeGroup')[['NumTeachersF', 'NumTeachersM']].sum().reset_index()
    grouped_age = grouped_age.rename(columns={'NumTeachersF': 'Female', 'NumTeachersM': 'Male'})
    grouped_age['Female'] = -grouped_age['Female']  # Negative for diverging bar chart

    # Create the diverging bar chart as before.
    fig_teachers_agegroup_gender = px.bar(
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
    fig_teachers_agegroup_gender.update_layout(xaxis=dict(range=[-rounded_max, rounded_max]))
    fig_teachers_agegroup_gender.update_xaxes(tickvals=tick_vals, ticktext=tick_text)
    
    return (
        fig_district, 
        fig_teachers_by_region_gender, 
        fig_teachers_authoritygovt, 
        fig_teachers_authorities_gender, 
        fig_teachers_by_school_type, 
        fig_teachers_agegroup_gender
    )

layout = teachers_overview_layout()