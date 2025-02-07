import os
import dash
from dash import dcc, html

import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__, 
    use_pages=True, 
    external_stylesheets=[dbc.themes.SANDSTONE]
)

server = app.server  # Expose the underlying Flask instance

# Create a Navigation Bar
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Dashboard", href="/")),        
        dbc.NavItem(dbc.NavLink("Schools", href="/schools")),
        dbc.NavItem(dbc.NavLink("Students", href="/students")),
        dbc.NavItem(dbc.NavLink("Teachers", href="/teachers")),
        dbc.NavItem(dbc.NavLink("Samples", href="/samples")),
    ],
    brand="Pacific EMIS Dashboard",
    brand_href="/",
    color="dark",
    dark=True,
)

# Define the app layout with a container for the pages
app.layout = html.Div([
    # dcc.Location is optional here, as dash.pages auto-injects it.
    dcc.Location(id="url", refresh=False),
    navbar,
    dash.page_container  # This container will render the current page's layout
])

# 🚀 Run the Dash App
# if __name__ == "__main__":
#     app.run_server(debug=False) #debug=True not working well with VS debugger?!

if __name__ == "__main__":
    os.environ["FLASK_ENV"] = "development"  # ✅ Enables Debug Mode
    os.environ["FLASK_RUN_EXTRA_FILES"] = "*.py"
    app.run_server(debug=True, dev_tools_hot_reload=True)  # ✅ Restores auto-reload