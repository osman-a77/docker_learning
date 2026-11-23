import os
from flask import Flask, render_template_string
import redis

app = Flask(__name__)

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(host=redis_host, port=redis_port)

SITE_NAME = "Turnstile"
TAGLINE = "Everyone who walks through gets counted."
ABOUT = (
    "A small Flask app talking to Redis, running in its own container. "
    "Every visit is counted, and you are part of the count."
)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ site_name }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,800&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #eef1f4;
    --ink: #14213d;
    --blue: #2d3be0;
    --stub: #f5d547;
    color-scheme: light dark;
  }
  @media (prefers-color-scheme: dark) {
    :root { --paper: #0f1626; --ink: #e8ecf5; --blue: #8a95ff; }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    background: var(--paper);
    color: var(--ink);
    font: 18px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif;
    display: grid;
    place-items: center;
    padding: 2rem 1.25rem;
  }
  main { width: 100%; max-width: 38rem; }
  h1 {
    font-family: "Bricolage Grotesque", system-ui, sans-serif;
    font-weight: 800;
    font-size: clamp(2.6rem, 9vw, 4.6rem);
    line-height: 1;
    letter-spacing: -0.03em;
    margin: 0 0 0.5rem;
  }
  .tagline { font-size: 1.25rem; color: var(--blue); margin: 0 0 1.5rem; }
  p { max-width: 34rem; margin: 0 0 2rem; }

  .ticket {
    display: flex;
    background: var(--stub);
    color: #14213d;
    border-radius: 0.6rem;
    margin: 0 0 2rem;
    box-shadow: 0 0 0 2px #14213d;
  }
  .ticket .label { padding: 1rem 1.25rem; flex: 1; align-self: center; }
  .ticket .label strong { display: block; font-size: 1.1rem; }
  .ticket .label span { font-size: 0.95rem; opacity: 0.8; }
  .ticket .number {
    font-family: "Bricolage Grotesque", system-ui, sans-serif;
    font-weight: 800;
    font-size: 2.6rem;
    padding: 0.5rem 1.25rem;
    border-left: 2px dashed #14213d;
    display: grid;
    place-items: center;
  }

  a { color: var(--blue); font-weight: 500; text-underline-offset: 0.2em; }
  a:focus-visible { outline: 3px solid var(--blue); outline-offset: 3px; }
</style>
</head>
<body>
<main>
  <h1>{{ site_name }}</h1>
  <p class="tagline">{{ tagline }}</p>
  {% if about %}<p>{{ about }}</p>{% endif %}

  <div class="ticket" role="status">
    <div class="label">
      <strong>{{ ticket_title }}</strong>
      <span>{{ message }}</span>
    </div>
    <div class="number">{{ count if count is not none else "?" }}</div>
  </div>

  {% if back_link %}<a href="/">Back to the entrance</a>{% endif %}
</main>
</body>
</html>
"""


def increment_visits():
    try:
        return r.incr("visit_count")
    except redis.exceptions.RedisError:
        return None


@app.route("/")
def home():
    count = increment_visits()
    message = (
        "You're the one holding this ticket."
        if count is not None
        else "The counter is resting. Try again in a moment."
    )
    return render_template_string(
        PAGE,
        site_name=SITE_NAME,
        tagline=TAGLINE,
        about=ABOUT,
        ticket_title="Visitor ticket",
        message=message,
        count=count,
        back_link=False,
    )


@app.route("/count")
def counts():
    count = increment_visits()
    message = (
        "People through the gate so far."
        if count is not None
        else "The counter is resting. Try again in a moment."
    )
    return render_template_string(
        PAGE,
        site_name=SITE_NAME,
        tagline="The running total.",
        about=None,
        ticket_title="Total visits",
        message=message,
        count=count,
        back_link=True,
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
