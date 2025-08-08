import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Import the CPD data
from services.api import (
    df_teachercpdx,
    vocab_district,
    vocab_region,
    vocab_authority,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,
)

from services.utilities import calculate_center, calculate_zoom

dash.register_page(__name__, path="/teachers/cpd-attendance", name="Teacher CPD Attendance")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024)

# --- Layout ---
def teachers_cpd_attendance_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers CPD Attendance"), width=12, className="m-1"),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="year-filter-cpd",
                    options=year_options,
                    value=default_year,
                    clearable=False,
                    style={'width': '200px'}
                ),
                className="m-1"
            )
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cpd-attendance-school-map-chart"), md=12, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cpd-attendance-district-gender-bar-chart"), md=4, xs=12, className="p-3"),
            # dbc.Col(dcc.Graph(id="cpd-attendance-school-map-chart"), md=3, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-attendance-district-gender-trend-chart"), md=8, xs=12, className="p-3"),
        ], className="m-1"),        
        dbc.Row([
            dbc.Col(dcc.Graph(id="cpd-attendance-region-bar-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-attendance-authoritygroup-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-attendance-authority-bar-chart"), md=4, xs=12, className="p-3"),
        ]),
        dbc.Row([            
            dbc.Col(dcc.Graph(id="cpd-attendance-schooltype-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-attendance-years-teaching-bar-chart"), md=8, xs=12, className="p-3"),
        ]),        
    ], fluid=True)

# --- Callbacks ---
@dash.callback(
    Output(component_id="cpd-attendance-district-gender-bar-chart", component_property="figure"),
    Output(component_id="cpd-attendance-district-gender-trend-chart", component_property="figure"),
    Output(component_id="cpd-attendance-school-map-chart", component_property="figure"),
    Output(component_id="cpd-attendance-region-bar-chart", component_property="figure"),
    Output(component_id="cpd-attendance-authoritygroup-pie-chart", component_property="figure"),
    Output(component_id="cpd-attendance-authority-bar-chart", component_property="figure"),
    Output(component_id="cpd-attendance-schooltype-pie-chart", component_property="figure"),
    Output(component_id="cpd-attendance-years-teaching-bar-chart", component_property="figure"),
    Input(component_id="year-filter-cpd", component_property="value")
)
def update_dashboard(selected_year):
    if selected_year is None:
        return {}, {}, {}, {}, {}, {}, {}, {}
    
    # Filter the CPD dataset
    filtered = df_teachercpdx[df_teachercpdx['SurveyYear'] == selected_year]

    ###########################################################################
    # CPD Average Attendance Rate by District and Gender (Grouped Bar Chart)
    ###########################################################################
    # filter for year
    filtered = df_teachercpdx[df_teachercpdx['SurveyYear'] == selected_year].copy()

    # compute mean rate per District × Gender
    grouped_rate = (
        filtered
        .groupby(['District', 'Gender'])['AverageAttendanceRate']
        .mean()
        .reset_index()
    )

    # build a grouped bar chart and display y-axis as percent
    fig_cpd_district_gender = px.bar(
        grouped_rate,
        x="District",
        y="AverageAttendanceRate",
        color="Gender",
        barmode="group",  # side-by-side bars
        title=f"CPD Average Attendance Rate by {vocab_district} and Gender in {selected_year}",        
        labels={
            "District": vocab_district,
            "AverageAttendanceRate": "Average Attendance Rate",
            "Gender": "Gender"
        }
    )

    # rotate the x-labels and format y-axis ticks as percentages
    fig_cpd_district_gender.update_layout(
        xaxis_tickangle=90,
        title_font_size=12,
    )
    fig_cpd_district_gender.update_yaxes(
        range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    )
    
    ###########################################################################
    # CPD Average Attendance by District and Gender Over Time (Trend Line Chart)
    ###########################################################################
    grouped_trend = (
        df_teachercpdx.groupby(['SurveyYear', 'District'])['AverageAttendanceRate']
        .mean()
        .reset_index()
    )

    fig_cpd_district_gender_trend = px.line(
        grouped_trend,
        x='SurveyYear',
        y='AverageAttendanceRate',
        color='District',
        line_group='District',
        markers=True,
        title=f"CPD Average Attendance by {vocab_district} Over Time",
        labels={
            "SurveyYear": "Year",
            "AverageAttendanceRate": "Average Attendance Rate",
            "District": vocab_district
        }
    )
    
    fig_cpd_district_gender_trend.update_layout(
        title_font_size=12,
    )
    
    fig_cpd_district_gender_trend.update_yaxes(
        #range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    )
    
    ###########################################################################
    # CPD Average Attendance by School (Map)
    ###########################################################################
    
    # Step 1: Default location of schools with no coordinates known
    DEFAULT_LAT = 1.4353492965396066
    DEFAULT_LON = 173.0003430428269
    filtered['lat'] = filtered['lat'].fillna(DEFAULT_LAT)
    filtered['lon'] = filtered['lon'].fillna(DEFAULT_LON)

    filtered_map = filtered
    
    # Prepare list of (lat, lon) tuples
    coords = list(zip(filtered_map['lat'], filtered_map['lon']))
    # Compute correct center
    center_lat, center_lon = calculate_center(coords)
    zoom = calculate_zoom(coords)
    
    print("center_lat:", center_lat)
    print("center_lon:", center_lon)
    print("zoom:", zoom)    

    # Group by school (in case some schools have multiple CPD events)
    grouped_map = filtered_map.groupby(['schNo', 'schName', 'lat', 'lon'], as_index=False)['AverageAttendanceRate'].mean()

    # Create the map
    fig_cpd_school_map = px.scatter_mapbox(
        grouped_map,
        lat='lat',
        lon='lon',
        size='AverageAttendanceRate',
        color='AverageAttendanceRate',
        color_continuous_scale="Blues",
        size_max=20,
        zoom=5,
        hover_name="schName",
        title=f"CPD Average Attendance by School for {selected_year}"
    )
    
    # 1) Format the colorbar ticks as percentages
    fig_cpd_school_map.update_layout(
        coloraxis_colorbar=dict(
            title="Average Attendance Rate",
            tickformat=".0%",   # no decimals, just "0–100%"
        )
    )

    # 2) Update your traces so that the hover shows e.g. “72%” instead of “0.72”
    fig_cpd_school_map.update_traces(
        hovertemplate=
            "<b>%{hovertext}</b><br>" +
            "Avg. Attendance: %{marker.color:.0%}<extra></extra>",
        selector=dict(type="scattermapbox")
    )

    # 3) And, of course, your map‐layout settings:
    fig_cpd_school_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=3, # calculated zoom is ok, but still decided to override her for now.
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        title_font_size=12
    )

    ###########################################################################
    # CPD Average Attendance by Region
    ###########################################################################
    fig_cpd_region = px.bar(
        filtered.groupby(['Region','Gender']).mean(numeric_only=True).reset_index(),
        x='Region', y='AverageAttendanceRate',        
        color="Gender",
        barmode="group",  # side-by-side bars
        title=f"CPD Average Attendance by {vocab_region} and Gender for {selected_year}",
        labels={"AverageAttendanceRate": "Average Attendance Rate"}
    )
    
    # rotate the x-labels and format y-axis ticks as percentages
    fig_cpd_region.update_layout(
        xaxis_tickangle=90,
        title_font_size=12
    )
    fig_cpd_region.update_yaxes(
        range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    )

    ###########################################################################
    # CPD Count by Authority Group (i.e. Govt) (Bar Chart)
    ###########################################################################
    fig_cpd_authoritygroup = px.bar(
        filtered.groupby(['AuthorityGroup','Gender']).mean(numeric_only=True).reset_index(),
        x='AuthorityGroup', y='AverageAttendanceRate',        
        color="Gender",
        barmode="group",  # side-by-side bars
        title=f"CPD Average Attendance by {vocab_authoritygovt} and Gender for {selected_year}",
        labels={"AverageAttendanceRate": "Average Attendance Rate"}
    )
    
    # rotate the x-labels and format y-axis ticks as percentages
    fig_cpd_authoritygroup.update_layout(
        xaxis_tickangle=90,
        title_font_size=12
    )
    fig_cpd_authoritygroup.update_yaxes(
        range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    )

    ###########################################################################
    # CPD Events by Authority (Horizontal Bar Chart)
    ###########################################################################
    fig_cpd_authority_gender = px.bar(
        filtered.groupby(['Authority','Gender']).mean(numeric_only=True).reset_index(),
        x='AverageAttendanceRate',
        y='Authority',
        color='Gender',
        barmode="group",  # side-by-side bars        
        orientation="h",
        title=f"CPD Average Attendance by {vocab_authority} and Gender for {selected_year}",
        labels={
            "Authority": vocab_authority,
            "AverageAttendanceRate": "Average Attendance Rate",
            "Gender": "Gender"
        }
    )
    
    # rotate the x-labels and format y-axis ticks as percentages
    fig_cpd_authority_gender.update_layout(
        xaxis_tickangle=45,
        title_font_size=12
    )
    fig_cpd_authority_gender.update_xaxes(
        range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    )

    ###########################################################################
    # CPD Count by School Types (Horizontal Bar Chart)
    ###########################################################################            
    fig_cpd_schooltype = px.bar(
        filtered.groupby(['SchoolType','Gender']).mean(numeric_only=True).reset_index(),
        x='AverageAttendanceRate', 
        y='SchoolType',        
        color="Gender",
        barmode="group",  # side-by-side bars       
        orientation="h",
        title=f"CPD Average Attendance by {vocab_schooltype} and Gender for {selected_year}",
        labels={"AverageAttendanceRate": "Average Attendance Rate"}
    )   
    
    # rotate the x-labels and format y-axis ticks as percentages
    fig_cpd_schooltype.update_layout(
        xaxis_tickangle=90,
        title_font_size=12
    )
    fig_cpd_schooltype.update_xaxes(
        range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    ) 

    ###########################################################################
    # CPD Events by Years of Teaching (Horizontal Bar Chart)
    ###########################################################################
    grouped_years_teaching = filtered.groupby(['YearsTeaching','Gender'])[['AverageAttendanceRate']].mean().reset_index()
    fig_cpd_years_teaching = px.bar(
        grouped_years_teaching,        
        x="AverageAttendanceRate",
        y="YearsTeaching",
        color='Gender',
        barmode="group",  # side-by-side bars       
        orientation="h",
        title=f"CPD Average Attendance by Years of Teaching by gender for {selected_year}",
        labels={"AverageAttendanceRate": "Average Attendance Rate", "YearsTeaching": "Years Teaching"}
    )
    
    # rotate the x-labels and format y-axis ticks as percentages
    fig_cpd_years_teaching.update_layout(
        xaxis_tickangle=90,
        title_font_size=12
    )
    fig_cpd_years_teaching.update_xaxes(
        range=[0, 1],     # forces 0% → 100%
        tickformat=".1%"  # still shows ticks as percentages
    )

    return (
        fig_cpd_district_gender,
        fig_cpd_district_gender_trend,
        fig_cpd_school_map,
        fig_cpd_region,
        fig_cpd_authoritygroup,
        fig_cpd_authority_gender,
        fig_cpd_schooltype,
        fig_cpd_years_teaching
    )

layout = teachers_cpd_attendance_layout()
