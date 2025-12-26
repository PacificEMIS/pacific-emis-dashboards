import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd

from services.api import (
    get_df_exams, get_latest_year_with_data, district_lookup, region_lookup,
    authoritygovts_lookup, vocab_district, vocab_region, vocab_authoritygovt, lookup_dict,
)

dash.register_page(__name__, path="/exams/benchmarks", name="Exams - Benchmarks")

ACHIEVEMENT_COLORS = {"Beginning": "#FF0000", "Developing": "#FFC000", "Proficient": "#92D050", "Advanced": "#00B050"}
ACHIEVEMENT_LEVELS = ["Beginning", "Developing", "Proficient", "Advanced"]
ANALYSIS_TYPE_OPTIONS = [
    {"label": "Candidate Count", "value": "candidateCount"},
    {"label": "Indicator Count", "value": "indicatorCount"},
    {"label": "Weighted Indicator Count", "value": "weight"},
]
RECORD_TYPE = "Benchmark"

survey_years = lookup_dict.get("surveyYears", [])
year_options = [{"label": item["N"], "value": item["C"]} for item in survey_years]
try:
    default_year = get_latest_year_with_data(get_df_exams(), year_column="examYear")
except Exception:
    default_year = year_options[0]["value"] if year_options else None


def create_mirror_bar_chart_percentage(grouped_df, y_col, value_col, title, y_label, height=400, full_label_col=None):
    fig = go.Figure()
    if grouped_df.empty:
        return fig
    y_values = list(grouped_df[y_col].unique())
    totals = grouped_df.groupby(y_col)[value_col].sum().to_dict()
    # Get full labels for tooltips if available
    if full_label_col and full_label_col in grouped_df.columns:
        full_labels = dict(zip(grouped_df[y_col], grouped_df[full_label_col]))
    else:
        full_labels = {y: y for y in y_values}
    # Order levels so stacking produces left-to-right: Beginning, Developing, Proficient, Advanced
    level_order = ["Developing", "Beginning", "Proficient", "Advanced"]
    for level in level_order:
        level_data = grouped_df[grouped_df["AchievementLevel"] == level]
        values_dict = dict(zip(level_data[y_col], level_data[value_col]))
        percentages = [(values_dict.get(y, 0) / totals.get(y, 1) * 100) if totals.get(y, 1) > 0 else 0 for y in y_values]
        raw_values = [values_dict.get(y, 0) for y in y_values]
        hover_data = [(full_labels.get(y, y), rv, abs(p)) for y, rv, p in zip(y_values, raw_values, percentages)]
        if level in ["Beginning", "Developing"]:
            percentages = [-p for p in percentages]
        fig.add_trace(go.Bar(y=y_values, x=percentages, name=level, orientation="h", marker_color=ACHIEVEMENT_COLORS[level],
            hovertemplate="%{customdata[0]}<br>" + level + ": %{customdata[1]:,.0f} (%{customdata[2]:.1f}%)<extra></extra>", customdata=hover_data))
    tick_vals = [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100]
    tick_text = ["100%", "80%", "60%", "40%", "20%", "0%", "20%", "40%", "60%", "80%", "100%"]
    fig.update_layout(barmode="relative", title=title, height=height,
        xaxis=dict(title="Percentage", tickvals=tick_vals, ticktext=tick_text, range=[-105, 105]),
        yaxis=dict(title=y_label), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def create_annotated_mirror_percentage_chart(grouped_df, y_col, group_col, value_col, title, y_label, group_label_func=str, height=600, full_label_col=None, reverse_groups=False, y_order=None):
    fig = go.Figure()
    if grouped_df.empty:
        return fig
    # Use provided y_order or default to unique values from data
    if y_order is not None:
        y_values = y_order
    else:
        y_values = list(grouped_df[y_col].unique())
    groups = sorted(grouped_df[group_col].unique(), reverse=reverse_groups)
    # Get full labels for tooltips if available
    if full_label_col and full_label_col in grouped_df.columns:
        full_labels = dict(zip(grouped_df[y_col], grouped_df[full_label_col]))
    else:
        full_labels = {y: y for y in y_values}
    # Build categories: iterate by label first, then groups within each label
    y_categories, y_ticktext = [], []
    for label in y_values:
        for group in groups:
            y_categories.append(f"{label}|{group}")
            y_ticktext.append(label)
    row_totals = grouped_df.groupby([y_col, group_col])[value_col].sum().to_dict()
    # Order levels so stacking produces left-to-right: Beginning, Developing, Proficient, Advanced
    level_order = ["Developing", "Beginning", "Proficient", "Advanced"]
    for level in level_order:
        level_data = grouped_df[grouped_df["AchievementLevel"] == level]
        y_vals, percentages, hover_data = [], [], []
        for label in y_values:
            for group in groups:
                y_vals.append(f"{label}|{group}")
                row = level_data[(level_data[group_col] == group) & (level_data[y_col] == label)]
                raw_val = row[value_col].sum() if not row.empty else 0
                total = row_totals.get((label, group), 1)
                pct = (raw_val / total * 100) if total > 0 else 0
                percentages.append(pct)
                hover_data.append((full_labels.get(label, label), raw_val, abs(pct)))
        if level in ["Beginning", "Developing"]:
            percentages = [-p for p in percentages]
        fig.add_trace(go.Bar(y=y_vals, x=percentages, name=level, orientation="h", marker_color=ACHIEVEMENT_COLORS[level],
            hovertemplate="%{customdata[0]}<br>" + level + ": %{customdata[1]:,.0f} (%{customdata[2]:.1f}%)<extra></extra>", customdata=hover_data))
    row_positive_pct = {}
    for label in y_values:
        for group in groups:
            key = f"{label}|{group}"
            total = row_totals.get((label, group), 1)
            positive_sum = 0
            for lvl in ["Proficient", "Advanced"]:
                lvl_data = grouped_df[(grouped_df[group_col] == group) & (grouped_df[y_col] == label) & (grouped_df["AchievementLevel"] == lvl)]
                if not lvl_data.empty:
                    positive_sum += lvl_data[value_col].sum()
            row_positive_pct[key] = (positive_sum / total * 100) if total > 0 else 0
    annotations = [dict(x=row_positive_pct.get(f"{label}|{group}", 0) + 2, y=f"{label}|{group}", text=group_label_func(group),
        showarrow=False, font=dict(size=10, color="gray"), xanchor="left") for label in y_values for group in groups]
    tick_vals = [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100]
    tick_text = ["100%", "80%", "60%", "40%", "20%", "0%", "20%", "40%", "60%", "80%", "100%"]
    fig.update_layout(barmode="relative", title=title, height=height,
        xaxis=dict(title="Percentage", tickvals=tick_vals, ticktext=tick_text, range=[-105, 115]),
        yaxis=dict(title=y_label, tickmode="array", tickvals=y_categories, ticktext=y_ticktext, categoryorder="array", categoryarray=y_categories[::-1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), annotations=annotations)
    return fig


def get_display_label(key, description, max_length=40):
    """Create truncated display label for Y-axis."""
    if pd.isna(key):
        label = str(description) if pd.notna(description) else "Unknown"
    elif pd.isna(description) or key == description:
        label = str(key)
    else:
        label = f"{key}: {description}"
    if len(label) > max_length:
        return label[:max_length - 3] + "..."
    return label


def get_full_label(key, description):
    """Create full label for tooltips."""
    if pd.isna(key):
        return str(description) if pd.notna(description) else "Unknown"
    if pd.isna(description) or key == description:
        return str(key)
    return f"{key}: {description}"


def get_analysis_label(t):
    return {"candidateCount": "Candidate Count", "indicatorCount": "Indicator Count", "weight": "Weighted Indicator Count"}.get(t, t)


def layout():
    return dbc.Container([
        dbc.Row([dbc.Col(html.H1("Benchmarks Overview"), width=12, className="m-1")]),
        dbc.Row([
            dbc.Col([html.Label("Year", className="fw-bold"), dcc.Dropdown(id="exams-bench-year-filter", options=year_options, value=default_year, clearable=False)], md=2, className="m-1"),
            dbc.Col([html.Label("Exam", className="fw-bold"), dcc.Dropdown(id="exams-bench-exam-filter", options=[], value=None, placeholder="Select Exam...", clearable=False)], md=4, className="m-1"),
            dbc.Col([html.Label("Analysis", className="fw-bold"), dcc.Dropdown(id="exams-bench-analysis-filter", options=ANALYSIS_TYPE_OPTIONS, value="candidateCount", clearable=False)], md=2, className="m-1"),
        ]),
        dcc.Loading(id="exams-bench-loading", type="default",
            children=html.Div(id="exams-bench-loading-spacer", style={"minHeight": "50vh"},
                children=dbc.Row([dbc.Col(dbc.Alert(id="exams-bench-nodata-msg", color="warning", is_open=False), width=12, className="m-1")]))),
        html.Div(id="exams-bench-content", style={"display": "none"}, children=[
            dbc.Row([dbc.Col(dcc.Graph(id="exams-bench-main-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-bench-year-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-bench-district-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-bench-region-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-bench-authgovt-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col([html.H3(id="exams-bench-table-title"), dash_table.DataTable(id="exams-bench-table", style_table={"overflowX": "auto"},
                style_header={"textAlign": "center", "fontWeight": "bold"}, style_cell={"textAlign": "left"},
                style_data_conditional=[{"if": {"column_id": "Total"}, "fontWeight": "bold"}])], md=12, className="m-1")]),
        ]),
    ], fluid=True)


@dash.callback(Output("exams-bench-exam-filter", "options"), Output("exams-bench-exam-filter", "value"),
    Input("exams-bench-year-filter", "value"), Input("warehouse-version-store", "data"))
def update_exam_dropdown(selected_year, _):
    df = get_df_exams()
    if df is None or df.empty:
        return [], None
    year_df = df[df["examYear"] == selected_year] if selected_year and "examYear" in df.columns else df
    if year_df.empty:
        return [], None
    exam_records = year_df[year_df["RecordType"] == "Exam"]
    if not exam_records.empty and "Description" in exam_records.columns:
        exams = exam_records[["examCode", "Description"]].drop_duplicates()
        options = [{"label": f"{r['examCode']}: {r['Description']}", "value": r["examCode"]} for _, r in exams.iterrows()]
    elif "examCode" in year_df.columns:
        options = [{"label": c, "value": c} for c in sorted(year_df["examCode"].unique())]
    else:
        return [], None
    return options, options[0]["value"] if options else None


@dash.callback(
    Output("exams-bench-main-chart", "figure"), Output("exams-bench-year-chart", "figure"), Output("exams-bench-district-chart", "figure"),
    Output("exams-bench-region-chart", "figure"), Output("exams-bench-authgovt-chart", "figure"), Output("exams-bench-table", "data"),
    Output("exams-bench-table", "columns"), Output("exams-bench-table-title", "children"), Output("exams-bench-nodata-msg", "children"),
    Output("exams-bench-nodata-msg", "is_open"), Output("exams-bench-loading-spacer", "style"), Output("exams-bench-content", "style"),
    Input("exams-bench-year-filter", "value"), Input("exams-bench-exam-filter", "value"), Input("exams-bench-analysis-filter", "value"), Input("warehouse-version-store", "data"))
def update_dashboard(selected_year, selected_exam, analysis_type, _):
    empty = ({}, {}, {}, {}, {}, [], [], "", "", False, {}, {"display": "none"})
    if not selected_year or not selected_exam:
        return (*empty[:5], [], [], "", "Please select a year and exam.", True, {}, {"display": "none"})
    df = get_df_exams()
    if df is None or df.empty:
        return (*empty[:5], [], [], "", "No exam data available.", True, {}, {"display": "none"})
    for col in ["candidateCount", "indicatorCount", "weight"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    # Use achievementDesc directly for level names (Beginning, Developing, Proficient, Advanced)
    df["AchievementLevel"] = df["achievementDesc"].fillna("Unknown")
    filtered = df[(df["examYear"] == selected_year) & (df["examCode"] == selected_exam) & (df["RecordType"] == RECORD_TYPE)].copy()
    if filtered.empty:
        return (*empty[:5], [], [], "", f"No {RECORD_TYPE} data for {selected_exam} in {selected_year}.", True, {}, {"display": "none"})
    filtered["DistrictName"] = filtered["DistrictCode"].map(district_lookup).fillna(filtered["DistrictCode"].fillna("Unknown")) if "DistrictCode" in filtered.columns else "Unknown"
    filtered["RegionName"] = filtered["RegionCode"].map(region_lookup).fillna(filtered["RegionCode"].fillna("Unknown")) if "RegionCode" in filtered.columns else "Unknown"
    filtered["AuthorityGroupName"] = filtered["AuthorityGovtCode"].map(authoritygovts_lookup).fillna(filtered["AuthorityGovtCode"].fillna("Unknown")) if "AuthorityGovtCode" in filtered.columns else "Unknown"
    exam_name = selected_exam
    exam_rec = df[(df["examCode"] == selected_exam) & (df["RecordType"] == "Exam")]
    if not exam_rec.empty and "Description" in exam_rec.columns and pd.notna(exam_rec["Description"].iloc[0]):
        exam_name = f"{selected_exam}: {exam_rec['Description'].iloc[0]}"
    analysis_label, value_col = get_analysis_label(analysis_type), analysis_type
    filtered["DisplayLabel"] = filtered.apply(lambda r: get_display_label(r.get("Key"), r.get("Description")), axis=1)
    filtered["FullLabel"] = filtered.apply(lambda r: get_full_label(r.get("Key"), r.get("Description")), axis=1)
    num_items = filtered["DisplayLabel"].nunique()
    main_height = max(300, min(num_items * 50, 800))

    grouped_main = filtered.groupby(["DisplayLabel", "FullLabel", "AchievementLevel"])[value_col].sum().reset_index()
    key_order = filtered[["Key", "DisplayLabel"]].drop_duplicates().sort_values("Key")["DisplayLabel"].tolist()
    fig_main = create_mirror_bar_chart_percentage(grouped_main, "DisplayLabel", value_col, f"{exam_name} - Benchmarks ({analysis_label})", "Benchmark", height=main_height, full_label_col="FullLabel")
    if key_order:
        fig_main.update_yaxes(categoryorder="array", categoryarray=key_order[::-1])

    # Filter to last 5 years based on selected year
    min_year = selected_year - 4
    year_data = df[(df["examCode"] == selected_exam) & (df["RecordType"] == RECORD_TYPE) & (df["examYear"] >= min_year) & (df["examYear"] <= selected_year)].copy()
    if not year_data.empty:
        year_data["DisplayLabel"] = year_data.apply(lambda r: get_display_label(r.get("Key"), r.get("Description")), axis=1)
        year_data["FullLabel"] = year_data.apply(lambda r: get_full_label(r.get("Key"), r.get("Description")), axis=1)
        year_data["AchievementLevel"] = year_data["achievementDesc"].fillna("Unknown")
        grouped_year = year_data.groupby(["examYear", "DisplayLabel", "FullLabel", "AchievementLevel"])[value_col].sum().reset_index()
        year_height = max(800, num_items * len(year_data["examYear"].unique()) * 30)
        fig_year = create_annotated_mirror_percentage_chart(grouped_year, "DisplayLabel", "examYear", value_col, f"Results by Year - {exam_name} ({analysis_label})", "Benchmark", lambda y: str(int(y)), height=year_height, full_label_col="FullLabel", reverse_groups=True, y_order=key_order)
    else:
        fig_year = {}

    district_data = filtered[filtered["DistrictName"] != "Unknown"]
    if not district_data.empty:
        grouped_dist = district_data.groupby(["DisplayLabel", "FullLabel", "DistrictName", "AchievementLevel"])[value_col].sum().reset_index()
        dist_height = max(800, num_items * district_data["DistrictName"].nunique() * 40)
        fig_district = create_annotated_mirror_percentage_chart(grouped_dist, "DisplayLabel", "DistrictName", value_col, f"Results by {vocab_district} - {exam_name} ({analysis_label})", "Benchmark", str, height=dist_height, full_label_col="FullLabel", y_order=key_order)
    else:
        fig_district = {}

    region_data = filtered[filtered["RegionName"] != "Unknown"]
    if not region_data.empty:
        grouped_reg = region_data.groupby(["DisplayLabel", "FullLabel", "RegionName", "AchievementLevel"])[value_col].sum().reset_index()
        reg_height = max(800, num_items * region_data["RegionName"].nunique() * 25)
        fig_region = create_annotated_mirror_percentage_chart(grouped_reg, "DisplayLabel", "RegionName", value_col, f"Results by {vocab_region} - {exam_name} ({analysis_label})", "Benchmark", str, height=reg_height, full_label_col="FullLabel", y_order=key_order)
    else:
        fig_region = {}

    authgovt_data = filtered[filtered["AuthorityGroupName"] != "Unknown"]
    if not authgovt_data.empty:
        grouped_ag = authgovt_data.groupby(["DisplayLabel", "FullLabel", "AuthorityGroupName", "AchievementLevel"])[value_col].sum().reset_index()
        ag_height = max(600, num_items * authgovt_data["AuthorityGroupName"].nunique() * 25)
        fig_authgovt = create_annotated_mirror_percentage_chart(grouped_ag, "DisplayLabel", "AuthorityGroupName", value_col, f"Results by {vocab_authoritygovt} - {exam_name} ({analysis_label})", "Benchmark", str, height=ag_height, full_label_col="FullLabel", y_order=key_order)
    else:
        fig_authgovt = {}

    table_title = f"{RECORD_TYPE} Results - Percentage Distribution"
    if not filtered.empty:
        pivot = filtered.pivot_table(index="DisplayLabel", columns="AchievementLevel", values=value_col, aggfunc="sum", fill_value=0).reset_index()
        for lvl in ACHIEVEMENT_LEVELS:
            if lvl not in pivot.columns:
                pivot[lvl] = 0
        level_cols = [l for l in ACHIEVEMENT_LEVELS if l in pivot.columns]
        pivot["Total"] = pivot[level_cols].sum(axis=1)
        for lvl in level_cols:
            pivot[lvl] = (pivot[lvl] / pivot["Total"] * 100).round(1).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")
        pivot = pivot.rename(columns={"DisplayLabel": "Benchmark"})
        pivot = pivot[["Benchmark"] + level_cols + ["Total"]]
        pivot["Total"] = pivot["Total"].round(0).astype(int)
        table_cols = [{"name": c, "id": c} for c in pivot.columns]
        table_data = pivot.to_dict("records")
    else:
        table_data, table_cols = [], []

    return fig_main, fig_year, fig_district, fig_region, fig_authgovt, table_data, table_cols, table_title, "", False, {"display": "none"}, {}
