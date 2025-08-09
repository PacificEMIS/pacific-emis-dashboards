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

dash.register_page(__name__, path="/teacherpd/overview", name="Teacher PD Overview")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024)

# --- Layout ---
def teachers_pd_events_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers PD Overview"), width=12, className="m-1"),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="year-filter-pd-overview",
                    options=year_options,
                    value=default_year,
                    clearable=False,
                    style={'width': '200px'}
                ),
                className="m-1"
            )
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-overview-school-map-chart"), md=12, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-overview-district-focus-bar-chart"), md=4, xs=12, className="p-3"),
            # dbc.Col(dcc.Graph(id="pd-overview-school-map-chart"), md=3, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-overview-district-trend-chart"), md=8, xs=12, className="p-3"),
        ], className="m-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-overview-region-bar-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-overview-authoritygroup-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-overview-authority-bar-chart"), md=4, xs=12, className="p-3"),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="pd-overview-schooltype-pie-chart"), md=4, xs=12, className="p-3"),
            dbc.Col(dcc.Graph(id="pd-overview-years-teaching-bar-chart"), md=8, xs=12, className="p-3"),
        ]),
    ], fluid=True)

# --- Callbacks ---
@dash.callback(
    Output(component_id="pd-overview-district-focus-bar-chart", component_property="figure"),
    Output(component_id="pd-overview-district-trend-chart", component_property="figure"),
    Output(component_id="pd-overview-school-map-chart", component_property="figure"),
    Output(component_id="pd-overview-region-bar-chart", component_property="figure"),
    Output(component_id="pd-overview-authoritygroup-pie-chart", component_property="figure"),
    Output(component_id="pd-overview-authority-bar-chart", component_property="figure"),
    Output(component_id="pd-overview-schooltype-pie-chart", component_property="figure"),
    Output(component_id="pd-overview-years-teaching-bar-chart", component_property="figure"),
    Input(component_id="year-filter-pd-overview", component_property="value")
)
def update_pd_events_dashboard(selected_year):
    if selected_year is None:
        return {}, {}, {}, {}, {}, {}, {}, {}

    # Filter the PD dataset
    filtered = df_teacherpdx[df_teacherpdx['SurveyYear'] == selected_year].copy()

    ###########################################################################
    # PD Events by District and Focus (Stacked Bar Chart)
    ###########################################################################
    grouped_pd = (
        filtered.groupby(['District', 'tpdFocus'])['tpdName']
        .nunique()
        .reset_index(name='Events')
    )

    fig_pd_district_focus = px.bar(
        grouped_pd,
        x="District",
        y="Events",
        color="tpdFocus",
        barmode="stack",
        title=f"PD Events by {vocab_district} and Focus in {selected_year}",
        labels={
            "District": vocab_district,
            "Events": "Number of PD Events",
            "tpdFocus": "PD Focus"
        }
    )

    fig_pd_district_focus.update_layout(xaxis_tickangle=90)

    ###########################################################################
    # PD Events by District Over Time (Trend Line Chart)
    ###########################################################################
    grouped_trend = (
        df_teacherpdx.groupby(['SurveyYear', 'District'])['tpdName']
        .nunique()
        .reset_index(name='Events')
    )

    fig_pd_district_trend = px.line(
        grouped_trend,
        x='SurveyYear',
        y='Events',
        color='District',
        line_group='District',
        markers=True,
        title=f"PD Events by {vocab_district} Over Time",
        labels={
            "SurveyYear": "Year",
            "Events": "Number of PD Events",
            "District": vocab_district
        }
    )

    ###########################################################################
    # PD Events by School (Map)
    ###########################################################################
    DEFAULT_LAT = 1.4353492965396066
    DEFAULT_LON = 173.0003430428269
    filtered['lat'] = filtered['lat'].fillna(DEFAULT_LAT)
    filtered['lon'] = filtered['lon'].fillna(DEFAULT_LON)

    filtered_map = filtered

    coords = list(zip(filtered_map['lat'], filtered_map['lon']))
    center_lat, center_lon = calculate_center(coords)
    zoom = calculate_zoom(coords)

    print("center_lat:", center_lat)
    print("center_lon:", center_lon)
    print("zoom:", zoom)

    grouped_map = (
        filtered_map.groupby(['schNo', 'schName', 'lat', 'lon'], as_index=False)['tpdName']
        .nunique()
        .rename(columns={'tpdName': 'Events'})
    )

    fig_pd_school_map = px.scatter_mapbox(
        grouped_map,
        lat='lat',
        lon='lon',
        size='Events',
        color='Events',
        color_continuous_scale="Blues",
        size_max=20,
        zoom=5,
        hover_name="schName",
        title=f"PD Events by School for {selected_year}"
    )

    fig_pd_school_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=3,
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    ###########################################################################
    # PD Events by Region
    ###########################################################################
    fig_pd_region = px.bar(
        filtered.groupby(['Region', 'tpdFocus'])['tpdName'].nunique().reset_index(name='Events'),
        x='Region', y='Events',
        color="tpdFocus",
        title=f"PD Events by {vocab_region} and Focus for {selected_year}",
        labels={"Events": "Number of PD Events", "tpdFocus": "PD Focus"}
    )

    ###########################################################################
    # PD Events by Authority Group (i.e. Govt) (Pie Chart)
    ###########################################################################
    grouped_authoritygroup = (
        filtered.groupby(['AuthorityGroup'])['tpdName']
        .nunique()
        .reset_index(name='Events')
    )

    fig_pd_authoritygroup = px.pie(
         grouped_authoritygroup,
         color_discrete_sequence=px.colors.qualitative.D3,
         names="AuthorityGroup",
         values="Events",
         title=f"PD Events by {vocab_authoritygovt} for {selected_year}",
         labels={"AuthorityGroup": vocab_authoritygovt, "Events": "Number of PD Events"}
    )

    ###########################################################################
    # PD Events by Authority (Horizontal Stacked Bar Chart)
    ###########################################################################
    fig_pd_authority_focus = px.bar(
        filtered.groupby(['Authority', 'tpdFocus'])['tpdName'].nunique().reset_index(name='Events'),
        x='Events',
        y='Authority',
        color='tpdFocus',
        barmode="stack",
        orientation="h",
        title=f"PD Events by {vocab_authority} and Focus for {selected_year}",
        labels={
            "Authority": vocab_authority,
            "Events": "Number of PD Events",
            "tpdFocus": "PD Focus"
        }
    )

    ###########################################################################
    # PD Events by School Types (Pie Chart)
    ###########################################################################
    grouped_schooltype = (
        filtered.groupby(['SchoolType'])['tpdName']
        .nunique()
        .reset_index(name='Events')
    )

    fig_pd_schooltype = px.pie(
         grouped_schooltype,
         color_discrete_sequence=px.colors.qualitative.D3,
         names="SchoolType",
         values="Events",
         title=f"PD Events by {vocab_schooltype} for {selected_year}",
         labels={"SchoolType": vocab_schooltype, "Events": "Number of PD Events"}
    )

    ###########################################################################
    # PD Events by Years of Teaching (Horizontal Bar Chart)
    ###########################################################################
    grouped_years_teaching = (
        filtered.groupby(['YearsTeaching','tpdFocus'])['tpdName']
        .nunique()
        .reset_index(name='Events')
    )

    fig_pd_years_teaching = px.bar(
        grouped_years_teaching,
        y="YearsTeaching",
        x="Events",
        orientation='h',
        color='tpdFocus',
        title=f"PD Events by Years of Teaching and Focus for {selected_year}",
        labels={"Events": "Number of PD Events", "YearsTeaching": "Years Teaching", "tpdFocus": "PD Focus"}
    )

    return (
        fig_pd_district_focus,
        fig_pd_district_trend,
        fig_pd_school_map,
        fig_pd_region,
        fig_pd_authoritygroup,
        fig_pd_authority_focus,
        fig_pd_schooltype,
        fig_pd_years_teaching
    )

layout = teachers_pd_events_layout()
