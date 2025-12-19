import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Import data and lookup dictionary from the API module
from services.api import (
    get_df_accreditation,
    get_latest_year_with_data,
    district_lookup,
    authorities_lookup,
    authoritygovts_lookup,
    schooltypes_lookup,
    vocab_district,
    vocab_authority,
    vocab_authoritygovt,
    vocab_schooltype,
    lookup_dict,
)

dash.register_page(__name__, path="/schoolaccreditation/overview", name="School Accreditation Overview")

# Accreditation level color scheme (from Pineapples)
# Level 1 (Not Accredited): Red
# Level 2 (Approaching): Orange/Gold
# Level 3 (Accredited): Light Green
# Level 4 (Exemplary): Dark Green
ACCREDITATION_COLORS = {
    "Level 1": "#FF0000",
    "Level 2": "#FFC000",
    "Level 3": "#92D050",
    "Level 4": "#00B050",
}

# Ordered list of levels for consistent display
ACCREDITATION_LEVELS = ["Level 1", "Level 2", "Level 3", "Level 4"]

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{"label": item["N"], "value": item["C"]} for item in survey_years]
# Use the latest year that actually has data, not just the max year in the list
default_year = get_latest_year_with_data(get_df_accreditation())


def schoolaccreditation_overview_layout():
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(html.H1("School Accreditation Overview"), width=12, className="m-1"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="accreditation-year-filter",
                            options=year_options,
                            value=default_year,
                            clearable=False,
                            style={"width": "200px"},
                        ),
                        className="m-1",
                    ),
                    dbc.Col(
                        dcc.RadioItems(
                            id="accreditation-view-mode",
                            options=[
                                {"label": " Evaluated in Year", "value": "in_year"},
                                {"label": " Cumulative to Year", "value": "cumulative"},
                            ],
                            value="cumulative",
                            inline=True,
                            className="mt-2",
                        ),
                        className="m-1",
                    ),
                ]
            ),
            # Loading spinner and no-data alert
            dcc.Loading(
                id="accreditation-overview-top-loading",
                type="default",
                children=html.Div(
                    id="accreditation-overview-loading-spacer",
                    style={"minHeight": "50vh"},
                    children=dbc.Row(
                        [
                            dbc.Col(
                                dbc.Alert(
                                    id="accreditation-overview-nodata-msg",
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
                id="accreditation-overview-content",
                style={"display": "none"},
                children=[
                    # Row 1: Accreditation Progress by Year
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="accreditation-year-chart"),
                                md=12,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Row 2: National pie chart and District bar chart
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="accreditation-national-chart"),
                                md=4,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="accreditation-district-chart"),
                                md=8,
                                xs=12,
                                className="p-3",
                            ),
                        ],
                        className="m-1",
                    ),
                    # Row 3: Authority Group pie and Authority bar charts
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="accreditation-authgovt-chart"),
                                md=4,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="accreditation-authority-chart"),
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
                                    html.H3(f"Accreditation by {vocab_district}"),
                                    dash_table.DataTable(
                                        id="accreditation-district-table",
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
                                    html.H3(f"Accreditation by {vocab_schooltype}"),
                                    dash_table.DataTable(
                                        id="accreditation-schooltype-table",
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


def create_mirror_bar_chart(grouped_df, y_col, title, y_label):
    """
    Create a horizontal bar chart with Level 1 on negative axis (left side)
    and Levels 2-4 on positive axis (right side) - mirror chart effect.
    """
    import math

    fig = go.Figure()

    # Get unique y values
    y_values = grouped_df[y_col].unique()

    # Track max values for dynamic axis scaling
    max_negative = 0  # Level 1 (will be shown negative)
    max_positive = 0  # Levels 2-4

    # Process each level
    for level in ACCREDITATION_LEVELS:
        level_data = grouped_df[grouped_df["AccreditationLevel"] == level]

        # Create a mapping of y_col to Num for this level
        values_dict = dict(zip(level_data[y_col], level_data["Num"]))

        # Get values for all y items (0 if not present)
        values = [values_dict.get(y, 0) for y in y_values]

        # Track max for axis scaling
        if level == "Level 1":
            max_negative = max(max_negative, max(values) if values else 0)
            values = [-v for v in values]  # Negative for Level 1
        else:
            max_positive = max(max_positive, max(values) if values else 0)

        fig.add_trace(go.Bar(
            y=y_values,
            x=values,
            name=level,
            orientation="h",
            marker_color=ACCREDITATION_COLORS[level],
        ))

    # Calculate symmetric axis range based on data
    max_val = max(max_negative, max_positive, 1)  # At least 1 to avoid division by zero

    # Round up to a nice number for tick spacing
    if max_val <= 10:
        tick_step = 2
    elif max_val <= 25:
        tick_step = 5
    elif max_val <= 50:
        tick_step = 10
    elif max_val <= 100:
        tick_step = 20
    elif max_val <= 250:
        tick_step = 50
    else:
        tick_step = 100

    # Round max_val up to nearest tick_step
    rounded_max = math.ceil(max_val / tick_step) * tick_step

    # Generate symmetric tick values
    tick_vals = list(range(-rounded_max, rounded_max + 1, tick_step))
    tick_text = [str(abs(v)) for v in tick_vals]  # Show absolute values

    fig.update_layout(
        barmode="relative",
        title=title,
        xaxis=dict(
            title="Number of Schools",
            tickformat="d",
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[-rounded_max * 1.05, rounded_max * 1.05],  # Small padding
        ),
        yaxis=dict(title=y_label),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


@dash.callback(
    Output("accreditation-year-chart", "figure"),
    Output("accreditation-national-chart", "figure"),
    Output("accreditation-district-chart", "figure"),
    Output("accreditation-authgovt-chart", "figure"),
    Output("accreditation-authority-chart", "figure"),
    Output("accreditation-district-table", "data"),
    Output("accreditation-district-table", "columns"),
    Output("accreditation-schooltype-table", "data"),
    Output("accreditation-schooltype-table", "columns"),
    # No data UX
    Output("accreditation-overview-nodata-msg", "children"),
    Output("accreditation-overview-nodata-msg", "is_open"),
    Output("accreditation-overview-loading-spacer", "style"),
    Output("accreditation-overview-content", "style"),
    Input("accreditation-year-filter", "value"),
    Input("accreditation-view-mode", "value"),
    Input("warehouse-version-store", "data"),
)
def update_accreditation_dashboard(selected_year, view_mode, _warehouse_version):
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
    df = get_df_accreditation()

    if df is None or df.empty:
        return (
            *empty_charts,
            *empty_tables,
            "No data available.",
            True,
            {},
            {"display": "none"},
        )

    # Get accreditation level column - could be InspectionResult or similar column
    level_col = None
    for col in ["InspectionResult", "AccreditationLevel", "Level", "Result"]:
        if col in df.columns:
            level_col = col
            break

    if level_col is None:
        return (
            *empty_charts,
            *empty_tables,
            "No accreditation level column found in data.",
            True,
            {},
            {"display": "none"},
        )

    # Ensure Num column is numeric on full dataset for year chart
    df["Num"] = pd.to_numeric(df["Num"], errors="coerce").fillna(0)
    df["AccreditationLevel"] = df[level_col].fillna("Unknown")

    # Filter based on view mode for other charts
    if view_mode == "in_year":
        # Only schools evaluated in the selected year
        filtered = df[df["SurveyYear"] == selected_year].copy()
        view_label = f"Evaluated in {selected_year}"
    else:
        # Cumulative: all data up to and including the selected year
        filtered = df[df["SurveyYear"] <= selected_year].copy()
        view_label = f"Cumulative to {selected_year}"

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
    filtered["DistrictName"] = (
        filtered["DistrictCode"].map(district_lookup).fillna(filtered.get("District", "Unknown"))
        if "DistrictCode" in filtered.columns
        else filtered.get("District", "Unknown")
    )

    filtered["AuthorityName"] = (
        filtered["AuthorityCode"].map(authorities_lookup).fillna(filtered.get("Authority", "Unknown"))
        if "AuthorityCode" in filtered.columns
        else filtered.get("Authority", "Unknown")
    )

    # Handle both AuthorityGovtCode and AuthorityGroupCode naming
    if "AuthorityGroupCode" in filtered.columns:
        filtered["AuthorityGroupName"] = (
            filtered["AuthorityGroupCode"].map(authoritygovts_lookup).fillna(filtered.get("AuthorityGroup", "Unknown"))
        )
    elif "AuthorityGovtCode" in filtered.columns:
        filtered["AuthorityGroupName"] = (
            filtered["AuthorityGovtCode"].map(authoritygovts_lookup).fillna(filtered.get("AuthorityGovt", "Unknown"))
        )
    else:
        filtered["AuthorityGroupName"] = "Unknown"

    filtered["SchoolTypeName"] = (
        filtered["SchoolTypeCode"].map(schooltypes_lookup).fillna(filtered.get("SchoolType", "Unknown"))
        if "SchoolTypeCode" in filtered.columns
        else filtered.get("SchoolType", "Unknown")
    )

    ###########################################################################
    # Chart 1: Accreditation Progress by Year (mirror bar chart)
    ###########################################################################
    grouped_year = (
        df.groupby(["SurveyYear", "AccreditationLevel"])["Num"]
        .sum()
        .reset_index()
    )
    grouped_year["SurveyYear"] = grouped_year["SurveyYear"].astype(str)

    fig_year = create_mirror_bar_chart(
        grouped_year,
        y_col="SurveyYear",
        title="Accreditation Progress by Year",
        y_label="Year"
    )

    ###########################################################################
    # Chart 2: National Accreditation (pie chart)
    ###########################################################################
    grouped_national = (
        filtered.groupby("AccreditationLevel")["Num"]
        .sum()
        .reset_index()
    )
    # Filter out zero values for cleaner pie chart
    grouped_national = grouped_national[grouped_national["Num"] > 0]

    fig_national = px.pie(
        grouped_national,
        names="AccreditationLevel",
        values="Num",
        title=f"National Accreditation ({view_label})",
        color="AccreditationLevel",
        color_discrete_map=ACCREDITATION_COLORS,
    )
    fig_national.update_traces(textposition="inside", textinfo="percent+value")

    ###########################################################################
    # Chart 3: Accreditation by District (mirror bar chart)
    ###########################################################################
    grouped_district = (
        filtered.groupby(["DistrictName", "AccreditationLevel"])["Num"]
        .sum()
        .reset_index()
    )

    fig_district = create_mirror_bar_chart(
        grouped_district,
        y_col="DistrictName",
        title=f"Accreditation by {vocab_district} ({view_label})",
        y_label=vocab_district
    )

    ###########################################################################
    # Chart 4: Accreditation by Authority Group (mirror bar chart)
    ###########################################################################
    grouped_authgovt = (
        filtered.groupby(["AuthorityGroupName", "AccreditationLevel"])["Num"]
        .sum()
        .reset_index()
    )

    fig_authgovt = create_mirror_bar_chart(
        grouped_authgovt,
        y_col="AuthorityGroupName",
        title=f"Accreditation by {vocab_authoritygovt} ({view_label})",
        y_label=vocab_authoritygovt
    )

    ###########################################################################
    # Chart 5: Accreditation by Authority (mirror bar chart)
    ###########################################################################
    grouped_authority = (
        filtered.groupby(["AuthorityName", "AccreditationLevel"])["Num"]
        .sum()
        .reset_index()
    )

    fig_authority = create_mirror_bar_chart(
        grouped_authority,
        y_col="AuthorityName",
        title=f"Accreditation by {vocab_authority} ({view_label})",
        y_label=vocab_authority
    )

    ###########################################################################
    # Table 1: District by Accreditation Level
    ###########################################################################
    table_district = filtered.pivot_table(
        index="DistrictName",
        columns="AccreditationLevel",
        values="Num",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Ensure all level columns exist
    for level in ACCREDITATION_LEVELS:
        if level not in table_district.columns:
            table_district[level] = 0

    # Reorder columns
    level_cols = [l for l in ACCREDITATION_LEVELS if l in table_district.columns]
    table_district["Total"] = table_district[level_cols].sum(axis=1)
    table_district = table_district.rename(columns={"DistrictName": vocab_district})
    table_district = table_district[[vocab_district] + level_cols + ["Total"]]

    # Add grand total row
    grand_total = table_district[level_cols + ["Total"]].sum().to_frame().T
    grand_total[vocab_district] = "Grand Total"
    table_district = pd.concat([table_district, grand_total], ignore_index=True)

    table1_columns = [{"name": c, "id": c} for c in table_district.columns]
    table1_data = table_district.to_dict("records")

    ###########################################################################
    # Table 2: School Type by Accreditation Level
    ###########################################################################
    table_schooltype = filtered.pivot_table(
        index="SchoolTypeName",
        columns="AccreditationLevel",
        values="Num",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Ensure all level columns exist
    for level in ACCREDITATION_LEVELS:
        if level not in table_schooltype.columns:
            table_schooltype[level] = 0

    # Reorder columns
    level_cols2 = [l for l in ACCREDITATION_LEVELS if l in table_schooltype.columns]
    table_schooltype["Total"] = table_schooltype[level_cols2].sum(axis=1)
    table_schooltype = table_schooltype.rename(columns={"SchoolTypeName": vocab_schooltype})
    table_schooltype = table_schooltype[[vocab_schooltype] + level_cols2 + ["Total"]]

    # Add grand total row
    grand_total2 = table_schooltype[level_cols2 + ["Total"]].sum().to_frame().T
    grand_total2[vocab_schooltype] = "Grand Total"
    table_schooltype = pd.concat([table_schooltype, grand_total2], ignore_index=True)

    table2_columns = [{"name": c, "id": c} for c in table_schooltype.columns]
    table2_data = table_schooltype.to_dict("records")

    # Success: hide alert, hide spacer, show content
    return (
        fig_year,
        fig_national,
        fig_district,
        fig_authgovt,
        fig_authority,
        table1_data,
        table1_columns,
        table2_data,
        table2_columns,
        "",
        False,
        {"display": "none"},
        {},
    )


layout = schoolaccreditation_overview_layout()
