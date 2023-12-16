from sanic import Sanic
from sanic.response import redirect, text
from sanic.exceptions import NotFound

from calendar_blueprint import calendar_blueprint

app = Sanic(__name__)
app.blueprint(calendar_blueprint)


@app.route("/")
async def index(_):
    return redirect("https://soos.dev?refer=api", status=301)


@app.exception(NotFound)
async def ignore_404s(_, __):
    return text("404")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5212)
