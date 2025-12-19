import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# Import the PD data
from services.api import (
    get_df_teacherpdattendancex,
    get_latest_year_with_data,
    vocab_district,
    vocab_region,
    vocab_authority,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,
)
df_teacherpdattendancex = get_df_teacherpdattendancex()

from services.utilities import calculate_center, calculate_zoom

dash.register_page(__name__, path="/teacherpd/attendance", name="Teachers PD Attendance")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
# Use the latest year that actually has data, not just the max year in the list
default_year = get_latest_year_with_data(df_teacherpdattendancex)

# --- Layout ---
def teachers_pd_attendance_layout():
    return dbc.Container([        
        dbc.Row([
            dbc.Col(html.H1("Teachers PD Attendance"), width=12, className="m-1"),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="pd-attendance-year-filter",
                    options=year_options,
                    value=default_year,
                    clearable=False,
                    style={'width': '200px'}
                ),
                className="m-1"
            )
        ]),
        # --- No data message (spinner host) ---
        # Wrap a spacer (minHeight 50vh) + alert inside dcc.Loading so the spinner is centered in that space
        dcc.Loading(
            id="pd-attendance-top-loading",
            type="default",  # "default" | "circle" | "dot" | "cube"
            children=html.Div(                     # <- this is the spacer the spinner will center within
                id="pd-attendance-loading-spacer",
                style={"minHeight": "50vh"},       # reserve space; spinner centers here while loading
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="pd-attendance-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),

        # --- Charts content ---
        # Charts hidden by default; callback will set style to {} when ready
        html.Div(id="pd-attendance-content", style={"display": "none"}, children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-attendance-school-map-chart"), md=12, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-attendance-district-focus-bar-chart"), md=6, xs=12, className="p-3"),
                # dbc.Col(dcc.Graph(id="pd-attendance-school-map-chart"), md=3, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="pd-attendance-district-trend-chart"), md=6, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-attendance-region-bar-chart"), md=6, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="pd-attendance-schooltype-pie-chart"), md=6, xs=12, className="p-3"),
            ]),
             dbc.Row([
                dbc.Col(dcc.Graph(id="pd-attendance-authoritygroup-pie-chart"), md=6, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="pd-attendance-authority-bar-chart"), md=6, xs=12, className="p-3"),
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-attendance-format-bar-chart"), md=8, xs=12, className="p-3"),
            ]),
        ]),
    ], fluid=True)

# --- Callbacks ---
    
@dash.callback(
    Output("pd-attendance-district-focus-bar-chart", "figure"),
    Output("pd-attendance-district-trend-chart", "figure"),
    Output("pd-attendance-school-map-chart", "figure"),
    Output("pd-attendance-region-bar-chart", "figure"),
    Output("pd-attendance-authoritygroup-pie-chart", "figure"),
    Output("pd-attendance-authority-bar-chart", "figure"),
    Output("pd-attendance-schooltype-pie-chart", "figure"),
    Output("pd-attendance-format-bar-chart", "figure"),
    # --- No data UX ---
    Output("pd-attendance-nodata-msg", "children"),
    Output("pd-attendance-nodata-msg", "is_open"),
    Output("pd-attendance-loading-spacer", "style"),  # hide spacer when done; keep while loading/no-data
    Output("pd-attendance-content", "style"),         # show charts when done
    Input("pd-attendance-year-filter", "value"),
    Input("warehouse-version-store", "data"),   # <— triggers when warehouse version changes
)
def update_pd_attendance_dashboard(selected_year, _warehouse_version):
    if selected_year is None:
        empty = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert; keep charts hidden; keep spacer visible (no minHeight override here)
        return (*empty, "No data", True, {}, {"display": "none"})

    # Get latest DF and guard against None/empty
    df = get_df_teacherpdattendancex()
    if df is None or df.empty:
        empty = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert; keep charts hidden; keep spacer visible so alert has room
        return (*empty, "No data available.", True, {}, {"display": "none"})

    # Filter the PD dataset
    filtered = df[df['SurveyYear'] == selected_year].copy()
    if filtered.empty:
        empty = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert; keep charts hidden; keep spacer visible so alert has room
        return (*empty, f"No data available for {selected_year}.", True, {}, {"display": "none"})

    # Helper to compute weighted rates per group
    def weighted_rates(df_in, group_cols):
        g = df_in.groupby(group_cols, dropna=False).agg(
            Attendants_sum=('Attendants', 'sum'),
            AttendantsCompleted_sum=('AttendantsCompleted', 'sum'),
            Teachers_sum=('TeachersInSchool', 'sum')
        ).reset_index()
        # avoid division by zero
        g['AttendanceRate'] = (g['Attendants_sum'] / g['Teachers_sum']).where(g['Teachers_sum'] > 0, 0)
        g['AttendanceRateCompleted'] = (g['AttendantsCompleted_sum'] / g['Teachers_sum']).where(g['Teachers_sum'] > 0, 0)
        return g

    ###########################################################################
    # Attendance Rate by District and Focus (Grouped Bar Chart)
    ###########################################################################
    grouped_pd = weighted_rates(filtered, ['District', 'tpdFocus'])
    grouped_pd['AttendanceRatePct'] = grouped_pd['AttendanceRate'] * 100
    grouped_pd['AttendanceRateCompletedPct'] = grouped_pd['AttendanceRateCompleted'] * 100

    fig_pd_district_focus = px.bar(
        grouped_pd,
        x="District",
        y="AttendanceRatePct",
        color="tpdFocus",
        barmode="group",
        title=f"Average Attendance Rate by {vocab_district} and Focus in {selected_year}",
        labels={
            "District": vocab_district,
            "AttendanceRatePct": "Attendance Rate (%)",
            "tpdFocus": "PD Focus"
        },
        hover_data={
            "AttendanceRatePct": ':.1f',
            "AttendanceRateCompletedPct": ':.1f',
            "Attendants_sum": True,
            "AttendantsCompleted_sum": True,
            "Teachers_sum": True
        }
    )
    fig_pd_district_focus.update_layout(xaxis_tickangle=90)

    ###########################################################################
    # Attendance Rate by District Over Time (Trend Line Chart)
    ###########################################################################
    grouped_trend = weighted_rates(df, ['SurveyYear', 'District'])
    # ensure x-axis uses whole years (not floats like 2024.5)
    grouped_trend['SurveyYear'] = grouped_trend['SurveyYear'].round().astype(int)
    grouped_trend['AttendanceRatePct'] = grouped_trend['AttendanceRate'] * 100

    fig_pd_district_trend = px.line(
        grouped_trend,
        x='SurveyYear',
        y='AttendanceRatePct',
        color='District',
        line_group='District',
        markers=True,
        title=f"Average Attendance Rate by {vocab_district} Over Time",
        labels={
            "SurveyYear": "Year",
            "AttendanceRatePct": "Attendance Rate (%)",
            "District": vocab_district
        }
    )

    # force integer year ticks only
    fig_pd_district_trend.update_xaxes(tickmode="linear", dtick=1, tickformat="d")

    ###########################################################################
    # Attendance Rate by School (Map)
    ###########################################################################
    DEFAULT_LAT = 1.4353492965396066
    DEFAULT_LON = 173.0003430428269
    filtered['lat'] = filtered['lat'].fillna(DEFAULT_LAT)
    filtered['lon'] = filtered['lon'].fillna(DEFAULT_LON)

    filtered_map = weighted_rates(filtered, ['schNo', 'schName', 'lat', 'lon'])
    filtered_map['AttendanceRatePct'] = filtered_map['AttendanceRate'] * 100
    filtered_map['AttendanceRateCompletedPct'] = filtered_map['AttendanceRateCompleted'] * 100

    coords = list(zip(filtered_map['lat'], filtered_map['lon']))
    center_lat, center_lon = calculate_center(coords)
    zoom = calculate_zoom(coords)

    print("center_lat:", center_lat)
    print("center_lon:", center_lon)
    print("zoom:", zoom)

    fig_pd_school_map = px.scatter_mapbox(
        filtered_map,
        lat='lat',
        lon='lon',
        size='Attendants_sum',
        color='AttendanceRatePct',
        color_continuous_scale="Blues",
        size_max=20,
        zoom=5,
        hover_name="schName",
        title=f"Attendance Rate by School for {selected_year}",
        hover_data={
            "AttendanceRatePct": ':.1f',
            "AttendanceRateCompletedPct": ':.1f',
            "Attendants_sum": True,
            "AttendantsCompleted_sum": True,
            "Teachers_sum": True
        }
    )

    fig_pd_school_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=3,
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    ###########################################################################
    # Attendance Rate by Region
    ###########################################################################
    grouped_region = weighted_rates(filtered, ['Region', 'tpdFocus'])
    grouped_region['AttendanceRatePct'] = grouped_region['AttendanceRate'] * 100

    fig_pd_region = px.bar(
        grouped_region,
        x='Region', y='AttendanceRatePct',
        color="tpdFocus",
        title=f"Average Attendance Rate by {vocab_region} and Focus for {selected_year}",
        labels={"AttendanceRatePct": "Attendance Rate (%)", "tpdFocus": "PD Focus"}
    )

    ###########################################################################
    # Attendance Rate by Authority Group (Pie Chart)
    ###########################################################################
    grouped_authoritygroup = weighted_rates(filtered, ['AuthorityGroup'])
    grouped_authoritygroup['AttendanceRatePct'] = grouped_authoritygroup['AttendanceRate'] * 100

    fig_pd_authoritygroup = px.pie(
         grouped_authoritygroup,
         color_discrete_sequence=px.colors.qualitative.D3,
         names="AuthorityGroup",
         values="AttendanceRatePct",
         title=f"Average Attendance Rate by {vocab_authoritygovt} for {selected_year}",
         labels={"AuthorityGroup": vocab_authoritygovt, "AttendanceRatePct": "Attendance Rate (%)"}
    )

    ###########################################################################
    # Attendance Rate by Authority (Horizontal Bar Chart)
    ###########################################################################
    grouped_authority = weighted_rates(filtered, ['Authority', 'tpdFocus'])
    grouped_authority['AttendanceRatePct'] = grouped_authority['AttendanceRate'] * 100

    fig_pd_authority = px.bar(
        grouped_authority,
        x='AttendanceRatePct',
        y='Authority',
        color='tpdFocus',
        barmode="group",
        orientation="h",
        title=f"Average Attendance Rate by {vocab_authority} and Focus for {selected_year}",
        labels={
            "Authority": vocab_authority,
            "AttendanceRatePct": "Attendance Rate (%)",
            "tpdFocus": "PD Focus"
        }
    )

    ###########################################################################
    # Attendance Rate by School Types (Pie Chart)
    ###########################################################################
    grouped_schooltype = weighted_rates(filtered, ['SchoolType'])
    grouped_schooltype['AttendanceRatePct'] = grouped_schooltype['AttendanceRate'] * 100

    fig_pd_schooltype = px.pie(
         grouped_schooltype,
         color_discrete_sequence=px.colors.qualitative.D3,
         names="SchoolType",
         values="AttendanceRatePct",
         title=f"Average Attendance Rate by {vocab_schooltype} for {selected_year}",
         labels={"SchoolType": vocab_schooltype, "AttendanceRatePct": "Attendance Rate (%)"}
    )

    ###########################################################################
    # Attendance Rate by Format (Horizontal Bar Chart)
    ###########################################################################
    grouped_format = weighted_rates(filtered, ['tpdFormat', 'tpdFocus'])
    grouped_format['AttendanceRatePct'] = grouped_format['AttendanceRate'] * 100

    fig_pd_format = px.bar(
        grouped_format,
        y="tpdFormat",
        x="AttendanceRatePct",
        orientation='h',
        color='tpdFocus',
        title=f"Average Attendance Rate by Format and Focus for {selected_year}",
        labels={"AttendanceRatePct": "Attendance Rate (%)", "tpdFormat": "Format", "tpdFocus": "PD Focus"}
    )

    # success: hide alert (empty+False), hide spacer, show charts
    return (
        fig_pd_district_focus,
        fig_pd_district_trend,
        fig_pd_school_map,
        fig_pd_region,
        fig_pd_authoritygroup,
        fig_pd_authority,
        fig_pd_schooltype,
        fig_pd_format,
        "", False, {"display": "none"}, {}
    )

layout = teachers_pd_attendance_layout()
