import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Import data and lookup dictionary from the API module
from services.api import (
    get_df_specialed,
    get_latest_year_with_data,
    district_lookup,
    authoritygovts_lookup,
    schooltypes_lookup,
    vocab_district,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,
)

dash.register_page(__name__, path="/specialed/overview", name="Special Education Overview")

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{"label": item["N"], "value": item["C"]} for item in survey_years]
# Use the latest year that actually has data, not just the max year in the list
default_year = get_latest_year_with_data(get_df_specialed())


def specialed_overview_layout():
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(html.H1("Special Education Overview"), width=12, className="m-1"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="specialed-year-filter",
                            options=year_options,
                            value=default_year,
                            clearable=False,
                            style={"width": "200px"},
                        ),
                        className="m-1",
                    )
                ]
            ),
            # Loading spinner and no-data alert
            dcc.Loading(
                id="specialed-overview-top-loading",
                type="default",
                children=html.Div(
                    id="specialed-overview-loading-spacer",
                    style={"minHeight": "50vh"},
                    children=dbc.Row(
                        [
                            dbc.Col(
                                dbc.Alert(
                                    id="specialed-overview-nodata-msg",
                                    color="warning",
                                    is_open=False,
                                ),
                                width=12,
                                className="m-1",
                            ),
                        ]
                    ),
                ),
            ),
            # Charts hidden by default; shown by callback when ready
            html.Div(
                id="specialed-overview-content",
                style={"display": "none"},
                children=[
                    # Row 1: Disability and Ethnicity charts
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="specialed-disability-chart"),
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="specialed-ethnicity-chart"),
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Row 2: Environment and English Learner charts
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="specialed-environment-chart"),
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="specialed-englishlearner-chart"),
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Row 3: District chart
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="specialed-district-chart"),
                                md=12,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Cross-tabulation tables
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5("Special Education Students by Disability and Gender"),
                                    dash_table.DataTable(
                                        id="specialed-disability-table",
                                        style_table={"overflowX": "auto"},
                                        style_header={
                                            "textAlign": "center",
                                            "fontWeight": "bold",
                                        },
                                        style_cell={"textAlign": "left"},
                                        style_data_conditional=[
                                            {
                                                "if": {"column_id": "Total"},
                                                "fontWeight": "bold",
                                            }
                                        ],
                                    ),
                                ],
                                md=12,
                                className="m-1",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5("Special Education Students by Environment and Gender"),
                                    dash_table.DataTable(
                                        id="specialed-environment-table",
                                        style_table={"overflowX": "auto"},
                                        style_header={
                                            "textAlign": "center",
                                            "fontWeight": "bold",
                                        },
                                        style_cell={"textAlign": "left"},
                                        style_data_conditional=[
                                            {
                                                "if": {"column_id": "Total"},
                                                "fontWeight": "bold",
                                            }
                                        ],
                                    ),
                                ],
                                md=12,
                                className="m-1",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5(f"Special Education Students by {vocab_district} and Gender"),
                                    dash_table.DataTable(
                                        id="specialed-district-table",
                                        style_table={"overflowX": "auto"},
                                        style_header={
                                            "textAlign": "center",
                                            "fontWeight": "bold",
                                        },
                                        style_cell={"textAlign": "left"},
                                        style_data_conditional=[
                                            {
                                                "if": {"column_id": "Total"},
                                                "fontWeight": "bold",
                                            }
                                        ],
                                    ),
                                ],
                                md=12,
                                className="m-1",
                            ),
                        ]
                    ),
                ],
            ),
        ],
        fluid=True,
    )


@dash.callback(
    Output("specialed-disability-chart", "figure"),
    Output("specialed-ethnicity-chart", "figure"),
    Output("specialed-environment-chart", "figure"),
    Output("specialed-englishlearner-chart", "figure"),
    Output("specialed-district-chart", "figure"),
    Output("specialed-disability-table", "data"),
    Output("specialed-disability-table", "columns"),
    Output("specialed-environment-table", "data"),
    Output("specialed-environment-table", "columns"),
    Output("specialed-district-table", "data"),
    Output("specialed-district-table", "columns"),
    # No data UX
    Output("specialed-overview-nodata-msg", "children"),
    Output("specialed-overview-nodata-msg", "is_open"),
    Output("specialed-overview-loading-spacer", "style"),
    Output("specialed-overview-content", "style"),
    Input("specialed-year-filter", "value"),
    Input("warehouse-version-store", "data"),
)
def update_specialed_dashboard(selected_year, _warehouse_version):
    empty_charts = ({}, {}, {}, {}, {})
    empty_tables = ([], [], [], [], [], [])

    if selected_year is None:
        return (
            *empty_charts,
            *empty_tables,
            "No year selected.",
            True,
            {},
            {"display": "none"},
        )

    # Fetch data
    df = get_df_specialed()

    if df is None or df.empty:
        return (
            *empty_charts,
            *empty_tables,
            "No data available.",
            True,
            {},
            {"display": "none"},
        )

    # Filter for selected year
    filtered = df[df["SurveyYear"] == selected_year].copy()
    if filtered.empty:
        return (
            *empty_charts,
            *empty_tables,
            f"No data available for {selected_year}.",
            True,
            {},
            {"display": "none"},
        )

    # Ensure Num column is numeric
    filtered["Num"] = pd.to_numeric(filtered["Num"], errors="coerce").fillna(0)

    # Apply lookups for friendly names where needed
    filtered["DistrictName"] = (
        filtered["DistrictCode"].map(district_lookup).fillna(filtered.get("District", "Unknown"))
        if "DistrictCode" in filtered.columns
        else filtered.get("District", "Unknown")
    )

    # Use name columns directly, fill None with "Not Specified"
    filtered["DisabilityName"] = filtered["Disability"].fillna("Not Specified") if "Disability" in filtered.columns else "Not Specified"
    filtered["EthnicityName"] = filtered["Ethnicity"].fillna("Not Specified") if "Ethnicity" in filtered.columns else "Not Specified"
    filtered["EnvironmentName"] = filtered["Environment"].fillna("Not Specified") if "Environment" in filtered.columns else "Not Specified"
    filtered["EnglishLearnerName"] = filtered["EnglishLearner"].fillna("Not Specified") if "EnglishLearner" in filtered.columns else "Not Specified"
    # Gender column already contains "Male"/"Female" values, just fill nulls
    filtered["GenderName"] = filtered["Gender"].fillna("Unknown") if "Gender" in filtered.columns else "Unknown"

    ###########################################################################
    # Chart 1: Students by Disability (horizontal bar with gender)
    ###########################################################################
    grouped_disability = (
        filtered.groupby(["DisabilityName", "GenderName"])["Num"]
        .sum()
        .reset_index()
        .rename(columns={"Num": "Students"})
    )

    fig_disability = px.bar(
        grouped_disability,
        y="DisabilityName",
        x="Students",
        color="GenderName",
        orientation="h",
        barmode="stack",
        title=f"Special Ed Students by Disability in {selected_year}",
        labels={
            "DisabilityName": "Disability",
            "Students": "Number of Students",
            "GenderName": "Gender",
        },
        color_discrete_map={"Male": "#1f77b4", "Female": "#e377c2"},
    )

    ###########################################################################
    # Chart 2: Students by Ethnicity (horizontal bar with gender)
    ###########################################################################
    grouped_ethnicity = (
        filtered.groupby(["EthnicityName", "GenderName"])["Num"]
        .sum()
        .reset_index()
        .rename(columns={"Num": "Students"})
    )

    fig_ethnicity = px.bar(
        grouped_ethnicity,
        y="EthnicityName",
        x="Students",
        color="GenderName",
        orientation="h",
        barmode="stack",
        title=f"Special Ed Students by Ethnicity in {selected_year}",
        labels={
            "EthnicityName": "Ethnicity",
            "Students": "Number of Students",
            "GenderName": "Gender",
        },
        color_discrete_map={"Male": "#1f77b4", "Female": "#e377c2"},
    )

    ###########################################################################
    # Chart 3: Students by Environment (horizontal bar with gender)
    ###########################################################################
    grouped_environment = (
        filtered.groupby(["EnvironmentName", "GenderName"])["Num"]
        .sum()
        .reset_index()
        .rename(columns={"Num": "Students"})
    )

    fig_environment = px.bar(
        grouped_environment,
        y="EnvironmentName",
        x="Students",
        color="GenderName",
        orientation="h",
        barmode="stack",
        title=f"Special Ed Students by Environment in {selected_year}",
        labels={
            "EnvironmentName": "Environment",
            "Students": "Number of Students",
            "GenderName": "Gender",
        },
        color_discrete_map={"Male": "#1f77b4", "Female": "#e377c2"},
    )

    ###########################################################################
    # Chart 4: Students by English Learner Status (horizontal bar with gender)
    ###########################################################################
    grouped_englishlearner = (
        filtered.groupby(["EnglishLearnerName", "GenderName"])["Num"]
        .sum()
        .reset_index()
        .rename(columns={"Num": "Students"})
    )

    fig_englishlearner = px.bar(
        grouped_englishlearner,
        y="EnglishLearnerName",
        x="Students",
        color="GenderName",
        orientation="h",
        barmode="stack",
        title=f"Special Ed Students by English Learner Status in {selected_year}",
        labels={
            "EnglishLearnerName": "English Learner Status",
            "Students": "Number of Students",
            "GenderName": "Gender",
        },
        color_discrete_map={"Male": "#1f77b4", "Female": "#e377c2"},
    )

    ###########################################################################
    # Chart 5: Students by District (horizontal bar with gender)
    ###########################################################################
    grouped_district = (
        filtered.groupby(["DistrictName", "GenderName"])["Num"]
        .sum()
        .reset_index()
        .rename(columns={"Num": "Students"})
    )

    fig_district = px.bar(
        grouped_district,
        y="DistrictName",
        x="Students",
        color="GenderName",
        orientation="h",
        barmode="stack",
        title=f"Special Ed Students by {vocab_district} in {selected_year}",
        labels={
            "DistrictName": vocab_district,
            "Students": "Number of Students",
            "GenderName": "Gender",
        },
        color_discrete_map={"Male": "#1f77b4", "Female": "#e377c2"},
    )

    ###########################################################################
    # Table 1: Disability by Gender (pivot Num by GenderName)
    ###########################################################################
    table_disability = filtered.pivot_table(
        index="DisabilityName",
        columns="GenderName",
        values="Num",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    # Ensure Male/Female columns exist
    for col in ["Male", "Female"]:
        if col not in table_disability.columns:
            table_disability[col] = 0
    table_disability["Total"] = table_disability["Male"] + table_disability["Female"]
    table_disability = table_disability.rename(columns={"DisabilityName": "Disability"})
    # Reorder columns
    table_disability = table_disability[["Disability", "Male", "Female", "Total"]]
    # Add grand total row
    grand_total = table_disability[["Male", "Female", "Total"]].sum().to_frame().T
    grand_total["Disability"] = "Grand Total"
    table_disability = pd.concat([table_disability, grand_total], ignore_index=True)

    table1_columns = [{"name": c, "id": c} for c in table_disability.columns]
    table1_data = table_disability.to_dict("records")

    ###########################################################################
    # Table 2: Environment by Gender (pivot Num by GenderName)
    ###########################################################################
    table_environment = filtered.pivot_table(
        index="EnvironmentName",
        columns="GenderName",
        values="Num",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    # Ensure Male/Female columns exist
    for col in ["Male", "Female"]:
        if col not in table_environment.columns:
            table_environment[col] = 0
    table_environment["Total"] = table_environment["Male"] + table_environment["Female"]
    table_environment = table_environment.rename(columns={"EnvironmentName": "Environment"})
    # Reorder columns
    table_environment = table_environment[["Environment", "Male", "Female", "Total"]]
    # Add grand total row
    grand_total2 = table_environment[["Male", "Female", "Total"]].sum().to_frame().T
    grand_total2["Environment"] = "Grand Total"
    table_environment = pd.concat([table_environment, grand_total2], ignore_index=True)

    table2_columns = [{"name": c, "id": c} for c in table_environment.columns]
    table2_data = table_environment.to_dict("records")

    ###########################################################################
    # Table 3: District by Gender (pivot Num by GenderName)
    ###########################################################################
    table_district = filtered.pivot_table(
        index="DistrictName",
        columns="GenderName",
        values="Num",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    # Ensure Male/Female columns exist
    for col in ["Male", "Female"]:
        if col not in table_district.columns:
            table_district[col] = 0
    table_district["Total"] = table_district["Male"] + table_district["Female"]
    table_district = table_district.rename(columns={"DistrictName": vocab_district})
    # Reorder columns
    table_district = table_district[[vocab_district, "Male", "Female", "Total"]]
    # Add grand total row
    grand_total3 = table_district[["Male", "Female", "Total"]].sum().to_frame().T
    grand_total3[vocab_district] = "Grand Total"
    table_district = pd.concat([table_district, grand_total3], ignore_index=True)

    table3_columns = [{"name": c, "id": c} for c in table_district.columns]
    table3_data = table_district.to_dict("records")

    # Success: hide alert, hide spacer, show content
    return (
        fig_disability,
        fig_ethnicity,
        fig_environment,
        fig_englishlearner,
        fig_district,
        table1_data,
        table1_columns,
        table2_data,
        table2_columns,
        table3_data,
        table3_columns,
        "",
        False,
        {"display": "none"},
        {},
    )


layout = specialed_overview_layout()
