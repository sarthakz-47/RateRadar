# RateRadar

A mini hotel revenue-management engine. It watches competitor room rates, predicts demand, recommends a price, and lets a human approve it before it is pushed to the hotel's PMS.

```
Mock OTA --Scrapy--> validate --> MySQL --> ML model (demand: low/med/high)
                                                  |
Mock PMS <-- approved rate <-- Flask API <-- pricing rules + guardrails
```

## Features

- **Crawler** (Scrapy) collects competitor rates for the next 60 days
- **Validation** removes duplicates, blanks and price outliers before loading
- **Demand model** compares a Decision Tree and an SVM and keeps the better one
- **Pricing rules** with min/max guardrails and a plain-English reason for each recommendation
- **Human approval**: nothing reaches the PMS until you approve it

## Tech stack

Python, Scrapy, Flask, pandas, scikit-learn, SQLAlchemy, MySQL, pytest

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then set your MySQL password
mysql -u root -p -e "CREATE DATABASE rateradar"
```

## Run

```bash
python -m scripts.seed_history   # create tables + synthetic history
python -m scripts.train_model    # train and save the best model

python -m mock_services.app      # terminal 1: mock OTA + PMS (port 5001)

cd crawler && scrapy crawl ota -O ../data/raw/latest.jsonl && cd ..   # terminal 2
python -m scripts.run_pipeline   # validate + load into MySQL

python -m api.app                # API (port 5000)
```

## Try it

```bash
curl localhost:5000/health
curl -X POST localhost:5000/recommendations/generate \
  -H "Content-Type: application/json" -d '{"days":14}'
curl "localhost:5000/recommendations?status=pending"
curl -X POST localhost:5000/recommendations/1/approve   # pushes to mock PMS
curl localhost:5001/pms/rates                           # see it arrive
```

## Tests

```bash
pytest -q    # uses in-memory SQLite, no MySQL needed
```

## Project layout

```
api/            Flask API and simple web page
core/           validation, features, model, pricing rules, PMS client
crawler/        Scrapy spider
mock_services/  fake OTA and PMS
scripts/        seed, train, and pipeline scripts
tests/          pytest suite
data/           event calendar
```

## Limitations

- Occupancy history and competitor prices are **synthetic**, so model accuracy shows the pipeline works, not real-world performance.
- Uses a mock OTA because real OTAs forbid scraping.
- No auth or scheduling (run the crawler and pipeline from cron).
