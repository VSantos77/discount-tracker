from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.spiderloader import SpiderLoader
import argparse

if __name__ == "__main__":
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    loader = SpiderLoader.from_settings(settings)

    parser = argparse.ArgumentParser(description="Run Scrapy Spiders")
    # Define your arguments
    parser.add_argument("--page_limit", type=int, default=0, help="Set page limit for crawls")
    parser.add_argument("--dry_run", type=str, default=0, help="Set dry run mode (1/0)")

    args = parser.parse_args()

    # Loop through every spider in the project and schedule it
    for spider_name in loader.list():
        print(f'Starting crawl for spider: {spider_name}')
        process.crawl(spider_name, **vars(args))

    process.start()







