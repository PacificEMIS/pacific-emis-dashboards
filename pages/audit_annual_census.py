import numpy as np
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
    vocab_region,
    lookup_dict,    
)

# Import data and lookup dictionary from the direct SQL module
from services.sql import (
    df_submission
)

from services.utilities import calculate_center, calculate_zoom

dash.register_page(__name__, path="/audit/annual-census", name="Annual Census Audit")

# Filters
# Extract survey years from lookup dictionary (assuming it contains a "surveyYears" key)
survey_years = lookup_dict.get("surveyYears", [])

# Create dropdown options using 'N' for display and 'C' for value
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]

# Determine the default value: the highest available year
default_year = max([int(item['C']) for item in survey_years], default=2024) 

# ✅ **Define Layout inside a Function**
def audit_overview_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Annual Census PDF Survey Audit"), width=12, className="m-1"),
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
            id="audit-overview-top-loading",
            type="default",
            children=html.Div(
                id="audit-overview-loading-spacer",
                style={"minHeight": "50vh"},
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="audit-overview-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),
        # Charts hidden by default; shown by callback when ready
        html.Div(id="audit-overview-content", style={"display": "none"}, children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id="audit-region-submission-rate-bar-chart"), md=6, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="audit-submission-timeliness-bar-chart"), md=6, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="audit-submission-rate-map"), md=6, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="audit-submission-timeliness-map"), md=6, xs=12, className="p-3"),
            ], className="m-1"),
        ]),
    ], fluid=True)

# Data processing
@dash.callback(
    Output(component_id="audit-region-submission-rate-bar-chart", component_property="figure"),
    Output(component_id="audit-submission-timeliness-bar-chart", component_property="figure"),
    Output(component_id="audit-submission-rate-map", component_property="figure"),
    Output(component_id="audit-submission-timeliness-map", component_property="figure"),
    # No data UX
    Output("audit-overview-nodata-msg", "children"),
    Output("audit-overview-nodata-msg", "is_open"),
    Output("audit-overview-loading-spacer", "style"),  # hide spacer when done; keep while loading/no-data
    Output("audit-overview-content", "style"),         # show charts when done
    Input(component_id="year-filter", component_property="value")
)
def update_dashboard(selected_year):
    if selected_year is None:
        empty_figs = ({}, {}, {}, {})
        # show alert, keep spacer visible, keep charts hidden
        return (*empty_figs, "No data", True, {}, {"display": "none"})
    
    ###########################################################################
    # Region Survey Submission Rate Bar Chart (Stacked Bars)
    ###########################################################################
    
    # Group by year and region
    region_grouped = (
        df_submission.groupby(["svyYear", "Region"])
        .agg(
            ActiveSchools=("schNo", "count"),
            SubmittedCount=("Submitted", "sum")
        )
        .reset_index()
    )

    # Compute submission rate
    region_grouped["SubmissionRatePercent"] = (
        100 * region_grouped["SubmittedCount"] / region_grouped["ActiveSchools"]
    ).round(1)

    region_grouped["svyYearLabel"] = region_grouped["svyYear"].astype(str)
    region_grouped.loc[region_grouped["svyYear"] == 2025, "svyYearLabel"] = "2025 (In Process)"

    fig_submission_progress = px.bar(
        region_grouped,
        x="svyYearLabel",
        y="SubmissionRatePercent",
        color="Region",
        barmode="group",
        text="SubmissionRatePercent",
        labels={
            "svyYearLabel": "Survey Year",
            "SubmissionRatePercent": "Submission Rate (%)",
            "Region": vocab_region
        },
        title="Submission Rate by Region Over Time"
    )

    fig_submission_progress.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_submission_progress.update_layout(
        yaxis=dict(range=[0, 110]),  # Make room for label above bars
        xaxis=dict(type='category'),
        legend_title_text=vocab_region
    )

    ###########################################################################
    # Survey Submission Timeliness Bar Chart
    ###########################################################################

    # Keep only submitted records with a valid timestamp
    df_timing = df_submission[df_submission["pCreateDateTime"].notna()].copy()

    # Calculate number of days after March 15
    df_timing["DaysSinceMarch15"] = (
        df_timing.apply(
            lambda row: (row["pCreateDateTime"] - pd.Timestamp(f"{row['svyYear']}-03-15")).days,
            axis=1
        )
    )

    # Group by year and compute stats
    timing_grouped = (
        df_timing.groupby("svyYear")["DaysSinceMarch15"]
        .agg(
            AvgDaysAfterMar15="mean",
            EarliestSubmission="min",
            LatestSubmission="max"
        )
        .round(1)
        .reset_index()
    )

    # Melt for multi-bar format (Plotly-friendly)
    timing_melted = timing_grouped.melt(
        id_vars="svyYear",
        value_vars=["AvgDaysAfterMar15", "EarliestSubmission", "LatestSubmission"],
        var_name="Metric",
        value_name="Days"
    )
    
    # Replace 2025 label with "2025 (In Process)"
    timing_melted["svyYearLabel"] = timing_melted["svyYear"].astype(str)
    timing_melted.loc[timing_melted["svyYear"] == 2025, "svyYearLabel"] = "2025 (In Process)"

    # Replace column names for nicer display
    label_map = {
        "AvgDaysAfterMar15": "Average number of days after March 15",
        "EarliestSubmission": "Earliest number day after March 15",
        "LatestSubmission": "Latest number of day after March 15"
    }
    timing_melted["Metric"] = timing_melted["Metric"].map(label_map)

    # Plot trend line chart
    fig_submission_timeliness = px.line(
        timing_melted,
        x="svyYearLabel",
        y="Days",
        color="Metric",
        markers=True,
        text="Days",
        title="Submission Timeliness Trend (Days After March 15 Annual Survey Submitted)",
        labels={
            "svyYear": "Survey Year",
            "Days": "Days After March 15",
            "Metric": "Timing Metric"
        }
    )

    fig_submission_timeliness.update_traces(textposition="top center")
    fig_submission_timeliness.update_layout(
        yaxis=dict(title="Days After March 15", rangemode="tozero"),
        xaxis=dict(type="category"),
        legend_title_text="Metric"
    )
    
    ###########################################################################
    # Submission Status Map by School
    ###########################################################################

    # Use fallback coordinates if missing
    df_submission["schLat"] = df_submission["schLat"].fillna(1.431943)
    df_submission["schLong"] = df_submission["schLong"].fillna(172.992563)

    # Filter for selected year
    df_map = df_submission[df_submission["svyYear"] == selected_year].copy()

    # If no rows for the selected year, show no data message
    if df_map.empty:
        empty_figs = ({}, {}, {}, {})
        return (*empty_figs, f"No data available for {selected_year}.", True, {}, {"display": "none"})

    # Coordinates
    coords = list(zip(df_map["schLat"], df_map["schLong"]))
    center_lat, center_lon = calculate_center(coords)
    zoom = calculate_zoom(coords)

    # Prepare data
    df_map["SubmissionStatus"] = df_map["Submitted"].map({1: "Submitted", 0: "Not Submitted"})

    fig_submission_map = px.scatter_mapbox(
        df_map,
        lat="schLat",
        lon="schLong",
        color="SubmissionStatus",
        hover_name="schName",
        size=[10]*len(df_map),  # uniform size for now
        zoom=zoom,
        title=f"Submission Status by School – {selected_year}",
        category_orders={"SubmissionStatus": ["Submitted", "Not Submitted"]}
    )

    fig_submission_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=zoom,
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    ###########################################################################
    # Submission Timeliness Map
    ###########################################################################

    df_timely_map = df_map[df_map["pCreateDateTime"].notna()].copy()
    df_timely_map["DaysSinceMarch15"] = (
        df_timely_map.apply(
            lambda row: (row["pCreateDateTime"] - pd.Timestamp(f"{row['svyYear']}-03-15")).days,
            axis=1
        )
    )

    fig_timeliness_map = px.scatter_mapbox(
        df_timely_map,
        lat="schLat",
        lon="schLong",
        size="DaysSinceMarch15",
        color="DaysSinceMarch15",
        color_continuous_scale="YlOrRd",
        hover_name="schName",
        size_max=15,
        title=f"Submission Timeliness by School – {selected_year}"
    )

    fig_timeliness_map.update_layout(
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_zoom=zoom,
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    fig_timeliness_map.update_coloraxes(colorbar_title="Days After Mar 15")

    # success: hide alert, hide spacer, show charts
    return (
        fig_submission_progress,
        fig_submission_timeliness,
        fig_submission_map,
        fig_timeliness_map,
        "", False, {"display": "none"}, {}
    )

layout = audit_overview_layout()
