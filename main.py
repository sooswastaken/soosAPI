from sanic import Sanic
from sanic.response import redirect, text, json as response_json
from sanic.exceptions import NotFound
from datetime import datetime
import json
import pytz

app = Sanic(__name__)


@app.listener("before_server_start")
async def setup(app_, _):
    file_path = "./school_calendar.json"
    with open(file_path, "r") as f:
        school_calendar = json.load(f)
    app_.ctx.hhs_school_calendar = school_calendar
    app_.ctx.timezone = pytz.timezone('US/Eastern')


@app.route("/")
async def index(request):
    return redirect("https://soos.dev?refer=api", status=301)


@app.route("/hhs/calendar/get-current-date")
async def get_current_date(request):
    # Get the current date in the EST timezone
    current_date_est = datetime.now(app.ctx.timezone).strftime('%Y-%m-%d')
    current_date_est = "2024-01-03"  # comment this out for production
    print(current_date_est)
    data = get_calendar_data(current_date_est, format_data=request.args.get('format', False))
    return response_json(data)


@app.route("/hhs/calendar/get-date/<date>")
async def get_date(request, date):
    return response_json(get_calendar_data(date, format_data=request.args.get('format', False)))


def get_calendar_data(date, format_data=False):
    # if it is a weekend, return a weekend message
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    if date_obj.weekday() == 5 or date_obj.weekday() == 6:
        if format_data:
            if date_obj.weekday() == 5:
                return "It's Saturday! Enjoy your weekend."
            if date_obj.weekday() == 6:
                return "It's Sunday! School starts tomorrow."
        else:
            return {'type': 'Weekend'}

    # if it is after june 15th, return a summer message
    if date_obj.month == 6 and date_obj.day >= 13:
        if format_data:
            return "It's summer! Have fun. Turn off this shortcut until next year."
        else:
            return {'type': 'Summer'}

    data = app.ctx.hhs_school_calendar.get(date)
    print(data)
    if format_data:
        return format_calender_day(data)
    else:
        return data


def format_calender_day(day_data):

    # Initial message
    message = f"Good morning. Today is a {day_data['type']}"

    # Add stinger if present and relevant
    if 'stinger' in day_data and day_data['stinger'] != "N/A":
        if 'TA' in day_data['stinger'] or any(char.isdigit() for char in day_data['stinger']):
            message += f" with {day_data['stinger']}"
        else:
            message += f". {day_data['stinger']} is taking place"

    # Process flags
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

    # Final punctuation
    message += "."

    return message


class SomeCustomException(Exception):
    pass


@app.exception(NotFound, SomeCustomException)
async def ignore_404s(request, exception):
    return text("404")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
