import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys

BASE_URL = "https://www.vinmec.com"
LIST_URL = f"{BASE_URL}/vie/thuoc/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9",
}


def get_all_slugs():
    """Extract all medicine name+slug pairs from the JS db[] array in the page."""
    print("Fetching medicine list...")
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    pattern = r'var db\s*=\s*(\[.*?\]);'
    match = re.search(pattern, resp.text, re.DOTALL)
    if not match:
        print("ERROR: Could not find db[] array in page source.")
        sys.exit(1)

    raw = match.group(1)
    raw = re.sub(
        r'`\s*(.*?)\s*`',
        lambda m: '"' + m.group(1).replace('\n', ' ').replace('"', '\\"') + '"',
        raw, flags=re.DOTALL
    )
    raw = re.sub(r',\s*([}\]])', r'\1', raw)

    medicines = json.loads(raw)
    print(f"Found {len(medicines)} medicines.")
    return medicines


def scrape_medicine(name: str, slug: str) -> dict:
    """Fetch a single medicine page and dynamically extract all sections."""
    url = f"{BASE_URL}/vie/thuoc/{slug}"
    result = {
        "Ten": name.strip(),
        "URL": url,
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 404:
            result["error"] = "404 Not Found"
            return result
        resp.raise_for_status()
    except Exception as e:
        result["error"] = str(e)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # Step 1: Read list_type_detail_sick to get all section labels + their tab IDs
    # e.g. <a href="#tab-13927"> Dang bao che - biet duoc</a>
    tag_ul = soup.find("ul", class_="list_type_detail_sick")
    if not tag_ul:
        result["error"] = "list_type_detail_sick not found"
        return result

    nav_sections = []
    for a in tag_ul.find_all("a", href=True):
        label = a.get_text(strip=True)
        tab_id = a["href"].lstrip("#")   # "tab-13927"
        if label and tab_id:
            nav_sections.append((label, tab_id))

    # "Tag" = list of all available section names for this drug
    result["Tag"] = ", ".join(label for label, _ in nav_sections)

    # Step 2: For each (label, tab_id), find the div and extract body text
    for label, tab_id in nav_sections:
        tab_div = soup.find(id=tab_id)
        if not tab_div:
            result[label] = None
            continue

        body = tab_div.find("div", class_="body")
        if body:
            result[label] = body.get_text(separator="\n", strip=True)
        else:
            h2 = tab_div.find("h2")
            if h2:
                h2.decompose()
            text = tab_div.get_text(separator="\n", strip=True)
            result[label] = text if text else None

    return result


def main():
    medicines = get_all_slugs()

    seen = set()
    unique = []
    for m in medicines:
        if m["slug"] not in seen:
            seen.add(m["slug"])
            unique.append(m)
    print(f"Unique medicines after dedup: {len(unique)}")

    results = []
    for i, m in enumerate(unique, 1):
        name = m["name"].strip()
        slug = m["slug"].strip()
        print(f"[{i}/{len(unique)}] {name} -> {slug}")

        data = scrape_medicine(name, slug)
        results.append(data)

        time.sleep(1)

        if i % 50 == 0:
            with open("medicines_checkpoint.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"  Checkpoint saved ({i} items)")

    output_file = "vinmec_medicines.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(results)} medicines saved to {output_file}")


if __name__ == "__main__":
    main()