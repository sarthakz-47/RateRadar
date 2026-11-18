from mock_services.app import app

client = app.test_client()


def test_listing_paginates():
    page1 = client.get("/hotels?page=1").get_data(as_text=True)
    page2 = client.get("/hotels?page=2").get_data(as_text=True)
    assert page1.count("hotel-link") == 3 and 'class="next"' in page1
    assert page2.count("hotel-link") == 3 and 'class="next"' not in page2
    assert client.get("/hotels?page=3").status_code == 404


def test_hotel_page_has_rate_rows():
    html = client.get("/hotel/h1?month=2026-12").get_data(as_text=True)
    assert html.count('class="rate"') == 31


def test_pms_requires_api_key():
    r = client.post("/pms/rates", json={"stay_date": "2026-12-01", "rate": 4500})
    assert r.status_code == 401
    r = client.post("/pms/rates", json={"stay_date": "2026-12-01", "rate": 4500},
                    headers={"X-API-Key": "dev-key"})
    assert r.status_code == 200
    r = client.post("/pms/rates", json={"stay_date": "2026-12-01", "rate": -5},
                    headers={"X-API-Key": "dev-key"})
    assert r.status_code == 400
