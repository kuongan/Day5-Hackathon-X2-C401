import json
import time
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "https://www.vinmec.com"
START_URL = "https://www.vinmec.com/vie/co-the-nguoi/"


def clean_text(value: str) -> str:
    return " ".join(value.split()) if value else ""


def parse_current_page(page_source: str, page_number: int) -> list[dict]:
    soup = BeautifulSoup(page_source, "html.parser")
    rows = []

    for anchor in soup.select("li a.name_drug"):
        title = clean_text(anchor.get_text())
        href = anchor.get("href", "")
        if not title or not href:
            continue

        rows.append(
            {
                "title": title,
                "url": urljoin(BASE_URL, href),
                "page": page_number,
            }
        )

    return rows


def get_active_page_number(driver: webdriver.Chrome) -> int | None:
    try:
        active = driver.find_element(By.CSS_SELECTOR, "div.paging a.item_paging.active")
        return int(active.text.strip())
    except Exception:
        return None


def click_next_page(driver: webdriver.Chrome, wait: WebDriverWait) -> bool:
    current_page = get_active_page_number(driver)
    if current_page is None:
        print("[WARN] Cannot detect current page, stop paging.")
        return False

    next_btn = None
    paging_items = driver.find_elements(By.CSS_SELECTOR, "div.paging a.item_paging")
    for item in paging_items:
        if item.text.strip() == ">":
            next_btn = item
            break

    if next_btn is None:
        print("[INFO] Next button not found, reached last page.")
        return False

    print(f"[INFO] Moving from page {current_page} to next page...")
    driver.execute_script("arguments[0].click();", next_btn)

    try:
        wait.until(lambda d: get_active_page_number(d) not in (None, current_page))
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li a.name_drug")))
        time.sleep(0.4)
        print("[INFO] Next page loaded.")
        return True
    except Exception:
        print("[WARN] Clicked next but page did not change in time.")
        return False


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(options=options)


def main() -> None:
    print(f"[START] Crawl Vinmec body articles from: {START_URL}")
    driver = build_driver()
    wait = WebDriverWait(driver, 20)
    seen_urls: set[str] = set()
    all_rows: list[dict] = []

    try:
        print("[INFO] Opening start page...")
        driver.get(START_URL)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li a.name_drug")))
        print("[INFO] First page loaded successfully.")

        while True:
            page_no = get_active_page_number(driver) or 1
            print(f"[INFO] Parsing page {page_no}...")
            rows = parse_current_page(driver.page_source, page_no)

            new_count = 0
            for row in rows:
                if row["url"] in seen_urls:
                    continue
                seen_urls.add(row["url"])
                all_rows.append(row)
                new_count += 1

            print(f"[INFO] Page {page_no}: +{new_count} new item(s), total={len(all_rows)}")

            if not click_next_page(driver, wait):
                break

    finally:
        print("[INFO] Closing browser...")
        driver.quit()

    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "data" / "vinmec_body_articles.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Writing output to: {output_path}")
    output_path.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[DONE] Saved {len(all_rows)} item(s) to {output_path}")


if __name__ == "__main__":
    main()
