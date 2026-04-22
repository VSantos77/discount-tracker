import scrapy


class CuentaDNISpider(scrapy.Spider):
    name = "cuentadni"
    allowed_domains = ["www.bancoprovincia.com.ar"]

    base_url = "https://www.bancoprovincia.com.ar/cuentadni/contenidos/cdniBeneficios/"
    detail_url = "https://www.bancoprovincia.com.ar/cuentadni/Home/GetBeneficioData2?idBeneficio={}"

    def start_requests(self):
        yield scrapy.Request(url=self.base_url, callback=self.parse)

    def parse(self, response):
        for div in response.css("div.callModalCDNI[id]"):
            raw_id = div.attrib["id"]
            numeric_id = raw_id.split("-")[-1]
            if not numeric_id.isdigit():
                self.logger.warning(f"Skipping non-numeric id fragment: {raw_id!r}")
                continue
            yield scrapy.Request(
                url=self.detail_url.format(numeric_id),
                callback=self.parse_detail,
                meta={"source_id": int(numeric_id)},
            )

    def parse_detail(self, response):
        data = response.json()
        if not data.get("Success"):
            self.logger.warning(
                f"API returned Success=false for id={response.meta['source_id']}"
            )
            return
        yield {
            "source_id": response.meta["source_id"],
            **data,
        }
        self.crawler.stats.inc_value("custom/items_scraped/cuentadni")
