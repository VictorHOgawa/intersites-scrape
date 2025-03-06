from datetime import date, datetime, timedelta
from scrapy.signals import spider_closed
from ...items import articleItem
from scrapy.http import Request
from bs4 import BeautifulSoup
import requests
import locale
import scrapy
import json
import os

locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

now = datetime.now()
timestamp = datetime.timestamp(now)

today = date.today().strftime("%d/%m/%Y")
today = datetime.strptime(today, "%d/%m/%Y")

search_limit = date.today() - timedelta(days=1)
search_limit = datetime.strptime(search_limit.strftime("%d/%m/%Y"), "%d/%m/%Y")

with open("/home/scrapeops/intersites-scrape/Spiders/CSS_Selectors/OGlobo.json") as f:
    search_terms = json.load(f)

site_id = "3d6db083-ef6f-44c4-b249-d0882a54c28c"

class OGloboSpider(scrapy.Spider):
    name = "OGlobo"
    allowed_domains = ["oglobo.globo.com"]
    start_urls = ["https://oglobo.globo.com/politica/index/feed/pagina-1.ghtml"]
    INCREMENT = 1
    data = []
    article_count = 0  # Added counter

    MAX_ARTICLES = 10  # Limit of articles per website

    def parse(self, response):
        if self.article_count >= self.MAX_ARTICLES:
            return  # Stop parsing further if limit is reached

        for article in response.css(search_terms['article']):
            if self.article_count >= self.MAX_ARTICLES:
                break  # Stop iterating if limit is reached

            link = article.css(search_terms['link']).get()
            yield Request(link, callback=self.parse_article, priority=1)

        self.INCREMENT += 1
        next_page = f"https://oglobo.globo.com/politica/index/feed/pagina-{self.INCREMENT}.ghtml"

        if self.article_count < self.MAX_ARTICLES:
            yield response.follow(next_page, callback=self.parse)
        else:
            print("Reached article limit, stopping scraper.")

    def parse_article(self, response):
        if self.article_count >= self.MAX_ARTICLES:
            return  # Stop parsing articles if limit is reached

        updated = response.css(search_terms['updated']).get()
        updated = updated.split("T")[0]
        updated = datetime.strptime(updated, "%Y-%m-%d")
        title = response.css(search_terms['title']).get()
        content = response.css(search_terms['content']).getall()
        content = BeautifulSoup(" ".join(content), "html.parser").text
        content = content.replace("\n", " ")
        if search_limit <= updated <= today:
            item = articleItem(
                updated=updated,
                title=title,
                content=content,
                link=response.url,
            )
            yield item
            self.data.append(item)
            self.article_count += 1  # Increment article count

        if self.article_count >= self.MAX_ARTICLES:
            self.crawler.engine.close_spider(self, "Reached article limit")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(OGloboSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.upload_data, signal=spider_closed)
        return spider

    def upload_data(self, spider):
        file_path = f"/home/scrapeops/intersites-scrape/Spiders/Results/{self.name}_{timestamp}.json"
        if not os.path.isfile(file_path):
            with open(file_path, "w") as f:
                json.dump([], f)

        with open(file_path, "r") as f:
            file_data = json.load(f)
            
        data_dicts = [item.to_dict() for item in self.data]

        file_data.extend(data_dicts)

        with open(file_path, "w") as f:
            json.dump(file_data, f, ensure_ascii=False)
            
        upload = requests.post(f"{os.environ['API_URL']}{site_id}", json={"news": file_data})
        print("upload: ", upload)