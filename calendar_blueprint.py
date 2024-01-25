import os
from datetime import datetime, timedelta
import pytz
import json
from typing import Union
from sanic import Blueprint
from sanic.response import text, json as response_json

from Scheduler.Scheduler import get_period_info as get_period_info_from_scheduler
from Scheduler.DayTypes import DayTypes

# Constants
DATE_FORMAT = '%Y-%m-%d'
TIMEZONE = 'US/Eastern'
SUMMER_END_DATE = datetime(2024, 6, 12)
WEEKEND_DAYS = [5, 6]

# Create a Blueprint instance
calendar_blueprint = Blueprint('calendar_blueprint', url_prefix='/hhs/calendar')


@calendar_blueprint.middleware("response")
async def cors(request, response):
    response.headers.update({"Access-Control-Allow-Origin": "*"})


@calendar_blueprint.listener('before_server_start')
async def setup_calendar(app, _):
    app.ctx.hhs_school_calendar = load_school_calendar()
    app.ctx.timezone = pytz.timezone(TIMEZONE)
    app.ctx.cache = {}  # Initialize cache


def load_school_calendar():
    file_path = "./school_calendar.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Calendar data not found at {file_path}. Please create one.") from None


def get_next_school_day(app_ctx, date_obj):
    next_day = date_obj + timedelta(days=1)
    while True:
        next_day_str = next_day.strftime(DATE_FORMAT)
        next_day_data = get_calendar_data(app_ctx, next_day_str)
        if next_day_data['type'] not in ['Student Holiday', "Teacher Workday", "Holiday", "Saturday", "Sunday"]:
            break
        next_day += timedelta(days=1)
    return next_day, next_day_data


def get_calendar_data(app_ctx, date_str, format_data=False) -> Union[str, dict]:
    date_obj = datetime.strptime(date_str, DATE_FORMAT)

    if date_str in app_ctx.cache:
        return app_ctx.cache[date_str]

    # Retrieve the full day data from the calendar, or use a default if not found
    day_data = app_ctx.hhs_school_calendar.get(date_str, {'type': date_obj.strftime('%A')})

    # Override type for weekends and summer
    if is_weekend(date_obj):
        day_data['type'] = date_obj.strftime('%A')
    elif date_obj > SUMMER_END_DATE:
        day_data['type'] = 'Summer'

    if format_data:
        formatted_data = format_calendar_day(day_data, date_obj, app_ctx)
        app_ctx.cache[date_str] = formatted_data
        return formatted_data
    return day_data


def is_weekend(date_obj):
    return date_obj.weekday() in WEEKEND_DAYS


def format_calendar_day(day_data, date_obj, app_ctx):
    messages = []

    if 'stinger' in day_data:
        messages.append(
            f"Don't forget about {day_data['stinger']} happening today." if 'TA' in day_data['stinger'] or any(
                char.isdigit() for char in
                day_data['stinger']) else f"Also, {day_data['stinger']} is taking place today.")

    day_type = day_data['type']
    if day_type in ['Sunday', 'Student Holiday', "Teacher Workday", "Holiday"]:
        next_day, next_day_data = get_next_school_day(app_ctx, date_obj)
        delta_days = (next_day - date_obj).days
        if delta_days == 1:
            messages.append(f"Looking ahead, we have a {next_day_data['type']} lined up for tomorrow. ")
        elif delta_days < 7:
            messages.append(f"Enjoy your time off! School will resume next {next_day.strftime('%A')}. ")
        else:
            messages.append(f"Keep enjoying your long break! School resumes on {next_day.strftime('%B %d')}. ")

    flags = day_data.get('flags', [])
    flag_messages = {
        'End of School Year': "You've made it! Today marks the last day of this school year. Congratulations! ",
        'Observance Day': "Today holds a special observance. Let's honor it together. ",
        'Evening Observance Day': "There's an observance event this evening. A wonderful opportunity to gather! ",
        'End of Quarter': "As we reach the quarter's end today, it's a great time to finalize any pending tasks. ",
        'Early Release': "Just a heads up, you get out 2 hours early today. ",
    }
    for flag in flags:
        if flag in flag_messages:
            messages.append(flag_messages[flag])

    greeting = "Good morning." if is_morning(app_ctx) else "Hello."
    messages.insert(0, f"{greeting} Today is a {day_data['type']}. ")

    return ''.join(messages)


def is_morning(app_ctx):
    current_hour = datetime.now(app_ctx.timezone).hour
    return current_hour < 12


def visited_count(request):
    # return false if header is not present
    if not request.headers.get("CF-Connecting-IP"):
        return False

    # check cf ip in visits.json, if not there, add it if it is increase by 1

    # check if visits.json exists, if not create it
    if not os.path.exists("visits.json"):
        with open("visits.json", "w") as f:
            json.dump({}, f)

    # load visits.json
    with open("visits.json", "r") as f:
        data = json.load(f)

    # check if cf ip is in visits.json
    if request.headers.get("CF-Connecting-IP") in data:
        # if it is, increase by 1
        data[request.headers.get("CF-Connecting-IP")] += 1
        print(data[request.headers.get("CF-Connecting-IP")])
        return data[request.headers.get("CF-Connecting-IP")]
    else:
        # if it isn't, add it
        data[request.headers.get("CF-Connecting-IP")] = 1
        print(data[request.headers.get("CF-Connecting-IP")])
        return 1


@calendar_blueprint.route("/get-current-date")
async def get_current_date(request):
    format_data = request.args.get('format', False)
    current_date_est = datetime.now(request.app.ctx.timezone).strftime(DATE_FORMAT)
    data = get_calendar_data(request.app.ctx, current_date_est, format_data=format_data)
    if not format_data:
        if visited_count(request) < 4:
            return text(data + " Visit schedule.soos.dev to view a live clock of the current period. ")
        return text(data)
    else:
        return response_json(data)


@calendar_blueprint.route("/get-period-info")
async def get_period_info(request):
    date = datetime.now(request.app.ctx.timezone).replace(tzinfo=None)
    date_data = get_calendar_data(request.app.ctx, date.strftime(DATE_FORMAT))

    if date_data['type'] == 'Summer':
        return text("It's summer! No school today.")
    if date_data['type'] in ['Student Holiday', "Teacher Workday", "Holiday", "Saturday", "Sunday"]:
        return response_json({"success": True, "no_school": True, "message": "No school today. It is currently a "
                                                                             + date_data['type']})

    period_data = get_period_info_from_scheduler(
        DayTypes.BLACK_DAY if date_data['type'] == "Black Day" else DayTypes.RED_DAY,
        date,
    ).json()

    if date_data['type'] == "Black Day":
        if period_data["period_type"] in [
            "STINGER_FIRST_HALF", "STINGER_FIRST_HALF_TRANSITION"
        ]:
            # first half means replace it with date_data["stinger"]'s text before the " &"
            period_data["period_type"] = period_data["period_type"].replace(
                "STINGER_FIRST_HALF", date_data["stinger"].split(" &")[0])
        if period_data["period_type"] in [
            "STINGER_SECOND_HALF", "STINGER_SECOND_HALF_TRANSITION"
        ]:
            # second half means replace it with date_data["stinger"]'s text after the "& "
            period_data["period_type"] = period_data["period_type"].replace(
                "STINGER_SECOND_HALF", date_data["stinger"].split("& ")[1])
    #  the current time in milliseconds since the epoch (for est timezone)
    period_data["now"] = int(datetime.now(request.app.ctx.timezone).timestamp() * 1000)

    return response_json(period_data)


@calendar_blueprint.route("/get-date/<date>")
async def get_date(request, date):
    format_data = request.args.get('format', False)
    try:
        datetime.strptime(date, DATE_FORMAT)
    except ValueError:
        return text("Invalid date format. Please use YYYY-MM-DD")

    data = get_calendar_data(request.app.ctx, date, format_data=format_data)
    if not format_data:
        if visited_count(request) < 4:
            return text(data + " Visit schedule.soos.dev to view a live clock of the current period. ")
        return text(data)
    else:
        return response_json(data)
