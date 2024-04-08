import json
import subprocess

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sanic import Sanic
from sanic.response import redirect, text
from sanic.exceptions import NotFound
from sanic_cors import CORS

try:
    with open("./config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("config.json not found. Please create one.") from None

from calendar_blueprint import calendar_blueprint

app = Sanic(__name__)
app.blueprint(calendar_blueprint)
schedule = AsyncIOScheduler()


@app.middleware("response")
async def cors(_, response):
    response.headers.update(
        {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "*"})


@app.route("/")
async def index(_):
    return redirect(config["index-redirect-url"], status=301)


@app.route("/restart", methods=["POST"])
async def restart(request):
    if request.token != config["github-actions-secret"]:
        return text("Invalid token")

    subprocess.call(["git", "pull"])
    subprocess.call(["pip", "install", "-r", "requirements.txt"])
    return text("Restarting")


@app.exception(NotFound)
async def ignore_404s(_, __):
    return text("404 - Route Not Found")


@app.listener('before_server_start')
async def initialize_scheduler(_, loop):
    # Attach the scheduler to the running event loop
    schedule.configure(event_loop=loop)
    # Add your scheduled job here to ensure it's using the correct loop
    schedule.start()


if __name__ == "__main__":
    app.ctx.config = config
    app.run(host="0.0.0.0",
            port=config["port"],
            auto_reload=True,
            debug=not config["production"],
            )
