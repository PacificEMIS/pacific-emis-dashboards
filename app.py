import os
import dash
from dash import dcc, html

import dash_bootstrap_components as dbc

from config import DEBUG, CONTEXT

app = dash.Dash(
    __name__, 
    use_pages=True, 
    external_stylesheets=[dbc.themes.SANDSTONE]    
)
app.config.suppress_callback_exceptions = True

server = app.server  # Expose the underlying Flask instance

# Create a Navigation Bar
navbar = dbc.NavbarSimple(
    children=[  
        dbc.NavItem(dbc.NavLink("Home", href="/")),      
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/indicators/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/indicators/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/indicators/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Indicators",
        #     color="secondary"
        # ),
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/budgets/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/budgets/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/budget/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Budgets",
        #     color="secondary"
        # ),
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/exams/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/exams/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/exams/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Exams",
        #     color="secondary"
        # ),
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/schools/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/schools/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/schools/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Schools",
        #     color="secondary"
        # ),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Overview", href="/students/overview"),
                dbc.DropdownMenuItem("Trends", href="/students/trends"),
                #dbc.DropdownMenuItem("Samples", href="/students/samples"),
            ],
            nav=True,
            in_navbar=True,
            label="Students",
            color="secondary"
        ),
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/specialed/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/specialed/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/specialed/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Special Education",
        #     color="secondary"
        # ),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Overview", href="/teachers/overview"),
                dbc.DropdownMenuItem("Trends", href="/teachers/trends"),
                dbc.DropdownMenuItem("CPD", href="/teachers/cpd"),
                dbc.DropdownMenuItem("CPD Attendance", href="/teachers/cpd-attendance"),
                #dbc.DropdownMenuItem("Samples", href="/teachers/samples"),
            ],
            nav=True,
            in_navbar=True,
            label="Teachers",
            color="secondary"
        ),
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/schoolaccreditation/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/schoolaccreditation/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/schoolaccreditation/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="Schools Accreditation",
        #     color="secondary"
        # ),
        # dbc.DropdownMenu(
        #     children=[
        #         dbc.DropdownMenuItem("Overview", href="/wash/overview"),
        #         dbc.DropdownMenuItem("Trends", href="/wash/trends"),
        #         dbc.DropdownMenuItem("Samples", href="/wash/samples"),
        #     ],
        #     nav=True,
        #     in_navbar=True,
        #     label="WASH Surveys",
        #     color="secondary"
        # ),
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Annual Census", href="/audit/annual-census"),
                #dbc.DropdownMenuItem("Samples", href="/audit/samples"),
            ],
            nav=True,
            in_navbar=True,
            label="Audit",
            color="secondary"
        ),
    ],
    brand=f"{CONTEXT.upper()} Dashboards",
    brand_href="/",
    color="rgb(21,101,192)",
    dark=True,
)

# Define the app layout with a container for the pages
app.layout = html.Div([
    # dcc.Location is optional here, as dash.pages auto-injects it.
    dcc.Location(id="url", refresh=False),
    navbar,
    dash.page_container  # This container will render the current page's layout
])


# Define chart palettes
import plotly.express as px
px.defaults.color_discrete_sequence = px.colors.qualitative.D3
px.defaults.color_continuous_scale = px.colors.sequential.Cividis


# 🚀 Run the Dash App
# if __name__ == "__main__":
#     app.run_server(debug=False) #debug=True not working well with VS debugger?!

if __name__ == "__main__":
    os.environ["FLASK_ENV"] = "development"  # ✅ Enables Debug Mode
    os.environ["FLASK_RUN_EXTRA_FILES"] = "*.py"
    app.run_server(debug=DEBUG, dev_tools_hot_reload=DEBUG)  # ✅ Restores auto-reload