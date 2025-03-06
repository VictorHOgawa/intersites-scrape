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

with open("/home/scrapeops/intersites-scrape/Spiders/CSS_Selectors/Brasil247.json") as f:
    search_terms = json.load(f)

main_url = "https://www.brasil247.com/ultimas-noticias/page/"

site_id = "99dae328-7650-423c-85a9-e5bf5dfc921d"

class Brasil247Spider(scrapy.Spider):
    name = "Brasil247"
    allowed_domains = ["brasil247.com"]
    start_urls = ["https://www.brasil247.com/ultimas-noticias/page/1"]
    INCREMENT = 1
    data = []

    def parse(self, response):
        for article in response.css(search_terms['article']):
            link = article.css(search_terms['link']).get()
            yield Request(f"https://www.brasil247.com{link}", callback=self.parse_article, priority=1)
        self.INCREMENT += 1
        next_page = f"{main_url}{self.INCREMENT}"
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)
        else:
            print("NÃO TEM NEXT BUTTON")
            
    def parse_article(self, response):
        updated = response.css(search_terms['updated']).get()
        updated = updated.split("T")[0]
        updated = updated[:10]
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
        else: 
            self.crawler.engine.stop()
            self.upload_data(self)
            
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(Brasil247Spider, cls).from_crawler(crawler, *args, **kwargs)
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