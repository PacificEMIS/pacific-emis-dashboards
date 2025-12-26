import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from services.api import (
    get_df_tableenrolx,
    get_latest_year_with_data,
    lookup_dict,
    vocab_district,
    vocab_region,
    vocab_schooltype,
)

df_tableenrolx = get_df_tableenrolx()

dash.register_page(__name__, path="/students/overview", name="Students Overview")

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
# Use the latest year that actually has data, not just the max year in the list
default_year = get_latest_year_with_data(df_tableenrolx)

# Common table styles
TABLE_STYLE_TABLE = {"overflowX": "auto"}
TABLE_STYLE_HEADER = {"textAlign": "center", "fontWeight": "bold"}
TABLE_STYLE_CELL = {"textAlign": "left"}


def students_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Students Overview"), width=12, className="m-1"),
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
            id="students-top-loading",
            type="default",
            children=html.Div(
                id="students-loading-spacer",
                style={"minHeight": "50vh"},
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="students-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),
        # Charts hidden by default; shown by callback when ready
        html.Div(id="students-content", style={"display": "none"}, children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id="fig-district-gender-graph"), md=12, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="fig-island-gender-graph"), md=12, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="fig-region-gender-graph"), md=6, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="fig-AuthorityGovt-gender-graph"), md=6, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="fig-Authority-gender-graph"), md=12, xs=12, className="p-3"),
            ], className="m-1"),
            # Table 1: Enrolment by Age Group, Education Level and Gender
            dbc.Row([
                dbc.Col([
                    html.H5("Enrolment by Age Group, Education Level and Gender"),
                    dash_table.DataTable(
                        id="enrollment-age-level-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 2: Enrolment by District, School Level and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="enrollment-district-schooltype-title"),
                    dash_table.DataTable(
                        id="enrollment-district-schooltype-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 3: Enrolment by District, Education Level and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="enrollment-district-level-title"),
                    dash_table.DataTable(
                        id="enrollment-district-level-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 4: Enrolment by Region, Education Level and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="enrollment-region-level-title"),
                    dash_table.DataTable(
                        id="enrollment-region-level-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 5: Enrolment by Authority Group, Education Level and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="enrollment-authgovt-level-title"),
                    dash_table.DataTable(
                        id="enrollment-authgovt-level-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
        ]),
    ], fluid=True)


def create_pivot_table(df, row_col, col_col, row_label):
    """
    Create a pivot table with Male/Female/Total columns grouped by col_col values.
    Returns (data, columns) for DataTable.
    """
    df = df.copy()
    df['EnrolTotal'] = df['EnrolM'] + df['EnrolF']

    df_grouped = df.groupby([row_col, col_col]).agg({
        "EnrolM": "sum",
        "EnrolF": "sum",
        "EnrolTotal": "sum"
    }).reset_index()

    df_pivot = df_grouped.pivot(
        index=row_col, columns=col_col, values=["EnrolM", "EnrolF", "EnrolTotal"]
    )
    df_pivot = df_pivot.swaplevel(axis=1).sort_index(axis=1, level=0)
    df_pivot.rename(columns={"EnrolM": "Male", "EnrolF": "Female", "EnrolTotal": "Total"}, level=1, inplace=True)

    # Totals per row
    df_pivot[("Total", "Male")] = df_pivot.xs("Male", axis=1, level=1).sum(axis=1)
    df_pivot[("Total", "Female")] = df_pivot.xs("Female", axis=1, level=1).sum(axis=1)
    df_pivot[("Total", "Total")] = df_pivot.xs("Total", axis=1, level=1).sum(axis=1)

    df_pivot = df_pivot.sort_index(axis=1, level=0)
    df_pivot.reset_index(inplace=True)
    df_pivot.rename(columns={row_col: row_label}, inplace=True)

    # Grand total row
    grand_total = df_pivot.drop(columns=[row_label]).sum(axis=0).to_frame().T
    grand_total.insert(0, row_label, "Grand Total")
    df_pivot = pd.concat([df_pivot, grand_total], ignore_index=True)

    # Fix column names for DataTable
    def fix_column(col):
        if isinstance(col, tuple):
            if col[0] == row_col:
                return row_label
            else:
                return f"{col[0]}_{col[1]}"
        return col

    df_pivot.columns = [fix_column(col) for col in df_pivot.columns]

    # Build columns spec for DataTable with merged headers
    # First column uses two-level name with empty second level for proper header alignment
    table_columns = [{'id': row_label, 'name': [row_label, '']}]
    for col in df_pivot.columns:
        if col != row_label:
            group, measure = col.split("_")
            table_columns.append({'id': col, 'name': [group, measure]})

    table_data = df_pivot.to_dict("records")
    return table_data, table_columns


# Data processing
@dash.callback(
    Output("fig-island-gender-graph", "figure"),
    Output("fig-district-gender-graph", "figure"),
    Output("fig-region-gender-graph", "figure"),
    Output("fig-AuthorityGovt-gender-graph", "figure"),
    Output("fig-Authority-gender-graph", "figure"),
    # Table 1: Age/Education Level
    Output("enrollment-age-level-table", "data"),
    Output("enrollment-age-level-table", "columns"),
    # Table 2: District/SchoolType
    Output("enrollment-district-schooltype-table", "data"),
    Output("enrollment-district-schooltype-table", "columns"),
    Output("enrollment-district-schooltype-title", "children"),
    # Table 3: District/Education Level
    Output("enrollment-district-level-table", "data"),
    Output("enrollment-district-level-table", "columns"),
    Output("enrollment-district-level-title", "children"),
    # Table 4: Region/Education Level
    Output("enrollment-region-level-table", "data"),
    Output("enrollment-region-level-table", "columns"),
    Output("enrollment-region-level-title", "children"),
    # Table 5: AuthorityGovt/Education Level
    Output("enrollment-authgovt-level-table", "data"),
    Output("enrollment-authgovt-level-table", "columns"),
    Output("enrollment-authgovt-level-title", "children"),
    # No data UX
    Output("students-nodata-msg", "children"),
    Output("students-nodata-msg", "is_open"),
    Output("students-loading-spacer", "style"),
    Output("students-content", "style"),
    Input("year-filter", "value"),
    Input("warehouse-version-store", "data"),
)
def update_dashboard(selected_year, _warehouse_version):
    # Empty returns: 5 charts + 5 tables (each with data, columns) + some with titles
    empty_charts = ({}, {}, {}, {}, {})
    empty_tables = ([], [], [], [], "", [], [], "", [], [], "", [], [], "")

    if not selected_year:
        return (*empty_charts, *empty_tables, "No data", True, {}, {"display": "none"})

    df = get_df_tableenrolx()
    if df is None or df.empty:
        return (*empty_charts, *empty_tables, "No data available.", True, {}, {"display": "none"})

    df_filtered = df[df["SurveyYear"] == selected_year].copy()
    if df_filtered.empty:
        return (*empty_charts, *empty_tables, f"No data available for {selected_year}.", True, {}, {"display": "none"})

    ##############################
    # Build the charts
    ##############################

    # -- By Island Chart (vertical bars) --
    df_island_gender = df_filtered.groupby("Island").agg({
        "EnrolM": "sum",
        "EnrolF": "sum"
    }).reset_index()
    df_island_gender_melt = df_island_gender.melt(
        id_vars="Island",
        value_vars=["EnrolM", "EnrolF"],
        var_name="Gender",
        value_name="Enrol"
    )
    df_island_gender_melt["Gender"] = df_island_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    fig_island_gender = px.bar(
        df_island_gender_melt,
        x="Island",
        y="Enrol",
        color="Gender",
        title="Enrolments by Island",
        labels={"Enrol": "Total Enrolments", "Island": "Island", "Gender": "Gender"}
    )
    fig_island_gender.update_layout(xaxis_tickangle=-45)

    # -- By District Chart (vertical bars) --
    df_district_gender = df_filtered.groupby("District").agg({
        "EnrolM": "sum",
        "EnrolF": "sum"
    }).reset_index()
    df_district_gender_melt = df_district_gender.melt(
        id_vars="District",
        value_vars=["EnrolM", "EnrolF"],
        var_name="Gender",
        value_name="Enrol"
    )
    df_district_gender_melt["Gender"] = df_district_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    fig_district_gender = px.bar(
        df_district_gender_melt,
        x="District",
        y="Enrol",
        color="Gender",
        title=f"Enrolments by {vocab_district}",
        labels={"Enrol": "Total Enrolments", "District": vocab_district, "Gender": "Gender"}
    )
    fig_district_gender.update_layout(xaxis_tickangle=-45)

    # -- By Region Chart --
    df_region_gender = df_filtered.groupby("Region").agg({
        "EnrolM": "sum",
        "EnrolF": "sum"
    }).reset_index()
    df_region_gender_melt = df_region_gender.melt(
        id_vars="Region",
        value_vars=["EnrolM", "EnrolF"],
        var_name="Gender",
        value_name="Enrol"
    )
    df_region_gender_melt["Gender"] = df_region_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    fig_region_gender = px.bar(
        df_region_gender_melt,
        y="Region",
        x="Enrol",
        color="Gender",
        orientation="h",
        title=f"Enrolments by {vocab_region}",
        labels={"Enrol": "Total Enrolments", "Region": vocab_region, "Gender": "Gender"}
    )

    # -- By AuthorityGovt Chart --
    df_AuthorityGovt_gender = df_filtered.groupby("AuthorityGovt").agg({
        "EnrolM": "sum",
        "EnrolF": "sum"
    }).reset_index()
    df_AuthorityGovt_gender_melt = df_AuthorityGovt_gender.melt(
        id_vars="AuthorityGovt",
        value_vars=["EnrolM", "EnrolF"],
        var_name="Gender",
        value_name="Enrol"
    )
    df_AuthorityGovt_gender_melt["Gender"] = df_AuthorityGovt_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    fig_AuthorityGovt_gender = px.bar(
        df_AuthorityGovt_gender_melt,
        y="AuthorityGovt",
        x="Enrol",
        color="Gender",
        orientation="h",
        title="Enrolments by Authority Group",
        labels={"Enrol": "Total Enrolments", "AuthorityGovt": "Authority Group", "Gender": "Gender"}
    )

    # -- By Authority Chart --
    df_Authority_gender = df_filtered.groupby("Authority").agg({
        "EnrolM": "sum",
        "EnrolF": "sum"
    }).reset_index()
    df_Authority_gender_melt = df_Authority_gender.melt(
        id_vars="Authority",
        value_vars=["EnrolM", "EnrolF"],
        var_name="Gender",
        value_name="Enrol"
    )
    df_Authority_gender_melt["Gender"] = df_Authority_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    fig_Authority_gender = px.bar(
        df_Authority_gender_melt,
        y="Authority",
        x="Enrol",
        color="Gender",
        orientation="h",
        title="Enrolments by Authority",
        labels={"Enrol": "Total Enrolments", "Authority": "Authority", "Gender": "Gender"}
    )

    ##############################
    # Build the tables
    ##############################

    # Create age groups
    df_filtered["AgeGroup"] = pd.cut(
        df_filtered["Age"],
        bins=[0, 5, 10, 15, 20, 25, 100],
        labels=["0-5", "6-10", "11-15", "16-20", "21-25", "26+"],
        right=True
    )

    # Derive Education Level from ClassLevel using lookups
    # levels lookup has 'C' (code like G1, GK) and 'L' (education level code like PRI, ECE)
    # educationLevels lookup has 'C' (code like PRI) and 'N' (name like Primary)
    levels = lookup_dict.get("levels", [])
    education_levels = lookup_dict.get("educationLevels", [])

    # Build mapping: ClassLevel code -> Education Level code
    class_to_edlevel_code = {item["C"]: item["L"] for item in levels if "C" in item and "L" in item}
    # Build mapping: Education Level code -> Education Level name
    edlevel_code_to_name = {item["C"]: item["N"] for item in education_levels if "C" in item and "N" in item}

    def get_education_level(class_level):
        if pd.isna(class_level):
            return "Unknown"
        ed_code = class_to_edlevel_code.get(class_level)
        if ed_code:
            return edlevel_code_to_name.get(ed_code, "Unknown")
        return "Unknown"

    df_filtered["EducationLevel"] = df_filtered["ClassLevel"].apply(get_education_level)

    # Table 1: Enrolment by Age Group, Education Level and Gender
    table1_data, table1_cols = create_pivot_table(df_filtered, "AgeGroup", "EducationLevel", "Age Group")

    # Table 2: Enrolment by District, School Type and Gender
    table2_data, table2_cols = create_pivot_table(df_filtered, "District", "SchoolType", vocab_district)
    table2_title = f"Enrolment by {vocab_district}, {vocab_schooltype} and Gender"

    # Table 3: Enrolment by District, Education Level and Gender
    table3_data, table3_cols = create_pivot_table(df_filtered, "District", "EducationLevel", vocab_district)
    table3_title = f"Enrolment by {vocab_district}, Education Level and Gender"

    # Table 4: Enrolment by Region, Education Level and Gender
    table4_data, table4_cols = create_pivot_table(df_filtered, "Region", "EducationLevel", vocab_region)
    table4_title = f"Enrolment by {vocab_region}, Education Level and Gender"

    # Table 5: Enrolment by Authority Group, Education Level and Gender
    table5_data, table5_cols = create_pivot_table(df_filtered, "AuthorityGovt", "EducationLevel", "Authority Group")
    table5_title = "Enrolment by Authority Group, Education Level and Gender"

    # success: hide alert, hide spacer, show charts
    return (
        fig_island_gender,
        fig_district_gender,
        fig_region_gender,
        fig_AuthorityGovt_gender,
        fig_Authority_gender,
        table1_data,
        table1_cols,
        table2_data,
        table2_cols,
        table2_title,
        table3_data,
        table3_cols,
        table3_title,
        table4_data,
        table4_cols,
        table4_title,
        table5_data,
        table5_cols,
        table5_title,
        "",
        False,
        {"display": "none"},
        {},
    )


layout = students_layout()
