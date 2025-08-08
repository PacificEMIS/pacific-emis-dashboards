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

dash.register_page(__name__, path="/teachers/cpd", name="Teacher CPD")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024)

# --- Layout ---
def teachers_cpd_overview_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers CPD Overview"), width=12, className="m-1"),
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
            dbc.Col(dcc.Graph(id="cpd-school-map-chart"), md=12, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cpd-district-gender-bar-chart"), md=4, xs=12, className="p-3"),
            # dbc.Col(dcc.Graph(id="cpd-school-map-chart"), md=3, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-district-gender-trend-chart"), md=8, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cpd-region-bar-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-authoritygroup-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-authority-bar-chart"), md=4, xs=12, className="p-3"),
        ]),
        dbc.Row([            
            dbc.Col(dcc.Graph(id="cpd-schooltype-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="cpd-years-teaching-bar-chart"), md=8, xs=12, className="p-3"),
        ]),        
    ], fluid=True)

# --- Callbacks ---
@dash.callback(
    Output(component_id="cpd-district-gender-bar-chart", component_property="figure"),
    Output(component_id="cpd-district-gender-trend-chart", component_property="figure"),
    Output(component_id="cpd-school-map-chart", component_property="figure"),
    Output(component_id="cpd-region-bar-chart", component_property="figure"),
    Output(component_id="cpd-authoritygroup-pie-chart", component_property="figure"),
    Output(component_id="cpd-authority-bar-chart", component_property="figure"),
    Output(component_id="cpd-schooltype-pie-chart", component_property="figure"),
    Output(component_id="cpd-years-teaching-bar-chart", component_property="figure"),
    Input(component_id="year-filter-cpd", component_property="value")
)
def update_dashboard(selected_year):
    if selected_year is None:
        return {}, {}, {}, {}, {}, {}, {}, {}
    
    # Filter the CPD dataset
    filtered = df_teachercpdx[df_teachercpdx['SurveyYear'] == selected_year]

    ###########################################################################
    # CPD Attendants by District and Gender (Stacked Bar Chart)
    ###########################################################################
    filtered = df_teachercpdx[df_teachercpdx['SurveyYear'] == selected_year].copy()

    # Group by user-friendly District and Gender
    grouped_cpd = (
        filtered.groupby(['District', 'Gender'])['Attendants']
        .sum()
        .reset_index()
    )

    # Create stacked bar chart
    fig_cpd_district_gender = px.bar(
        grouped_cpd,
        x="District",
        y="Attendants",
        color="Gender",
        barmode="stack",
        title=f"CPD Attendants by {vocab_district} and Gender in {selected_year}",
        labels={
            "District": vocab_district,
            "Attendants": "Number of Attendants",
            "Gender": "Gender"
        }
    )

    fig_cpd_district_gender.update_layout(xaxis_tickangle=90)
    
    ###########################################################################
    # CPD Attendants by District and Gender Over Time (Trend Line Chart)
    ###########################################################################
    grouped_trend = (
        df_teachercpdx.groupby(['SurveyYear', 'District'])['Attendants']
        .sum()
        .reset_index()
    )

    fig_cpd_district_gender_trend = px.line(
        grouped_trend,
        x='SurveyYear',
        y='Attendants',
        color='District',
        line_group='District',
        markers=True,
        title=f"CPD Attendants by {vocab_district} Over Time",
        labels={
            "SurveyYear": "Year",
            "Attendants": "Number of Attendants",
            "District": vocab_district
        }
    )
    
    ###########################################################################
    # CPD Attendants by School (Map)
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
    grouped_map = filtered_map.groupby(['schNo', 'schName', 'lat', 'lon'], as_index=False)['Attendants'].sum()

    # Create the map
    fig_cpd_school_map = px.scatter_mapbox(
        grouped_map,
        lat='lat',
        lon='lon',
        size='Attendants',
        color='Attendants',
        color_continuous_scale="Blues",
        size_max=20,
        zoom=5,
        hover_name="schName",
        title=f"CPD Attendants by School for {selected_year}"
    )

    fig_cpd_school_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=3, # calculated zoom is ok, but still decided to override her for now.
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    ###########################################################################
    # CPD Attendants by Region
    ###########################################################################
    fig_cpd_region = px.bar(
        filtered.groupby(['Region','Gender']).sum(numeric_only=True).reset_index(),
        x='Region', y='Attendants',        
        color="Gender",
        title=f"CPD Attendants by {vocab_region} and Gender for {selected_year}",
        labels={"Attendants": "Number of Attendants"}
    )

    ###########################################################################
    # CPD Count by Authority Group (i.e. Govt) (Pie Chart)
    ###########################################################################            
    grouped_school = filtered.groupby(['AuthorityGroup','Gender'])['Attendants'].sum().reset_index()

    fig_cpd_authoritygroup = px.pie(
         grouped_school,
         color_discrete_sequence=px.colors.qualitative.D3, # For some reason pie requires an override...
         names="AuthorityGroup",
         values="Attendants",
         title=f"CPD Attendants by {vocab_authoritygovt} and Gender for {selected_year}",
         labels={"AuthorityGroup": vocab_authoritygovt, "Attendants": "Number of Attendants"}
    )

    ###########################################################################
    # CPD Events by Authority (Horizontal Stacked Bar Chart)
    ###########################################################################
    fig_cpd_authority_gender = px.bar(
        filtered.groupby(['Authority','Gender']).sum(numeric_only=True).reset_index(),
        x='Attendants',
        y='Authority',
        color='Gender',
        barmode="stack",
        orientation="h",
        title=f"CPD Attendants by {vocab_authority} and Gender for {selected_year}",
        labels={
            "Authority": vocab_authority,
            "Attendants": "Number of Attendants",
            "Gender": "Gender"
        }
    )

    ###########################################################################
    # CPD Count by School Types (Pie Chart)
    ###########################################################################            
    grouped_school = filtered.groupby(['SchoolType','Gender'])['Attendants'].sum().reset_index()

    fig_cpd_schooltype = px.pie(
         grouped_school,
         color_discrete_sequence=px.colors.qualitative.D3, # For some reason pie requires an override...
         names="SchoolType",
         values="Attendants",
         title=f"CPD Attendants by {vocab_schooltype} and Gender for {selected_year}",
         labels={"SchoolType": vocab_schooltype, "Attendants": "Number of Attendants"}
    )

    ###########################################################################
    # CPD Events by Years of Teaching (Horizontal Bar Chart)
    ###########################################################################
    grouped_years_teaching = filtered.groupby(['YearsTeaching','Gender'])[['Attendants']].sum().reset_index()
    fig_cpd_years_teaching = px.bar(
        grouped_years_teaching,
        y="YearsTeaching",
        x="Attendants",
        orientation='h',
        color='Gender',
        title="CPD Attendants by Years of Teaching by Gender for {selected_year}",
        labels={"Attendants": "Number of Attendants", "YearsTeaching": "Years Teaching"}
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

layout = teachers_cpd_overview_layout()
