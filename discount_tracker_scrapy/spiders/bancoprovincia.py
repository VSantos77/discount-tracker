import re
import scrapy


class BancoprovinciaspiderSpider(scrapy.Spider):
    name = "bancoprovincia"
    allowed_domains = ["www.bancoprovincia.com.ar"]

    base_url = "https://www.bancoprovincia.com.ar/mvc/Beneficios?"

    _DETAIL_RE = re.compile(r"^/mvc/banca-personal/")
    _INDEX_RE = re.compile(r"/Beneficios/SearchBeneficio")
    _PCT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
    _NUM_RE = re.compile(r"^\d+$")

    def start_requests(self):
        yield scrapy.Request(url=self.base_url, callback=self.parse_listing)

    # ------------------------------------------------------------------
    # Listing page  →  detail pages  +  index (sub-category) pages
    # ------------------------------------------------------------------
    def parse_listing(self, response):
        seen = set()
        yield from self._dispatch_links(response, seen, follow_index=True)

    # ------------------------------------------------------------------
    # Sub-category index page  →  detail pages only
    # ------------------------------------------------------------------
    def parse_index(self, response):
        seen = set()
        yield from self._dispatch_links(response, seen, follow_index=False)

    # ------------------------------------------------------------------
    # Detail page  →  one item per discount block
    # ------------------------------------------------------------------
    def parse_detail(self, response):
        slug = response.meta["slug"]
        blocks = list(self._extract_blocks(response))
        n = len(blocks)
        for i, block in enumerate(blocks):
            source_id = slug if n == 1 else f"{slug}_{i}"
            yield {
                "source_id": source_id,
                "category_slug": slug,
                "discount_url": response.url,
                **block,
            }
            self.crawler.stats.inc_value("custom/items_scraped/bancoprovincia")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _dispatch_links(self, response, seen, follow_index):
        """Follow banca-personal hrefs and, optionally, SearchBeneficio hrefs."""
        for href in response.css("div.w3-col a::attr(href)").getall():
            if href in seen:
                continue
            seen.add(href)
            if self._DETAIL_RE.match(href):
                slug = href.rstrip("/").split("/")[-1]
                yield response.follow(
                    href,
                    callback=self.parse_detail,
                    meta={"slug": slug},
                )
            elif follow_index and self._INDEX_RE.search(href):
                yield response.follow(href, callback=self.parse_index)

    def _extract_blocks(self, response):
        """
        Yield one dict per discount block found on the detail page.

        Block identification strategy:
        - Each block has an "En ..." merchant heading (h2/h3/p/div).
        - For each such heading, walk backwards via XPath preceding:: axes to
          find the associated discount rate ("de ahorro") and installments
          ("cuotas sin interés") elements.

        NOTE: These XPath selectors match on text content and are therefore
        layout-agnostic. If the site structure changes, only the element
        type list (h2|h3|p|div) may need adjustment.
        """
        # Page-level legal text (shared across all blocks)
        legal_parts = response.xpath(
            '//*[contains(., "TASA NOMINAL ANUAL") or contains(., "BANCO DE LA PROVINCIA")]'
            "[not(ancestor::header) and not(ancestor::footer) and not(ancestor::nav)]"
            "/descendant-or-self::text()"
        ).getall()
        legal_text = " ".join(t.strip() for t in legal_parts if t.strip()) or None

        # Page-level date / validity heading (outermost h1 outside chrome)
        page_date = response.xpath(
            "//h1[not(ancestor::header) and not(ancestor::footer) and not(ancestor::nav)][1]/text()"
        ).get("").strip() or None

        # Merchant headings anchor each block — find them in document order
        merchant_nodes = response.xpath(
            "//*[self::h2 or self::h3 or self::p or self::div]"
            "[starts-with(normalize-space(.), 'En ')]"
            "[not(ancestor::header) and not(ancestor::footer) and not(ancestor::nav)]"
        )

        if not merchant_nodes:
            self.logger.warning(
                "No merchant headings found on %s — page structure may have changed",
                response.url,
            )
            return

        for merchant_node in merchant_nodes:
            merchant_text = merchant_node.xpath("normalize-space(.)").get("").strip() or None

            # --- Discount rate ---
            # Nearest preceding "de ahorro" element, then its preceding sibling's text
            discount_rate = None
            rate_sib_text = merchant_node.xpath(
                "preceding::*[normalize-space(text())='de ahorro'][1]"
                "/preceding-sibling::*[1]/descendant-or-self::text()"
            ).get("").strip()
            if not rate_sib_text:
                # Text node directly before the "de ahorro" element
                rate_sib_text = merchant_node.xpath(
                    "preceding::*[normalize-space(text())='de ahorro'][1]"
                    "/preceding::text()[1]"
                ).get("").strip()
            pct_match = self._PCT_RE.search(rate_sib_text)
            if pct_match:
                try:
                    discount_rate = int(
                        float(pct_match.group(1).replace(",", "."))
                    )
                except ValueError:
                    pass

            # --- Installments ---
            installments = None
            cuotas_sib_text = merchant_node.xpath(
                "preceding::*[contains(normalize-space(text()), 'cuotas sin interés')][1]"
                "/preceding-sibling::*[1]/descendant-or-self::text()"
            ).get("").strip()
            if not cuotas_sib_text:
                cuotas_sib_text = merchant_node.xpath(
                    "preceding::*[contains(normalize-space(text()), 'cuotas sin interés')][1]"
                    "/preceding::text()[1]"
                ).get("").strip()
            if self._NUM_RE.match(cuotas_sib_text):
                try:
                    installments = int(cuotas_sib_text)
                except ValueError:
                    pass

            # --- Date / validity text ---
            # Nearest preceding h1 (outside chrome) or the page-level date
            block_date = (
                merchant_node.xpath(
                    "preceding::h1"
                    "[not(ancestor::header) and not(ancestor::footer) and not(ancestor::nav)]"
                    "[1]/text()"
                ).get("").strip()
                or page_date
            )

            # --- Description ---
            # Up to 3 sibling paragraphs after the merchant heading,
            # before legal text starts
            desc_parts = merchant_node.xpath(
                "following-sibling::p"
                "[not(contains(., 'TASA NOMINAL')) and not(contains(., 'BANCO DE LA PROVINCIA'))]"
                "[position() <= 3]"
                "/descendant-or-self::text()"
            ).getall()
            description = " ".join(t.strip() for t in desc_parts if t.strip()) or None

            yield {
                "date_text": block_date,
                "discount_rate": discount_rate,
                "installments": installments,
                "merchant_text": merchant_text,
                "description": description,
                "legal_text": legal_text,
            }
