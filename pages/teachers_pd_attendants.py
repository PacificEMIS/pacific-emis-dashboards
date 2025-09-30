import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# Import the PD data
from services.api import (
    get_df_teacherpdx,
    vocab_district,
    vocab_region,
    vocab_authority,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,
)
df_teacherpdx = get_df_teacherpdx()

from services.utilities import calculate_center, calculate_zoom

dash.register_page(__name__, path="/teacherpd/attendants", name="Teacher PD Attendants")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024)

# --- Layout ---
def teachers_pd_attendants_layout():
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
        # No data message + spinner host centered in a reserved spacer (prevents footer jump)
        dcc.Loading(
            id="pd-attendants-top-loading",
            type="default",
            children=html.Div(
                id="pd-attendants-loading-spacer",
                style={"minHeight": "50vh"},
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="pd-attendants-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),
        # Charts hidden by default; shown by callback when ready
        html.Div(id="pd-attendants-content", style={"display": "none"}, children=[
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
        ]),
    ], fluid=True)

# --- Callbacks ---
@dash.callback(
    Output("pd-district-gender-bar-chart", "figure"),
    Output("pd-district-gender-trend-chart", "figure"),
    Output("pd-school-map-chart", "figure"),
    Output("pd-region-bar-chart", "figure"),
    Output("pd-authoritygroup-pie-chart", "figure"),
    Output("pd-authority-bar-chart", "figure"),
    Output("pd-schooltype-pie-chart", "figure"),
    Output("pd-years-teaching-bar-chart", "figure"),
    # No data UX
    Output("pd-attendants-nodata-msg", "children"),
    Output("pd-attendants-nodata-msg", "is_open"),
    Output("pd-attendants-loading-spacer", "style"),  # hide spacer when done; keep while loading/no-data
    Output("pd-attendants-content", "style"),         # show charts when done
    Input("year-filter-pd", "value"),
    Input("warehouse-version-store", "data"),   # <— triggers when warehouse version changes
)
def update_dashboard(selected_year, _warehouse_version):
    if selected_year is None:
        empty = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (*empty, "No data", True, {}, {"display": "none"})

    # Get latest DF and guard against None/empty
    df = get_df_teacherpdx()
    if df is None or df.empty:
        empty = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (*empty, "No data available.", True, {}, {"display": "none"})

    # Filter the PD dataset
    filtered = df[df['SurveyYear'] == selected_year].copy()
    if filtered.empty:
        empty = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (*empty, f"No data available for {selected_year}.", True, {}, {"display": "none"})

    ###########################################################################
    # PD Attendants by District and Gender (Stacked Bar Chart)
    ###########################################################################
    grouped_pd = (
        filtered.groupby(['District', 'Gender'])['Attendants']
        .sum()
        .reset_index()
    )

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
        df.groupby(['SurveyYear', 'District'])['Attendants']
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

    grouped_map = filtered_map.groupby(['schNo', 'schName', 'lat', 'lon'], as_index=False)['Attendants'].sum()

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
        mapbox_zoom=3,  # keep override
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
         color_discrete_sequence=px.colors.qualitative.D3,
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
         color_discrete_sequence=px.colors.qualitative.D3,
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
        title=f"PD Attendants by Years of Teaching by Gender for {selected_year}",
        labels={"Attendants": "Number of Attendants", "YearsTeaching": "Years Teaching"}
    )

    # success: hide alert, hide spacer, show charts
    return (
        fig_pd_district_gender,
        fig_pd_district_gender_trend,
        fig_pd_school_map,
        fig_pd_region,
        fig_pd_authoritygroup,
        fig_pd_authority_gender,
        fig_pd_schooltype,
        fig_pd_years_teaching,
        "", False, {"display": "none"}, {}
    )

layout = teachers_pd_attendants_layout()
