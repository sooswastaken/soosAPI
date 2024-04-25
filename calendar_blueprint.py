import os
from datetime import datetime, timedelta
import pytz
import json
from typing import Union

from apscheduler.triggers.cron import CronTrigger
from sanic import Blueprint
from sanic.response import text, json as response_json
from pywebpush import webpush

from Scheduler.BLACK_DAY_PERIOD_TYPES import BLACK_DAY_PERIOD_TYPES
from Scheduler.RED_DAY_PERIOD_TYPES import RED_DAY_PERIOD_TYPES
from Scheduler.PeriodTypes import PeriodTypes
from Scheduler.Scheduler import get_period_info as get_period_info_from_scheduler
from Scheduler.DayTypes import DayTypes

from ratelimit import ratelimiter
import aiosqlite

from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Constants
DATE_FORMAT = '%Y-%m-%d'
TIMEZONE = 'US/Eastern'
SUMMER_END_DATE = datetime(2024, 6, 12)
WEEKEND_DAYS = [5, 6]

# Create a Blueprint instance
calendar_blueprint = Blueprint('calendar_blueprint', url_prefix='/hhs/calendar')

DER_BASE64_ENCODED_PRIVATE_KEY_FILE_PATH = os.path.join(os.getcwd(), "private_key.txt")
DER_BASE64_ENCODED_PUBLIC_KEY_FILE_PATH = os.path.join(os.getcwd(), "public_key.txt")

VAPID_PRIVATE_KEY = open(DER_BASE64_ENCODED_PRIVATE_KEY_FILE_PATH, "r").read().strip()
VAPID_PUBLIC_KEY = open(DER_BASE64_ENCODED_PUBLIC_KEY_FILE_PATH, "r").read().strip()

VAPID_CLAIMS = {"sub": "mailto:contact@soos.dev"}

scheduler = AsyncIOScheduler()


async def handle_daily_scheduling(_app):
    # Assuming DATE_FORMAT is defined elsewhere
    current_date_est = datetime.now(_app.ctx.timezone).strftime(DATE_FORMAT)
    data = get_calendar_data(_app.ctx, current_date_est, format_data=False)
    if data['type'] in ["Black Day", "Red Day"]:
        await schedule_tasks_for_day(scheduler, data['type'], _app.ctx.timezone)


@calendar_blueprint.after_server_stop
async def shutdown_scheduler(_, __):
    scheduler.shutdown()


async def send_web_push(subscription_info, message_body):
    return webpush(
        subscription_info=subscription_info,
        data=message_body.replace('"', ''),
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims=VAPID_CLAIMS.copy()
    )


@calendar_blueprint.route('/admin/announce', methods=['GET'])
async def announce(request):
    message = request.args.get('message')
    password = request.args.get('password')
    if password == request.app.ctx.config['admin-password']:
        await send_notifications(message)
        return response_json({"message": "Notifications sent"})
    return response_json({"message": "Invalid password"})


async def send_notifications(message):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT token FROM subscriptions") as cursor:
            async for row in cursor:
                try:
                    token = json.loads(row[0])
                    await send_web_push(token, message)
                except Exception as e:
                    print(f"Error sending notification: {e}")


async def schedule_tasks_for_day(_scheduler, day_type, timezone):
    day_periods = BLACK_DAY_PERIOD_TYPES if day_type == "Black Day" else RED_DAY_PERIOD_TYPES

    now = datetime.now(timezone)  # Make sure 'now' is timezone-aware

    for period in day_periods:
        period_info = period.value
        # Ensure task_time is also timezone-aware
        task_time = datetime.combine(now.date(), period_info["end"], tzinfo=timezone)
        # subtract an hour from task_time for daylight savings time
        task_time = task_time - timedelta(hours=1)

        # subtract 30 seconds

        task_time = task_time + timedelta(seconds=30)

        # print all the tasks that would have been ran this day
        print(f"Task for {period_info['type']} would have been scheduled at {task_time}")

        if task_time > now and period_info["type"] not in [PeriodTypes.AFTER_SCHOOL, PeriodTypes.BEFORE_SCHOOL] \
                and "Transition" not in str(period_info["type"]):
            _scheduler.add_job(
                send_notifications,
                trigger=DateTrigger(run_date=task_time),
                args=[f"{period_info['type']} ends in 5 minutes!"],
            )


@calendar_blueprint.route("/subscription/", methods=["OPTIONS"])
async def subscription_options(request):
    # preflight request for CORS
    return response_json({"public_key": VAPID_PUBLIC_KEY})


@calendar_blueprint.route("/subscription/", methods=["POST", "GET"])
async def subscription(request):
    if request.method == "GET":
        return response_json({"public_key": VAPID_PUBLIC_KEY})

    if request.method == "POST":
        subscription_token = request.json.get("sub_token")
        if not subscription_token:
            return response_json({"message": "Invalid subscription token"}, status=400)
        state = request.json.get("state")
        if state:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT token FROM subscriptions WHERE token = ?",
                                      (json.dumps(subscription_token),)) as cursor:
                    row = await cursor.fetchone()
                    if row is None:
                        await db.execute("INSERT INTO subscriptions (token) VALUES (?)",
                                         (json.dumps(subscription_token),))
                        await db.commit()
        else:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("DELETE FROM subscriptions WHERE token = ?", (json.dumps(subscription_token),))
                await db.commit()
        return response_json({"message": "Subscription updated successfully"}, status=201)


@calendar_blueprint.middleware("request")
async def rate_limit_middleware(request):
    ratelimit = await ratelimiter(request)
    if ratelimit:
        return response_json(
            {
                "success": False,
                "retryAfter": ratelimit,
                "ratelimitInfo": "200 requests per 60 seconds"
            },
            headers={"Cache-Control": "no-store"},
            status=429)


DB_FILE = "subscribed_users_notifications.db"


@calendar_blueprint.listener('before_server_start')
async def setup(app, _):
    app.ctx.hhs_school_calendar = load_school_calendar()
    app.ctx.timezone = pytz.timezone(TIMEZONE)
    app.ctx.cache = {}  # Initialize cache
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS subscriptions (token TEXT UNIQUE);")
        await db.commit()

    try:
        with open("./config.json", "r", encoding="utf-8") as f:
            app.ctx.config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("config.json not found. Please create one.") from None

    scheduler.start()

    # Schedule the daily task check to run at 00:01 every day
    scheduler.add_job(
        handle_daily_scheduling,
        CronTrigger(hour=6, minute=0),  # Adjust the time as needed
        args=[app],
    )

    # also run the daily scheduling task immediately
    await handle_daily_scheduling(app)


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
            message += ". By the way, today is an early release day"

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
        if get_calendar_data(request.app.ctx, current_date_est, format_data=False)["type"] \
                not in ['Student Holiday', "Teacher Work Day", "Holiday", "Saturday", "Sunday", "Summer"] \
                and visited_count(request) < 4:
            return text(data + " Visit schedule.soos.dev to view a live clock of the current period. ")
        return text(data)
    else:
        return response_json(data)


@calendar_blueprint.route("/get-period-info")
async def get_period_info(request):
    # date is current date (timezone) but then stripped of the timezones
    date = datetime.now(request.app.ctx.timezone).replace(tzinfo=None)
    date_data = get_calendar_data(request.app.ctx, date.strftime(DATE_FORMAT))

    if date_data['type'] in ['Student Holiday', "Teacher Work Day", "Holiday", "Saturday", "Sunday", "Summer"]:
        return response_json({"success": True, "no_school": True, "message": "No school today. It is currently a "
                                                                             + date_data['type'] + "."})

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
    period_data["period_type"] = period_data["period_type"] \
        .replace("AFTER_SCHOOL", "Till midnight") \
        .replace("BEFORE_SCHOOL", "Till 8:00 AM")

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
        if get_calendar_data(request.app.ctx, date, format_data=False)["type"] \
                not in ['Student Holiday', "Teacher Work Day", "Holiday", "Saturday", "Sunday", "Summer"] \
                and visited_count(request) < 4:
            return text(data + " Visit schedule.soos.dev to view a live clock of the current period. ")
        return text(data)
    else:
        return response_json(data)
