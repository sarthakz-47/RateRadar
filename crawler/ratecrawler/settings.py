BOT_NAME = "ratecrawler"
SPIDER_MODULES = ["ratecrawler.spiders"]
NEWSPIDER_MODULE = "ratecrawler.spiders"

# Polite crawling. The mock OTA allows everything in robots.txt; keep this True for real sites.
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 0.2
CONCURRENT_REQUESTS_PER_DOMAIN = 4
RETRY_ENABLED = True
RETRY_TIMES = 2
AUTOTHROTTLE_ENABLED = True
LOG_LEVEL = "INFO"
FEED_EXPORT_ENCODING = "utf-8"
