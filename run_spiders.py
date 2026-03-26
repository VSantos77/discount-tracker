from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.spiderloader import SpiderLoader
from scrapy import signals
from scrapy.signalmanager import dispatcher
import argparse
import os
import datetime

def execute_crawls(spiders='', itemcount=0, page_limit=0, dry_run='false'):
    """
    Main entry point for orchestrate.py to run spiders and get stats back.
    """
    spider_crawl_stats = {} # Changed to dict for easier lookup in orchestrate

    def spider_results(spider, reason):
        stats = spider.crawler.stats.get_stats()
        # Store just the relevant bits for the monitor
        spider_crawl_stats[spider.name] = {
            'start_time': stats.get('start_time', ''),
            'finish_time': stats.get('finish_time', ''),
            "count": stats.get('item_scraped_count', 0),
            "reason": reason,
            "runtime": stats.get('elapsed_time_seconds', 0)
        }
        print(f"✅ {spider.name} finished: {spider_crawl_stats[spider.name]['count']} items.")

    settings = get_project_settings()

    # --- Configure Logging ---
    log_dir = "logs/scrapy"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    settings.set('LOG_FILE', os.path.join(log_dir, f"scrapy_{timestamp}.log"))
    settings.set('LOG_LEVEL', 'INFO')

    if itemcount > 0:
        settings.set('CLOSESPIDER_ITEMCOUNT', itemcount)

    process = CrawlerProcess(settings)
    loader = SpiderLoader.from_settings(settings)
    
    # Logic to filter spiders
    if spiders:
        spider_names = [name.strip() for name in spiders.split(',')]
        valid_spider_names = [n for n in spider_names if n in loader.list()]
    else:
        valid_spider_names = loader.list()
    
    # Schedule crawls
    for spider_name in valid_spider_names:
        # Pass parameters directly to the spider
        process.crawl(spider_name, itemcount=itemcount, page_limit=page_limit, dry_run=dry_run)

    dispatcher.connect(spider_results, signal=signals.spider_closed)

    process.start() # Blocks until all spiders are done
    return spider_crawl_stats

# This allows you to still run it manually from the terminal
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Scrapy Spiders")
    parser.add_argument("--spiders", type=str, default='')
    parser.add_argument("--itemcount", type=int, default=0)
    args = parser.parse_args()
    
    # Call the function with command line args
    results = execute_crawls(spiders=args.spiders, itemcount=args.itemcount)
    print("Final Results:", results)