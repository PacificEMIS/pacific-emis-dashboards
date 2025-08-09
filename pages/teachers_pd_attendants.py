import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Import the PD data
from services.api import (
    df_teacherpdx,
    vocab_district,
    vocab_region,
    vocab_authority,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,
)

from services.utilities import calculate_center, calculate_zoom

dash.register_page(__name__, path="/teacherpd/attendants", name="Teacher PD Attendants")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024)

# --- Layout ---
def teachers_pd_overview_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers PD Attendants"), width=12, className="m-1"),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="year-filter-pd",
                    options=year_options,
                    value=default_year,
                    clearable=False,
                    style={'width': '200px'}
                ),
                className="m-1"
            )
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-school-map-chart"), md=12, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-district-gender-bar-chart"), md=4, xs=12, className="p-3"),
            # dbc.Col(dcc.Graph(id="pd-school-map-chart"), md=3, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-district-gender-trend-chart"), md=8, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-region-bar-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-authoritygroup-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-authority-bar-chart"), md=4, xs=12, className="p-3"),
        ]),
        dbc.Row([            
            dbc.Col(dcc.Graph(id="pd-schooltype-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-years-teaching-bar-chart"), md=8, xs=12, className="p-3"),
        ]),        
    ], fluid=True)

# --- Callbacks ---
@dash.callback(
    Output(component_id="pd-district-gender-bar-chart", component_property="figure"),
    Output(component_id="pd-district-gender-trend-chart", component_property="figure"),
    Output(component_id="pd-school-map-chart", component_property="figure"),
    Output(component_id="pd-region-bar-chart", component_property="figure"),
    Output(component_id="pd-authoritygroup-pie-chart", component_property="figure"),
    Output(component_id="pd-authority-bar-chart", component_property="figure"),
    Output(component_id="pd-schooltype-pie-chart", component_property="figure"),
    Output(component_id="pd-years-teaching-bar-chart", component_property="figure"),
    Input(component_id="year-filter-pd", component_property="value")
)
def update_dashboard(selected_year):
    if selected_year is None:
        return {}, {}, {}, {}, {}, {}, {}, {}
    
    # Filter the PD dataset
    filtered = df_teacherpdx[df_teacherpdx['SurveyYear'] == selected_year]

    ###########################################################################
    # PD Attendants by District and Gender (Stacked Bar Chart)
    ###########################################################################
    filtered = df_teacherpdx[df_teacherpdx['SurveyYear'] == selected_year].copy()

    # Group by user-friendly District and Gender
    grouped_pd = (
        filtered.groupby(['District', 'Gender'])['Attendants']
        .sum()
        .reset_index()
    )

    # Create stacked bar chart
    fig_pd_district_gender = px.bar(
        grouped_pd,
        x="District",
        y="Attendants",
        color="Gender",
        barmode="stack",
        title=f"PD Attendants by {vocab_district} and Gender in {selected_year}",
        labels={
            "District": vocab_district,
            "Attendants": "Number of Attendants",
            "Gender": "Gender"
        }
    )

    fig_pd_district_gender.update_layout(xaxis_tickangle=90)
    
    ###########################################################################
    # PD Attendants by District and Gender Over Time (Trend Line Chart)
    ###########################################################################
    grouped_trend = (
        df_teacherpdx.groupby(['SurveyYear', 'District'])['Attendants']
        .sum()
        .reset_index()
    )

    fig_pd_district_gender_trend = px.line(
        grouped_trend,
        x='SurveyYear',
        y='Attendants',
        color='District',
        line_group='District',
        markers=True,
        title=f"PD Attendants by {vocab_district} Over Time",
        labels={
            "SurveyYear": "Year",
            "Attendants": "Number of Attendants",
            "District": vocab_district
        }
    )
    
    ###########################################################################
    # PD Attendants by School (Map)
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

    # Group by school (in case some schools have multiple PD events)
    grouped_map = filtered_map.groupby(['schNo', 'schName', 'lat', 'lon'], as_index=False)['Attendants'].sum()

    # Create the map
    fig_pd_school_map = px.scatter_mapbox(
        grouped_map,
        lat='lat',
        lon='lon',
        size='Attendants',
        color='Attendants',
        color_continuous_scale="Blues",
        size_max=20,
        zoom=5,
        hover_name="schName",
        title=f"PD Attendants by School for {selected_year}"
    )

    fig_pd_school_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=3, # calculated zoom is ok, but still decided to override her for now.
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    ###########################################################################
    # PD Attendants by Region
    ###########################################################################
    fig_pd_region = px.bar(
        filtered.groupby(['Region','Gender']).sum(numeric_only=True).reset_index(),
        x='Region', y='Attendants',        
        color="Gender",
        title=f"PD Attendants by {vocab_region} and Gender for {selected_year}",
        labels={"Attendants": "Number of Attendants"}
    )

    ###########################################################################
    # PD Count by Authority Group (i.e. Govt) (Pie Chart)
    ###########################################################################            
    grouped_school = filtered.groupby(['AuthorityGroup','Gender'])['Attendants'].sum().reset_index()

    fig_pd_authoritygroup = px.pie(
         grouped_school,
         color_discrete_sequence=px.colors.qualitative.D3, # For some reason pie requires an override...
         names="AuthorityGroup",
         values="Attendants",
         title=f"PD Attendants by {vocab_authoritygovt} and Gender for {selected_year}",
         labels={"AuthorityGroup": vocab_authoritygovt, "Attendants": "Number of Attendants"}
    )

    ###########################################################################
    # PD Events by Authority (Horizontal Stacked Bar Chart)
    ###########################################################################
    fig_pd_authority_gender = px.bar(
        filtered.groupby(['Authority','Gender']).sum(numeric_only=True).reset_index(),
        x='Attendants',
        y='Authority',
        color='Gender',
        barmode="stack",
        orientation="h",
        title=f"PD Attendants by {vocab_authority} and Gender for {selected_year}",
        labels={
            "Authority": vocab_authority,
            "Attendants": "Number of Attendants",
            "Gender": "Gender"
        }
    )

    ###########################################################################
    # PD Count by School Types (Pie Chart)
    ###########################################################################            
    grouped_school = filtered.groupby(['SchoolType','Gender'])['Attendants'].sum().reset_index()

    fig_pd_schooltype = px.pie(
         grouped_school,
         color_discrete_sequence=px.colors.qualitative.D3, # For some reason pie requires an override...
         names="SchoolType",
         values="Attendants",
         title=f"PD Attendants by {vocab_schooltype} and Gender for {selected_year}",
         labels={"SchoolType": vocab_schooltype, "Attendants": "Number of Attendants"}
    )

    ###########################################################################
    # PD Events by Years of Teaching (Horizontal Bar Chart)
    ###########################################################################
    grouped_years_teaching = filtered.groupby(['YearsTeaching','Gender'])[['Attendants']].sum().reset_index()
    fig_pd_years_teaching = px.bar(
        grouped_years_teaching,
        y="YearsTeaching",
        x="Attendants",
        orientation='h',
        color='Gender',
        title="PD Attendants by Years of Teaching by Gender for {selected_year}",
        labels={"Attendants": "Number of Attendants", "YearsTeaching": "Years Teaching"}
    )

    return (
        fig_pd_district_gender,
        fig_pd_district_gender_trend,
        fig_pd_school_map,
        fig_pd_region,
        fig_pd_authoritygroup,
        fig_pd_authority_gender,
        fig_pd_schooltype,
        fig_pd_years_teaching
    )

layout = teachers_pd_overview_layout()
