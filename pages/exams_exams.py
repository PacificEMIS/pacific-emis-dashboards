import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash import dash_table
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd

# Import data and lookup dictionary from the API module
from services.api import (
    get_df_exams,
    get_latest_year_with_data,
    district_lookup,
    region_lookup,
    authoritygovts_lookup,
    vocab_district,
    vocab_region,
    vocab_authoritygovt,
    lookup_dict,
)

dash.register_page(__name__, path="/exams/exams", name="Exams - Exam Level")

# Achievement level color scheme (using descriptions)
ACHIEVEMENT_COLORS = {
    "Beginning": "#FF0000",
    "Developing": "#FFC000",
    "Proficient": "#92D050",
    "Advanced": "#00B050",
}
ACHIEVEMENT_LEVELS = ["Beginning", "Developing", "Proficient", "Advanced"]

# Analysis type options
ANALYSIS_TYPE_OPTIONS = [
    {"label": "Candidate Count", "value": "candidateCount"},
    {"label": "Indicator Count", "value": "indicatorCount"},
    {"label": "Weighted Indicator Count", "value": "weight"},
]

# Fixed record type for this page
RECORD_TYPE = "Exam"

# Filters
survey_years = lookup_dict.get("surveyYears", [])
year_options = [{"label": item["N"], "value": item["C"]} for item in survey_years]
try:
    default_year = get_latest_year_with_data(get_df_exams(), year_column="examYear")
except Exception:
    default_year = year_options[0]["value"] if year_options else None


def create_mirror_bar_chart_percentage(grouped_df, y_col, value_col, title, y_label, full_label_col=None, height=None):
    """Create a horizontal mirror bar chart with percentages for achievement levels.

    This chart displays a single row per y-value, with stacked bars showing the distribution
    of achievement levels (Beginning, Developing on the left; Proficient, Advanced on the right).

    Args:
        grouped_df: DataFrame with columns for y_col, value_col, and 'AchievementLevel'
        y_col: Column name for y-axis categories
        value_col: Column name for the count/value to display
        title: Chart title
        y_label: Y-axis label
        full_label_col: Optional column with full labels for tooltips
        height: Chart height in pixels. If None, calculated dynamically based on number of items
                (min 300px, max 800px, 50px per item)

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    if grouped_df.empty:
        return fig

    y_values = list(grouped_df[y_col].unique())

    # Calculate dynamic height based on number of items
    if height is None:
        height = max(300, min(len(y_values) * 50, 800))
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
        percentages = []
        hover_data = []
        for y in y_values:
            raw_val = values_dict.get(y, 0)
            total = totals.get(y, 1)
            pct = (raw_val / total * 100) if total > 0 else 0
            percentages.append(pct)
            hover_data.append((full_labels.get(y, y), raw_val, abs(pct)))

        if level in ["Beginning", "Developing"]:
            percentages = [-p for p in percentages]

        fig.add_trace(go.Bar(
            y=y_values, x=percentages, name=level, orientation="h",
            marker_color=ACHIEVEMENT_COLORS[level],
            hovertemplate="%{customdata[0]}<br>" + level + ": %{customdata[1]:,.0f} (%{customdata[2]:.1f}%)<extra></extra>",
            customdata=hover_data,
        ))

    tick_vals = [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100]
    tick_text = ["100%", "80%", "60%", "40%", "20%", "0%", "20%", "40%", "60%", "80%", "100%"]

    fig.update_layout(
        barmode="relative", title=title,
        xaxis=dict(title="Percentage", tickvals=tick_vals, ticktext=tick_text, range=[-105, 105]),
        yaxis=dict(title=y_label),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=height,
    )
    return fig


def create_annotated_mirror_percentage_chart(grouped_df, y_col, group_col, value_col, title, y_label, group_label_func=str, full_label_col=None, reverse_groups=False, y_order=None, height=None):
    """Create a grouped horizontal mirror bar chart with percentages and annotations.

    This chart displays multiple rows per y-value (one per group), with stacked bars showing
    the distribution of achievement levels. It's used for breakdowns by year, district, region, etc.

    Args:
        grouped_df: DataFrame with columns for y_col, group_col, value_col, and 'AchievementLevel'
        y_col: Column name for primary y-axis categories (e.g., exam names)
        group_col: Column name for grouping within each y-value (e.g., year, district)
        value_col: Column name for the count/value to display
        title: Chart title
        y_label: Y-axis label
        group_label_func: Function to format group labels (default: str)
        full_label_col: Optional column with full labels for tooltips
        reverse_groups: If True, reverse the order of groups (useful for year sorting)
        y_order: Optional list specifying the order of y-values
        height: Chart height in pixels. If None, calculated dynamically based on content
                (min 300px, max 2000px, 40px per row)

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    if grouped_df.empty:
        return fig

    # Use provided y_order if available, otherwise use unique values from data
    if y_order is not None:
        y_values = [y for y in y_order if y in grouped_df[y_col].values]
    else:
        y_values = list(grouped_df[y_col].unique())
    groups = sorted(grouped_df[group_col].unique(), reverse=reverse_groups)

    # Calculate dynamic height based on number of items if not provided
    num_rows = len(y_values) * len(groups)
    if height is None:
        # Scale between min 300 and max based on content
        # Use 40px per row with min/max bounds
        height = max(300, min(num_rows * 40, 2000))

    # Get full labels for tooltips if available
    if full_label_col and full_label_col in grouped_df.columns:
        full_labels = dict(zip(grouped_df[y_col], grouped_df[full_label_col]))
    else:
        full_labels = {y: y for y in y_values}

    # Build categories: iterate by label first, then groups within each label
    y_categories = []
    y_ticktext = []
    for label in y_values:
        for group in groups:
            y_categories.append(f"{label}|{group}")
            y_ticktext.append(label)

    row_totals = grouped_df.groupby([y_col, group_col])[value_col].sum().to_dict()

    # Order levels so stacking produces left-to-right: Beginning, Developing, Proficient, Advanced
    level_order = ["Developing", "Beginning", "Proficient", "Advanced"]
    for level in level_order:
        level_data = grouped_df[grouped_df["AchievementLevel"] == level]
        y_vals = []
        percentages = []
        hover_data = []
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

        fig.add_trace(go.Bar(
            y=y_vals, x=percentages, name=level, orientation="h",
            marker_color=ACHIEVEMENT_COLORS[level],
            hovertemplate="%{customdata[0]}<br>" + level + ": %{customdata[1]:,.0f} (%{customdata[2]:.1f}%)<extra></extra>",
            customdata=hover_data,
        ))

    # Calculate annotation positions
    row_positive_pct = {}
    for label in y_values:
        for group in groups:
            key = f"{label}|{group}"
            total = row_totals.get((label, group), 1)
            positive_sum = 0
            for lvl in ["Proficient", "Advanced"]:
                lvl_data = grouped_df[
                    (grouped_df[group_col] == group) & (grouped_df[y_col] == label) & (grouped_df["AchievementLevel"] == lvl)
                ]
                if not lvl_data.empty:
                    positive_sum += lvl_data[value_col].sum()
            pct = (positive_sum / total * 100) if total > 0 else 0
            row_positive_pct[key] = pct

    annotations = []
    for label in y_values:
        for group in groups:
            key = f"{label}|{group}"
            x_pos = row_positive_pct.get(key, 0) + 2
            annotations.append(dict(
                x=x_pos, y=key, text=group_label_func(group),
                showarrow=False, font=dict(size=10, color="gray"), xanchor="left",
            ))

    tick_vals = [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100]
    tick_text = ["100%", "80%", "60%", "40%", "20%", "0%", "20%", "40%", "60%", "80%", "100%"]

    fig.update_layout(
        barmode="relative", title=title, height=height,
        xaxis=dict(title="Percentage", tickvals=tick_vals, ticktext=tick_text, range=[-105, 115]),
        yaxis=dict(title=y_label, tickmode="array", tickvals=y_categories, ticktext=y_ticktext,
                   categoryorder="array", categoryarray=y_categories[::-1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=annotations,
    )
    return fig


def get_display_label(key, description, max_length=40):
    """Create truncated display label from Key and Description for Y-axis.

    Args:
        key: The key/code value
        description: The full description
        max_length: Maximum length for the display label (default 40)

    Returns:
        Truncated label for display on Y-axis
    """
    if pd.isna(key):
        label = str(description) if pd.notna(description) else "Unknown"
    elif pd.isna(description) or key == description:
        label = str(key)
    else:
        label = f"{key}: {description}"

    # Truncate if too long
    if len(label) > max_length:
        return label[:max_length - 3] + "..."
    return label


def get_full_label(key, description):
    """Create full label from Key and Description for tooltips."""
    if pd.isna(key):
        return str(description) if pd.notna(description) else "Unknown"
    if pd.isna(description) or key == description:
        return str(key)
    return f"{key}: {description}"


def get_analysis_label(analysis_type):
    """Get human-readable label for analysis type."""
    return {"candidateCount": "Candidate Count", "indicatorCount": "Indicator Count", "weight": "Weighted Indicator Count"}.get(analysis_type, analysis_type)


def layout():
    return dbc.Container([
        dbc.Row([dbc.Col(html.H1("Exams Overview"), width=12, className="m-1")]),
        dbc.Row([
            dbc.Col([
                html.Label("Year", className="fw-bold"),
                dcc.Dropdown(id="exams-exam-year-filter", options=year_options, value=default_year, clearable=False),
            ], md=2, className="m-1"),
            dbc.Col([
                html.Label("Exam", className="fw-bold"),
                dcc.Dropdown(id="exams-exam-exam-filter", options=[], value=None, placeholder="Select Exam...", clearable=False),
            ], md=4, className="m-1"),
            dbc.Col([
                html.Label("Analysis", className="fw-bold"),
                dcc.Dropdown(id="exams-exam-analysis-filter", options=ANALYSIS_TYPE_OPTIONS, value="candidateCount", clearable=False),
            ], md=2, className="m-1"),
        ]),
        dcc.Loading(
            id="exams-exam-loading", type="default",
            children=html.Div(id="exams-exam-loading-spacer", style={"minHeight": "50vh"},
                children=dbc.Row([dbc.Col(dbc.Alert(id="exams-exam-nodata-msg", color="warning", is_open=False), width=12, className="m-1")])
            ),
        ),
        html.Div(id="exams-exam-content", style={"display": "none"}, children=[
            dbc.Row([dbc.Col(dcc.Graph(id="exams-exam-main-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-exam-year-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-exam-district-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-exam-region-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col(dcc.Graph(id="exams-exam-authgovt-chart"), md=12, className="p-3")], className="m-1"),
            dbc.Row([dbc.Col([
                html.H3(id="exams-exam-table-title"),
                dash_table.DataTable(id="exams-exam-table", style_table={"overflowX": "auto"},
                    style_header={"textAlign": "center", "fontWeight": "bold"}, style_cell={"textAlign": "left"},
                    style_data_conditional=[{"if": {"column_id": "Total"}, "fontWeight": "bold"}]),
            ], md=12, className="m-1")]),
        ]),
    ], fluid=True)


@dash.callback(
    Output("exams-exam-exam-filter", "options"),
    Output("exams-exam-exam-filter", "value"),
    Input("exams-exam-year-filter", "value"),
    Input("warehouse-version-store", "data"),
)
def update_exam_dropdown(selected_year, _):
    df = get_df_exams()
    if df is None or df.empty:
        return [], None
    if selected_year and "examYear" in df.columns:
        year_df = df[df["examYear"] == selected_year]
    else:
        year_df = df
    if year_df.empty:
        return [], None

    exam_records = year_df[year_df["RecordType"] == "Exam"]
    if not exam_records.empty and "Description" in exam_records.columns:
        exams = exam_records[["examCode", "Description"]].drop_duplicates()
        options = [{"label": f"{row['examCode']}: {row['Description']}", "value": row["examCode"]} for _, row in exams.iterrows()]
    elif "examCode" in year_df.columns:
        options = [{"label": code, "value": code} for code in sorted(year_df["examCode"].unique())]
    else:
        return [], None
    return options, options[0]["value"] if options else None


@dash.callback(
    Output("exams-exam-main-chart", "figure"),
    Output("exams-exam-year-chart", "figure"),
    Output("exams-exam-district-chart", "figure"),
    Output("exams-exam-region-chart", "figure"),
    Output("exams-exam-authgovt-chart", "figure"),
    Output("exams-exam-table", "data"),
    Output("exams-exam-table", "columns"),
    Output("exams-exam-table-title", "children"),
    Output("exams-exam-nodata-msg", "children"),
    Output("exams-exam-nodata-msg", "is_open"),
    Output("exams-exam-loading-spacer", "style"),
    Output("exams-exam-content", "style"),
    Input("exams-exam-year-filter", "value"),
    Input("exams-exam-exam-filter", "value"),
    Input("exams-exam-analysis-filter", "value"),
    Input("warehouse-version-store", "data"),
)
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

    # Apply lookups
    filtered["DistrictName"] = filtered["DistrictCode"].map(district_lookup).fillna(filtered["DistrictCode"].fillna("Unknown")) if "DistrictCode" in filtered.columns else "Unknown"
    filtered["RegionName"] = filtered["RegionCode"].map(region_lookup).fillna(filtered["RegionCode"].fillna("Unknown")) if "RegionCode" in filtered.columns else "Unknown"
    filtered["AuthorityGroupName"] = filtered["AuthorityGovtCode"].map(authoritygovts_lookup).fillna(filtered["AuthorityGovtCode"].fillna("Unknown")) if "AuthorityGovtCode" in filtered.columns else "Unknown"

    exam_name = selected_exam
    exam_rec = df[(df["examCode"] == selected_exam) & (df["RecordType"] == "Exam")]
    if not exam_rec.empty and "Description" in exam_rec.columns:
        desc = exam_rec["Description"].iloc[0]
        if pd.notna(desc):
            exam_name = f"{selected_exam}: {desc}"

    analysis_label = get_analysis_label(analysis_type)
    value_col = analysis_type

    # Create truncated display labels for Y-axis and full labels for tooltips
    filtered["DisplayLabel"] = filtered.apply(lambda r: get_display_label(r.get("Key"), r.get("Description")), axis=1)
    filtered["FullLabel"] = filtered.apply(lambda r: get_full_label(r.get("Key"), r.get("Description")), axis=1)

    # Chart 1: Main
    grouped_main = filtered.groupby(["DisplayLabel", "FullLabel", "AchievementLevel"])[value_col].sum().reset_index()
    fig_main = create_mirror_bar_chart_percentage(grouped_main, "DisplayLabel", value_col, f"{exam_name} - Exams ({analysis_label})", "Exam", "FullLabel")

    # Chart 2: By Year (last 5 years based on selected year)
    min_year = selected_year - 4  # Show 5 years: selected_year-4 to selected_year
    year_data = df[(df["examCode"] == selected_exam) & (df["RecordType"] == RECORD_TYPE) & (df["examYear"] >= min_year) & (df["examYear"] <= selected_year)].copy()
    if not year_data.empty:
        year_data["DisplayLabel"] = year_data.apply(lambda r: get_display_label(r.get("Key"), r.get("Description")), axis=1)
        year_data["FullLabel"] = year_data.apply(lambda r: get_full_label(r.get("Key"), r.get("Description")), axis=1)
        year_data["AchievementLevel"] = year_data["achievementDesc"].fillna("Unknown")
        # Get consistent key order from filtered data (selected year)
        key_order = list(filtered["DisplayLabel"].unique())
        grouped_year = year_data.groupby(["examYear", "DisplayLabel", "FullLabel", "AchievementLevel"])[value_col].sum().reset_index()
        fig_year = create_annotated_mirror_percentage_chart(grouped_year, "DisplayLabel", "examYear", value_col,
            f"Results by Year - {exam_name} ({analysis_label})", "Exam", lambda y: str(int(y)), "FullLabel",
            reverse_groups=True, y_order=key_order)
    else:
        fig_year = {}

    # Chart 3: By District
    district_data = filtered[filtered["DistrictName"] != "Unknown"]
    if not district_data.empty:
        grouped_dist = district_data.groupby(["DisplayLabel", "FullLabel", "DistrictName", "AchievementLevel"])[value_col].sum().reset_index()
        fig_district = create_annotated_mirror_percentage_chart(grouped_dist, "DisplayLabel", "DistrictName", value_col,
            f"Results by {vocab_district} - {exam_name} ({analysis_label})", "Exam", str, "FullLabel")
    else:
        fig_district = {}

    # Chart 4: By Region
    region_data = filtered[filtered["RegionName"] != "Unknown"]
    if not region_data.empty:
        grouped_reg = region_data.groupby(["DisplayLabel", "FullLabel", "RegionName", "AchievementLevel"])[value_col].sum().reset_index()
        fig_region = create_annotated_mirror_percentage_chart(grouped_reg, "DisplayLabel", "RegionName", value_col,
            f"Results by {vocab_region} - {exam_name} ({analysis_label})", "Exam", str, "FullLabel")
    else:
        fig_region = {}

    # Chart 5: By Authority Group
    authgovt_data = filtered[filtered["AuthorityGroupName"] != "Unknown"]
    if not authgovt_data.empty:
        grouped_ag = authgovt_data.groupby(["DisplayLabel", "FullLabel", "AuthorityGroupName", "AchievementLevel"])[value_col].sum().reset_index()
        fig_authgovt = create_annotated_mirror_percentage_chart(grouped_ag, "DisplayLabel", "AuthorityGroupName", value_col,
            f"Results by {vocab_authoritygovt} - {exam_name} ({analysis_label})", "Exam", str, "FullLabel")
    else:
        fig_authgovt = {}

    # Table
    table_title = f"Results by {vocab_district} - Percentage Distribution"
    table_df = district_data if not district_data.empty else filtered
    if not table_df.empty:
        pivot = table_df.pivot_table(index="DistrictName", columns="AchievementLevel", values=value_col, aggfunc="sum", fill_value=0).reset_index()
        for lvl in ACHIEVEMENT_LEVELS:
            if lvl not in pivot.columns:
                pivot[lvl] = 0
        level_cols = [l for l in ACHIEVEMENT_LEVELS if l in pivot.columns]
        pivot["Total"] = pivot[level_cols].sum(axis=1)
        for lvl in level_cols:
            pivot[lvl] = (pivot[lvl] / pivot["Total"] * 100).round(1).apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0.0%")
        pivot = pivot.rename(columns={"DistrictName": vocab_district})
        pivot = pivot[[vocab_district] + level_cols + ["Total"]]
        pivot["Total"] = pivot["Total"].round(0).astype(int)
        table_cols = [{"name": c, "id": c} for c in pivot.columns]
        table_data = pivot.to_dict("records")
    else:
        table_data, table_cols = [], []

    return fig_main, fig_year, fig_district, fig_region, fig_authgovt, table_data, table_cols, table_title, "", False, {"display": "none"}, {}
