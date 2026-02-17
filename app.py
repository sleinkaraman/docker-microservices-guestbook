import os
import time
import logging
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string
import psycopg2
import psycopg2.extras
import redis

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


app = Flask(__name__)


# Configuration 

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "guestbook")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

REDIS_HOST = os.getenv("REDIS_HOST", "cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

PAGE_VIEW_KEY = "guestbook:page_views"


# Connection helpers 

def get_db_connection(retries: int = 5, delay: int = 2):
    """Return a new psycopg2 connection, retrying on failure."""
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            return conn
        except psycopg2.OperationalError as exc:
            logger.warning("DB connection attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    raise ConnectionError("Could not connect to PostgreSQL after multiple retries.")


def get_redis_client(retries: int = 5, delay: int = 2):
    """Return a Redis client, retrying on failure."""
    for attempt in range(1, retries + 1):
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            client.ping()       
            return client
        except redis.exceptions.ConnectionError as exc:
            logger.warning("Redis connection attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    raise ConnectionError("Could not connect to Redis after multiple retries.")


# Database 

def init_db():
    """Ensure the required schema exists in PostgreSQL."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id         SERIAL PRIMARY KEY,
                    author     VARCHAR(100) NOT NULL,
                    content    TEXT         NOT NULL,
                    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
                );
                """
            )
        conn.commit()
        logger.info("Database initialised successfully.")
    finally:
        conn.close()



HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>☁️ Cloud-Ready Guestbook</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; background: #f5f7fa; color: #333; }
    h1   { color: #2c3e50; }
    .stat{ background:#2c3e50; color:#fff; padding:8px 16px; border-radius:6px; display:inline-block; margin-bottom:24px; font-size:.9rem; }
    form { background:#fff; padding:20px; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,.1); margin-bottom:32px; }
    input, textarea { width:100%; padding:10px; margin:8px 0 16px; border:1px solid #ddd; border-radius:4px; box-sizing:border-box; }
    button { background:#3498db; color:#fff; padding:10px 24px; border:none; border-radius:4px; cursor:pointer; font-size:1rem; }
    button:hover { background:#2980b9; }
    .message  { background:#fff; padding:16px; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:12px; }
    .meta     { font-size:.8rem; color:#888; margin-top:6px; }
    .author   { font-weight:600; color:#2c3e50; }
    .error    { color:#e74c3c; padding:10px; background:#fdf3f2; border-radius:4px; }
  </style>
</head>
<body>
  <h1>☁️ Cloud-Ready Guestbook</h1>
  <div class="stat">👁 Page views: <strong>{{ page_views }}</strong></div>

  {% if error %}
    <p class="error">{{ error }}</p>
  {% endif %}

  <form action="/messages" method="post">
    <h2>Leave a message</h2>
    <label>Your name</label>
    <input type="text" name="author" placeholder="e.g. Ada Lovelace" required maxlength="100" />
    <label>Message</label>
    <textarea name="content" rows="3" placeholder="Write something…" required></textarea>
    <button type="submit">Post ✉️</button>
  </form>

  <h2>Messages</h2>
  {% for msg in messages %}
    <div class="message">
      <span class="author">{{ msg.author }}</span>
      <p>{{ msg.content }}</p>
      <div class="meta">{{ msg.created_at.strftime('%d %b %Y, %H:%M') }}</div>
    </div>
  {% else %}
    <p>No messages yet — be the first! 👋</p>
  {% endfor %}
</body>
</html>
"""

# Routes

@app.route("/", methods=["GET"])
def index():
    """Home page: increment view counter, list all messages."""
    try:
        r = get_redis_client()
        page_views = r.incr(PAGE_VIEW_KEY)
    except ConnectionError:
        logger.error("Redis unavailable — page views will show as N/A.")
        page_views = "N/A"

    messages = []
    error = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT author, content, created_at FROM messages ORDER BY created_at DESC;")
            messages = cur.fetchall()
        conn.close()
    except ConnectionError as exc:
        error = f"Database unavailable: {exc}"
        logger.error(error)

    return render_template_string(
        HTML_TEMPLATE,
        messages=messages,
        page_views=page_views,
        error=error,
    )


@app.route("/messages", methods=["POST"])
def add_message():
    """Accept a new guestbook entry and store it in PostgreSQL."""
    author  = request.form.get("author",  "").strip()
    content = request.form.get("content", "").strip()

    if not author or not content:
        return "Author and content are required.", 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (author, content) VALUES (%s, %s);",
                (author, content),
            )
        conn.commit()
        conn.close()
        logger.info("New message from '%s' saved.", author)
    except ConnectionError as exc:
        logger.error("Failed to save message: %s", exc)
        return f"Could not save message: {exc}", 500


    from flask import redirect, url_for
    return redirect(url_for("index"))


@app.route("/health", methods=["GET"])
def health():
    """
    Lightweight health-check endpoint used by Docker / load balancers.
    Returns HTTP 200 when both backing services are reachable.
    """
    status = {"status": "ok", "postgres": "ok", "redis": "ok"}
    http_code = 200

    try:
        conn = get_db_connection(retries=1, delay=0)
        conn.close()
    except Exception as exc:
        status["postgres"] = f"error: {exc}"
        status["status"]   = "degraded"
        http_code = 503

    try:
        r = get_redis_client(retries=1, delay=0)
        r.ping()
    except Exception as exc:
        status["redis"]  = f"error: {exc}"
        status["status"] = "degraded"
        http_code = 503

    return jsonify(status), http_code


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)