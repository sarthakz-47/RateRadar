import re
from datetime import date, datetime, timedelta, timezone

import scrapy


class OtaSpider(scrapy.Spider):
    """Crawls the mock OTA: hotel listing (paginated) -> each hotel's monthly rate tables."""

    name = "ota"

    def __init__(self, base_url="http://localhost:5001", horizon=60, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.horizon = int(horizon)
        self.today = date.today()
        self.last_day = self.today + timedelta(days=self.horizon)
        self.start_urls = [f"{self.base_url}/hotels"]
        self.scraped_at = datetime.now(timezone.utc).isoformat()

    def _months(self):
        days = (self.today + timedelta(days=i) for i in range(self.horizon + 1))
        return sorted({d.strftime("%Y-%m") for d in days})

    def parse(self, response):
        for link in response.css("a.hotel-link"):
            hotel_id = link.attrib["data-id"]
            for month in self._months():
                yield response.follow(f"/hotel/{hotel_id}?month={month}", callback=self.parse_hotel)
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_hotel(self, response):
        name = response.css("h1.hotel-name::text").get()
        hotel_id = response.css("h1.hotel-name::attr(data-id)").get()
        for row in response.css("tr.rate"):
            stay_date = row.css("td.date::text").get()
            if not stay_date or not (self.today <= date.fromisoformat(stay_date) <= self.last_day):
                continue
            digits = re.sub(r"[^\d]", "", row.css("td.price::text").get() or "")
            yield {
                "hotel_id": hotel_id,
                "hotel_name": name,
                "stay_date": stay_date,
                "price": int(digits) if digits else None,  # None is caught by the validator
                "available": (row.css("td.status::text").get() or "").strip() == "Available",
                "scraped_at": self.scraped_at,
            }
