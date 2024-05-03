# Importing Libraries
import s3
import mysql_database
import radial_bar_chart
import invoke_lambda
import pandas as pd
import math, ast, json
import calendar
from datetime import datetime, date, timedelta
import plotly.express as px
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
from dash import Dash, html, dcc, Input, Output, State, callback_context, clientside_callback, no_update
from dash.exceptions import PreventUpdate
from flask import Flask, session
import secrets

# Read the latest Data directly from AWS and MySQL Database
# df = pd.read_csv("Data/final_24-02-2024_02_05_40.csv")
df = s3.get_data()
metadata_df = mysql_database.get_report_metadata("j.teng@chatstat.com")

# Defining Colors and Plotly Graph Options
image_folder = "https://chatstat-dashboard.s3.ap-southeast-2.amazonaws.com/images/"
plot_config = {"modeBarButtonsToRemove": ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d", "hoverClosestCartesian", "hoverCompareCartesian"],
               "staticPlot": False, "displaylogo": False}
platform_colors = {"Instagram": "#25D366", "Twitter": "#2D96FF", "Facebook": "#FF5100", "Tiktok": "#f6c604"}
alert_colors = {"High": "#FF5100", "Medium": "#f6c604", "Low": "#25D366"}
alert_overview_colors = {"High": "red", "Medium": "yellow", "Low": "green"}
comment_classification_colors = {"Offensive": "#FFD334", "Sexually Explicit": "#2D96FF", "Sexually Suggestive": "#FF5100", "Other": "#25D366", "Self Harm & Death": "#f77d07"}
category_bar_colors = {"Mental & Emotional Health": "rgb(255,211,52)", "Other Toxic Content": "rgb(45,150,255)", "Violence & Threats": "rgb(236,88,0)", "Cyberbullying": "rgb(37,211,102)", "Self Harm & Death": "rgb(255,81,0)", "Sexual & Inappropriate Content": "rgb(160,32,240)"}
platform_icons = {"Instagram": "skill-icons:instagram", "Twitter": "devicon:twitter", "Facebook": "devicon:facebook", "Tiktok": "logos:tiktok-icon"}


# Filter Functions
def user_filter(dataframe, user_value):
    dataframe = dataframe[dataframe["email_users"] == user_value]
    return dataframe

def time_filter(dataframe, time_value, date_range_value):
    if(time_value == "all"):
        end_date = datetime.combine(datetime.strptime(date_range_value[1], "%Y-%m-%d"), datetime.max.time())
        start_date = datetime.combine(datetime.strptime(date_range_value[0], "%Y-%m-%d"), datetime.min.time())
        dataframe["createTime_contents"] = pd.to_datetime(dataframe["createTime_contents"], format="%Y-%m-%d %H:%M:%S.%f")
        dataframe = dataframe[(dataframe["createTime_contents"] >= start_date) & (dataframe["createTime_contents"] <= end_date)]
        return dataframe
    else:
        end_date = datetime.combine(datetime.now(), datetime.max.time())
        if(time_value == "W"):
            start_date = end_date - timedelta(days=end_date.weekday())
        elif(time_value == "M"):
            start_date = end_date.replace(day=1)
        elif(time_value == "Q"):
            start_date = end_date.replace(day=1).replace(month=3*round((end_date.month - 1) // 3 + 1) - 2)
        elif(time_value == "A"):
            start_date = end_date.replace(day=1).replace(month=1)
        else:
            start_date = end_date
        start_date = datetime.combine(start_date, datetime.min.time())

        dataframe["createTime_contents"] = pd.to_datetime(dataframe["createTime_contents"], format="%Y-%m-%d %H:%M:%S.%f")
        dataframe = dataframe[(dataframe["createTime_contents"] >= start_date) & (dataframe["createTime_contents"] <= end_date)]
        return dataframe

def member_filter(dataframe, member_value):
    if((member_value is not None) and (member_value != "all")):
        dataframe = dataframe[dataframe["name_childrens"] == member_value]
    return dataframe

def platform_filter(dataframe, platform_value):
    if((platform_value is not None) and (platform_value != "all")):
        dataframe = dataframe[dataframe["platform_contents"] == platform_value]
    return dataframe

def alert_filter(dataframe, alert_value):
    if((alert_value is not None) and (alert_value != "all")):
        dataframe = dataframe[dataframe["alert_contents"] == alert_value]
    return dataframe

def slider_filter(dataframe, slider_value, date_dict):
    start_date = pd.to_datetime(date_dict[str(slider_value[0])], format="%Y-%m-%d").date()
    end_date = pd.to_datetime(date_dict[str(slider_value[1])], format="%Y-%m-%d").date()
    dataframe["commentTime_comments"] = pd.to_datetime(dataframe["commentTime_comments"], format="%Y-%m-%d %H:%M:%S").dt.date
    dataframe = dataframe[(dataframe["commentTime_comments"] >= start_date) & (dataframe["commentTime_comments"] <= end_date)]
    return dataframe


# Function if No Data is available
def no_data_graph():
    message = html.Div(className="no_data_container", children=[
        html.Img(src=image_folder + "empty_ghost.gif", alt="Empty", width="40%"),
        html.P("No Data to Display", className="no_data_message"),
        html.P("Please make a different Filter Selection", className="no_data_selection")
        ], style={"height": "100%"}
    )
    return message


# SideBar
sidebar = html.Div(className="sidebar", children=[
    html.Div(children=[
        html.A(html.Div(className="sidebar_header", children=[
            html.Img(src=image_folder + "chatstatlogo.png", alt="Logo"),
            html.H2("chatstat")
            ]), href="https://chatstat.com/", target="_blank", style={"color": "#25D366", "textDecoration": "none"}
        ),

        html.Div(className="sidebar_navlink_menu", children=[html.P("Main Menu"), html.Hr()]),
        dbc.Nav(className="sidebar_navlink", children=[
            dbc.NavLink(children=[html.Img(src=image_folder + "dashboard.png", alt="Dashboard"), html.Span("Dashboard")],
                        href="/Dashboard", active="exact", className="sidebar_navlink_option"),
            dbc.NavLink(children=[html.Img(src=image_folder + "analytics.png", alt="Analytics"), html.Span("Analytics")],
                        href="/Analytics", active="exact", className="sidebar_navlink_option"),
            dbc.NavLink(children=[html.Img(src=image_folder + "report.png", alt="Report"), html.Span("Report & Logs")],
                        href="/Report&Logs", active="exact", className="sidebar_navlink_option")
        ], vertical=True, pills=True),

        html.Div(className="sidebar_navlink_menu", children=[html.P("General"), html.Hr()]),
        dbc.Nav(className="sidebar_navlink", children=[
            dbc.NavLink(children=[html.Img(src=image_folder + "account.png", alt="Account"), html.Span("My Account")],
                        external_link=True, href="https://family.chatstat.com/family", target="_blank", className="sidebar_navlink_option"),
            dbc.NavLink(children=[html.Img(src=image_folder + "setting.png", alt="Settings"), html.Span("Settings")],
                        external_link=True, href="https://family.chatstat.com/settings", target="_blank", className="sidebar_navlink_option")
        ], vertical=True, pills=True)
    ]),

    html.Img(className="sidebar_help", src=image_folder + "help_circle.png", alt="Need Help"),
    html.Div(className="sidebar_help_container", children=[
        html.Img(src=image_folder + "help_circle.png", alt="Need Help", width="20%",
                 style={"position": "absolute", "top": "-15%", "padding": "5px", "border-radius": "100%", "background-color": "#25D366"}),
        html.P("Need Help?"),
        html.A(html.P("Go to Learning Centre", style={"padding": "0px 10px", "background-color": "#052F5F", "border-radius": "5px"}),
               href="https://chatstat.com/faq/", target="_blank", style={"color": "white", "textDecoration": "none"})
    ])
])


# Header
header = dmc.Header(className="header", height="8.5vh", fixed=False, children=[
    dmc.Text(className="header_title", id="header_title"),
    dmc.Menu(className="user_container", trigger="hover", children=[
        dmc.MenuTarget(html.Div(className="user_information", children=[
            dmc.Avatar(id="user_avatar", className="user_avatar", size="6vh", radius="100%",
                src="https://e7.pngegg.com/pngimages/799/987/png-clipart-computer-icons-avatar-icon-design-avatar-heroes-computer-wallpaper-thumbnail.png"),
            dmc.Text(id="user_name", className="user_name")
        ])),
        dmc.MenuDropdown(className="user_container_dropdown", children=[
            dmc.MenuItem(children=[
                html.Div(className="user_container_info", children=[html.Strong("Email:", style={"margin": "0"}), dmc.Space(w=10), html.P(id="user_email", style={"margin": "0"})]),
                html.Div(className="user_container_info", children=[html.Strong("Plan:", style={"margin": "0"}), dmc.Space(w=10), html.P(id="user_plan", style={"margin": "0"})]),
                html.A(dmc.Button("Upgrade Plan", leftIcon=DashIconify(icon="streamline:upload-computer", width=20), fullWidth=True, variant="gradient", gradient={"from": "teal", "to": "lime"}),
                       href="https://family.chatstat.com/pricing", style={"textDecoration": "none"})
            ]),
            dmc.MenuDivider(),
            dmc.MenuItem(className="user_container_option", children="My Account", icon=DashIconify(icon="material-symbols:account-box-outline", width=30), href="https://family.chatstat.com/family", target="_blank"),
            dmc.MenuItem(className="user_container_option", children="Settings", icon=DashIconify(icon="lets-icons:setting-alt-line", width=30), href="https://family.chatstat.com/settings", target="_blank"),
            dmc.MenuItem(className="user_container_option", children="Sign Out", icon=DashIconify(icon="tabler:logout-2", color="red", width=30), style={"color": "red"}, href="https://family.chatstat.com/signin")
        ])
    ])
])


# Controls
filters = html.Div(className="filter_row", children=[
    html.Div(className="filter_container", children=[
        html.P("FILTERS", className="filter_label"),
        dmc.HoverCard(openDelay=1000, position="right", transition="pop", withArrow=True, children=[
            dmc.HoverCardTarget(
                dmc.SegmentedControl(id="time_control", className="time_control", value="A", radius="md", size="xs", data=[
                    {"label": "Daily", "value": "D"},
                    {"label": "Weekly", "value": "W"},
                    {"label": "Monthly", "value": "M"},
                    {"label": "Quarterly", "value": "Q"},
                    {"label": "Yearly", "value": "A"},
                    {"label": "Custom Range", "value": "all"}
                ])
            ),
            dmc.HoverCardDropdown(className="time_control_information", id="time_control_information")
        ]),
        dbc.Popover(id="popover_date_picker", className="popover_date_picker", children=[
            dbc.PopoverHeader("Selected Date Range", className="popover_date_picker_label"),
            dmc.DateRangePicker(id="date_range_picker", className="date_range_picker", clearable=False, inputFormat="MMM DD, YYYY",
                                icon=DashIconify(icon=f"arcticons:calendar-simple-{datetime.now().day}", color="black", width=30),
                                value=[datetime.now().date()-timedelta(days=500), datetime.now().date()]
            )
            ], target="time_control", placement="bottom", trigger="legacy", hide_arrow=True
        ),
        html.Div(className="member_dropdown_container", children=[
            html.P("Members", className="member_dropdown_label"),
            dmc.Select(className="member_dropdown", id="member_dropdown", clearable=False, searchable=False, value="all",
               rightSection=DashIconify(icon="radix-icons:chevron-down", color="black")
            ),
        ]),
        html.Div(className="platform_dropdown_container", children=[
            html.P("Social Platform", className="platform_dropdown_label"),
            dmc.Select(className="platform_dropdown", id="platform_dropdown", clearable=False, searchable=False, value="all",
                rightSection=DashIconify(icon="radix-icons:chevron-down", color="black")
            )
        ]),
        html.Div(className="alert_dropdown_container", children=[
            html.P("Alert Level", className="alert_dropdown_label"),
            dmc.Select(className="alert_dropdown", id="alert_dropdown", clearable=False, searchable=False, value="all",
                rightSection=DashIconify(icon="radix-icons:chevron-down", color="black")
            )
        ]),
        dmc.ActionIcon(DashIconify(icon="grommet-icons:power-reset", color="white", width=25, flip="horizontal"), id="reset_filter_container", className="reset_filter_container", n_clicks=0, variant="transparent")
    ]),

    html.Div(className="searchbar_container", children=[
        html.P("Child Overview Snapshot", className="searchbar_label"),
        dmc.Select(className="searchbar", id="searchbar", clearable=True, searchable=True, placeholder="Search...", nothingFound="Nothing Found",
            iconWidth=40, icon=html.Img(src=image_folder + "chatstatlogo_black.png", alt="Logo", width="60%"),
            rightSection=DashIconify(icon="radix-icons:chevron-right", color="black"), limit=5,
            data=[{"group": "Members", "label": child_name.title(), "value": child_name} for child_name in list(df["name_childrens"].unique())] +
            [{"group": "ID", "label": child_id.title(), "value": child_id} for child_id in list(df["id_childrens"].unique())]
        )
    ]),
    dmc.Modal(className="child_overview", id="child_overview", zIndex=10, centered=True, overflow="outside", children=[
        html.Div(className="overview_info_container", children=[
            dmc.Avatar(className="overview_avatar", id="overview_avatar", size=70, radius="100%"),
            html.Div(className="overview_info", id="overview_info")
        ]),
        html.Div(className="overview_title", children=[html.P("Platform Risk Distribution"), html.Hr()]),
        html.Div(className="overview_platform", id="overview_platform"),
        html.Div(className="overview_title", children=[html.P("Alert Type Count"), html.Hr()]),
        html.Div(className="overview_alert", id="overview_alert"),
        html.Div(className="overview_title", children=[html.P("User Content Classification"), html.Hr()]),
        html.Div(className="overview_classification", id="overview_classification"),
        html.Div(className="overview_title", children=[html.P("Comments Received Categories"), html.Hr()]),
        html.Div(className="overview_comments", id="overview_comments")
    ])
])


# KPI Card
kpi_cards = html.Div(className="kpi_container", children=[
    html.Div(id="kpi_alert_count_container", className="kpi_alert_count_container"),
    html.Div(className="kpi_platform_count_container", children=[
        dcc.Store(id="kpi_platform_store", data=0),
        dmc.ActionIcon(DashIconify(icon="ep:arrow-left-bold", color="black", width=20), id="kpi_platform_backward", className="kpi_platform_backward",
                       variant="transparent", n_clicks=0),
        html.Div(id="kpi_platform_count", className="kpi_platform_count"),
        dmc.ActionIcon(DashIconify(icon="ep:arrow-right-bold", color="black", width=20), id="kpi_platform_forward", className="kpi_platform_forward",
                       variant="transparent", n_clicks=0)
    ])
])


# Page Charts
dashboard_charts = html.Div(className="dashboard_charts", children=[
    html.Div(className="row1", children=[
        html.Div(id="content_risk_classification_container", className="content_risk_classification_container", children=[
            html.Div(id="content_classification_radial_chart", className="content_classification_radial_chart"),
            html.Div(id="risk_categories_horizontal_bar", className="risk_categories_horizontal_bar"),
            dmc.ActionIcon(DashIconify(icon="f7:camera-fill", color="rgba(68, 68, 68, 0.3)", width=16), id="save_as_image", className="save_as_image", n_clicks=0, variant="transparent")
        ]),
        html.Div(id="content_risk_bar_chart", className="content_risk_bar_chart")
    ]),
    html.Div(className="row2", children=[
        html.Div(id="comment_alert_line_chart_container", className="comment_alert_line_chart_container", children=[
            html.Div(id="comment_alert_line_chart"),
            dcc.Store(id="comment_alert_line_chart_slider_storage", storage_type="memory"),
            html.Div(className="comment_alert_line_chart_slider_container", children=dcc.RangeSlider(id="comment_alert_line_chart_slider", className="comment_alert_line_chart_slider", updatemode="drag", pushable=1, min=0, max=730, value=[0, 730]))
        ]),
        html.Div(id="comment_classification_pie_chart", className="comment_classification_pie_chart")
    ])
])


# Analytic Charts
analytic_charts = html.Div(children=[
    html.Img(src=image_folder + "coming_soon_green.jpg", alt="Coming Soon", height="100%")
], style={"height": "calc(100vh - 8.5vh - 20px)", "width": "100%", "text-align": "center", "background-color": "white", "border-radius": "5px"})


# Report Page
report_page = html.Div(className="report_page_container", id="report_page_container", children=[
    html.Div(className="report_main_container", children=[
        html.Div(className="report_main_container_header", children=[
            html.Div(className="report_main_logo_container", children=[
                html.Img(src=image_folder + "New-Report.png", alt="New Report Icon"),
                html.P(id="report_main_logo_text")
            ]),
            dmc.Tabs(id="report_main_container_tabs", children=[
                dmc.TabsList(className="report_main_container_tab_list", children=[
                    dmc.Tab("Generate Report", value="generate", className="report_main_container_tab_option"),
                    dmc.Tab("Saved Reports", value="saved", className="report_main_container_tab_option"),
                ])
            ], value="generate", color="green", variant="pills")
        ]),
        html.Div(id="report_page_content", className="report_page_content")
    ]),

    html.Div(className="report_side_container", children=[
        html.Div(className="report_side_cards", children=[
            dcc.Link(children=[
                html.P(className="report_side_card_header", children="Need Help?"),
                html.P(className="report_side_card_text", children="Explore our Help or FAQ section for detailed information on how to interpret alerts, manage settings, and make the most of Chatstat. Your child's safety is our top priority.")
            ], href="https://chatstat.com/custom-alert-levels/", target="_blank", style={"text-decoration": "none"})
        ]),

        html.Div(className="report_side_cards", children=[
            dcc.Link(children=[
                html.P(className="report_side_card_header", children="New User?"),
                html.P(className="report_side_card_text", children="For new users, the report will go back up to 60 days. As you continue with your membership, more data will be available for analysis and included in the report.")
            ], href="https://chatstat.com/how-to-guide/", target="_blank", style={"text-decoration": "none"})
        ]),

        dcc.Store(id="report_generate_url_store", storage_type="session"), dcc.Store(id="report_saved_url_store", storage_type="session"),
        html.Div(className="report_side_download", id="report_side_download")
    ]),
    dcc.Store(id="report_preview_modal_overview_store", storage_type="memory"),
    dmc.Modal(className="report_preview_overview", id="report_preview_overview", size="50%", zIndex=10, centered=True, overflow="outside", opened=False, children=[
        html.Div(className="report_preview_overview_header_container", children=[
            html.Div(className="report_preview_overview_header", id="report_preview_overview_header")
        ]),
        html.Div(className="report_preview_overview_container", id="report_preview_overview_container"),
        dmc.Pagination(id="report_preview_overview_pagination", total=1, page=1, siblings=1, color="green", withControls=True, radius="5px")
    ])
])

report_generate_tab = html.Div(className="report_generate_container", children=[
    html.P("Report will provide a quick overview of your child's activity.", className="report_subheader"),
    dbc.Row(children=[
        dbc.Col(html.Div(className="report_filter_header", children=[
            DashIconify(className="report_filter_header_icon", icon="mdi:account-circle", color="#2d96ff", width=22),
            html.P("Member Account", className="report_filter_header_text")
        ]), width=4, align="center"),
        dbc.Col(dmc.Select(className="report_filter_member", id="report_filter_member", clearable=False, searchable=False, placeholder="Select Member", value="all",
            icon=DashIconify(icon="f7:person", color="black", width=25), rightSection=DashIconify(icon="radix-icons:chevron-down", color="black")
        ), width=4, align="center")
    ]),
    html.Div(className="report_date_range_container", children=[
        html.Div(className="report_filter_header", children=[
            DashIconify(className="report_filter_header_icon", icon="ph:clock-bold", color="#2d96ff", width=22),
            html.P("Retrieve Data Between", className="report_filter_header_text")
        ]),
        dmc.DateRangePicker(className="report_filter_daterange", id="report_filter_daterange", dropdownPosition="right", amountOfMonths=2,
            value=[datetime.now() - timedelta(days=365*2), datetime.now()],  inputFormat="MMMM DD, YYYY",
            icon=DashIconify(icon=f"arcticons:calendar-simple-{datetime.now().day}", color="black", width=30)
        )
    ]),
    html.Div(className="report_filter_row", children=[
        html.Div(className="report_filter_option", children=[
            html.Div(className="report_filter_header", children=[
                DashIconify(className="report_filter_header_icon", icon="ic:round-computer", color="#2d96ff", width=22),
                html.P("Platform Content", className="report_filter_header_text")
            ]),
            dmc.CheckboxGroup(className="report_filter_platform", id="report_filter_platform", orientation="vertical")
        ]),

        html.Div(className="report_filter_option", children=[
            html.Div(className="report_filter_header", children=[
                DashIconify(className="report_filter_header_icon", icon="ant-design:alert-outlined", color="#2d96ff", width=22),
                html.P("Alert Level Raised", className="report_filter_header_text")
            ]),
            dmc.CheckboxGroup(className="report_filter_alert", id="report_filter_alert", orientation="vertical", value=["high"])
        ])
    ]),
    html.Div(className="report_filter_row", children=[
        html.Div(className="report_filter_option", children=[
            html.Div(className="report_filter_header", children=[
                DashIconify(className="report_filter_header_icon", icon="icon-park-outline:comments", color="#2d96ff", width=22),
                html.P("Content Type", className="report_filter_header_text")
            ]),
            dmc.ChipGroup(className="report_filter_chip", id="report_filter_chip", value=["posts"], multiple=True, children=[
                dmc.Chip("All posts", value="posts", variant="outline", color="green"), dmc.Chip("All comments", value="comments", variant="outline", color="green"),
                dmc.Chip("Watchlist", value="watchlist", variant="outline", color="green")
            ])
        ]),

        html.Div(className="report_filter_option", children=[
            html.Div(className="report_filter_header", children=[
                DashIconify(className="report_filter_header_icon", icon="bx:file", color="#2d96ff", width=22),
                html.P("Export File Type", className="report_filter_header_text")
            ]),
            dmc.RadioGroup([dmc.Radio("PDF", value="pdf", color="green"), dmc.Radio("Excel", value="excel", color="green")],
                value="excel", orientation="horizontal", className="report_filter_type", id="report_filter_type"
            )
        ])
    ]),
    html.Div(className="report_button_list", children=[
        dmc.Button("Preview", className="report_button", id="preview_report_button", variant="filled", color="green", n_clicks=0, leftIcon=DashIconify(icon="el:eye-open", width=20)),
        dmc.Button("Create Report", className="report_button", id="generate_report_button", variant="filled", color="green", n_clicks=0, leftIcon=DashIconify(icon="heroicons-outline:document-report", width=25))
    ]),
    html.Img(src=image_folder + "report_person.png", alt="Report Person", className="report_image")
])

report_saved_tab = html.Div(className="report_saved_container", children=[
    dcc.Store(id="report_saved_modal_overview_store", storage_type="memory"),
    dmc.Modal(className="report_saved_overview", id="report_saved_overview", size="50%", zIndex=10, centered=True, overflow="outside", opened=False, children=[
        html.Div(className="report_saved_overview_header_container", children=[
            html.Div(className="report_saved_overview_header", id="report_saved_overview_header"),
            html.Button("Download", className="report_saved_overview_button", id="report_saved_overview_button", n_clicks=0)
        ]),
        html.Div(className="report_saved_overview_container", id="report_saved_overview_container"),
        dmc.Pagination(id="report_saved_overview_pagination", total=1, page=1, siblings=1, color="green", withControls=True, radius="5px")
    ]),
    dcc.Store(id="report_saved_card_list_store", storage_type="memory"),
    html.Div(className="report_saved_card_list", id="report_saved_card_list"),
    dcc.Store(id="report_saved_card_store", storage_type="memory"),
    html.Div(className="report_saved_card_pagination_container", children=[
        dmc.Pagination(id="report_saved_card_pagination", total=((len(metadata_df)-1)//5)+1, page=1, siblings=1, color="green", withControls=True, radius="5px")
    ])
])


# Designing Main App
server = Flask(__name__)
app = Dash(__name__, server=server, assets_folder="desktop_assets", suppress_callback_exceptions=True, update_title=None, external_stylesheets=[dbc.themes.BOOTSTRAP, "https://fonts.googleapis.com/css2?family=Poppins:wght@200;300;400;500;600;700&display=swap"])
app.server.secret_key = secrets.token_hex(16)
app.css.config.serve_locally = True
app.title = "Parent Dashboard"
app.layout = dmc.NotificationsProvider(
    html.Div(children=[
        dmc.Notification(className="dashboard_notification", id="preview_report_notification_message", action="hide", autoClose=6000, loading=True,
                         color="green", title="Loading Preview", message="Creating preview from selected options"),
        dmc.Notification(className="dashboard_notification", id="saved_report_notification_message", action="hide", autoClose=5000, loading=True,
                         color="green", title="Loading Report", message="Creating report from saved options"),
        dmc.Notification(className="dashboard_notification", id="generate_report_notification_message", action="hide", autoClose=5000, loading=True,
                         color="green", title="Generating Report", message="Producing file ... "),
        dcc.Interval(id="time_interval", disabled=True), html.Div(id="data_refresh"), dcc.Interval(id="data_refresh_interval", interval=3600000),
        html.Div(id="page_title"), dcc.Location(id="url_path", refresh=False),
        sidebar, header,
        html.Div(className="content_container", id="content_container", children=[
            html.Div(className="sidebar_placeholder", children=[]),
            html.Div(className="page_content", children=[
                html.Div(className="header_placeholder", children=[]),
                html.Div(className="content_outer_container", children=[
                    html.Div(className="content_inner_container", id="content_inner_container")
                ])
            ])
        ])
    ]), zIndex=5, position="top-right"
)


# Website Page Navigation
@app.callback(Output("content_inner_container", "children"),
              [Input("url_path", "pathname")]
)
def display_page(pathname):
    if pathname.split("/")[-1] == "Dashboard":
        return [filters, kpi_cards, dashboard_charts]
    elif pathname.split("/")[-1] == "Analytics":
        return [analytic_charts]
    elif pathname.split("/")[-1] == "Report&Logs":
        return [report_page]


# Page Title
clientside_callback(
    """
    function(pathname) {
        if (pathname.split("/").pop() == "Dashboard") {
            document.title = "Chatstat Dashboard"
        } else if (pathname.split("/").pop() == "Analytics") {
            document.title = "Chatstat Analytics"
        } else if (pathname.split("/").pop() == "Report&Logs") {
            document.title = "Chatstat Reports"
        }
    }
    """,
    Output("page_title", "children"),
    Input("url_path", "pathname")
)


# Header
@app.callback(
    Output("header_title", "children"),
    [Input("url_path", "pathname")]
)
def update_header(pathname):
    title = pathname.split("/")[-1].replace("&", " & ")
    return title


# Refresh Data
@app.callback(
    Output("data_refresh", "children"),
    Input("data_refresh_interval", "n_intervals")
)
def update_global_data(data_time_interval):
    global df
    df = s3.get_data()
    return ""


# User Info
@app.callback(
    [Output("user_name", "children"), Output("user_email", "children"), Output("user_plan", "children")],
    Input("time_interval", "n_intervals")
)
def update_user_info(time_interval):
    #payload = {"email": request.authorization["username"]}
    payload = {"email": "jaskeerat.singh@uqconnect.edu.au"}
    user_info = invoke_lambda.get_info(payload)
    return user_info["name"].split(" ")[0].title(), user_info["email"], user_info["level"].title()


# Time Control Information
@app.callback(
    Output("time_control_information", "children"),
    Input("time_interval", "n_intervals")
)
def update_time_control_information(time_interval):
    information = html.Div([
        DashIconify(icon="ion:information-circle", color="#0b71aa", width=30, style={"position": "absolute", "top": "10px", "right": "10px"}),
        html.P(className="time_control_info_option", children=[html.Strong("Daily:"), f" For Today's Date {datetime.now().strftime('%d %B, %Y')}"]),
        html.P(className="time_control_info_option", children=[html.Strong("Weekly:"), f" From Monday to Sunday"]),
        html.P(className="time_control_info_option", children=[html.Strong("Monthly:"), f" From the 1st of {datetime.now().strftime('%B')}"]),
        html.P(className="time_control_info_option", children=[html.Strong("Quarterly:"), f" For this Quarter starting from {datetime.now().replace(month=3*round((datetime.now().month - 1) // 3 + 1) - 2).strftime('%B')}"]),
        html.P(className="time_control_info_option", children=[html.Strong("Yearly:"), f" From the Beginning of {datetime.now().year}"]),
        html.P(className="time_control_info_option", children=[html.Strong("Custom Range:"), " Select from Date Picker"])
    ])
    return information


# Date Picker
@app.callback(
    [Output("popover_date_picker", "style"), Output("popover_date_picker", "offset")],
    [Input("time_control", "value")]
)
def update_popover_date_picker(time_value):
    if(time_value == "all"):
        return {"display": "block"}, "160,10"
    else:
        return {"display": "none"}, ""


# Member Dropdown
@app.callback(
    [Output("member_dropdown", "data"), Output("member_dropdown", "icon"), Output("member_dropdown", "disabled")],
    Input("member_dropdown", "value")
)
def update_member_dropdown(member_value):
    user_list = df[(df["name_childrens"].astype(str) != "nan") & (df["name_childrens"].astype(str) != "no")]["name_childrens"].unique()
    if(len(user_list) == 1):
        disable_flag = True
        data = [{"label": i.split(" ")[0].title(), "value": "all"} for i in user_list]
    else:
        disable_flag = False
        data = [{"label": "All Members", "value": "all"}] + [{"label": i.split(" ")[0].title(), "value": i} for i in user_list]
    return data, DashIconify(icon=f"tabler:square-letter-{member_value[0].lower()}", width=25, color="#25D366"), disable_flag


# Member Report Dropdown
@app.callback(
    Output("report_filter_member", "data"),
    Input("time_interval", "n_intervals")
)
def update_report_member_dropdown(time_interval):
    user_list = df[(df["name_childrens"].astype(str) != "nan") & (df["name_childrens"].astype(str) != "no")]["name_childrens"].unique()
    data = [{"label": user.split(" ")[0].title(), "value": user} for user in user_list]
    return data


# Platform Dropdown
@app.callback(
    [Output("platform_dropdown", "data"), Output("platform_dropdown", "icon"), Output("platform_dropdown", "disabled")],
    Input("platform_dropdown", "value")
)
def update_platform_dropdown(platform_value):
    platform_list = df[(df["platform_contents"].astype(str) != "nan") & (df["platform_contents"].astype(str) != "no")]["platform_contents"].unique()
    if(len(platform_list) == 1):
        disable_flag = True
        data = [{"label": platform.title(), "value": "all"} for platform in platform_list]
        return data, DashIconify(icon=platform_icons[platform_list[0].title()], width=20), disable_flag
    else:
        disable_flag = False
        data = [{"label": "All Platforms", "value": "all"}] + [{"label": platform.title(), "value": platform} for platform in platform_list]
        if(platform_value in ["all", None]):
            return data, DashIconify(icon="emojione-v1:globe-showing-asia-australia", width=20), disable_flag
        else:
            return data, DashIconify(icon=platform_icons[platform_value.title()], width=20), disable_flag


# Platform Checkbox
@app.callback(
    [Output("report_filter_platform", "children"), Output("report_filter_platform", "value")],
    Input("report_filter_member", "value")
)
def update_platform_checkbox(member_value):
    # Filters
    platform_list_df = df.copy()
    platform_list_df = member_filter(platform_list_df, member_value)

    platform_list = platform_list_df[(platform_list_df["platform_contents"].astype(str) != "nan") & (platform_list_df["platform_contents"].astype(str) != "no")]["platform_contents"].unique()
    data = [dmc.Checkbox(label=platform.title(), value=platform.lower(), color="green") for platform in platform_list]
    return data, [platform.lower() for platform in platform_list]


# Alert Dropdown
@app.callback(
    [Output("alert_dropdown", "data"), Output("alert_dropdown", "icon")],
    Input("alert_dropdown", "value")
)
def update_alert_dropdown(alert_value):
    alert_list = df["alert_contents"].unique()
    data = [{"label": "All Alerts", "value": "all"}] + [{"label": alert.title(), "value": alert}
                for alert in sorted(alert_list, key=lambda x: ["high", "medium", "low"].index(x.lower())
                    if isinstance(x, str) and x.lower() in ["high", "medium", "low"] else float("inf"))
                    if (isinstance(alert, str) and str(alert).lower() != "nan") and (str(alert).lower() != "no")]
    if(alert_value in ["all", None]):
        return data, DashIconify(icon="line-md:alert", color="#012749", width=30)
    else:
        return data, DashIconify(icon="line-md:alert", color=alert_colors[alert_value.title()], width=30)


# Alert Checkbox
@app.callback(
    Output("report_filter_alert", "children"),
    Input("time_interval", "n_intervals")
)
def update_alert_checkbox(time_interval):
    alert_list = df["alert_contents"].unique()
    data = [dmc.Checkbox(label=alert.title(), value=alert.lower(), color="green") for alert in sorted(alert_list, key=lambda x: ["high", "medium", "low"].index(x.lower())
        if isinstance(x, str) and x.lower() in ["high", "medium", "low"] else float("inf"))
        if (isinstance(alert, str) and str(alert).lower() != "nan") and (str(alert).lower() != "no")]
    return data


# Reset Filter Container
@app.callback(
    [Output("time_control", "value"), Output("member_dropdown", "value"), Output("platform_dropdown", "value"), Output("alert_dropdown", "value")],
    Input("reset_filter_container", "n_clicks"),
    prevent_initial_call=True
)
def reset_filters(n_clicks):
    return "A", "all", "all", "all"


# SearchBar Reset on Overview Open/Close
@app.callback(
    Output("searchbar", "value"),
    Input("child_overview", "opened"),
    prevent_initial_call=True
)
def reset_searchbar(modal_status):
    if(modal_status):
        return no_update
    else:
        return None


# Generate Overview Card
@app.callback(
    [Output("child_overview", "opened"), Output("child_overview", "title"), Output("overview_avatar", "children"), Output("overview_info", "children"),
     Output("overview_platform", "children"), Output("overview_alert", "children"), Output("overview_classification", "children"), Output("overview_comments", "children")],
    Input("searchbar", "value")
)
def update_overview_card(searchbar_value):
    if(searchbar_value is None):
        raise PreventUpdate
    else:
        # Filters
        overview_df = df.copy()
        overview_df = member_filter(overview_df, searchbar_value)

        overview_info_children = [
            html.Div(className="overview_info_option", children=[html.Strong("Name:"), html.P(searchbar_value)]),
            html.Div(className="overview_info_option", children=[html.Strong("Email:"), html.P(df.loc[df["name_childrens"] == searchbar_value, "email_users"].iloc[0])]),
            html.Div(className="overview_info_option", children=[html.Strong("ID:"), html.P(df.loc[df["name_childrens"] == searchbar_value, "id_childrens"].iloc[0])])
        ]

        # Platform Risk Distribution
        overview_platform_df = overview_df.copy()
        overview_platform_df = overview_platform_df[(overview_platform_df["alert_contents"].str.lower() != "no") & (overview_platform_df["alert_contents"].str.lower() != "") & (overview_platform_df["alert_contents"].notna())]
        overview_platform_df = overview_platform_df[(overview_platform_df["result_contents"].str.lower() != "no") & (overview_platform_df["result_contents"].str.lower() != "") & (overview_platform_df["result_contents"].notna())]

        if(len(overview_platform_df) == 0):
            platform_div = no_data_graph()
        else:
            overview_platform_df["createTime_contents"] = pd.to_datetime(overview_platform_df["createTime_contents"], format="%Y-%m-%d %H:%M:%S.%f")
            overview_platform_df = overview_platform_df.groupby(by=["platform_contents"], as_index=False)["id_contents"].nunique()
            overview_platform_df.columns = ["platform", "count"]
            overview_platform_df["percentage_count"] = (overview_platform_df["count"]/overview_platform_df["count"].sum()) * 100
            overview_platform_df["percentage_count"] = overview_platform_df["percentage_count"].round().astype(int)
            overview_platform_df.loc[overview_platform_df["percentage_count"].idxmax(), "percentage_count"] += 100 - overview_platform_df["percentage_count"].sum()
            overview_platform_df.sort_values(by=["percentage_count"], ascending=False, inplace=True)

            bar_legend = []
            for index, row in overview_platform_df.iterrows():
                bar_legend.append([
                    dmc.Col(DashIconify(icon="material-symbols:circle", width=12, color=platform_colors[row["platform"]]), span=2, offset=1),
                    dmc.Col(dmc.Text(className="overview_platform_label", children=row["platform"]), span=6),
                    dmc.Col(html.Header(className="overview_platform_count", children=str(row["percentage_count"]) + "%"), span=3),
                    ]
                )
            platform_ring_legend = dmc.Grid(children=sum(bar_legend, []), gutter="xs", justify="center", align="center")
            platform_ring = dmc.RingProgress(size=120, thickness=10, roundCaps=True, label=dmc.Center(className="overview_platform_graph_label", children=str(overview_platform_df["count"].sum()) + "\nPosts"),
                sections=[{"value": row["percentage_count"], "color": platform_colors[row["platform"]], "tooltip": f"""{row["platform"].title()} - {row["count"]} Posts"""} for index, row in overview_platform_df.iterrows()]
            )
            platform_div = dmc.Grid(className="overview_platform_container", children=[dmc.Col(platform_ring_legend, span=6), dmc.Col(platform_ring, span=4, offset=1)], gutter="xs", justify="center", align="center")

        # Alert Count
        overview_alert_df = overview_df.copy()
        overview_alert_df = overview_alert_df[(overview_alert_df["alert_contents"].str.lower() != "no") & (overview_alert_df["alert_contents"].str.lower() != "") & (overview_alert_df["alert_contents"].notna())]
        overview_alert_df = overview_alert_df.groupby(by=["alert_contents"], as_index=False)["id_contents"].nunique()

        if(len(overview_alert_df) == 0):
            overview_alert_df = pd.DataFrame(columns=["alert", "count"])
        else:
            overview_alert_df.columns = ["alert", "count"]

        categories = ["High", "Medium", "Low"]
        for cat in categories:
            if(cat not in overview_alert_df["alert"].unique()):
                new_row = {"alert": cat, "count": "0"}
                overview_alert_df = pd.concat([overview_alert_df, pd.DataFrame(new_row, index=[len(overview_alert_df)])])
        overview_alert_df["alert"] = pd.Categorical(overview_alert_df["alert"], categories=categories, ordered=True)
        overview_alert_df = overview_alert_df.sort_values(by="alert")
        alert_div = html.Div(children=[
            dbc.Stack([html.Div(children=[
                dmc.Avatar(row["count"], radius="100%", size=75, color=alert_overview_colors[row["alert"]], style={"border": f"""2px solid {alert_colors[row["alert"]]}"""}),
                dmc.Text(className="overview_alert_label", children=row["alert"])
            ], className="mx-auto overview_alert_option") for index, row in overview_alert_df.iterrows()], direction="horizontal")
        ])

        # Content Classification
        overview_classification_df = overview_df.copy()
        overview_classification_df = overview_classification_df[(overview_classification_df["result_contents"].str.lower() != "no") & (overview_classification_df["result_contents"].str.lower() != "") & (overview_classification_df["result_contents"].notna())]
        overview_classification_df = overview_classification_df[(overview_classification_df["alert_contents"].str.lower() != "no") & (overview_classification_df["alert_contents"].str.lower() != "") & (overview_classification_df["alert_contents"].notna())]

        if(len(overview_classification_df) == 0):
            content_classification_chart = no_data_graph()
        else:
            overview_classification_df = overview_classification_df.groupby(by=["result_contents"], as_index=False)["id_contents"].nunique()
            overview_classification_df.columns = ["category", "count"]
            overview_classification_df.sort_values(by=["count"], ascending=[False], inplace=True)

            for classification in category_bar_colors.keys():
                if(classification not in overview_classification_df["category"].unique()):
                    new_row = {"category": classification, "count": 0}
                    overview_classification_df = pd.concat([overview_classification_df, pd.DataFrame(new_row, index=[len(overview_classification_df)])])

            overview_classification_df["category_break"] = overview_classification_df["category"].apply(lambda x: "<b>" + x.replace(" ", "<br>", 3).replace("<br>", " ", 1) + "</b>" if x.count(" ") >= 3 else "<b>" + x.replace(" ", "<br>", 1) + "</b>")
            tick_values = list(range(int(math.floor(overview_classification_df["count"].min() / 10.0)) * 10, (int(math.ceil(overview_classification_df["count"].max() / 10.0)) * 10) + 10, 10))
            tick_values = tick_values[1::2]

            overview_classification_fig = px.bar_polar(overview_classification_df, r="count", theta="category_break", hover_name="category", color="category", color_discrete_map=category_bar_colors, template="none")
            overview_classification_fig.update_layout(polar=dict(radialaxis=dict(tickvals=tick_values, gridcolor="#98AFC7", gridwidth=1.5, linecolor="black", linewidth=1),
                hole=0.1, angularaxis=dict(showticklabels=True, tickfont=dict(size=12, family="Poppins", color="black"), gridcolor="gold", gridwidth=2, linecolor="gold", linewidth=2)))
            overview_classification_fig.update_traces(marker_line_color="black", marker_line_width=1, opacity=0.9)
            overview_classification_fig.update_layout(legend_title_text="", showlegend=False, margin=dict(t=10, b=10), height=320)
            overview_classification_fig.update_layout(hoverlabel=dict(bgcolor="#c1dfff", font_size=12, font_family="Poppins", align="left"))
            overview_classification_fig.update_traces(hovertemplate="<i><b>%{hovertext} Class</b></i><br>Total Alerts: <b>%{r}</b><extra></extra>")
            content_classification_chart = dcc.Graph(figure=overview_classification_fig, config={"displayModeBar": False})

        # Comment Area Chart
        overview_comments_df = overview_df.copy()
        overview_comments_df = overview_comments_df[(overview_comments_df["alert_comments"].str.lower() != "no") & (overview_comments_df["alert_comments"].str.lower() != "") & (overview_comments_df["alert_comments"].notna())]
        overview_comments_df = overview_comments_df[(overview_comments_df["result_comments"].str.lower() != "no") & (overview_comments_df["result_comments"].str.lower() != "") & (overview_comments_df["result_comments"].notna())]
        overview_comments_df["commentTime_comments"] = pd.to_datetime(overview_comments_df["commentTime_comments"], format="%Y-%m-%d %H:%M:%S")
        overview_comments_df = overview_comments_df[overview_comments_df["commentTime_comments"] >= datetime.now()-timedelta(days=365)]

        if(len(overview_comments_df) == 0):
            comment_area_chart = no_data_graph()
        else:
            overview_comments_df["commentTime_comments"] = pd.to_datetime(overview_comments_df["commentTime_comments"].apply(lambda x: x.replace(day=1))).dt.date
            overview_comments_df["commentTime_comments"] = pd.to_datetime(overview_comments_df["commentTime_comments"])
            overview_comments_df = overview_comments_df.groupby(by=["commentTime_comments", "result_comments"], as_index=False)["id_comments"].nunique()
            overview_comments_df.columns = ["commentTime", "result", "count"]
            total_counts = overview_comments_df.groupby("commentTime")["count"].sum()
            overview_comments_df["percentage"] = overview_comments_df.apply(lambda x: (x["count"] / total_counts[x["commentTime"]]) * 100, axis=1)

            for dat in overview_comments_df["commentTime"].unique():
                for res in overview_comments_df["result"].unique():
                    if(overview_comments_df[(overview_comments_df["commentTime"] == dat) & (overview_comments_df["result"] == res)].empty):
                        new_row = {"commentTime": dat, "result": res, "count": 0, "percentage": 0}
                        overview_comments_df = pd.concat([overview_comments_df, pd.DataFrame(new_row, index=[len(overview_comments_df)])])
            overview_comments_df.sort_values(by=["commentTime", "count"], ascending=True, inplace=True)

            overview_comments_fig = px.area(overview_comments_df, x="commentTime", y="count", color="result", custom_data=["result", "percentage"], color_discrete_map=comment_classification_colors)
            overview_comments_fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), plot_bgcolor="rgba(0, 0, 0, 0)", height=230)
            overview_comments_fig.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text=None)
            overview_comments_fig.update_layout(xaxis_showgrid=False, xaxis=dict(tickfont=dict(size=10, family="Poppins", color="black")))
            overview_comments_fig.update_layout(yaxis=dict(dtick=50, tickfont=dict(size=10, family="Poppins", color="#8E8E8E"), griddash="dash", gridwidth=1, gridcolor="#DADADA"))
            overview_comments_fig.update_layout(yaxis_showgrid=True, yaxis_ticksuffix=" ")
            overview_comments_fig.update_xaxes(fixedrange=False, tickformat="<br>%b'%y")
            overview_comments_fig.update_yaxes(fixedrange=True)
            overview_comments_fig.update_traces(showlegend=False, mode="lines+markers", line=dict(width=2), marker=dict(size=8))
            overview_comments_fig.update_layout(title=f"<b>Hover to Show Info</b>", title_x=0.5, title_y=1, title_font_color="#8E8E8E", title_font=dict(size=10, family="Poppins"))
            overview_comments_fig.update_layout(hoverlabel=dict(bgcolor="#c1dfff", font_size=10, font_family="Poppins", align="left"))
            overview_comments_fig.update_traces(hovertemplate="<i><b>%{customdata[0]} Comments</b></i><br>Total Comments: <b>%{y}</b><br>% of %{x|%B}: <b>%{customdata[1]:.2f}%</b><extra></extra>")
            comment_area_chart = dcc.Graph(figure=overview_comments_fig, config={"displayModeBar": False})
        return True, f"{searchbar_value.title()} Overview", searchbar_value[0].upper(), overview_info_children, platform_div, alert_div, content_classification_chart, comment_area_chart


# KPI Count Card
@app.callback(
    Output("kpi_alert_count_container", "children"),
    [Input("time_control", "value"), Input("date_range_picker", "value"), Input("member_dropdown", "value"), Input("alert_dropdown", "value")]
)
def update_kpi_count(time_value, date_range_value, member_value, alert_value):
    alert_count_df = df.copy()
    alert_count_df = alert_count_df[(alert_count_df["alert_contents"].str.lower() != "no") & (alert_count_df["alert_contents"].str.lower() != "") & (alert_count_df["alert_contents"].notna())]

    # Filters
    alert_count_df = member_filter(alert_count_df, member_value)
    alert_count_df = alert_filter(alert_count_df, alert_value)

    if(time_value == "all"):
        alert_count_df = time_filter(alert_count_df, time_value, date_range_value)
        from_date = datetime.strptime(date_range_value[0], "%Y-%m-%d").strftime("%b %d, %Y")
        to_date = datetime.strptime(date_range_value[1], "%Y-%m-%d").strftime("%b %d, %Y")
        card = [
            dmc.Text("Number of Alerts", className="kpi_alert_count_label"),
            html.Div(className="kpi_alert_count", children=[
                dmc.Group(children=[
                    dmc.Text(alert_count_df["id_contents"].nunique(), className="kpi_alert_number"),
                    dmc.Text(f"Between\n{from_date}\n& {to_date}", className="kpi_alert_info")
                ], position="center", style={"margin": "0px", "padding": "0px"}),
            ])
        ]
        return card

    else:
        alert_count_df["createTime_contents"] = pd.to_datetime(alert_count_df["createTime_contents"], format="%Y-%m-%d %H:%M:%S.%f")
        alert_count_df.set_index("createTime_contents", inplace=True)
        alert_count_df = alert_count_df.resample(time_value)["id_contents"].nunique()
        alert_count_df = alert_count_df.reset_index()
        alert_count_df.columns = ["date", "count"]

        if(len(alert_count_df) == 1):
            alert_count_df["increase"] = alert_count_df["count"].diff().fillna(alert_count_df["count"].iloc[0]).astype(int)
        else:
            alert_count_df["increase"] = alert_count_df["count"].diff().fillna(0).astype(int)
        alert_count_df["date"] = alert_count_df["date"].dt.date
        alert_count_df = alert_count_df.sort_values(by="date", ascending=False)

        if(time_value == "W"):
            today = datetime.now().date()
            date_comparison = today + timedelta(days=(6 - today.weekday()) % 7)
            metric_text = "vs Last Week"
        elif(time_value == "M"):
            today = datetime.now().date()
            date_comparison = datetime(today.year, today.month, calendar.monthrange(today.year, today.month)[-1]).date()
            metric_text = "vs Last Month"
        elif(time_value == "Q"):
            today = datetime.now().date()
            date_comparison = (today + pd.tseries.offsets.QuarterEnd(0)).date()
            metric_text = "vs Last Quarter"
        elif(time_value == "A"):
            today = datetime.now().date()
            date_comparison = datetime(today.year, 12, 31).date()
            metric_text = "vs Last Year"
        else:
            date_comparison = datetime.now().date()
            metric_text = "vs Last Day"

        if(date_comparison in alert_count_df["date"].values):
            card = [
                dmc.Text("Number of Alerts", className="kpi_alert_count_label"),
                html.Div(className="kpi_alert_count", children=[
                    dmc.Group(children=[
                        dmc.Text(alert_count_df["count"].iloc[0], className="kpi_alert_number"),
                        dmc.Stack([
                            dmc.Text("▲"+str(alert_count_df["increase"].iloc[0]) if alert_count_df["increase"].iloc[0] > 0 else "▼"+str(abs(alert_count_df["increase"].iloc[0])),
                                     style={"color": "#FF5100" if alert_count_df["increase"].iloc[0] > 0 else "#25D366", "fontSize": "20px", "fontFamily": "Poppins", "fontWeight": 600}),
                            dmc.Text(metric_text, className="kpi_alert_info")
                        ], align="center", justify="center", spacing="0px")
                    ], position="center", style={"margin": "0px", "padding": "0px"}),
                ])
            ]
        else:
            card = [
                dmc.Text("Number of Alerts", className="kpi_alert_count_label"),
                dmc.Text("No Data Found", className="kpi_alert_count_no_data")
            ]
        return card


# KPI Platform Card
@app.callback(
    [Output("kpi_platform_count", "children"), Output("kpi_platform_store", "data")],
    [Input("time_control", "value"), Input("date_range_picker", "value"), Input("member_dropdown", "value"), Input("alert_dropdown", "value"),
     Input("kpi_platform_backward", "n_clicks"), Input("kpi_platform_forward", "n_clicks")],
    State("kpi_platform_store", "data")
)
def update_kpi_platform(time_value, date_range_value, member_value, alert_value, n_clicks_backward, n_clicks_forward, current_index):
    kpi_platform_df = df.copy()
    kpi_platform_df = kpi_platform_df[(kpi_platform_df["alert_contents"].str.lower() != "no") & (kpi_platform_df["alert_contents"].str.lower() != "") & (kpi_platform_df["alert_contents"].notna())]
    kpi_platform_df = kpi_platform_df[(kpi_platform_df["result_contents"].str.lower() != "no") & (kpi_platform_df["result_contents"].str.lower() != "") & (kpi_platform_df["result_contents"].notna())]

    # Filters
    kpi_platform_df = time_filter(kpi_platform_df, time_value, date_range_value)
    kpi_platform_df = member_filter(kpi_platform_df, member_value)
    kpi_platform_df = alert_filter(kpi_platform_df, alert_value)

    if(len(kpi_platform_df) == 0):
        card = dmc.Card(className="kpi_platform_card_no_data", children=[html.P("No Cards to Display")], withBorder=True, radius="5px")
        current_index = 0
        return card, current_index
    else:
        kpi_platform_df = kpi_platform_df.groupby(by=["platform_contents", "result_contents"], as_index=False)["id_contents"].nunique()
        kpi_platform_df.columns = ["platform", "result", "count"]
        kpi_platform_df.sort_values(by=["platform", "count"], ascending=[True, False], inplace=True)

        kpi_platform_list = []
        for platform in kpi_platform_df["platform"].unique():

            # Producing Increase for each Platform
            if(time_value != "all"):
                kpi_platform_count_df = df.copy()
                kpi_platform_count_df = kpi_platform_count_df[(kpi_platform_count_df["alert_contents"].str.lower() != "no") & (kpi_platform_count_df["alert_contents"].str.lower() != "") & (kpi_platform_count_df["alert_contents"].notna())]
                kpi_platform_count_df = kpi_platform_count_df[(kpi_platform_count_df["result_contents"].str.lower() != "no") & (kpi_platform_count_df["result_contents"].str.lower() != "") & (kpi_platform_count_df["result_contents"].notna())]
                kpi_platform_count_df["createTime_contents"] = pd.to_datetime(kpi_platform_count_df["createTime_contents"], format="%Y-%m-%d %H:%M:%S.%f")

                # Filters
                kpi_platform_count_df = kpi_platform_count_df[kpi_platform_count_df["platform_contents"] == platform]
                kpi_platform_count_df = member_filter(kpi_platform_count_df, member_value)
                kpi_platform_count_df = alert_filter(kpi_platform_count_df, alert_value)

                kpi_platform_count_df.set_index("createTime_contents", inplace=True)
                kpi_platform_count_df = kpi_platform_count_df.resample(time_value)["id_contents"].nunique()
                kpi_platform_count_df = kpi_platform_count_df.reset_index()
                kpi_platform_count_df.columns = ["date", "count"]
                if(len(kpi_platform_count_df) == 1):
                    kpi_platform_count_df["increase"] = kpi_platform_count_df["count"].diff().fillna(kpi_platform_count_df["count"].iloc[0]).astype(int)
                else:
                    kpi_platform_count_df["increase"] = kpi_platform_count_df["count"].diff().fillna(0).astype(int)
                kpi_platform_count_df["date"] = kpi_platform_count_df["date"].dt.date
                kpi_platform_count_df = kpi_platform_count_df.sort_values(by="date", ascending=False)

            # Producing Card for the Platform
            platform_df = kpi_platform_df[kpi_platform_df["platform"] == platform]
            title = platform.title()+f" - {alert_value} Alerts" if ((alert_value is not None) and (alert_value != "all")) else platform.title()
            kpi_platform_list.append(
                html.Div(className="kpi_platform_card", children=[
                    dbc.Row(className="kpi_platform_card_row1", children=[
                        dbc.Col(dmc.Text(title, className="kpi_platform_count_label"), align="center", width=9),
                        dbc.Col(dmc.Text(className="kpi_platform_comparison", children=["--" if time_value == "all"
                            else ("▲"+str(kpi_platform_count_df["increase"].iloc[0]) if kpi_platform_count_df["increase"].iloc[0] > 0 else "▼"+str(abs(kpi_platform_count_df["increase"].iloc[0])))],
                            style={"color": "#25D366" if time_value == "all" else ("#FF5100" if kpi_platform_count_df["increase"].iloc[0] > 0 else "#25D366"),
                            "background-color": "rgba(37, 211, 102, 0.3)" if time_value == "all" else ("rgba(255, 81, 0, 0.3)" if kpi_platform_count_df["increase"].iloc[0] > 0 else "rgba(37, 211, 102, 0.3)")}),
                        align="center", width="auto")
                    ], justify="between"),
                    html.Div(className="kpi_platform_card_row2", children=[
                        html.Img(className="kpi_platform_image", src=image_folder + f"{platform}.png", alt=f"{platform}"),
                        dmc.Stack(className="kpi_platform_classification_container", children=[
                            html.Div(children=[
                                dmc.Text(className="kpi_platform_classification", children=row["result"]),
                                dmc.Text(className="kpi_platform_classification_count", children=row["count"])
                            ], style={"display": "flex", "justifyContent": "space-between", "width": "100%"})
                            for index, row in platform_df.iterrows()], align="flex-start", justify="flex-end", spacing="0px"),
                        dmc.Text(className="kpi_platform_number", children=platform_df["count"].sum())
                    ])
                ])
            )

        # Add more Platforms
        kpi_platform_list.append(dcc.Link(className="kpi_add_platform_card_link", children=[
            html.Div(className="kpi_add_platform_card", children=[html.Strong("Add more Platforms"), DashIconify(icon="basil:add-outline", color="#25D366", width=40)])
        ], href="https://family.chatstat.com/addchild", target="_blank", style={"text-decoration": "none"})
        )

        # Producing Carousel
        if(len(kpi_platform_list) < 3):
            kpi_group_list = [kpi_platform_list[i:i+len(kpi_platform_list)] for i in range(len(kpi_platform_list) - (len(kpi_platform_list)-1))]
        else:
            kpi_group_list = [kpi_platform_list[i:i+3] for i in range(len(kpi_platform_list) - 2)]
        button_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        if(button_id == "kpi_platform_backward"):
            current_index = max(0, current_index - 1)
        elif(button_id == "kpi_platform_forward"):
            current_index = min(len(kpi_group_list) - 1, current_index + 1)
        return kpi_group_list[current_index], current_index


# Content Classification Radial Chart
@app.callback(
    Output("content_classification_radial_chart", "children"),
    [Input("time_control", "value"), Input("date_range_picker", "value"), Input("member_dropdown", "value"), Input("platform_dropdown", "value"), Input("alert_dropdown", "value")]
)
def update_radial_chart(time_value, date_range_value, member_value, platform_value, alert_value):
    result_contents_df = df.copy()
    result_contents_df = result_contents_df[(result_contents_df["result_contents"].str.lower() != "no") & (result_contents_df["result_contents"].str.lower() != "") & (result_contents_df["result_contents"].notna())]
    result_contents_df = result_contents_df[(result_contents_df["alert_contents"].str.lower() != "no") & (result_contents_df["alert_contents"].str.lower() != "") & (result_contents_df["alert_contents"].notna())]

    # Filters
    result_contents_df = time_filter(result_contents_df, time_value, date_range_value)
    result_contents_df = member_filter(result_contents_df, member_value)
    result_contents_df = platform_filter(result_contents_df, platform_value)
    result_contents_df = alert_filter(result_contents_df, alert_value)

    if(len(result_contents_df) == 0):
        return no_data_graph()
    else:
        result_contents_df = result_contents_df.groupby(by=["result_contents"], as_index=False)["id_contents"].nunique()
        result_contents_df.columns = ["classification", "count"]
        result_contents_df["radial"] = (result_contents_df["count"] / result_contents_df["count"].sum()) * 270
        result_contents_df["total_radial"] = 270
        result_contents_df.sort_values(by=["radial"], ascending=True, inplace=True)

        if(((platform_value is not None) and (platform_value != "all")) and ((alert_value is not None) and (alert_value != "all"))):
            title = f"Comment Risk Classification - {platform_value} & {alert_value} Alerts"
        elif((platform_value is not None) and (platform_value != "all")):
            title = f"Content Risk Classification - {platform_value}"
        elif((alert_value is not None) and (alert_value != "all")):
            title = f"Content Risk Classification - {alert_value} Alerts"
        else:
            title = "Content Risk Classification"
        return [
            html.P(title, style={"color": "#052F5F", "fontWeight": "bold", "fontSize": 17, "margin": "10px 25px 0px 25px"}),
            html.Div(className="content_classification_image", children=[
                html.Img(src=radial_bar_chart.radial_chart(result_contents_df, "desktop_assets"), alt="Radial Chart", width="100%", style={"object-fit": "cover"})]
            )
        ]


# Risk Categories Horizontal Bar
@app.callback(
    Output("risk_categories_horizontal_bar", "children"),
    [Input("time_control", "value"), Input("date_range_picker", "value"), Input("member_dropdown", "value")]
)
def update_horizontal_bar(time_value, date_range_value, member_value):
    risk_categories_df = df.copy()
    risk_categories_df = risk_categories_df[(risk_categories_df["result_contents"].str.lower() != "no") & (risk_categories_df["result_contents"].str.lower() != "") & (risk_categories_df["result_contents"].notna())]
    risk_categories_df = risk_categories_df[(risk_categories_df["alert_contents"].str.lower() != "no") & (risk_categories_df["alert_contents"].str.lower() != "") & (risk_categories_df["alert_contents"].notna())]

    # Filters
    risk_categories_df = time_filter(risk_categories_df, time_value, date_range_value)
    risk_categories_df = member_filter(risk_categories_df, member_value)

    if(len(risk_categories_df) == 0):
        return no_data_graph()
    else:
        risk_categories_df = risk_categories_df.groupby(by=["result_contents"], as_index=False)["id_contents"].nunique()
        risk_categories_df.columns = ["category", "count"]
        risk_categories_df["percentage_of_total"] = (risk_categories_df["count"] / risk_categories_df["count"].sum()) * 100
        risk_categories_df["percentage_of_total"] = risk_categories_df["percentage_of_total"].round().astype(int)
        risk_categories_df.loc[risk_categories_df["percentage_of_total"].idxmax(), "percentage_of_total"] += 100 - risk_categories_df["percentage_of_total"].sum()
        risk_categories_df.sort_values(by="percentage_of_total", ascending=True, inplace=True)
        bar_sections = [{"value": row["percentage_of_total"], "color": category_bar_colors[row["category"]], "label": str(row["percentage_of_total"])+"%", "tooltip": f"""{row["category"].title()} - {row["percentage_of_total"]}%""" } for index, row in risk_categories_df.iterrows()]

        # Handling Missing Values
        for classification in category_bar_colors.keys():
            if(classification not in risk_categories_df["category"].unique()):
                new_row = {"category": classification, "count": 0, "percentage_of_total": 0}
                risk_categories_df = pd.concat([risk_categories_df, pd.DataFrame(new_row, index=[len(risk_categories_df)])])

        bar_legend = []
        risk_categories_df.sort_values(by="percentage_of_total", ascending=False, inplace=True)
        for index, row in risk_categories_df.iterrows():
            bar_legend.append([
                dmc.Col(DashIconify(className="risk_categories_progress_legend_symbol", icon="material-symbols:circle", width=12, color=category_bar_colors[row["category"]]), span=1),
                dmc.Col(dmc.Text(className="risk_categories_progress_legend_marking", children=row["category"]), span=6),
                dmc.Col(html.Header(row["count"], style={"color": "#081A51", "fontFamily": "Poppins", "fontWeight": "bold", "fontSize": 14, "text-align": "right"}), span=2),
                dmc.Col(dmc.Avatar(className="risk_categories_progress_legend_avatar", children=str(row["percentage_of_total"])+"%", size=35, radius="xl", color="#2D96FF"), span=1, offset=2)
                ]
            )

        return dmc.Stack(className="risk_categories_progress_bar_container", children=[
            html.Div(className="risk_categories_progress_bar_label", children=[
                html.Hr(style={"width": "30%", "borderTop": "2px solid", "borderBottom": "2px solid", "opacity": "unset"}),
                dmc.Text("Categories", style={"fontFamily": "Poppins"}),
                html.Hr(style={"width": "30%", "borderTop": "2px solid", "borderBottom": "2px solid", "opacity": "unset"})
            ], style={"width": "100%"}),
            dmc.Progress(className="risk_categories_progress_bar", sections=bar_sections, radius=10, size=25, animate=False, striped=False),
            dmc.Grid(className="risk_categories_progress_legend", children=sum(bar_legend, []), gutter="xs", justify="center", align="center")
            ], justify="space-evenly")


# Content Risk Bar Chart
@app.callback(
    Output("content_risk_bar_chart", "children"),
    [Input("time_control", "value"), Input("date_range_picker", "value"), Input("member_dropdown", "value"), Input("platform_dropdown", "value")]
)
def update_bar_chart(time_value, date_range_value, member_value, platform_value):
    risk_content_df = df.copy()
    risk_content_df = risk_content_df[(risk_content_df["alert_contents"].str.lower() != "no") & (risk_content_df["alert_contents"].str.lower() != "") & (risk_content_df["alert_contents"].notna())]

    # Filters
    risk_content_df = time_filter(risk_content_df, time_value, date_range_value)
    risk_content_df = member_filter(risk_content_df, member_value)
    risk_content_df = platform_filter(risk_content_df, platform_value)

    if(len(risk_content_df) == 0):
        return no_data_graph()
    else:
        risk_content_df["createTime_contents"] = pd.to_datetime(risk_content_df["createTime_contents"], format="%Y-%m-%d %H:%M:%S.%f")
        risk_content_df = risk_content_df.groupby(by=["alert_contents", "platform_contents"], as_index=False)["id_contents"].nunique()
        risk_content_df.columns = ["alert", "platform", "count"]
        categories = ["High", "Medium", "Low"]

        # Handling Missing Values
        for platform in risk_content_df["platform"].unique():
            for cat in categories:
                if(cat not in risk_content_df[risk_content_df["platform"] == platform]["alert"].unique()):
                    new_row = {"alert": cat, "platform": platform.title(), "count": 0}
                    risk_content_df = pd.concat([risk_content_df, pd.DataFrame(new_row, index=[len(risk_content_df)])])

        risk_content_df["alert"] = pd.Categorical(risk_content_df["alert"], categories=categories, ordered=True)
        risk_content_df["percentage_alert"] = risk_content_df.groupby("alert")["count"].transform(lambda x: (x / x.sum()) * 100).round()
        risk_content_df["percentage_total"] = ((risk_content_df["count"] / risk_content_df["count"].sum()) * 100).round()
        risk_content_df = risk_content_df.sort_values(by="alert")

        if((platform_value is None) or (platform_value == "all")):
            content_risk = px.bar(risk_content_df, x="alert", y="count", text="count", hover_name="platform", custom_data=["percentage_total"], color="platform", color_discrete_map=platform_colors)
            content_risk.update_layout(title="<b>Alerts on User Content</b>", title_font_color="#052F5F", title_font=dict(size=17, family="Poppins"))
            content_risk.update_traces(width=0.5, hovertemplate="<i><b>%{hovertext}</b></i><br>Alert Severity: <b>%{x}</b><br>Total Alerts: <b>%{text}</b><br>% of Total: <b>%{customdata}%</b><extra></extra>")
            content_risk.update_layout(legend=dict(font=dict(family="Poppins"), traceorder="grouped", orientation="h", x=0.5, y=-0.2, xanchor="center", yanchor="bottom", title_text="", bgcolor="rgba(0,0,0,0)"))
        else:
            content_risk = px.bar(risk_content_df, x="alert", y="count", color="alert", color_discrete_map=alert_colors)
            content_risk.update_layout(title=f"<b>Alerts on User Content - {platform_value}</b>", title_font_color="#052F5F", title_font=dict(size=17, family="Poppins"))
            content_risk.update_traces(width=0.4, hovertemplate="Alert Severity: <b>%{x}</b><br>Total Alerts: <b>%{y}</b><extra></extra>")
            content_risk.update_layout(showlegend=False)

        content_risk.update_layout(margin=dict(l=25, r=25, b=0), barmode="relative")
        content_risk.update_layout(xaxis_title="", yaxis_title="", legend_title_text="", plot_bgcolor="rgba(0, 0, 0, 0)")
        content_risk.update_layout(yaxis_showgrid=True, yaxis_ticksuffix=" ", yaxis=dict(tickfont=dict(size=12, family="Poppins", color="#8E8E8E"), griddash="dash", gridwidth=1, gridcolor="#DADADA"))
        content_risk.update_layout(xaxis_showgrid=False, xaxis=dict(tickfont=dict(size=16, family="Poppins", color="#052F5F")))
        content_risk.update_layout(hoverlabel=dict(bgcolor="#c1dfff", font_size=12, font_family="Poppins", align="left"))
        content_risk.update_traces(marker_line=dict(color="black", width=1.5), textfont=dict(color="#052F5F", size=16, family="Poppins"), textangle=0)
        content_risk.update_xaxes(fixedrange=True)
        content_risk.update_yaxes(fixedrange=True)

        # Adding Bubbles on top for effect
        if(platform_value not in [None, "all"]):
            risk_content_df = risk_content_df.groupby(by=["alert"], as_index=False)["count"].sum()
            scatter_trace = px.scatter(risk_content_df, x="alert", y="count", color="alert", color_discrete_map=alert_colors, text="count")
            scatter_trace.update_layout(hoverlabel=dict(bgcolor="#c1dfff", font_size=12, font_family="Poppins", align="left"))
            scatter_trace.update_traces(hovertemplate="Alert Severity: <b>%{x}</b><br>Total Alerts: <b>%{y}</b><extra></extra>")
            scatter_trace.update_traces(textfont=dict(color="#052F5F", size=16, family="Poppins"))
            scatter_trace.update_traces(marker=dict(size=70, symbol="circle", line=dict(width=2, color="black")), showlegend=False)
            content_risk.add_trace(scatter_trace.data[0])
            content_risk.add_trace(scatter_trace.data[1])
            content_risk.add_trace(scatter_trace.data[2])

        return dcc.Graph(figure=content_risk, responsive=True, config=plot_config, style={"height": "100%", "width": "100%"})


# Comment Alert Line Chart
@app.callback(
    Output("comment_alert_line_chart", "children"),
    [Input("member_dropdown", "value"), Input("alert_dropdown", "value"), Input("comment_alert_line_chart_slider", "value"), Input("comment_alert_line_chart_slider_storage", "data")]
)
def update_line_chart(member_value, alert_value, slider_value, storage_dict):
    alert_comment_df = df.copy()
    alert_comment_df = alert_comment_df[(alert_comment_df["alert_comments"].str.lower() != "no") & (alert_comment_df["alert_comments"].str.lower() != "") & (alert_comment_df["alert_comments"].notna())]

    # Filters
    alert_comment_df = member_filter(alert_comment_df, member_value)
    alert_comment_df = alert_filter(alert_comment_df, alert_value)
    alert_comment_df = slider_filter(alert_comment_df, slider_value, storage_dict)

    if(len(alert_comment_df) == 0):
        return no_data_graph()
    else:
        alert_comment_df["commentTime_comments"] = pd.to_datetime(alert_comment_df["commentTime_comments"], format="%Y-%m-%d").dt.strftime("%b %Y")
        alert_comment_df = alert_comment_df.groupby(by=["commentTime_comments", "platform_comments"], as_index=False)["id_comments"].nunique()
        alert_comment_df.columns = ["commentTime", "platform", "count"]
        alert_comment_df["commentTime"] = pd.to_datetime(alert_comment_df["commentTime"], format="%b %Y")
        alert_comment_df.sort_values(by="commentTime", inplace=True)

        comment_alert = px.line(alert_comment_df, x="commentTime", y="count", hover_name="platform", color="platform", color_discrete_map=platform_colors)
        comment_alert.update_layout(margin=dict(l=25, r=25, b=0), height=400)
        comment_alert.update_layout(legend=dict(font=dict(family="Poppins"), traceorder="grouped", orientation="h", x=1, y=1, xanchor="right", yanchor="bottom", title_text=""))
        comment_alert.update_layout(xaxis_title="", yaxis_title="", legend_title_text="", plot_bgcolor="rgba(0, 0, 0, 0)")
        comment_alert.update_layout(yaxis_showgrid=True, yaxis_ticksuffix="  ", yaxis=dict(dtick=100, tickfont=dict(size=12, family="Poppins", color="#8E8E8E"), griddash="dash", gridwidth=1, gridcolor="#DADADA"))
        comment_alert.update_layout(xaxis_showgrid=False, xaxis=dict(tickfont=dict(size=10, family="Poppins", color="#052F5F"), tickangle=0))
        comment_alert.update_traces(mode="lines+markers", line=dict(width=2), marker=dict(sizemode="diameter", size=8, color="white", line=dict(width=2)))
        comment_alert.update_xaxes(fixedrange=True)
        comment_alert.update_yaxes(fixedrange=True)
        comment_alert.add_vline(x=alert_comment_df[alert_comment_df["count"] == alert_comment_df["count"].max()]["commentTime"].iloc[0], line_width=2, line_dash="dashdot", line_color="#017EFA")

        # Hover Label
        comment_alert.update_layout(hoverlabel=dict(bgcolor="#c1dfff", font_size=12, font_family="Poppins", align="left"))
        comment_alert.update_traces(hovertemplate="<i><b>%{hovertext}</b></i><br>In: <b>%{x|%b %Y}</b><br>Total Alerts: <b>%{y}</b><extra></extra>")

        if((alert_value is not None) and (alert_value != "all")):
            comment_alert.update_layout(title=f"<b>Alerts on Comments Received - {alert_value} Alerts</b>", title_font_color="#052F5F", title_font=dict(size=17, family="Poppins"))
        else:
            comment_alert.update_layout(title="<b>Alerts on Comments Received</b>", title_font_color="#052F5F", title_font=dict(size=17, family="Poppins"))
        return dcc.Graph(figure=comment_alert, config=plot_config)


# Comment Alert Line Chart Slider
@app.callback(
    [Output("comment_alert_line_chart_slider", "marks"), Output("comment_alert_line_chart_slider", "max"), Output("comment_alert_line_chart_slider", "min"),
     Output("comment_alert_line_chart_slider", "value"), Output("comment_alert_line_chart_slider_storage", "data")],
    [Input("member_dropdown", "value")]
)
def update_line_chart_slider(member_value):
    slider_df = df.copy()
    slider_df = slider_df[(slider_df["alert_comments"].str.lower() != "no") & (slider_df["alert_comments"].str.lower() != "") & (slider_df["alert_comments"].notna())]

    # Filters
    slider_df = member_filter(slider_df, member_value)

    slider_df["commentTime_comments"] = pd.to_datetime(slider_df["commentTime_comments"], format="%Y-%m-%d %H:%M:%S").dt.date
    slider_df = slider_df[slider_df["commentTime_comments"] >= date.today()-timedelta(days=365*2)]

    try:
        min_date = slider_df["commentTime_comments"].min()
        max_date = slider_df["commentTime_comments"].max()
        date_range = range((max_date - min_date).days + 1)
    except:
        min_date = datetime.now() - timedelta(days=365)
        max_date = datetime.now()
        date_range = range((max_date - min_date).days + 1)

    maximum_mark = max(date_range)
    minimum_mark = min(date_range)
    date_list = [min_date + timedelta(days=i) for i in date_range]

    date_dict = {i: d.strftime("%Y-%m-%d") for i, d in enumerate(date_list)}
    marks = {i: {"label": d.strftime("%b'%y"), "style": {"font-family": "Poppins", "font-weight": 600, "font-size": "10px"}} for i, d in enumerate(date_list) if ((d.month in [1, 4, 7, 10]) and (d.day == 1))}
    return marks, maximum_mark, minimum_mark, [minimum_mark, maximum_mark], date_dict


# Comment Classification Pie Chart
@app.callback(
    Output("comment_classification_pie_chart", "children"),
    [Input("time_control", "value"), Input("date_range_picker", "value"), Input("member_dropdown", "value"), Input("platform_dropdown", "value"), Input("alert_dropdown", "value")]
)
def update_pie_chart(time_value, date_range_value, member_value, platform_value, alert_value):
    result_comment_df = df.copy()
    result_comment_df = result_comment_df[(result_comment_df["result_comments"].str.lower() != "no") & (result_comment_df["result_comments"].str.lower() != "") & (result_comment_df["result_comments"].notna())]
    result_comment_df = result_comment_df[(result_comment_df["alert_comments"].str.lower() != "no") & (result_comment_df["alert_comments"].str.lower() != "") & (result_comment_df["alert_comments"].notna())]

    # Filters
    result_comment_df = time_filter(result_comment_df, time_value, date_range_value)
    result_comment_df = member_filter(result_comment_df, member_value)
    result_comment_df = platform_filter(result_comment_df, platform_value)
    result_comment_df = alert_filter(result_comment_df, alert_value)

    if(len(result_comment_df) == 0):
        return no_data_graph()
    else:
        result_comment_df = result_comment_df.groupby(by=["result_comments"], as_index=False)["id_comments"].nunique()
        result_comment_df.columns = ["classification", "count"]
        result_comment_df.sort_values(by=["count"], ascending=True, inplace=True)

        comment_classification = px.pie(result_comment_df, values="count", names="classification", color="classification", color_discrete_map=comment_classification_colors)
        comment_classification.update_layout(margin=dict(l=25, r=25), plot_bgcolor="white", paper_bgcolor="white")
        comment_classification.update_layout(annotations=[dict(text="<b>"+str(result_comment_df["count"].sum())+"</b>", x=0.5, y=0.55, font=dict(family="Poppins", size=28, color="#052F5F"), showarrow=False),
                                                          dict(text="Total Comments", x=0.5, y=0.45, font=dict(family="Poppins", size=18, color="#052F5F"), showarrow=False)]
                                             )
        comment_classification.update_layout(legend={"orientation": "h", "x": 0.5, "y": -0.1, "xanchor": "center", "font": {"family": "Poppins", "color": "#2a3f5f", "size": 12}})
        comment_classification.update_traces(textinfo="percent", texttemplate="<b>%{percent}</b>", textposition="outside")
        comment_classification.update_traces(outsidetextfont=dict(family="Poppins", size=14, color="black"), insidetextorientation="horizontal")
        comment_classification.update_traces(hole=0.65, marker=dict(line=dict(color="white", width=2.5)))

        # Hover Label
        comment_classification.update_layout(hoverlabel=dict(bgcolor="#c1dfff", font_size=12, font_family="Poppins", align="left"))
        comment_classification.update_traces(hovertemplate="<i><b>%{customdata[0]} Comments</b></i><br>Total Comments: <b>%{value}</b><br>% of Total: <b>%{percent}</b><extra></extra>")

        if(((platform_value is not None) and (platform_value != "all")) and ((alert_value is not None) and (alert_value != "all"))):
            comment_classification.update_layout(title={"text": f"<b>Comment Classification - {platform_value} &<br>{alert_value} Alerts</b>"}, title_font_color="#052F5F", title_font=dict(family="Poppins", size=17))
        elif((platform_value is not None) and (platform_value != "all")):
            comment_classification.update_layout(title={"text": f"<b>Comment Classification - {platform_value}</b>"}, title_font_color="#052F5F", title_font=dict(family="Poppins", size=17))
        elif((alert_value is not None) and (alert_value != "all")):
            comment_classification.update_layout(title={"text": f"<b>Comment Classification - {alert_value} Alerts</b>"}, title_font_color="#052F5F", title_font=dict(family="Poppins", size=17))
        else:
            comment_classification.update_layout(title={"text": "<b>Comment Classification</b>"}, title_font_color="#052F5F", title_font=dict(family="Poppins", size=17))
        return dcc.Graph(figure=comment_classification, config=plot_config)


# Report Page Tab Value
@app.callback(
    Output("report_main_container_tabs", "value"),
    Input("report_side_download_no_data_button", "n_clicks"),
    prevent_initial_call=True
)
def update_report_page_tab(button_click):
    if(button_click):
        return "saved"
    else:
        raise PreventUpdate


# Report Page Content
@app.callback(
    [Output("report_page_content", "children"), Output("report_main_logo_text", "children"), Output("preview_report_notification_message", "action"),
     Output("generate_report_notification_message", "action"), Output("saved_report_notification_message", "action")],
    Input("report_main_container_tabs", "value")
)
def update_report_page_content(tab_value):
    if(tab_value == "generate"):
        return report_generate_tab, "New Report", "hide", "hide", "hide"
    elif(tab_value == "saved"):
        return report_saved_tab, "Saved Reports", "hide", "hide", "hide"


# Preview Report Mail
@app.callback(
    [Output("report_preview_overview", "opened"), Output("report_preview_overview", "title"), Output("report_preview_overview_header", "children"), Output("report_preview_modal_overview_store", "data")],
    Input("preview_report_button", "n_clicks"),
    [State("report_filter_member", "value"), State("report_filter_daterange", "value"), State("report_filter_platform", "value"),
     State("report_filter_alert", "value"), State("report_filter_chip", "value"), State("report_filter_type", "value")]
)
def update_report_preview_overview(preview_button_click, member_value, time_range, platform_value, alert_value, content_type, file_type):
    if(callback_context.triggered[0]["value"]):
        # Creating Payload
        payload = {
            "email": "j.teng@chatstat.com", "children": "test", "timerange": time_range, "platform": platform_value,
            "alert": alert_value, "contenttype": content_type, "filetype": file_type
        }
        
        # Calling Lambda for Response Body
        response_json, response_url = invoke_lambda.generate_report(payload)
        response_modal_div = []
        for res in json.loads(response_json):
            response_modal_div.append(html.Div(className="report_preview_overview_children", children=[
                html.Div(className="report_preview_overview_children_platform", children=[
                    html.Img(src=image_folder + f"""{res["platform"].title()}.png""", alt=f"""{res["platform"].title()}"""),
                    html.P(children=res["type"].title())
                ]),
                html.P(className="report_preview_overview_children_text", children=res["text"]),
                html.P(className="report_preview_overview_children_date", children=datetime.utcfromtimestamp(int(res["datetime"])/1000).strftime("%d %B %Y %I:%M%p"))
            ]))
        response_modal_div = [response_modal_div[i:i+4] for i in range(0, len(response_modal_div), 4)]

        # Header for Response Body
        report_preview_overview_header = [
            dbc.Row(children=[
                dbc.Col(html.Div(className="report_preview_overview_filter", children=[
                    DashIconify(icon="ph:clock-bold", color="#2d96ff", width=22),
                    html.P("Btw " + " & ".join(datetime.fromisoformat(d).strftime("%d %b'%y") for d in reversed(payload["timerange"])) )
                    ]), width=6, align="center"),
                dbc.Col(html.Div(className="report_preview_overview_filter", children=[
                    DashIconify(icon="ic:round-computer", color="#2d96ff", width=22),
                    html.P(", ".join(platform.title() for platform in payload["platform"]))
                    ]), width=6, align="center")
            ]),
            dbc.Row(children=[
                dbc.Col(html.Div(className="report_preview_overview_filter", children=[
                    DashIconify(icon="ant-design:alert-outlined", color="#2d96ff", width=22),
                    html.P(f"""{ ", ".join(alert.title() for alert in payload["alert"]) } Alerts""")
                    ]), width=6, align="center"),
                dbc.Col(html.Div(className="report_preview_overview_filter", children=[
                    DashIconify(icon="icon-park-outline:comments", color="#2d96ff", width=22),
                    html.P(", ".join(content.title() for content in payload["contenttype"]))
                    ]), width=6, align="center")
            ])
        ]
        return True, f"""Report for { payload["children"].title() }""", report_preview_overview_header, response_modal_div
    else:
        return False, "Preview Report", [], []


# Preview Report Mail Overview Pagination
@app.callback(
    [Output("report_preview_overview_container", "children"), Output("report_preview_overview_pagination", "total"), Output("report_preview_overview_pagination", "page")],
    [Input("report_preview_overview", "opened"), Input("report_preview_overview_pagination", "page")],
    State("report_preview_modal_overview_store", "data")
)
def update_preview_report_mail_pagination(modal_status, page, report_modal_data):
    if(modal_status):
        return report_modal_data[page-1], len(report_modal_data), page
    else:
        return "", 1, 1


# Generate Report Mail
@app.callback(
    Output("report_generate_url_store", "data"),
    Input("generate_report_button", "n_clicks"),
    [State("report_filter_member", "value"), State("report_filter_daterange", "value"), State("report_filter_platform", "value"),
     State("report_filter_alert", "value"), State("report_filter_chip", "value"), State("report_filter_type", "value")]
)
def generate_report_mail(generate_button_click, member_value, time_range, platform_value, alert_value, content_type, file_type):
    if(callback_context.triggered[0]["value"]):
        payload = {
            "email": "j.teng@chatstat.com",
            "children": "test",
            "timerange": time_range,
            "platform": platform_value,
            "alert": alert_value,
            "contenttype": content_type,
            "filetype": file_type
        }
        mysql_database.post_report_metadata(payload)
        lambda_response, response_url = invoke_lambda.generate_report(payload)
        session["report_url"] = response_url
        return response_url


# Report Page Saved Tab Content
@app.callback(
    [Output("report_saved_card_list", "children"), Output("report_saved_card_list_store", "data")],
    [Input("report_main_container_tabs", "value"), Input("report_saved_card_pagination", "page")]
)
def update_report_page_saved_content(tab_value, pagination_page):
    start_report = (pagination_page-1)*5
    end_report = pagination_page*5
    page_df = metadata_df.iloc[start_report:end_report]
    page_df.reset_index(drop=True, inplace=True)

    saved_report_list = []
    saved_report_dict = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}}
    for index, row in page_df.iterrows():
        saved_report_dict[index] = row.to_dict()
        report_container = html.Button(className="report_saved_card", id=f"report_saved_card_{index}", children=[
            dbc.Row(children=[
                dbc.Col(children=[
                    dbc.Row(children=[
                        html.Div(className="report_saved_header", children=[DashIconify(icon="ph:bookmark-duotone", color="#2d96ff", width=26),
                        html.P(f"""Report for { row["children"].title() }""")])
                    ], justify="center"),
                    dbc.Row(children=[
                        html.Div(className="report_saved_header_text", children=[DashIconify(icon="icons8:create-new", color="#2d96ff", width=18),
                        html.P(row["created_at"].strftime("%d %b, %Y %I:%M %p"))])
                    ], justify="center")
                ], width=4, align="center"),
                dbc.Col(children=[
                    dbc.Row(children=[
                        dbc.Col(html.Div(className="report_saved_filter", children=[DashIconify(icon="ph:clock-bold", color="#2d96ff", width=22),
                                html.P("Btw " + " & ".join(datetime.fromisoformat(d).strftime("%d %b'%y") for d in reversed(ast.literal_eval(row["timerange"])) ) ) ]),
                            width=6, align="center"),
                        dbc.Col(html.Div(className="report_saved_filter", children=[DashIconify(icon="ic:round-computer", color="#2d96ff", width=22),
                                html.P(", ".join(platform.title() for platform in ast.literal_eval(row["platform"]))) ]),
                            width=6, align="center")
                    ]),
                    dbc.Row(children=[
                        dbc.Col(html.Div(className="report_saved_filter", children=[DashIconify(icon="ant-design:alert-outlined", color="#2d96ff", width=22),
                                html.P(f"""{ ", ".join(alert.title() for alert in ast.literal_eval(row["alert"])) } Alerts""")] ),
                            width=6, align="center"),
                        dbc.Col(html.Div(className="report_saved_filter", children=[DashIconify(icon="icon-park-outline:comments", color="#2d96ff", width=22),
                                html.P(", ".join(content.title() for content in ast.literal_eval(row["contenttype"]))) ]),
                            width=6, align="center")
                    ])
                ], width=8, align="center")
            ])
        ])
        saved_report_list.append(report_container)

    while(len(saved_report_list) < 5):
        saved_report_list.append(html.Button(className="report_saved_card", id=f"report_saved_card_{len(saved_report_list)}", style={"display": "none"}))
    return saved_report_list, saved_report_dict


# Saved Report Output
@app.callback(
    [Output("report_saved_overview", "opened"), Output("report_saved_overview", "title"), Output("report_saved_overview_header", "children"), Output("report_saved_card_store", "data"), Output("report_saved_modal_overview_store", "data")],
    [Input("report_saved_card_0", "n_clicks"), Input("report_saved_card_1", "n_clicks"), Input("report_saved_card_2", "n_clicks"), Input("report_saved_card_3", "n_clicks"), Input("report_saved_card_4", "n_clicks")],
    State("report_saved_card_list_store", "data")
)
def update_report_saved_overview(card0_click, card1_click, card2_click, card3_click, card4_click, store_data):
    if(all(context["value"] is None for context in callback_context.triggered)):
        return False, "Report OverView", [], {}, []
    else:
        button_id = callback_context.triggered[0]["prop_id"].split(".")[0]
        button_value = int(button_id.split("_")[-1])

        # Creating Payload
        payload = store_data[str(button_value)]
        payload.pop("created_at", None)
        for key in payload.keys():
            try:
                payload[key] = json.loads(payload[key])
            except Exception as e:
                pass

        # Calling Lambda for response body
        response_json, response_url = invoke_lambda.generate_report(payload)
        response_modal_div = []
        for res in json.loads(response_json):
            response_modal_div.append(html.Div(className="report_saved_overview_children", children=[
                html.Div(className="report_saved_overview_children_platform", children=[
                    html.Img(src=image_folder + f"""{res["platform"].title()}.png""", alt=f"""{res["platform"].title()}"""),
                    html.P(children=res["type"].title())
                ]),
                html.P(className="report_saved_overview_children_text", children=res["text"]),
                html.P(className="report_saved_overview_children_date", children=datetime.utcfromtimestamp(int(res["datetime"])/1000).strftime("%d %B %Y %I:%M%p"))
            ]))
        response_modal_div = [response_modal_div[i:i+4] for i in range(0, len(response_modal_div), 4)]

        # Header Filter
        report_saved_overview_header = [
            dbc.Row(children=[
                dbc.Col(html.Div(className="report_saved_overview_filter", children=[
                    DashIconify(icon="ph:clock-bold", color="#2d96ff", width=22),
                    html.P("Btw " + " & ".join(datetime.fromisoformat(d).strftime("%d %b'%y") for d in reversed(payload["timerange"])) )
                    ]), width=6, align="center"),
                dbc.Col(html.Div(className="report_saved_overview_filter", children=[
                    DashIconify(icon="ic:round-computer", color="#2d96ff", width=22),
                    html.P(", ".join(platform.title() for platform in payload["platform"]))
                    ]), width=6, align="center")
            ]),
            dbc.Row(children=[
                dbc.Col(html.Div(className="report_saved_overview_filter", children=[
                    DashIconify(icon="ant-design:alert-outlined", color="#2d96ff", width=22),
                    html.P(f"""{ ", ".join(alert.title() for alert in payload["alert"]) } Alerts""")
                    ]), width=6, align="center"),
                dbc.Col(html.Div(className="report_saved_overview_filter", children=[
                    DashIconify(icon="icon-park-outline:comments", color="#2d96ff", width=22),
                    html.P(", ".join(content.title() for content in payload["contenttype"]))
                    ]), width=6, align="center")
            ])
        ]
        return True, f"""Report for { payload["children"].title() }""", report_saved_overview_header, payload, response_modal_div


# Saved Report Overview Pagination
@app.callback(
    [Output("report_saved_overview_container", "children"), Output("report_saved_overview_pagination", "total"), Output("report_saved_overview_pagination", "page")],
    [Input("report_saved_overview", "opened"), Input("report_saved_overview_pagination", "page")],
    State("report_saved_modal_overview_store", "data")
)
def update_saved_report_mail_pagination(modal_status, page, report_modal_data):
    if(modal_status):
        return report_modal_data[page-1], len(report_modal_data), page
    else:
        return "", 1, 1


# Saved Report Overview Email Push
@app.callback(
    Output("report_saved_url_store", "data"),
    Input("report_saved_overview_button", "n_clicks"),
    State("report_saved_card_store", "data")
)
def perform_user_email_push(overview_button_click, saved_payload):
    if(callback_context.triggered[0]["value"]):
        lambda_response, response_url = invoke_lambda.generate_report(saved_payload)
        session["report_url"] = response_url
        return response_url


# Download Report
@app.callback(
    Output("report_side_download", "children"),
    [Input("report_generate_url_store", "data"), Input("report_saved_url_store", "data")]
)
def update_download_report(generate_url, saved_url):
    latest_url = session.get("report_url", None)
    if(latest_url is None):
        return html.Div(className="report_side_download_no_data", children=[
            DashIconify(icon="pajamas:download", width=65, color="#25D366"),
            html.Strong("No Report Downloaded"),
            html.P("Your Latest Report will appear here"),
            html.Button(id="report_side_download_no_data_button", children="Check out saved reports", n_clicks=0)
        ])
    else:
        return html.Div(className="report_side_download_data", children=[
            html.Div(className="report_side_download_data_header", children=[
                DashIconify(icon="icon-park-twotone:check-one", width=65, color="#25D366"),
                html.Strong("Your Report is ready for download")
            ]),
            html.A(className="report_side_download_data_button_link", children=html.Button(className="report_side_download_data_button", children="Download"), href=latest_url),
            html.Div(className="report_side_download_data_link_container", children=[
                html.Strong("or download using this link (valid for 15 min):"),
                html.P(latest_url)
            ])
        ])


# Preview Report Notification
@app.callback(
    Output("preview_report_notification_message", "action", allow_duplicate=True),
    Input("preview_report_button", "n_clicks"),
    prevent_initial_call=True
)
def update_preview_report_notification(preview_button_click):
    if(callback_context.triggered[0]["value"] == 0):
        return "hide"
    else:
        return "show"


# Generate Report Notification
@app.callback(
    Output("generate_report_notification_message", "action", allow_duplicate=True),
    Input("generate_report_button", "n_clicks"),
    prevent_initial_call=True
)
def update_generate_report_notification(generate_button_click):
    if(callback_context.triggered[0]["value"] == 0):
        return "hide"
    else:
        return "show"


# Saved Report Notification
@app.callback(
    Output("saved_report_notification_message", "action", allow_duplicate=True),
    [Input("report_saved_card_0", "n_clicks"), Input("report_saved_card_1", "n_clicks"), Input("report_saved_card_2", "n_clicks"), Input("report_saved_card_3", "n_clicks"), Input("report_saved_card_4", "n_clicks")],
    prevent_initial_call=True
)
def update_saved_report_notification(card0_click, card1_click, card2_click, card3_click, card4_click):
    if(all(context["value"] is None for context in callback_context.triggered)):
        return "hide"
    else:
        return "show"


# Running Main App
if __name__ == "__main__":
    app.run_server(debug=False)
