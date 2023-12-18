from sanic import Blueprint
from sanic.response import text, json as response_json
from datetime import datetime, timedelta
import pytz
import json

# Create a Blueprint instance
calendar_blueprint = Blueprint('calendar_blueprint', url_prefix='/hhs/calendar')


@calendar_blueprint.listener('before_server_start')
async def setup_calendar(app, _):
    file_path = "./school_calendar.json"
    with open(file_path, "r", encoding="utf-8") as f:
        school_calendar = json.load(f)
    app.ctx.hhs_school_calendar = school_calendar
    app.ctx.timezone = pytz.timezone('US/Eastern')
    app.ctx.cache = {}  # Initialize cache


def get_calendar_data(app_ctx, date, format_data=False):
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    if format_data and date in app_ctx.cache:
        return app_ctx.cache[date]

    # if it is a weekend, the data is instead {type: "Saturday" or "Sunday"}
    if date_obj.weekday() >= 5:
        data = {'type': date_obj.strftime('%A')}
    else:
        data = app_ctx.hhs_school_calendar.get(date)

    # if the date is after June 12, 2024, the data is instead {type: "Summer"}
    if date_obj > datetime(2024, 6, 12):
        data = {'type': 'Summer'}

    if format_data:
        formatted_data = format_calender_day(data, date_obj, app_ctx)
        app_ctx.cache[date] = formatted_data  # Cache the formatted data
        return formatted_data
    else:
        return data


def format_calender_day(day_data, date_obj, app_ctx):
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


@calendar_blueprint.route("/get-current-date")
async def get_current_date(request):
    current_date_est = datetime.now(request.app.ctx.timezone).strftime('%Y-%m-%d')
    data = get_calendar_data(request.app.ctx, current_date_est, format_data=request.args.get('format', False))
    return request.args.get('format', False) and text(data) or response_json(data)


@calendar_blueprint.route("/get-date/<date>")
async def get_date(request, date):
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return text("Invalid date format. Please use YYYY-MM-DD")

    data = get_calendar_data(request.app.ctx, date, format_data=request.args.get('format', False))

    return request.args.get('format', False) and text(data) or response_json(data)
