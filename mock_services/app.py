"""Mock OTA (for the crawler to scrape) + mock PMS (to receive approved rates).

Run: python -m mock_services.app   (port 5001)
"""
import calendar
import zlib
from datetime import date

from flask import Flask, abort, jsonify, render_template_string, request

from core.config import PMS_API_KEY
from core.events import event_impact, load_events
from core.simulate import HOTELS, competitor_price, is_sold_out

app = Flask(__name__)
EVENTS = load_events()
PAGE_SIZE = 3
PMS_RATES = {}

LISTING = """<html><body><h1>Hotels</h1>
{% for h in hotels %}<div class="hotel"><a class="hotel-link" data-id="{{h.id}}" href="/hotel/{{h.id}}">{{h.name}}</a></div>{% endfor %}
{% if next_page %}<a class="next" href="/hotels?page={{next_page}}">Next</a>{% endif %}
</body></html>"""

HOTEL = """<html><body><h1 class="hotel-name" data-id="{{h.id}}">{{h.name}}</h1>
<table>{% for r in rows %}<tr class="rate"><td class="date">{{r.date}}</td>
<td class="price">{{r.price}}</td><td class="status">{{r.status}}</td></tr>{% endfor %}</table></body></html>"""


@app.get("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\n", 200, {"Content-Type": "text/plain"}


@app.get("/hotels")
def hotels():
    page = max(int(request.args.get("page", 1)), 1)
    chunk = HOTELS[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    if not chunk:
        abort(404)
    has_next = page * PAGE_SIZE < len(HOTELS)
    return render_template_string(LISTING, hotels=chunk, next_page=page + 1 if has_next else None)


@app.get("/hotel/<hotel_id>")
def hotel(hotel_id):
    h = next((x for x in HOTELS if x["id"] == hotel_id), None)
    if not h:
        abort(404)
    try:
        year, month = map(int, request.args.get("month", date.today().strftime("%Y-%m")).split("-"))
        days = calendar.monthrange(year, month)[1]
    except ValueError:
        abort(400)
    dates = [date(year, month, d) for d in range(1, days + 1)]
    impacts = event_impact(dates, EVENTS)
    rows = []
    for d, imp in zip(dates, impacts):
        price = competitor_price(h["base"], d, int(imp))
        noise = zlib.crc32(f"x{hotel_id}{d}".encode()) % 100
        shown = f"Rs {price * 10:,}" if noise == 0 else "-" if noise == 1 else f"Rs {price:,}"  # ~1% typos, ~1% blanks
        status = "Sold out" if is_sold_out(h["base"], d, int(imp)) else "Available"
        rows.append({"date": d.isoformat(), "price": shown, "status": status})
    return render_template_string(HOTEL, h=h, rows=rows)


# ---------------- mock PMS ----------------
@app.post("/pms/rates")
def pms_set_rate():
    if request.headers.get("X-API-Key") != PMS_API_KEY:
        return jsonify(error="invalid api key"), 401
    body = request.get_json(silent=True) or {}
    if "stay_date" not in body or not isinstance(body.get("rate"), int) or body["rate"] <= 0:
        return jsonify(error="stay_date and positive integer rate required"), 400
    PMS_RATES[body["stay_date"]] = body["rate"]
    return jsonify(ok=True, stay_date=body["stay_date"], rate=body["rate"])


@app.get("/pms/rates")
def pms_list():
    return jsonify(PMS_RATES)


if __name__ == "__main__":
    app.run(port=5001)
