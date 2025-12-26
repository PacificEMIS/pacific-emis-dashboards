import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Import data and lookup dictionary from the API module
from services.api import (
    get_df_schoolcount,
    get_latest_year_with_data,
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

dash.register_page(__name__, path="/schools/overview", name="Schools Overview")

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{"label": item["N"], "value": item["C"]} for item in survey_years]
# Use the latest year that actually has data, not just the max year in the list
default_year = get_latest_year_with_data(get_df_schoolcount())


def schools_overview_layout():
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(html.H1("Schools Overview"), width=12, className="m-1"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="schools-year-filter",
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
                id="schools-overview-top-loading",
                type="default",
                children=html.Div(
                    id="schools-overview-loading-spacer",
                    style={"minHeight": "50vh"},
                    children=dbc.Row(
                        [
                            dbc.Col(
                                dbc.Alert(
                                    id="schools-overview-nodata-msg",
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
                id="schools-overview-content",
                style={"display": "none"},
                children=[
                    # Row 1: District chart (full width)
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="schools-district-chart"),
                                md=12,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Row 2: Region and School Type charts
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="schools-region-chart"),
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="schools-schooltype-chart"),
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Row 3: Authority Group and Authority charts
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="schools-authgovt-chart"),
                                md=4,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="schools-authority-chart"),
                                md=8,
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
                                    html.H5(f"Schools by {vocab_district} and {vocab_schooltype}"),
                                    dash_table.DataTable(
                                        id="schools-district-schooltype-table",
                                        merge_duplicate_headers=True,
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
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5(
                                        f"Schools by {vocab_schooltype} and {vocab_authoritygovt}"
                                    ),
                                    dash_table.DataTable(
                                        id="schools-schooltype-authgovt-table",
                                        merge_duplicate_headers=True,
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
                            )
                        ]
                    ),
                ],
            ),
        ],
        fluid=True,
    )


@dash.callback(
    Output("schools-district-chart", "figure"),
    Output("schools-region-chart", "figure"),
    Output("schools-authgovt-chart", "figure"),
    Output("schools-authority-chart", "figure"),
    Output("schools-schooltype-chart", "figure"),
    Output("schools-district-schooltype-table", "data"),
    Output("schools-district-schooltype-table", "columns"),
    Output("schools-schooltype-authgovt-table", "data"),
    Output("schools-schooltype-authgovt-table", "columns"),
    # No data UX
    Output("schools-overview-nodata-msg", "children"),
    Output("schools-overview-nodata-msg", "is_open"),
    Output("schools-overview-loading-spacer", "style"),
    Output("schools-overview-content", "style"),
    Input("schools-year-filter", "value"),
    Input("warehouse-version-store", "data"),
)
def update_schools_dashboard(selected_year, _warehouse_version):
    empty_charts = ({}, {}, {}, {}, {})
    empty_tables = ([], [], [], [])

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
    df = get_df_schoolcount()
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

    # Apply lookups for friendly names
    # Standard convention: Name column (e.g. District) and Code column (e.g. DistrictCode)
    # Use code with lookup if available, otherwise fall back to name column
    filtered["DistrictName"] = (
        filtered["DistrictCode"].map(district_lookup).fillna(filtered.get("District", "Unknown"))
        if "DistrictCode" in filtered.columns
        else filtered.get("District", "Unknown")
    )

    filtered["RegionName"] = (
        filtered["RegionCode"].map(region_lookup).fillna(filtered.get("Region", "Unknown"))
        if "RegionCode" in filtered.columns
        else filtered.get("Region", "Unknown")
    )

    filtered["AuthorityName"] = (
        filtered["AuthorityCode"].map(authorities_lookup).fillna(filtered.get("Authority", "Unknown"))
        if "AuthorityCode" in filtered.columns
        else filtered.get("Authority", "Unknown")
    )

    filtered["AuthorityGroupName"] = (
        filtered["AuthorityGroupCode"].map(authoritygovts_lookup).fillna(filtered.get("AuthorityGroup", "Unknown"))
        if "AuthorityGroupCode" in filtered.columns
        else filtered.get("AuthorityGroup", "Unknown")
    )

    filtered["SchoolTypeName"] = (
        filtered["SchoolTypeCode"].map(schooltypes_lookup).fillna(filtered.get("SchoolType", "Unknown"))
        if "SchoolTypeCode" in filtered.columns
        else filtered.get("SchoolType", "Unknown")
    )

    ###########################################################################
    # Chart 1: Schools by District (stacked by School Type)
    ###########################################################################
    grouped_district = (
        filtered.groupby(["DistrictName", "SchoolTypeName"])["NumSchools"]
        .sum()
        .reset_index()
    )
    fig_district = px.bar(
        grouped_district,
        x="DistrictName",
        y="NumSchools",
        color="SchoolTypeName",
        barmode="stack",
        title=f"Schools by {vocab_district} in {selected_year}",
        labels={
            "DistrictName": vocab_district,
            "NumSchools": "Number of Schools",
            "SchoolTypeName": vocab_schooltype,
        },
        color_discrete_sequence=px.colors.qualitative.D3,
    )
    fig_district.update_layout(xaxis_tickangle=-45)

    ###########################################################################
    # Chart 2: Schools by Region (stacked by School Type)
    ###########################################################################
    # Check if we have Region data (either code or name column)
    has_region = "RegionCode" in df.columns or "Region" in df.columns
    if has_region and filtered["RegionName"].notna().any():
        grouped_region = (
            filtered.groupby(["RegionName", "SchoolTypeName"])["NumSchools"]
            .sum()
            .reset_index()
        )
        fig_region = px.bar(
            grouped_region,
            x="RegionName",
            y="NumSchools",
            color="SchoolTypeName",
            barmode="stack",
            title=f"Schools by {vocab_region} in {selected_year}",
            labels={
                "RegionName": vocab_region,
                "NumSchools": "Number of Schools",
                "SchoolTypeName": vocab_schooltype,
            },
            color_discrete_sequence=px.colors.qualitative.D3,
        )
    else:
        fig_region = {}

    ###########################################################################
    # Chart 3: Schools by Authority Group (pie chart)
    ###########################################################################
    grouped_authgovt = (
        filtered.groupby("AuthorityGroupName")["NumSchools"].sum().reset_index()
    )
    fig_authgovt = px.pie(
        grouped_authgovt,
        names="AuthorityGroupName",
        values="NumSchools",
        title=f"Schools by {vocab_authoritygovt} in {selected_year}",
        labels={
            "AuthorityGroupName": vocab_authoritygovt,
            "NumSchools": "Number of Schools",
        },
        color_discrete_sequence=px.colors.qualitative.D3,
    )

    ###########################################################################
    # Chart 4: Schools by Authority (horizontal stacked by School Type)
    ###########################################################################
    grouped_authority = (
        filtered.groupby(["AuthorityName", "SchoolTypeName"])["NumSchools"]
        .sum()
        .reset_index()
    )
    fig_authority = px.bar(
        grouped_authority,
        y="AuthorityName",
        x="NumSchools",
        color="SchoolTypeName",
        barmode="stack",
        orientation="h",
        title=f"Schools by {vocab_authority} in {selected_year}",
        labels={
            "AuthorityName": vocab_authority,
            "NumSchools": "Number of Schools",
            "SchoolTypeName": vocab_schooltype,
        },
        color_discrete_sequence=px.colors.qualitative.D3,
    )

    ###########################################################################
    # Chart 5: Schools by School Type (pie chart)
    ###########################################################################
    grouped_schooltype = (
        filtered.groupby("SchoolTypeName")["NumSchools"].sum().reset_index()
    )
    fig_schooltype = px.pie(
        grouped_schooltype,
        names="SchoolTypeName",
        values="NumSchools",
        title=f"Schools by {vocab_schooltype} in {selected_year}",
        labels={
            "SchoolTypeName": vocab_schooltype,
            "NumSchools": "Number of Schools",
        },
        color_discrete_sequence=px.colors.qualitative.D3,
    )

    ###########################################################################
    # Table 1: Cross-tab - District x School Type
    ###########################################################################
    pivot_district = filtered.pivot_table(
        index="DistrictName",
        columns="SchoolTypeName",
        values="NumSchools",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Add total column
    numeric_cols = [c for c in pivot_district.columns if c != "DistrictName"]
    pivot_district["Total"] = pivot_district[numeric_cols].sum(axis=1)

    # Add grand total row
    grand_total = pivot_district[numeric_cols + ["Total"]].sum().to_frame().T
    grand_total["DistrictName"] = "Grand Total"
    pivot_district = pd.concat([pivot_district, grand_total], ignore_index=True)

    # Rename for display
    pivot_district = pivot_district.rename(columns={"DistrictName": vocab_district})

    table1_columns = [{"name": c, "id": c} for c in pivot_district.columns]
    table1_data = pivot_district.to_dict("records")

    ###########################################################################
    # Table 2: Cross-tab - School Type x Authority Group
    ###########################################################################
    pivot_schooltype_authgovt = filtered.pivot_table(
        index="SchoolTypeName",
        columns="AuthorityGroupName",
        values="NumSchools",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Add total column
    numeric_cols2 = [c for c in pivot_schooltype_authgovt.columns if c != "SchoolTypeName"]
    pivot_schooltype_authgovt["Total"] = pivot_schooltype_authgovt[numeric_cols2].sum(
        axis=1
    )

    # Add grand total row
    grand_total2 = (
        pivot_schooltype_authgovt[numeric_cols2 + ["Total"]].sum().to_frame().T
    )
    grand_total2["SchoolTypeName"] = "Grand Total"
    pivot_schooltype_authgovt = pd.concat(
        [pivot_schooltype_authgovt, grand_total2], ignore_index=True
    )

    # Rename for display
    pivot_schooltype_authgovt = pivot_schooltype_authgovt.rename(
        columns={"SchoolTypeName": vocab_schooltype}
    )

    table2_columns = [{"name": c, "id": c} for c in pivot_schooltype_authgovt.columns]
    table2_data = pivot_schooltype_authgovt.to_dict("records")

    # Success: hide alert, hide spacer, show content
    return (
        fig_district,
        fig_region,
        fig_authgovt,
        fig_authority,
        fig_schooltype,
        table1_data,
        table1_columns,
        table2_data,
        table2_columns,
        "",
        False,
        {"display": "none"},
        {},
    )


layout = schools_overview_layout()
