from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.spiderloader import SpiderLoader
import argparse
import os
import datetime

if __name__ == "__main__":
    settings = get_project_settings()

    parser = argparse.ArgumentParser(description="Run Scrapy Spiders")
    # Define your arguments
    parser.add_argument("--spiders", type=str, default='', help="Comma-separated list of spiders to run (default: all)")
    parser.add_argument("--page_limit", type=int, default=0, help="Set page limit for crawls")
    parser.add_argument("--dry_run", type=str, default='false', help="Set dry run mode (1/0)")
    parser.add_argument("--itemcount", type=int, default=0, help="Set item count limit for crawls")

    args = parser.parse_args()

    # --- Configure Logging to File ---
    log_dir = "logs/scrapy"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"scrapy_{timestamp}.log")
    
    settings.set('LOG_FILE', log_file)
    settings.set('LOG_LEVEL', 'INFO')
    print(f"🕷️  Logs will be saved to: {log_file}")

    if args.itemcount > 0:
        settings.set('CLOSESPIDER_ITEMCOUNT', args.itemcount)

    process = CrawlerProcess(settings)
    loader = SpiderLoader.from_settings(settings)

    # Spider arg parsing
    if args.spiders:
        spider_names = [name.strip() for name in args.spiders.split(',')]
        valid_spider_names = []
        for spider_name in spider_names:
            if spider_name not in loader.list():
                print(f"❌ Spider '{spider_name}' not found. Available spiders: {loader.list()}")
            else:
                valid_spider_names.append(spider_name)
    else:
        valid_spider_names = loader.list()
        print(f"🚀 No specific spiders provided. All available spiders will be run: {valid_spider_names}")
    
    # Loop through every spider in the project and schedule it
    for spider_name in valid_spider_names:
        print(f'Starting crawl for spider: {spider_name}')
        process.crawl(spider_name, **vars(args))

    process.start()
