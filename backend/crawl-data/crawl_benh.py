import json
import logging
import string
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE = "https://www.vinmec.com"
URL_TMPL = "https://www.vinmec.com/vie/tra-cuu-benh/{char}/page_{i}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VinmecCrawler/1.0; +https://example.com/bot)"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def clean_text(s):
    return " ".join(s.split()) if s else ""


def get_max_page(soup):
    paging = soup.select_one("div.paging")
    if not paging:
        return 1
    pages = []
    for a in paging.select("a.page_button"):
        txt = clean_text(a.get_text())
        if txt.isdigit():
            pages.append(int(txt))
    return max(pages) if pages else 1


def crawl_page(char, page):
    url = URL_TMPL.format(char=char, i=page)
    logger.info("Fetch list page %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for a in soup.select("ul.list_result_AZ li a"):
        title = clean_text(a.get_text())
        href = a.get("href", "").strip()
        if not title or not href:
            continue
        items.append(
            {
                "char": char,
                "page": page,
                "title": title,
                "url": urljoin(BASE, href),
            }
        )
    return soup, items


def crawl_detail(url):
    logger.info("Fetch detail %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    section = soup.select_one("section.detail_sick.mb50.mt40")
    if not section:
        # Fallback in case classes change or are partially missing
        section = soup.select_one("section.detail_sick")
    return str(section) if section else ""


def crawl_char(char):
    all_items = []
    logger.info("Crawl char %s", char)
    soup, items = crawl_page(char, 1)
    all_items.extend(items)
    max_page = get_max_page(soup)
    logger.info("Char %s has %d pages", char, max_page)
    time.sleep(0.6)
    for p in range(2, max_page + 1):
        _, items = crawl_page(char, p)
        all_items.extend(items)
        time.sleep(0.6)
    return all_items


def main():
    results = []
    for ch in string.ascii_lowercase:
        results.extend(crawl_char(ch))

    # Crawl each disease detail page to extract the section HTML
    for i, item in enumerate(results, 1):
        try:
            item["detail_section_html"] = crawl_detail(item["url"])
        except requests.RequestException:
            item["detail_section_html"] = ""
            logger.warning("Failed detail %s", item["url"])
        time.sleep(0.6)
        if i % 50 == 0:
            logger.info("Detail progress %d/%d", i, len(results))

    out_path = "/home/duckduck/dev/work/VinUni/Day5-Hackathon-X2-C401/backend/vinmec_benh.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d rows to %s", len(results), out_path)


if __name__ == "__main__":
    main()
