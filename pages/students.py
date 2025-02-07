import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from tabulate import tabulate
from dash.dependencies import Input, Output
from services.api import df_tableenrolx, lookup_dict

dash.register_page(__name__, path="/students", name="Students")

# Filters
# Extract survey years from lookup dictionary (assuming it contains a "surveyYears" key)
survey_years = lookup_dict.get("surveyYears", [])

print("survey_years", survey_years)

# Create dropdown options using 'N' for display and 'C' for value
year_options = [{'label': item['N'], 'value': item['C']} for item in survey_years]

# Determine the default value: the highest available year
default_year = max([int(item['C']) for item in survey_years], default=0)  # Avoid errors if empty
default_year = str(default_year) if default_year else None  # Convert to string if needed

# ✅ **Define Layout inside a Function**
def students_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H3("Students Dashboard"), width=12, className="m-1"),
        ]),
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="year-filter",  # 🔥 Ensure this ID is correctly defined
                    options=year_options,
                    value=default_year,  # Default to latest year
                    clearable=False,
                    style={'width': '200px'}
                ),
                className="m-1"
            )
        ]),
        dbc.Row([    
            dbc.Col(dcc.Graph(id="fig-island-gender-graph"), md=12, xs=12, className="p-3"),
            #dbc.Col(dcc.Graph(id="fig-district-gender-graph"), md=6, xs=12, className="p-3"),
            #dbc.Col(dcc.Graph(id="fig-region-gender-graph"), md=6, xs=12, className="p-3"),
            #dbc.Col(dcc.Graph(id="fig-AuthorityGovt-gender-graph"), md=4, xs=12, className="p-3"),
            #dbc.Col(dcc.Graph(id="fig-Authority-gender-graph"), md=8, xs=12, className="p-3"),
        ], className="m-1"),
        #dbc.Row([
        #      dbc.Col([
        #         html.H3("Enrolments by School Type, District and Gender"),
        #         dash_table.DataTable(
        #             id="enrollment-schooltype-district",
        #             merge_duplicate_headers=True,
        #             style_table={"overflowX": "auto"},
        #             style_header={"textAlign": "center", "fontWeight": "bold"},
        #             style_cell={"textAlign": "left"},
        #         )
        #     ], md=12, className="m-1")
        # ]),
    ], fluid=True)

# ✅ **Now, Assign Layout Using Function**
layout = students_layout()

@dash.callback(
    Output(component_id="fig-island-gender-graph", component_property="figure"),
    #Output("fig-district-gender-graph", "figure"),
    #Output("fig-region-gender-graph", "figure"),
    #Output("fig-AuthorityGovt-gender-graph", "figure"),
    #Output("fig-Authority-gender-graph", "figure"),
    #utput("enrollment-schooltype-district", "data"),
    #Output("enrollment-schooltype-district", "columns"),
    Input(component_id="year-filter", component_property="value")
)

# Data processing
def update_dashboard(selected_year):
    if not selected_year:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # 🔹 Filter dataset for the selected year
    df_filtered = df_tableenrolx[df_tableenrolx["SurveyYear"] == selected_year].copy()

    # Filter the main dataset for the selected year.
    # (Assuming your df_tableenrolx has a column 'SurveyYear' that is comparable with selected_year.)
    df_filtered = df_tableenrolx[df_tableenrolx["SurveyYear"] == selected_year].copy()
    
    ##############################
    # Build the charts as before
    ##############################
    
    # -- By Island Chart --
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
        y="Island",
        x="Enrol",
        color="Gender",
        orientation="h",
        title="Enrolments by Island",
        labels={"Enrol": "Total Enrolments", "Island": "Island", "Gender": "Gender"}
    )
    
    # # -- By District Chart --
    # df_district_gender = df_filtered.groupby("District").agg({
    #     "EnrolM": "sum",
    #     "EnrolF": "sum"
    # }).reset_index()
    # df_district_gender_melt = df_district_gender.melt(
    #     id_vars="District", 
    #     value_vars=["EnrolM", "EnrolF"],
    #     var_name="Gender", 
    #     value_name="Enrol"
    # )
    # df_district_gender_melt["Gender"] = df_district_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    # fig_district_gender = px.bar(
    #     df_district_gender_melt,
    #     y="District",
    #     x="Enrol",
    #     color="Gender",
    #     orientation="h",
    #     title="Enrolments by District",
    #     labels={"Enrol": "Total Enrolments", "District": "District", "Gender": "Gender"}
    # )
    
    # # -- By Region Chart --
    # df_region_gender = df_filtered.groupby("Region").agg({
    #     "EnrolM": "sum",
    #     "EnrolF": "sum"
    # }).reset_index()
    # df_region_gender_melt = df_region_gender.melt(
    #     id_vars="Region", 
    #     value_vars=["EnrolM", "EnrolF"],
    #     var_name="Gender", 
    #     value_name="Enrol"
    # )
    # df_region_gender_melt["Gender"] = df_region_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    # fig_region_gender = px.bar(
    #     df_region_gender_melt,
    #     y="Region",
    #     x="Enrol",
    #     color="Gender",
    #     orientation="h",
    #     title="Enrolments by Region",
    #     labels={"Enrol": "Total Enrolments", "Region": "Region", "Gender": "Gender"}
    # )
    
    # # -- By AuthorityGovt Chart --
    # df_AuthorityGovt_gender = df_filtered.groupby("AuthorityGovt").agg({
    #     "EnrolM": "sum",
    #     "EnrolF": "sum"
    # }).reset_index()
    # df_AuthorityGovt_gender_melt = df_AuthorityGovt_gender.melt(
    #     id_vars="AuthorityGovt", 
    #     value_vars=["EnrolM", "EnrolF"],
    #     var_name="Gender", 
    #     value_name="Enrol"
    # )
    # df_AuthorityGovt_gender_melt["Gender"] = df_AuthorityGovt_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    # fig_AuthorityGovt_gender = px.bar(
    #     df_AuthorityGovt_gender_melt,
    #     y="AuthorityGovt",
    #     x="Enrol",
    #     color="Gender",
    #     orientation="h",
    #     title="Enrolments by Authority Government",
    #     labels={"Enrol": "Total Enrolments", "AuthorityGovt": "Authority Government", "Gender": "Gender"}
    # )
    
    # # -- By Authority Chart --
    # df_Authority_gender = df_filtered.groupby("Authority").agg({
    #     "EnrolM": "sum",
    #     "EnrolF": "sum"
    # }).reset_index()
    # df_Authority_gender_melt = df_Authority_gender.melt(
    #     id_vars="Authority", 
    #     value_vars=["EnrolM", "EnrolF"],
    #     var_name="Gender", 
    #     value_name="Enrol"
    # )
    # df_Authority_gender_melt["Gender"] = df_Authority_gender_melt["Gender"].map({"EnrolM": "Male", "EnrolF": "Female"})
    # fig_Authority_gender = px.bar(
    #     df_Authority_gender_melt,
    #     y="Authority",
    #     x="Enrol",
    #     color="Gender",
    #     orientation="h",
    #     title="Enrolments by Authority",
    #     labels={"Enrol": "Total Enrolments", "Authority": "Authority", "Gender": "Gender"}
    # )
    
    # # -- Table: Enrolments by School Type, District and Gender --
    # # (Repeat your table-building steps using df_filtered)
    # df_filtered['EnrolTotal'] = df_filtered['EnrolM'] + df_filtered['EnrolF']
    # df_grouped_table = df_filtered.groupby(['SchoolType', 'District']).agg({
    #     "EnrolM": "sum",
    #     "EnrolF": "sum",
    #     "EnrolTotal": "sum"
    # }).reset_index()
    # df_pivot_table = df_grouped_table.pivot(index="SchoolType", columns="District", values=["EnrolM", "EnrolF", "EnrolTotal"])
    # df_pivot_table = df_pivot_table.swaplevel(axis=1).sort_index(axis=1, level=0)
    # df_pivot_table.rename(columns={"EnrolM": "Male", "EnrolF": "Female", "EnrolTotal": "Total"}, level=1, inplace=True)
    # df_pivot_table[("Total", "Male")] = df_pivot_table.xs("Male", axis=1, level=1).sum(axis=1)
    # df_pivot_table[("Total", "Female")] = df_pivot_table.xs("Female", axis=1, level=1).sum(axis=1)
    # df_pivot_table[("Total", "Total")] = df_pivot_table.xs("Total", axis=1, level=1).sum(axis=1)
    # df_pivot_table = df_pivot_table.sort_index(axis=1, level=0)
    # df_pivot_table.reset_index(inplace=True)
    # df_pivot_table.rename(columns={"SchoolType": "School Type"}, inplace=True)
    # grand_total_table = df_pivot_table.drop(columns=["School Type"]).sum(axis=0).to_frame().T
    # grand_total_table.insert(0, "School Type", "Grand Total")
    # df_pivot_table = pd.concat([df_pivot_table, grand_total_table], ignore_index=True)
    # def fix_column(col):
    #     if isinstance(col, tuple):
    #         if col[0] == "SchoolType":
    #             return "School Type"
    #         else:
    #             return f"{col[0]}_{col[1]}"
    #     return col
    # df_pivot_table.columns = [fix_column(col) for col in df_pivot_table.columns]
    # table_columns_table = [{'id': 'School Type', 'name': 'School Type'}]
    # for col in df_pivot_table.columns:
    #     if col != 'School Type':
    #         district, measure = col.split("_")
    #         table_columns_table.append({'id': col, 'name': [district, measure]})
    # table_data = df_pivot_table.to_dict("records")

    return fig_island_gender #, fig_district_gender, fig_region_gender, fig_AuthorityGovt_gender, fig_Authority_gender, table_data, table_columns_table

    # return (fig_island_gender, fig_district_gender, fig_region_gender, 
    #         fig_AuthorityGovt_gender, fig_Authority_gender, table_data, table_columns_table)
