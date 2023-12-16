from sanic import Blueprint
from sanic.response import text, json as response_json
from datetime import datetime
import pytz
import json

# Create a Blueprint instance
calendar_blueprint = Blueprint('calendar_blueprint', url_prefix='/hhs/calendar')


@calendar_blueprint.listener('before_server_start')
async def setup_calendar(app, _):
    file_path = "./school_calendar.json"
    with open(file_path, "r") as f:
        school_calendar = json.load(f)
    app.ctx.hhs_school_calendar = school_calendar
    app.ctx.timezone = pytz.timezone('US/Eastern')
    app.ctx.cache = {}  # Initialize cache

def get_calendar_data(app_ctx, date, format_data=False):
    date_obj = datetime.strptime(date, '%Y-%m-%d')

    # Check cache first
    if format_data and date in app_ctx.cache:
        return app_ctx.cache[date]

    if date_obj.weekday() == 5 or date_obj.weekday() == 6:
        if format_data:
            if date_obj.weekday() == 5:
                return "It's Saturday! Enjoy your weekend."
            if date_obj.weekday() == 6:
                return "It's Sunday! School starts tomorrow."
        else:
            return {'type': 'Weekend'}

    if date_obj.month == 6 and date_obj.day >= 13:
        if format_data:
            return "It's summer! Have fun. Turn off this shortcut until next year."
        else:
            return {'type': 'Summer'}

    data = app_ctx.hhs_school_calendar.get(date)

    if format_data:
        formatted_data = format_calender_day(data)
        app_ctx.cache[date] = formatted_data  # Cache the formatted data
        return formatted_data
    else:
        return data


def format_calender_day(day_data):
    message = f"Good morning. Today is a {day_data['type']}"
    if 'stinger' in day_data and day_data['stinger'] != "N/A":
        if 'TA' in day_data['stinger'] or any(char.isdigit() for char in day_data['stinger']):
            message += f" with {day_data['stinger']}"
        else:
            message += f". {day_data['stinger']} is taking place"

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
    data = get_calendar_data(request.app.ctx, date, format_data=request.args.get('format', False))
    return request.args.get('format', False) and text(data) or response_json(data)