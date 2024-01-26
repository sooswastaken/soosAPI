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

    if date_str in app_ctx.cache and format_data:
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
    # if it is summer, return "It is summer break! Turn off this shortcut until next school year"

    if day_data['type'] == 'Summer':
        return "It's summer break! Turn off this shortcut until next school year"

    message = f"Good morning. Today is a {day_data['type']}"
    if 'stinger' in day_data and day_data['stinger'] != "N/A":
        if 'TA' in day_data['stinger'] or any(char.isdigit() for char in day_data['stinger']):
            message += f" with {day_data['stinger']}"
        else:
            message += f". {day_data['stinger']} is taking place"

    # if it is a sunday/holiday, add a message about when the next school day is

    # for sundays, it is the next day (check if the next day is a holiday), but for holidays, recalculate the next
    # day until it is not a holiday
    if day_data['type'] == 'Sunday' or day_data['type'] in ['Student Holiday', "Teacher Workday", "Holiday"]:
        # check if the next day is a holiday
        next_day = date_obj + timedelta(days=1)
        next_day_data = get_calendar_data(app_ctx, next_day.strftime('%Y-%m-%d'))

        # if the next day is a holiday, keep recalculating until it is not
        while next_day_data['type'] in ['Student Holiday', "Teacher Workday", "Holiday", "Saturday", "Sunday"]:
            next_day = next_day + timedelta(days=1)
            next_day_data = get_calendar_data(app_ctx, next_day.strftime('%Y-%m-%d'))

        # since its a sunday, we can assume the next day is not a weekend

        # if it is one day, say "tomorrow", otherwise say "on <day of week>" if it is within the next week,
        # otherwise say "on <month> <day>"
        if next_day == date_obj + timedelta(days=1):
            message += f". Tomorrow is a {next_day_data['type']}"
        elif next_day - date_obj < timedelta(days=7):
            message += f". School resumes on {next_day.strftime('%A')}"
        else:
            message += f". School resumes on {next_day.strftime('%B %d')}"

    if day_data['type'] == 'Black Day' or day_data['type'] == 'Red Day':
        if 'End of School Year' in day_data['flags']:
            message += ". It is the last day of school!"
        elif 'Observance Day' in day_data['flags']:
            message += ". Don't forget the special observance today"
        elif 'Evening Observance Day' in day_data['flags']:
            message += ". There's an observance event this evening"
        elif 'Quarter End' in day_data['flags']:
            message += ". The quarter ends today. Time to wrap things up"
        elif 'Early Release' in day_data['flags']:
            message += ". Remember, today is an early release day"

    message += "."
    return message


def is_morning(app_ctx):
    current_hour = datetime.now(app_ctx.timezone).hour
    return current_hour < 12


def visited_count(request):
    # return false if header is not present
    if not request.headers.get("CF-Connecting-IP"):
        return False
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

        # save visits.json
        with open("visits.json", "w") as f:
            json.dump(data, f)

        return data[request.headers.get("CF-Connecting-IP")]
    else:
        # if it isn't, add it
        data[request.headers.get("CF-Connecting-IP")] = 1

        # save visits.json
        with open("visits.json", "w") as f:
            json.dump(data, f)

        return 1


@calendar_blueprint.route("/get-current-date")
async def get_current_date(request):
    format_data = request.args.get('format', False)
    current_date_est = datetime.now(request.app.ctx.timezone).strftime(DATE_FORMAT)
    data = get_calendar_data(request.app.ctx, current_date_est, format_data=format_data)
    if format_data:
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
    period_data["period_type"].replace("AFTER_SCHOOL", "Till midnight")
    period_data["period_type"].replace("BEFORE_SCHOOL", "Till 8:00 AM")

    return response_json(period_data)


@calendar_blueprint.route("/get-date/<date>")
async def get_date(request, date):
    format_data = request.args.get('format', False)
    try:
        datetime.strptime(date, DATE_FORMAT)
    except ValueError:
        return text("Invalid date format. Please use YYYY-MM-DD")

    data = get_calendar_data(request.app.ctx, date, format_data=format_data)
    if format_data:
        if visited_count(request) < 4:
            return text(data + " Visit schedule.soos.dev to view a live clock of the current period. ")
        return text(data)
    else:
        return response_json(data)
