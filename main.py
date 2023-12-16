import json
import subprocess

from sanic import Sanic
from sanic.response import redirect, text
from sanic.exceptions import NotFound

try:
    with open("./config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    print("Config file not found. Exiting...")
    exit(1)


from calendar_blueprint import calendar_blueprint

app = Sanic(__name__)
app.blueprint(calendar_blueprint)


@app.route("/")
async def index(_):
    return redirect("https://soos.dev?refer=api", status=301)


@app.route("/restart", methods=["POST"])
def webhook(request):
    if request.token != config["github-actions-secret"]:
        return text("Invalid token")

    subprocess.call(["git", "pull"])
    return text("Restarting")


@app.exception(NotFound)
async def ignore_404s(_, __):
    return text("404 - Page Not Found")


if __name__ == "__main__":
    app.run(host="0.0.0.0",
            port=config["port"],
            auto_reload=True,
            debug=not config["production"],
            )
