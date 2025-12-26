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
    get_df_accreditation_bystandard,
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

# Star display names for table headers
LEVEL_STAR_NAMES = {
    "Level 1": "★",
    "Level 2": "★★",
    "Level 3": "★★★",
    "Level 4": "★★★★",
}

# Standard names lookup (School Evaluation and Classroom Observation)
STANDARD_NAMES = {
    "SE.1": "SE.1: Leadership",
    "SE.2": "SE.2: Teacher Performance",
    "SE.3": "SE.3: School Management",
    "SE.4": "SE.4: Safe & Healthy Environment",
    "SE.5": "SE.5: School/Community Relationship",
    "SE.6": "SE.6: Student Outcomes",
    "CO.1": "CO.1: Preparation",
    "CO.2": "CO.2: Classroom Environment",
    "CO.3": "CO.3: Instruction",
    "CO.4": "CO.4: Assessment",
    "CO.5": "CO.5: Professionalism",
}

# Custom sort order for standards (SE first, then CO)
STANDARD_SORT_ORDER = ["SE.1", "SE.2", "SE.3", "SE.4", "SE.5", "SE.6", "CO.1", "CO.2", "CO.3", "CO.4", "CO.5"]

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
                                md=6,
                                xs=12,
                                className="p-3",
                            ),
                            dbc.Col(
                                dcc.Graph(id="accreditation-authority-chart"),
                                md=6,
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
                                    html.H5(id="accreditation-district-table-title"),
                                    dash_table.DataTable(
                                        id="accreditation-district-table",
                                        style_table={"overflowX": "auto"},
                                        style_header={
                                            "textAlign": "center",
                                            "fontWeight": "bold",
                                        },
                                        style_cell={"textAlign": "left"},
                                        style_cell_conditional=[
                                            {"if": {"column_id": "★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "Total Evaluated"}, "textAlign": "right"},
                                            {"if": {"column_id": "Accredited"}, "textAlign": "right"},
                                        ],
                                        style_data_conditional=[
                                            {"if": {"column_id": "Accredited"}, "fontWeight": "bold"},
                                            {"if": {"column_id": "Total Evaluated"}, "fontWeight": "bold"},
                                        ],
                                        style_header_conditional=[
                                            {"if": {"column_id": "★"}, "color": "#FF0000"},
                                            {"if": {"column_id": "★★"}, "color": "#FFC000"},
                                            {"if": {"column_id": "★★★"}, "color": "#92D050"},
                                            {"if": {"column_id": "★★★★"}, "color": "#00B050"},
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
                                    html.H5(id="accreditation-schooltype-table-title"),
                                    dash_table.DataTable(
                                        id="accreditation-schooltype-table",
                                        style_table={"overflowX": "auto"},
                                        style_header={
                                            "textAlign": "center",
                                            "fontWeight": "bold",
                                        },
                                        style_cell={"textAlign": "left"},
                                        style_cell_conditional=[
                                            {"if": {"column_id": "★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "Total Evaluated"}, "textAlign": "right"},
                                            {"if": {"column_id": "Accredited"}, "textAlign": "right"},
                                        ],
                                        style_data_conditional=[
                                            {"if": {"column_id": "Accredited"}, "fontWeight": "bold"},
                                            {"if": {"column_id": "Total Evaluated"}, "fontWeight": "bold"},
                                        ],
                                        style_header_conditional=[
                                            {"if": {"column_id": "★"}, "color": "#FF0000"},
                                            {"if": {"column_id": "★★"}, "color": "#FFC000"},
                                            {"if": {"column_id": "★★★"}, "color": "#92D050"},
                                            {"if": {"column_id": "★★★★"}, "color": "#00B050"},
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
                                    html.H5(id="accreditation-standard-table-title"),
                                    dash_table.DataTable(
                                        id="accreditation-standard-table",
                                        style_table={"overflowX": "auto"},
                                        style_header={
                                            "textAlign": "center",
                                            "fontWeight": "bold",
                                        },
                                        style_cell={"textAlign": "left"},
                                        style_cell_conditional=[
                                            {"if": {"column_id": "★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "★★★★"}, "textAlign": "right"},
                                            {"if": {"column_id": "Total Evaluated"}, "textAlign": "right"},
                                            {"if": {"column_id": "Accredited"}, "textAlign": "right"},
                                        ],
                                        style_data_conditional=[
                                            {"if": {"column_id": "Accredited"}, "fontWeight": "bold"},
                                            {"if": {"column_id": "Total Evaluated"}, "fontWeight": "bold"},
                                        ],
                                        style_header_conditional=[
                                            {"if": {"column_id": "★"}, "color": "#FF0000"},
                                            {"if": {"column_id": "★★"}, "color": "#FFC000"},
                                            {"if": {"column_id": "★★★"}, "color": "#92D050"},
                                            {"if": {"column_id": "★★★★"}, "color": "#00B050"},
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


def create_mirror_bar_chart(grouped_df, y_col, title, y_label, min_height=400, show_legend=True):
    """
    Create a horizontal bar chart with Level 1 on negative axis (left side)
    and Levels 2-4 on positive axis (right side) - mirror chart effect.
    Height is dynamically calculated based on number of items.
    """
    import math

    fig = go.Figure()

    # Get unique y values
    y_values = grouped_df[y_col].unique()

    # Calculate dynamic height based on number of items (30px per bar minimum)
    num_items = len(y_values)
    chart_height = max(min_height, num_items * 30)

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
        # Store original positive values for hover display
        abs_values = values.copy()

        # Track max for axis scaling
        if level == "Level 1":
            max_negative = max(max_negative, max(values) if values else 0)
            values = [-v for v in values]  # Negative for Level 1 (visual only)
        else:
            max_positive = max(max_positive, max(values) if values else 0)

        fig.add_trace(go.Bar(
            y=y_values,
            x=values,
            name=level,
            orientation="h",
            marker_color=ACCREDITATION_COLORS[level],
            customdata=abs_values,
            hovertemplate="%{y}<br>" + level + ": %{customdata:,.0f}<extra></extra>",
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
        height=chart_height,
        xaxis=dict(
            title="Number of Schools",
            tickformat="d",
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[-rounded_max * 1.05, rounded_max * 1.05],  # Small padding
        ),
        yaxis=dict(title=y_label),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=show_legend,
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
    Output("accreditation-standard-table", "data"),
    Output("accreditation-standard-table", "columns"),
    Output("accreditation-district-table-title", "children"),
    Output("accreditation-schooltype-table-title", "children"),
    Output("accreditation-standard-table-title", "children"),
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
    empty_tables = ([], [], [], [], [], [])  # 6 items: 3 tables x 2 (data, columns)
    empty_titles = ("", "", "")

    if selected_year is None:
        return (
            *empty_charts,
            *empty_tables,
            *empty_titles,
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
            *empty_titles,
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
            *empty_titles,
            "No accreditation level column found in data.",
            True,
            {},
            {"display": "none"},
        )

    # Ensure numeric columns are properly typed
    df["Num"] = pd.to_numeric(df["Num"], errors="coerce").fillna(0)
    if "NumThisYear" in df.columns:
        df["NumThisYear"] = pd.to_numeric(df["NumThisYear"], errors="coerce").fillna(0)
    else:
        df["NumThisYear"] = df["Num"]  # Fallback if column doesn't exist
    df["AccreditationLevel"] = df[level_col].fillna("Unknown")

    # Always filter to the selected year - the difference is which column we use
    # - "in_year": Use NumThisYear (schools evaluated in that specific year)
    # - "cumulative": Use Num (cumulative count up to that year)
    filtered = df[df["SurveyYear"] == selected_year].copy()
    if view_mode == "in_year":
        value_col = "NumThisYear"
        view_label = f"Evaluated in {selected_year}"
    else:
        value_col = "Num"
        view_label = f"Cumulative to {selected_year}"

    if filtered.empty:
        return (
            *empty_charts,
            *empty_tables,
            *empty_titles,
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
    # Shows all years up to selected year
    # - "in_year" mode: Each bar shows schools evaluated in that specific year
    # - "cumulative" mode: Each bar shows cumulative totals for that year
    ###########################################################################
    year_data = df[df["SurveyYear"] <= selected_year].copy()

    # Use same value column as other charts (NumThisYear for in_year, Num for cumulative)
    grouped_year = (
        year_data.groupby(["SurveyYear", "AccreditationLevel"])[value_col]
        .sum()
        .reset_index()
    )
    grouped_year = grouped_year.rename(columns={value_col: "Num"})
    grouped_year["SurveyYear"] = grouped_year["SurveyYear"].astype(str)

    year_chart_title = "Schools Evaluated by Year" if view_mode == "in_year" else "Cumulative Accreditation by Year"
    fig_year = create_mirror_bar_chart(
        grouped_year,
        y_col="SurveyYear",
        title=year_chart_title,
        y_label="Year"
    )

    ###########################################################################
    # Chart 2: National Accreditation (pie chart)
    ###########################################################################
    grouped_national = (
        filtered.groupby("AccreditationLevel")[value_col]
        .sum()
        .reset_index()
    )
    grouped_national = grouped_national.rename(columns={value_col: "Value"})
    # Filter out zero values for cleaner pie chart
    grouped_national = grouped_national[grouped_national["Value"] > 0]

    fig_national = px.pie(
        grouped_national,
        names="AccreditationLevel",
        values="Value",
        title=f"National Accreditation ({view_label})",
        color="AccreditationLevel",
        color_discrete_map=ACCREDITATION_COLORS,
    )
    fig_national.update_traces(textposition="inside", textinfo="percent+value+label")
    fig_national.update_layout(showlegend=False)

    ###########################################################################
    # Chart 3: Accreditation by District (mirror bar chart)
    # Always show all districts that have cumulative data, with values based on view mode
    ###########################################################################
    # Get all districts that have any cumulative data
    all_districts = filtered[filtered["Num"] > 0]["DistrictName"].unique()
    all_levels = ACCREDITATION_LEVELS

    # Create full grid of district x level combinations
    district_level_grid = pd.MultiIndex.from_product(
        [all_districts, all_levels], names=["DistrictName", "AccreditationLevel"]
    )
    grouped_district = (
        filtered.groupby(["DistrictName", "AccreditationLevel"])[value_col]
        .sum()
        .reindex(district_level_grid, fill_value=0)
        .reset_index()
    )
    grouped_district = grouped_district.rename(columns={value_col: "Num"})

    fig_district = create_mirror_bar_chart(
        grouped_district,
        y_col="DistrictName",
        title=f"Accreditation by {vocab_district} ({view_label})",
        y_label=vocab_district,
        show_legend=False
    )

    ###########################################################################
    # Chart 4: Accreditation by Authority Group (mirror bar chart)
    ###########################################################################
    all_authgovts = filtered[filtered["Num"] > 0]["AuthorityGroupName"].unique()
    authgovt_level_grid = pd.MultiIndex.from_product(
        [all_authgovts, all_levels], names=["AuthorityGroupName", "AccreditationLevel"]
    )
    grouped_authgovt = (
        filtered.groupby(["AuthorityGroupName", "AccreditationLevel"])[value_col]
        .sum()
        .reindex(authgovt_level_grid, fill_value=0)
        .reset_index()
    )
    grouped_authgovt = grouped_authgovt.rename(columns={value_col: "Num"})

    fig_authgovt = create_mirror_bar_chart(
        grouped_authgovt,
        y_col="AuthorityGroupName",
        title=f"Accreditation by {vocab_authoritygovt} ({view_label})",
        y_label=vocab_authoritygovt,
        show_legend=False
    )

    ###########################################################################
    # Chart 5: Accreditation by Authority (mirror bar chart)
    ###########################################################################
    all_authorities = filtered[filtered["Num"] > 0]["AuthorityName"].unique()
    authority_level_grid = pd.MultiIndex.from_product(
        [all_authorities, all_levels], names=["AuthorityName", "AccreditationLevel"]
    )
    grouped_authority = (
        filtered.groupby(["AuthorityName", "AccreditationLevel"])[value_col]
        .sum()
        .reindex(authority_level_grid, fill_value=0)
        .reset_index()
    )
    grouped_authority = grouped_authority.rename(columns={value_col: "Num"})

    fig_authority = create_mirror_bar_chart(
        grouped_authority,
        y_col="AuthorityName",
        title=f"Accreditation by {vocab_authority} ({view_label})",
        y_label=vocab_authority,
        show_legend=False
    )

    ###########################################################################
    # Table 1: District by Accreditation Level
    ###########################################################################
    table_district = filtered.pivot_table(
        index="DistrictName",
        columns="AccreditationLevel",
        values=value_col,
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Ensure all level columns exist
    for level in ACCREDITATION_LEVELS:
        if level not in table_district.columns:
            table_district[level] = 0

    # Reorder columns and add computed columns
    level_cols = [l for l in ACCREDITATION_LEVELS if l in table_district.columns]
    # Accredited = Level 2 + Level 3 + Level 4
    accredited_cols = [l for l in ["Level 2", "Level 3", "Level 4"] if l in table_district.columns]
    table_district["Accredited"] = table_district[accredited_cols].sum(axis=1)
    table_district["Total Evaluated"] = table_district[level_cols].sum(axis=1)
    table_district = table_district.rename(columns={"DistrictName": vocab_district})
    table_district = table_district[[vocab_district] + level_cols + ["Total Evaluated", "Accredited"]]

    # Add grand total row
    grand_total = table_district[level_cols + ["Accredited", "Total Evaluated"]].sum().to_frame().T
    grand_total[vocab_district] = "Grand Total"
    table_district = pd.concat([table_district, grand_total], ignore_index=True)

    # Rename level columns to stars
    table_district = table_district.rename(columns=LEVEL_STAR_NAMES)

    table1_columns = [{"name": c, "id": c} for c in table_district.columns]
    table1_data = table_district.to_dict("records")

    ###########################################################################
    # Table 2: School Type by Accreditation Level
    ###########################################################################
    table_schooltype = filtered.pivot_table(
        index="SchoolTypeName",
        columns="AccreditationLevel",
        values=value_col,
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Ensure all level columns exist
    for level in ACCREDITATION_LEVELS:
        if level not in table_schooltype.columns:
            table_schooltype[level] = 0

    # Reorder columns and add computed columns
    level_cols2 = [l for l in ACCREDITATION_LEVELS if l in table_schooltype.columns]
    # Accredited = Level 2 + Level 3 + Level 4
    accredited_cols2 = [l for l in ["Level 2", "Level 3", "Level 4"] if l in table_schooltype.columns]
    table_schooltype["Accredited"] = table_schooltype[accredited_cols2].sum(axis=1)
    table_schooltype["Total Evaluated"] = table_schooltype[level_cols2].sum(axis=1)
    table_schooltype = table_schooltype.rename(columns={"SchoolTypeName": vocab_schooltype})
    table_schooltype = table_schooltype[[vocab_schooltype] + level_cols2 + ["Total Evaluated", "Accredited"]]

    # Add grand total row
    grand_total2 = table_schooltype[level_cols2 + ["Accredited", "Total Evaluated"]].sum().to_frame().T
    grand_total2[vocab_schooltype] = "Grand Total"
    table_schooltype = pd.concat([table_schooltype, grand_total2], ignore_index=True)

    # Rename level columns to stars
    table_schooltype = table_schooltype.rename(columns=LEVEL_STAR_NAMES)

    table2_columns = [{"name": c, "id": c} for c in table_schooltype.columns]
    table2_data = table_schooltype.to_dict("records")

    ###########################################################################
    # Table 3: Performance by Standard
    ###########################################################################
    df_standard = get_df_accreditation_bystandard()
    table3_data = []
    table3_columns = []

    if df_standard is not None and not df_standard.empty:
        # Filter to selected year
        df_standard_filtered = df_standard[df_standard["SurveyYear"] == selected_year].copy()

        if not df_standard_filtered.empty:
            # Use appropriate value column based on view mode
            std_value_col = "NumInYear" if view_mode == "in_year" else "Num"

            # The data has Standard, Result (Level 1-4), and Num/NumInYear columns
            # We need to pivot to get levels as columns
            table_standard = df_standard_filtered.pivot_table(
                index="Standard",
                columns="Result",
                values=std_value_col,
                aggfunc="sum",
                fill_value=0,
            ).reset_index()

            # Ensure all level columns exist
            for level in ACCREDITATION_LEVELS:
                if level not in table_standard.columns:
                    table_standard[level] = 0

            # Sort by custom order (SE.1, SE.2, ... then CO.1, CO.2, ...)
            def get_sort_key(std_code):
                try:
                    return STANDARD_SORT_ORDER.index(std_code)
                except ValueError:
                    return 999  # Unknown standards go last
            table_standard["_sort_key"] = table_standard["Standard"].apply(get_sort_key)
            table_standard = table_standard.sort_values("_sort_key").drop(columns=["_sort_key"])

            # Apply full standard names (e.g., "SE.1: Leadership")
            table_standard["Standard"] = table_standard["Standard"].map(
                lambda x: STANDARD_NAMES.get(x, x)
            )

            # Reorder columns and add computed columns
            level_cols3 = [l for l in ACCREDITATION_LEVELS if l in table_standard.columns]
            accredited_cols3 = [l for l in ["Level 2", "Level 3", "Level 4"] if l in table_standard.columns]
            table_standard["Accredited"] = table_standard[accredited_cols3].sum(axis=1)
            table_standard["Total Evaluated"] = table_standard[level_cols3].sum(axis=1)
            table_standard = table_standard[["Standard"] + level_cols3 + ["Total Evaluated", "Accredited"]]

            # Rename level columns to stars
            table_standard = table_standard.rename(columns=LEVEL_STAR_NAMES)

            table3_columns = [{"name": c, "id": c} for c in table_standard.columns]
            table3_data = table_standard.to_dict("records")

    # Generate table titles with view mode
    table1_title = f"Accreditation by {vocab_district} ({view_label})"
    table2_title = f"Accreditation by {vocab_schooltype} ({view_label})"
    table3_title = f"Performance by Standard ({view_label})"

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
        table3_data,
        table3_columns,
        table1_title,
        table2_title,
        table3_title,
        "",
        False,
        {"display": "none"},
        {},
    )


layout = schoolaccreditation_overview_layout()
