import warnings
import urllib3
import requests
import os
import dash
import time
from datetime import datetime, timezone

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from config import DEBUG, CONTEXT, DASHBOARDS

# 🔄 Background data refresh (ETag-aware)
from services.api import get_warehouse_version, background_refresh_all

# ✅ Robust server-side background refresher
import threading, logging

_bg_thread_started = False
_bg_lock = threading.Lock()

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _start_server_side_refresh():
    global _bg_thread_started
    with _bg_lock:
        if _bg_thread_started:
            return
        _bg_thread_started = True

        def _loop():
            while True:
                try:
                    background_refresh_all()
                except Exception as e:
                    logging.warning(f"Background refresh error: {e}")
                time.sleep(300)  # 5 minutes

        t = threading.Thread(target=_loop, name="bg-refresh", daemon=True)
        t.start()


app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.SANDSTONE])
app.config.suppress_callback_exceptions = True

server = app.server  # Expose the underlying Flask instance

# 🔧 Start background thread regardless of reloader quirks
_start_server_side_refresh()


# 🔧 Belt-and-suspenders: start again on first request (no-op if already started)
@server.before_request
def _ensure_bg_started():
    _start_server_side_refresh()


def build_navbar():
    """Build navigation bar dynamically from DASHBOARDS config."""
    nav_items: list = [dbc.NavItem(dbc.NavLink("Home", href="/"))]

    for section_key, section in DASHBOARDS.items():
        # Skip disabled sections
        if not section.get("enabled", False):
            continue

        # Build menu items for this section
        menu_items = []
        for item_key, item in section.get("items", {}).items():
            if item.get("enabled", False):
                menu_items.append(
                    dbc.DropdownMenuItem(item["label"], href=item["path"])
                )

        # Only add dropdown if there are enabled items
        if menu_items:
            nav_items.append(
                dbc.DropdownMenu(
                    children=menu_items,
                    nav=True,
                    in_navbar=True,
                    label=section["label"],
                    color="secondary",
                )
            )

    return dbc.NavbarSimple(
        children=nav_items,
        brand=f"{CONTEXT.upper()} Data Portal",
        brand_href="/",
        color="rgb(21,101,192)",
        dark=True,
    )


# Create Navigation Bar from config
navbar = build_navbar()

# Global footer
footer = dbc.Container(
    dbc.Row(
        dbc.Col(
            html.Span(
                "Last updated data from warehouse: unknown",
                id="warehouse-last-updated",
                style={"color": "white"},
            ),
            className="text-start",
        ),
        className="py-2",
        style={
            "backgroundColor": "rgb(21,101,192)",  # match navbar blue
        },
    ),
    fluid=True,
)

# Define the app layout with a container for the pages
app.layout = html.Div(
    [
        # dcc.Location is optional here, as dash.pages auto-injects it.
        dcc.Location(id="url", refresh=False),
        navbar,
        # 🔄 Global warehouse version pollers (present on every page)
        dcc.Interval(id="warehouse-version-tick", interval=60 * 1000, n_intervals=0),
        dcc.Store(id="warehouse-version-store"),
        dash.page_container,  # This container will render the current page's layout
        footer,
        # 🔄 Background interval + invisible store to carry callback output
        dcc.Store(id="bg-refresh-state"),
        dcc.Interval(id="bg-refresh", interval=300_000, n_intervals=0),  # 5 minutes
    ]
)


@dash.callback(
    Output("warehouse-version-store", "data"),
    Input("warehouse-version-tick", "n_intervals"),
    State("warehouse-version-store", "data"),
    prevent_initial_call=False,
)
def poll_warehouse_version(_n, current):
    try:
        new_ver = get_warehouse_version()  # e.g. {'id': '...', 'datetime': '...'}

        if not new_ver:
            raise PreventUpdate

        # Only update when changed
        if current and new_ver == current:
            raise PreventUpdate

        return new_ver

    except PreventUpdate:
        # This is the normal "no change" path — don't log as an error
        raise
    except Exception as e:
        # Real errors only
        print("Version poll error:", e)
        raise PreventUpdate


# Format helper
def _format_last_updated(version_data):
    if not version_data or not version_data.get("datetime"):
        return "Last updated data from warehouse: unknown"
    raw = version_data["datetime"]
    try:
        iso = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        pretty = dt_utc.strftime("%b %d, %Y, %H:%M:%S UTC")
        return f"Last updated data from warehouse: {pretty}"
    except Exception:
        return f"Last updated data from warehouse: {raw} (raw)"


# One global callback
@app.callback(
    Output("warehouse-last-updated", "children"),
    Input("warehouse-version-store", "data"),
)
def _update_footer_label(version_data):
    if not version_data:
        raise PreventUpdate
    return _format_last_updated(version_data)


# Background refresh callback (runs regardless of user navigation)
@dash.callback(Output("bg-refresh-state", "data"), Input("bg-refresh", "n_intervals"))
def _background_refresh(_):
    background_refresh_all()
    return {"last": time.time()}


# Define chart palettes
import plotly.express as px

px.defaults.color_discrete_sequence = px.colors.qualitative.D3  # type: ignore[assignment]
px.defaults.color_continuous_scale = px.colors.sequential.Cividis  # type: ignore[assignment]


# 🚀 Run the Dash App
# if __name__ == "__main__":
#     app.run_server(debug=False) #debug=True not working well with VS debugger?!

if __name__ == "__main__":
    os.environ["FLASK_ENV"] = "development"  # ✅ Enables Debug Mode
    os.environ["FLASK_RUN_EXTRA_FILES"] = "*.py"
    app.run_server(debug=DEBUG, dev_tools_hot_reload=DEBUG)  # ✅ Restores auto-reload
