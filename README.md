# RateRadar - mini hotel revenue-management engine

A small, end-to-end version of what a RMS like ZettaRMS.ai does: **watch competitor rates, read demand signals, recommend a room rate, let a human approve it, push it to the PMS.**

```
 Mock OTA (Flask) --Scrapy--> latest.jsonl --validate--> MySQL --features--> Decision Tree / SVM
                                                                                   |
 Mock PMS (Flask) <--approved rate-- Flask API <-- rate rules + guardrails <-- demand: low/med/high
```

## Stack
Python, Scrapy (crawler), Flask (API + mock OTA/PMS), pandas, scikit-learn (decision tree vs SVM), SQLAlchemy + **MySQL**, pytest.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # set your MySQL password
mysql -u root -p -e "CREATE DATABASE rateradar"
```

## Run (in this order)
```bash
python -m scripts.seed_history          # create tables + 2 yrs of synthetic history
python -m scripts.train_model           # trains decision tree + SVM, keeps the better one

python -m mock_services.app             # terminal 1: mock OTA + PMS on :5001

cd crawler && scrapy crawl ota -O ../data/raw/latest.jsonl && cd ..    # terminal 2: rate-shop
python -m scripts.run_pipeline          # validate + load into MySQL

python -m api.app                       # API on :5000
```

## Try the API
```bash
curl localhost:5000/health
curl "localhost:5000/rates?from=2026-12-01&to=2026-12-07"
curl -X POST localhost:5000/recommendations/generate -H "Content-Type: application/json" -d '{"days":14}'
curl "localhost:5000/recommendations?status=pending"
curl -X POST localhost:5000/recommendations/1/approve     # pushes the rate to the mock PMS
curl localhost:5001/pms/rates                             # see it arrive
```

## Tests
```bash
pytest -q       # API tests use in-memory SQLite, so MySQL is not needed for tests
```

## How it works
- **Crawler**: follows listing pagination, then each hotel's monthly rate table, for the next 60 days. Respects robots.txt, retries, throttles. Uses a mock OTA because real OTAs forbid scraping.
- **Validation** (`core/validate.py`): drops missing/duplicate rows, removes price outliers (the mock OTA injects ~1% typos and ~1% blanks), and checks feed freshness and coverage. A failed check stops the load.
- **Model**: features = day of week, weekend, month, event impact (`data/events.csv`), competitor average price. Label = low/medium/high occupancy. A decision tree and an SVM are compared on a chronological hold-out and the better one is saved.
- **Pricing rules** (`core/recommend.py`): base rate x demand multiplier, kept within 15% of the competitor average, and inside min/max guardrails. Every recommendation stores a human-readable reason.
- **Human in the loop**: recommendations stay `pending` until approved. Approval pushes to the PMS; failures are recorded as `push_failed` and can be retried.

## Honest limitations
- Occupancy history and competitor prices are **synthetic**. The model accuracy shows the pipeline works, not real-world performance. With real PMS data you would swap the `seed_history` step.
- Event dates in `events.csv` are approximate.
- Not built (by design, to keep scope small): LLM explanations, dashboard, auth, scheduling (run the crawler + pipeline from cron).
