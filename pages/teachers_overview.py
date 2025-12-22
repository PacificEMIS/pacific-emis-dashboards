import numpy as np
import math
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Import data and lookup dictionary from the API module
from services.api import (
    get_df_teachercount,
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
df_teachercount = get_df_teachercount()

dash.register_page(__name__, path="/teachers/overview", name="Teachers Overview")

# Common table styles
TABLE_STYLE_TABLE = {"overflowX": "auto"}
TABLE_STYLE_HEADER = {"textAlign": "center", "fontWeight": "bold"}
TABLE_STYLE_CELL = {"textAlign": "left"}

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]
# Use the latest year that actually has data, not just the max year in the list
default_year = get_latest_year_with_data(df_teachercount) 

# ✅ Define Layout inside a Function
def teachers_overview_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Teachers Overview"), width=12, className="m-1"),
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
            id="teachers-overview-top-loading",
            type="default",
            children=html.Div(
                id="teachers-overview-loading-spacer",
                style={"minHeight": "50vh"},
                children=dbc.Row([
                    dbc.Col(
                        dbc.Alert(id="teachers-overview-nodata-msg", color="warning", is_open=False),
                        width=12,
                        className="m-1"
                    ),
                ])
            )
        ),
        # Charts hidden by default; shown by callback when ready
        html.Div(id="teachers-overview-content", style={"display": "none"}, children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id="teachers-district-gender-bar-chart"), md=12, xs=12, className="p-3"),
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="teachers-region-gender-bar-chart"), md=4, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="teachers-authgovt-pie-chart"), md=4, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="teachers-auth-bar-chart"), md=4, xs=12, className="p-3"),            
            ], className="m-1"),
            dbc.Row([
                dbc.Col(dcc.Graph(id="teachers-schooltype-pie-chart"), md=4, xs=12, className="p-3"),
                dbc.Col(dcc.Graph(id="teachers-age-group-gender-bar-chart"), md=8, xs=12, className="p-3"),
            ], className="m-1"),
            # Table 1: Teachers by Island, School Type and Gender
            dbc.Row([
                dbc.Col([
                    html.H5("Teachers by Atoll/Island, School Type and Gender"),
                    dash_table.DataTable(
                        id="teachers-island-schooltype-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 2: Teachers by School Type, Region and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="teachers-schooltype-region-title"),
                    dash_table.DataTable(
                        id="teachers-schooltype-region-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 3: Teachers by District, School Type and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="teachers-district-schooltype-title"),
                    dash_table.DataTable(
                        id="teachers-district-schooltype-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
            # Table 4: Teachers by District, ISCED Levels and Gender
            dbc.Row([
                dbc.Col([
                    html.H5(id="teachers-district-isced-title"),
                    dash_table.DataTable(
                        id="teachers-district-isced-table",
                        merge_duplicate_headers=True,
                        style_table=TABLE_STYLE_TABLE,
                        style_header=TABLE_STYLE_HEADER,
                        style_cell=TABLE_STYLE_CELL,
                    )
                ], md=12, className="m-1")
            ]),
        ]),
    ], fluid=True)

# Data processing
@dash.callback(
    Output("teachers-district-gender-bar-chart", "figure"),
    Output("teachers-region-gender-bar-chart", "figure"),
    Output("teachers-authgovt-pie-chart", "figure"),
    Output("teachers-auth-bar-chart", "figure"),
    Output("teachers-schooltype-pie-chart", "figure"),
    Output("teachers-age-group-gender-bar-chart", "figure"),
    # Table 1: Island/SchoolType
    Output("teachers-island-schooltype-table", "data"),
    Output("teachers-island-schooltype-table", "columns"),
    # Table 2: SchoolType/Region
    Output("teachers-schooltype-region-table", "data"),
    Output("teachers-schooltype-region-table", "columns"),
    Output("teachers-schooltype-region-title", "children"),
    # Table 3: District/SchoolType
    Output("teachers-district-schooltype-table", "data"),
    Output("teachers-district-schooltype-table", "columns"),
    Output("teachers-district-schooltype-title", "children"),
    # Table 4: District/ISCED
    Output("teachers-district-isced-table", "data"),
    Output("teachers-district-isced-table", "columns"),
    Output("teachers-district-isced-title", "children"),
    # No data UX
    Output("teachers-overview-nodata-msg", "children"),
    Output("teachers-overview-nodata-msg", "is_open"),
    Output("teachers-overview-loading-spacer", "style"),
    Output("teachers-overview-content", "style"),
    Input("year-filter", "value"),
    Input("warehouse-version-store", "data"),
)
def update_dashboard(selected_year, _warehouse_version):
    # Empty returns: 6 charts + 4 tables (each with data, columns) + 3 with titles
    empty_charts = ({}, {}, {}, {}, {}, {})
    empty_tables = ([], [], [], [], "", [], [], "", [], [], "")

    if selected_year is None:
        return (*empty_charts, *empty_tables, "No data", True, {}, {"display": "none"})

    # Re-fetch and guard against None/empty
    df = get_df_teachercount()
    if df is None or df.empty:
        return (*empty_charts, *empty_tables, "No data available.", True, {}, {"display": "none"})

    # Filter data for the selected survey year
    filtered = df[df['SurveyYear'] == selected_year].copy()
    if filtered.empty:
        return (*empty_charts, *empty_tables, f"No data available for {selected_year}.", True, {}, {"display": "none"})

    ###########################################################################
    # District Bar Chart (Stacked Bars)
    ###########################################################################
    grouped_district = filtered.groupby('DistrictCode')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_district['DistrictName'] = grouped_district['DistrictCode'].apply(
        lambda code: district_lookup.get(code, code)
    )
    grouped_district = grouped_district.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })
    fig_district = px.bar(
        grouped_district,
        x="DistrictName",
        y=["Male", "Female", "Not Available"],
        barmode="stack",
        title=f"Teachers by {vocab_district} in {selected_year}",
        labels={"DistrictName": vocab_district, "value": "Teacher Count", "variable": "Teacher Category"}
    )
    fig_district.update_layout(xaxis_tickangle=90)

    ###########################################################################
    # Teacher Count by Region (Stacked Bar Chart)
    ###########################################################################
    filtered['RegionName'] = filtered['RegionCode'].apply(lambda code: region_lookup.get(code, code))
    grouped_region = filtered.groupby('RegionName')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_region = grouped_region.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })
    fig_teachers_by_region_gender = px.bar(
        grouped_region,
        x="RegionName",
        y=["Male", "Female", "Not Available"],
        barmode="stack",
        title=f"Teacher Count by {vocab_region} and Gender for {selected_year}",
        labels={"RegionName": vocab_region, "value": "Teacher Count", "variable": "Gender"}
    )

    ###########################################################################
    # Teacher Count by Authority Govt (Pie Chart)
    ###########################################################################
    filtered['AuthorityGovtName'] = filtered['AuthorityGovtCode'].apply(lambda code: authoritygovts_lookup.get(code, code))
    grouped_school_authgovt = filtered.groupby('AuthorityGovtName')['TotalTeachers'].sum().reset_index()
    fig_teachers_authoritygovt = px.pie(
        grouped_school_authgovt,
        color_discrete_sequence=px.colors.qualitative.D3,
        names="AuthorityGovtName",
        values="TotalTeachers",
        title=f"Teacher Count by {vocab_authoritygovt} for {selected_year}",
        labels={"AuthorityGovtName": vocab_authoritygovt, "TotalTeachers": "Teacher Count"}
    )

    ###########################################################################
    # Teacher Count by Authority (Horizontal Stacked Bar Chart)
    ###########################################################################
    filtered['AuthorityName'] = filtered['AuthorityCode'].apply(lambda code: authorities_lookup.get(code, code))
    grouped_auth = filtered.groupby('AuthorityName')[["NumTeachersM", "NumTeachersF", "NumTeachersNA"]].sum().reset_index()
    grouped_auth = grouped_auth.rename(columns={
        "NumTeachersM": "Male",
        "NumTeachersF": "Female",
        "NumTeachersNA": "Not Available"
    })
    fig_teachers_authorities_gender = px.bar(
        grouped_auth,
        y="AuthorityName",
        x=["Male", "Female", "Not Available"],
        barmode="stack",
        orientation="h",
        title=f"Teacher Count by {vocab_authority} and Gender for {selected_year}",
        labels={"AuthorityName": vocab_authority, "value": "Teacher Count", "variable": "Gender"}
    ) 

    ###########################################################################
    # Teacher Count by School Type (Pie Chart)
    ###########################################################################
    filtered['SchoolTypeName'] = filtered['SchoolTypeCode'].apply(lambda code: schooltypes_lookup.get(code, code))
    grouped_schooltype = filtered.groupby('SchoolTypeName')['TotalTeachers'].sum().reset_index()
    fig_teachers_by_school_type = px.pie(
        grouped_schooltype,
        color_discrete_sequence=px.colors.qualitative.D3,
        names="SchoolTypeName",
        values="TotalTeachers",
        title=f"Teacher Count by {vocab_schooltype} for {selected_year}",
        labels={"SchoolTypeName": vocab_schooltype, "TotalTeachers": "Teacher Count"}
    )

    ###########################################################################
    # Teacher Count by Age Groups (Diverging Horizontal Bar Chart)
    ###########################################################################
    grouped_age = filtered.groupby('AgeGroup')[['NumTeachersF', 'NumTeachersM']].sum().reset_index()
    grouped_age = grouped_age.rename(columns={'NumTeachersF': 'Female', 'NumTeachersM': 'Male'})
    grouped_age['Female'] = -grouped_age['Female']  # Negative for diverging bar chart

    fig_teachers_agegroup_gender = px.bar(
        grouped_age,
        y="AgeGroup",
        x=["Female", "Male"],
        orientation='h',
        title=f"Teacher Count by Age Groups for {selected_year}",
        labels={"AgeGroup": "Age Group", "value": "Teacher Count", "variable": "Gender"}
    )

    # Symmetric axis based on max absolute
    max_val = max(grouped_age['Male'].max(), abs(grouped_age['Female'].min())) if not grouped_age.empty else 0
    rounded_max = math.ceil(max_val / 50) * 50 if max_val else 50
    num_ticks = 11
    tick_vals = np.linspace(-rounded_max, rounded_max, num=num_ticks)
    tick_text = [str(int(abs(val))) for val in tick_vals]
    fig_teachers_agegroup_gender.update_layout(xaxis=dict(range=[-rounded_max, rounded_max]))
    fig_teachers_agegroup_gender.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

    ###########################################################################
    # Helper function to create pivot tables for teachers
    ###########################################################################
    def create_teacher_pivot_table(df, row_col, col_col, row_label):
        """
        Create a pivot table with Male/Female/Total columns grouped by col_col values.
        Returns (data, columns) for DataTable.
        """
        df = df.copy()
        # Fill NaN values with 0 for numeric columns
        df['NumTeachersM'] = df['NumTeachersM'].fillna(0)
        df['NumTeachersF'] = df['NumTeachersF'].fillna(0)
        df['TeacherTotal'] = df['NumTeachersM'] + df['NumTeachersF']

        df_grouped = df.groupby([row_col, col_col]).agg({
            "NumTeachersM": "sum",
            "NumTeachersF": "sum",
            "TeacherTotal": "sum"
        }).reset_index()

        df_pivot = df_grouped.pivot(
            index=row_col, columns=col_col, values=["NumTeachersM", "NumTeachersF", "TeacherTotal"]
        )
        df_pivot = df_pivot.swaplevel(axis=1).sort_index(axis=1, level=0)
        df_pivot.rename(columns={"NumTeachersM": "Male", "NumTeachersF": "Female", "TeacherTotal": "Total"}, level=1, inplace=True)

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

    ###########################################################################
    # Table 1: Teachers by Island, School Type and Gender
    ###########################################################################
    table1_data, table1_cols = create_teacher_pivot_table(filtered, "Island", "SchoolTypeName", "Atoll/Island")

    ###########################################################################
    # Table 2: Teachers by School Type, Region and Gender
    ###########################################################################
    table2_data, table2_cols = create_teacher_pivot_table(filtered, "SchoolTypeName", "RegionName", vocab_schooltype)
    table2_title = f"Teachers by {vocab_schooltype}, {vocab_region} and Gender"

    ###########################################################################
    # Table 3: Teachers by District, School Type and Gender
    ###########################################################################
    # Use DistrictName from earlier
    filtered['DistrictName'] = filtered['DistrictCode'].apply(lambda code: district_lookup.get(code, code))
    table3_data, table3_cols = create_teacher_pivot_table(filtered, "DistrictName", "SchoolTypeName", vocab_district)
    table3_title = f"Teachers by {vocab_district}, {vocab_schooltype} and Gender"

    ###########################################################################
    # Table 4: Teachers by District, ISCED Levels and Gender
    ###########################################################################
    # Build ISCED lookup from iscedLevelsSub
    isced_levels_sub = lookup_dict.get("iscedLevelsSub", [])
    isced_lookup = {item["C"]: item["N"] for item in isced_levels_sub if "C" in item and "N" in item}
    filtered['ISCEDName'] = filtered['ISCEDSubClassCode'].map(isced_lookup).fillna(filtered['ISCEDSubClassCode'])
    table4_data, table4_cols = create_teacher_pivot_table(filtered, "DistrictName", "ISCEDName", vocab_district)
    table4_title = f"Teachers by {vocab_district}, ISCED Level and Gender"

    # success: hide alert, hide spacer, show content
    return (
        fig_district,
        fig_teachers_by_region_gender,
        fig_teachers_authoritygovt,
        fig_teachers_authorities_gender,
        fig_teachers_by_school_type,
        fig_teachers_agegroup_gender,
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
        "",
        False,
        {"display": "none"},
        {},
    )

layout = teachers_overview_layout()
