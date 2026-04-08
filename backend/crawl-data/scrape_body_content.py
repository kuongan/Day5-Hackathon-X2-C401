import json
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.vinmec.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def clean_text(value: str) -> str:
    """Clean and normalize text."""
    return " ".join(value.split()) if value else ""


def scrape_article_content(url: str) -> Optional[dict]:
    """
    Scrape article content from a single URL.
    Returns dict with title, url, content, description, etc.
    """
    try:
        logger.info(f"Scraping: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None

    try:
        soup = BeautifulSoup(resp.text, "html.parser")

        # Vinmec body pages often use .title_drug_detail and .content_detail_drug.
        title = ""
        title_selectors = [
            "div.title_drug_detail",
            "h1.page-title",
            "h1",
            "meta[property='og:title']",
            "title",
        ]
        for selector in title_selectors:
            tag = soup.select_one(selector)
            if not tag:
                continue
            if tag.name == "meta":
                title = clean_text(tag.get("content", ""))
            else:
                title = clean_text(tag.get_text())
            if title:
                break

        # Prefer exact content blocks for this Vinmec section.
        content = ""
        structured_sections = []
        content_root = soup.select_one("div.content_detail_drug")
        if content_root:
            for bad_tag in content_root(["script", "style", "noscript"]):
                bad_tag.decompose()

            section_nodes = content_root.select("div.item_type_drug")
            if section_nodes:
                for section in section_nodes:
                    heading_tag = section.select_one("h2.title_type_drug")
                    heading = clean_text(heading_tag.get_text()) if heading_tag else ""

                    body_tag = section.select_one("div.content_type_drug")
                    body_text = clean_text(body_tag.get_text(" ")) if body_tag else ""
                    if not body_text:
                        continue

                    structured_sections.append(
                        {
                            "heading": heading,
                            "text": body_text,
                        }
                    )

                content = "\n\n".join(
                    f"{item['heading']}: {item['text']}" if item["heading"] else item["text"]
                    for item in structured_sections
                )

        # Fallback for other template variants.
        if not content:
            fallback = soup.select_one(
                "div.article-content, div.post-content, div.content, div.entry-content, "
                "div.body-content, div.main-content"
            )
            if fallback:
                for bad_tag in fallback(["script", "style", "noscript"]):
                    bad_tag.decompose()
                content = clean_text(fallback.get_text(" "))

        # Extract description/excerpt from meta or first paragraph
        desc = ""
        meta_desc = soup.select_one("meta[name='description']")
        if meta_desc:
            desc = clean_text(meta_desc.get("content", ""))
        if not desc:
            first_p = soup.select_one("div.content_detail_drug p, p")
            if first_p:
                desc = clean_text(first_p.get_text())

        # Extract category/tags if available
        breadcrumb = None
        breadcrumb_div = soup.select_one("div.bread-cump-main, nav.breadcrumb, div.breadcrumb")
        if breadcrumb_div:
            breadcrumb = clean_text(breadcrumb_div.get_text())

        article_data = {
            "title": title,
            "url": url,
            "description": desc,
            "content": content,
            "sections": structured_sections,
            "breadcrumb": breadcrumb,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        logger.info(
            "✓ Scraped: %s | content_len=%s | sections=%s",
            title[:80],
            len(content),
            len(structured_sections),
        )
        return article_data

    except Exception as e:
        logger.error(f"Error parsing {url}: {e}")
        return None


def main() -> None:
    logger.info("[START] Begin scraping article content")

    # Read input JSON
    project_root = Path(__file__).resolve().parents[2]
    input_path = project_root / "data" / "vinmec_body_articles.json"

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    logger.info(f"Reading articles list from: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        articles_list = json.load(f)

    logger.info(f"Found {len(articles_list)} articles to scrape")

    all_content = []
    success_count = 0
    error_count = 0

    for idx, article in enumerate(articles_list, 1):
        url = article.get("url")
        if not url:
            logger.warning(f"[{idx}/{len(articles_list)}] No URL found, skipping")
            continue

        logger.info(f"[{idx}/{len(articles_list)}] Processing...")
        content_data = scrape_article_content(url)

        if content_data:
            all_content.append(content_data)
            success_count += 1
        else:
            error_count += 1

        # Be gentle with server
        time.sleep(0.5)

    # Write output
    output_path = project_root / "data" / "vinmec_body_content.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Writing output to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_content, f, ensure_ascii=False, indent=2)

    logger.info(f"[DONE] Scraped {success_count} articles, {error_count} failed")
    logger.info(f"Total saved: {len(all_content)} to {output_path}")


if __name__ == "__main__":
    main()
