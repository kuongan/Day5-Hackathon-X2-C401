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


def extract_item_detail(item_soup):
    title_el = item_soup.select_one("h2.title_detail_sick")
    title = clean_text(title_el.get_text()) if title_el else ""

    texts = []
    body = item_soup.select_one(".body.collapsible-target")
    if body:
        seen = set()
        for el in body.find_all(["p", "h3", "li"], recursive=True):
            # If h3/li are wrapped inside a <p>, the <p> will capture them.
            if el.name in {"h3", "li"} and el.find_parent("p"):
                continue
            txt = clean_text(el.get_text(separator=" ", strip=True))
            if txt:
                if txt in seen:
                    continue
                seen.add(txt)
                texts.append(txt)

    return {"title": title, "content": texts}


def crawl_detail(url):
    logger.info("Fetch detail %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    section = soup.select_one("section.detail_sick.mb50.mt40")
    if not section:
        # Fallback in case classes change or are partially missing
        section = soup.select_one("section.detail_sick")
    if not section:
        return []

    details = []
    for item in section.select("div.content_detail_sick div.item_detial_sick"):
        details.append(extract_item_detail(item))
    return details


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
            item["detail_sections"] = crawl_detail(item["url"])
            logger.info("Result %d/%d: %s | %s", i, len(results), item.get("title"), item.get("url"))
            for sec in item["detail_sections"]:
                logger.info("  Section: %s", sec.get("title"))
                for line in sec.get("content", []):
                    logger.info("    %s", line)
        except requests.RequestException:
            item["detail_sections"] = []
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
