import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Import the PD data
from services.api import (
    get_df_teacherpdx,
    vocab_district,      # kept (unused in figures now, but leaving import unchanged)
    vocab_region,        # kept (unused)
    vocab_authority,     # kept (unused)
    vocab_authoritygovt, # kept (unused)
    vocab_schooltype,    # kept (unused)
    lookup_dict,
)
df_teacherpdx = get_df_teacherpdx()

from services.utilities import calculate_center, calculate_zoom  # kept (unused now, but leaving import unchanged)

dash.register_page(__name__, path="/teacherpd/overview", name="Teacher PD Overview")

# Filters
survey_years = lookup_dict.get("surveyYears", [])

year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
default_year = max([int(item['C']) for item in survey_years], default=2024)

# Event-centric helpers (unique events)
UNIQUE_EVENT_KEYS = ["tpdName","tpdFormat","tpdFocus","tpdLocation","SurveyYear"]
LOCATION_LABEL = "Location"  # simple label so titles read well

def _build_unique_events(df_like: pd.DataFrame) -> pd.DataFrame:
    """Return one row per unique event based on EXACT keys (no trimming/casefold)."""
    if df_like is None or df_like.empty:
        return df_like
    ev = (
        df_like.dropna(subset=UNIQUE_EVENT_KEYS, how="any")
               .drop_duplicates(subset=UNIQUE_EVENT_KEYS)
               .copy()
    )
    ev["EventID"] = ev[UNIQUE_EVENT_KEYS].astype(str).agg("||".join, axis=1)
    return ev

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
        # No data message + spinner host centered in a reserved spacer (prevents footer jump)
        dcc.Loading(
            id="pd-overview-top-loading",
            type="default",
            children=html.Div(
                id="pd-overview-loading-spacer",
                style={"minHeight": "50vh"},
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="pd-overview-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),
        # Charts hidden by default; shown by callback when ready
        html.Div(id="pd-overview-content", style={"display": "none"}, children=[

            ###################################################################
            # Unique PD Events table (summary)
            ###################################################################
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            html.Strong(
                                                id="pd-overview-events-title",
                                                children=f"Summary PD Events from {default_year}"
                                            ),
                                            width="auto"
                                        ),
                                        dbc.Col(
                                            dbc.Badge(id="pd-overview-events-count", color="primary", className="ms-2"),
                                            width="auto",
                                            className="d-flex align-items-center"
                                        ),
                                    ],
                                    className="g-2 flex-nowrap"
                                )
                            ),
                            dbc.CardBody(
                                dash_table.DataTable(
                                    id="pd-overview-events-table",
                                    columns=[
                                        {"name": "Survey Year", "id": "SurveyYear"},
                                        {"name": "Event Name", "id": "tpdName"},
                                        {"name": "Format", "id": "tpdFormat"},
                                        {"name": "Focus", "id": "tpdFocus"},
                                        {"name": "Location", "id": "tpdLocation"},
                                    ],
                                    data=[],
                                    page_size=15,
                                    sort_action="native",
                                    filter_action="native",
                                    #export_format="csv",
                                    style_table={"overflowX": "auto"},
                                    style_cell={"whiteSpace": "normal", "height": "auto"},
                                )
                            ),
                        ],
                        className="mb-2"
                    ),
                    md=12, xs=12, className="p-3"
                ),
            ], className="m-1"),

            # Row 1: Event Name — Pie (left) + Trend (right)
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-overview-region-bar-chart"), md=6, xs=12, className="p-3"),         # Event Name (Pie)
                dbc.Col(dcc.Graph(id="pd-overview-district-trend-chart"), md=6, xs=12, className="p-3"),      # Event Name (Trend)
            ], className="m-1"),

            # Row 2: Format — Pie (left) + Trend (right)
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-overview-authoritygroup-pie-chart"), md=6, xs=12, className="p-3"),  # Format (Pie)
                dbc.Col(dcc.Graph(id="pd-overview-authority-bar-chart"), md=6, xs=12, className="p-3"),       # Format (Trend)
            ], className="m-1"),

            # Row 3: Focus — Pie (left) + Trend (right)
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-overview-schooltype-pie-chart"), md=6, xs=12, className="p-3"),      # Focus (Pie)
                dbc.Col(dcc.Graph(id="pd-overview-years-teaching-bar-chart"), md=6, xs=12, className="p-3"),  # Focus (Trend)
            ], className="m-1"),

            # Row 4: Location — Pie (left) + Trend (right)
            dbc.Row([
                dbc.Col(dcc.Graph(id="pd-overview-district-focus-bar-chart"), md=6, xs=12, className="p-3"),  # Location (Pie)
                dbc.Col(dcc.Graph(id="pd-overview-school-map-chart"), md=6, xs=12, className="p-3"),          # Location (Trend)
            ], className="m-1"),
        ]),
    ], fluid=True)

@dash.callback(
    Output("pd-overview-events-title", "children"),

    # Table + count badge
    Output("pd-overview-events-table", "data"),
    Output("pd-overview-events-count", "children"),

    # Row 1 (Event Name): Pie + Trend
    Output("pd-overview-region-bar-chart", "figure"),
    Output("pd-overview-district-trend-chart", "figure"),

    # Row 2 (Format): Pie + Trend
    Output("pd-overview-authoritygroup-pie-chart", "figure"),
    Output("pd-overview-authority-bar-chart", "figure"),

    # Row 3 (Focus): Pie + Trend
    Output("pd-overview-schooltype-pie-chart", "figure"),
    Output("pd-overview-years-teaching-bar-chart", "figure"),

    # Row 4 (Location): Pie + Trend
    Output("pd-overview-district-focus-bar-chart", "figure"),
    Output("pd-overview-school-map-chart", "figure"),

    # No data UX
    Output("pd-overview-nodata-msg", "children"),
    Output("pd-overview-nodata-msg", "is_open"),
    Output("pd-overview-loading-spacer", "style"),  # hide spacer when done; keep while loading/no-data
    Output("pd-overview-content", "style"),         # show charts when done
    # Inputs
    Input("year-filter-pd-overview", "value"),
    Input("warehouse-version-store", "data"),   # <— triggers when warehouse version changes
)
def update_pd_events_dashboard(selected_year, _warehouse_version):
    # Dynamic Title
    title_str = f"Summary PD Events from {selected_year if selected_year is not None else default_year}"
    
    # (no logic change needed; the extra Input just retriggers when version changes)
    if selected_year is None:
        empty_figs = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (title_str, [], "0",
                *empty_figs,
                "No data", True, {}, {"display": "none"})

    # Get latest DF and guard against None/empty
    df = get_df_teacherpdx()
    if df is None or df.empty:
        empty_figs = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (title_str, [], "0",
                *empty_figs,
                "No data available.", True, {}, {"display": "none"})

    # Filter the PD dataset
    filtered = df[df['SurveyYear'] == selected_year].copy()
    if filtered.empty:
        empty_figs = ({}, {}, {}, {}, {}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (title_str, [], "0",
                *empty_figs,
                f"No data available for {selected_year}.", True, {}, {"display": "none"})

    # ---- Unique events table data & count (based on exact uniqueness rule) ----
    # Uniqueness keys: [tpdName, tpdFormat, tpdFocus, tpdLocation, SurveyYear]
    ev_unique = _build_unique_events(filtered)
    unique_events_df = (
        ev_unique.loc[:, ["SurveyYear", "tpdName", "tpdFormat", "tpdFocus", "tpdLocation"]]
                  .sort_values(["SurveyYear", "tpdName"])
                  .reset_index(drop=True)
    )
    unique_events_data = unique_events_df.to_dict("records")
    unique_events_count = str(len(unique_events_df))

    # For trends we need all years (event-centric)
    ev_all_years = _build_unique_events(df)

    ###########################################################################
    # Row 1 — Event Name (Pie) + Event Name over time (Trend)
    ###########################################################################
    grouped_name_pie = (
        ev_unique.groupby('tpdName', as_index=False)
                 .size().rename(columns={'size':'Events'})
                 .sort_values('Events', ascending=False)
    )
    fig_name_pie = px.pie(
        grouped_name_pie,
        names="tpdName",
        values="Events",
        color_discrete_sequence=px.colors.qualitative.D3,
        title=f"PD Events by Event Name for {selected_year}",
        labels={"tpdName": "Event Name", "Events": "Number of PD Events"}
    )

    grouped_name_trend = (
        ev_all_years.groupby(['SurveyYear','tpdName'], as_index=False)
                    .size().rename(columns={'size':'Events'})
                    .sort_values(['tpdName','SurveyYear'])
    )
    fig_name_trend = px.line(
        grouped_name_trend,
        x='SurveyYear',
        y='Events',
        color='tpdName',
        line_group='tpdName',
        markers=True,
        title="PD Events by Event Name Over Time",
        labels={"SurveyYear": "Year", "Events": "Number of PD Events", "tpdName": "Event Name"}
    )
    fig_name_trend.update_xaxes(tickmode="linear", dtick=1, tickformat="d")

    ###########################################################################
    # Row 2 — Format (Pie) + Format over time (Trend)
    ###########################################################################
    grouped_format_pie = (
        ev_unique.groupby('tpdFormat', as_index=False)
                 .size().rename(columns={'size':'Events'})
                 .sort_values('Events', ascending=False)
    )
    fig_format_pie = px.pie(
        grouped_format_pie,
        names="tpdFormat",
        values="Events",
        color_discrete_sequence=px.colors.qualitative.D3,
        title=f"PD Events by Format for {selected_year}",
        labels={"tpdFormat": "PD Format", "Events": "Number of PD Events"}
    )

    grouped_format_trend = (
        ev_all_years.groupby(['SurveyYear','tpdFormat'], as_index=False)
                    .size().rename(columns={'size':'Events'})
                    .sort_values(['tpdFormat','SurveyYear'])
    )
    fig_format_trend = px.line(
        grouped_format_trend,
        x='SurveyYear',
        y='Events',
        color='tpdFormat',
        line_group='tpdFormat',
        markers=True,
        title="PD Events by Format Over Time",
        labels={"SurveyYear": "Year", "Events": "Number of PD Events", "tpdFormat": "PD Format"}
    )
    fig_format_trend.update_xaxes(tickmode="linear", dtick=1, tickformat="d")

    ###########################################################################
    # Row 3 — Focus (Pie) + Focus over time (Trend)
    ###########################################################################
    grouped_focus_pie = (
        ev_unique.groupby('tpdFocus', as_index=False)
                 .size().rename(columns={'size':'Events'})
                 .sort_values('Events', ascending=False)
    )
    fig_focus_pie = px.pie(
        grouped_focus_pie,
        names="tpdFocus",
        values="Events",
        color_discrete_sequence=px.colors.qualitative.D3,
        title=f"PD Events by Focus for {selected_year}",
        labels={"tpdFocus": "PD Focus", "Events": "Number of PD Events"}
    )

    grouped_focus_trend = (
        ev_all_years.groupby(['SurveyYear','tpdFocus'], as_index=False)
                    .size().rename(columns={'size':'Events'})
                    .sort_values(['tpdFocus','SurveyYear'])
    )
    fig_focus_trend = px.line(
        grouped_focus_trend,
        x='SurveyYear',
        y='Events',
        color='tpdFocus',
        line_group='tpdFocus',
        markers=True,
        title="PD Events by Focus Over Time",
        labels={"SurveyYear": "Year", "Events": "Number of PD Events", "tpdFocus": "PD Focus"}
    )
    fig_focus_trend.update_xaxes(tickmode="linear", dtick=1, tickformat="d")

    ###########################################################################
    # Row 4 — Location (Pie) + Location over time (Trend)
    ###########################################################################
    grouped_loc_pie = (
        ev_unique.groupby('tpdLocation', as_index=False)
                 .size().rename(columns={'size':'Events'})
                 .sort_values('Events', ascending=False)
    )
    fig_loc_pie = px.pie(
        grouped_loc_pie,
        names="tpdLocation",
        values="Events",
        color_discrete_sequence=px.colors.qualitative.D3,
        title=f"PD Events by {LOCATION_LABEL} for {selected_year}",
        labels={"tpdLocation": LOCATION_LABEL, "Events": "Number of PD Events"}
    )

    grouped_loc_trend = (
        ev_all_years.groupby(['SurveyYear','tpdLocation'], as_index=False)
                    .size().rename(columns={'size':'Events'})
                    .sort_values(['tpdLocation','SurveyYear'])
    )
    fig_loc_trend = px.line(
        grouped_loc_trend,
        x='SurveyYear',
        y='Events',
        color='tpdLocation',
        line_group='tpdLocation',
        markers=True,
        title=f"PD Events by {LOCATION_LABEL} Over Time",
        labels={"SurveyYear": "Year", "Events": "Number of PD Events", "tpdLocation": LOCATION_LABEL}
    )
    fig_loc_trend.update_xaxes(tickmode="linear", dtick=1, tickformat="d")

    # success: hide alert, hide spacer, show charts
    return (
        title_str,
        unique_events_data,
        unique_events_count,
        # Row 1: Event Name (Pie) + Trend
        fig_name_pie,
        fig_name_trend,
        # Row 2: Format (Pie) + Trend
        fig_format_pie,
        fig_format_trend,
        # Row 3: Focus (Pie) + Trend
        fig_focus_pie,
        fig_focus_trend,
        # Row 4: Location (Pie) + Trend
        fig_loc_pie,
        fig_loc_trend,
        "", False, {"display": "none"}, {}
    )

layout = teachers_pd_events_layout()
