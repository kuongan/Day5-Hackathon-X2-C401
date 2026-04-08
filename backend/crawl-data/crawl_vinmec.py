# /home/duckduck/dev/work/VinUni/Day06-AI-Product-Hackathon/crawl_vinmec.py
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.vinmec.com"
URL_TMPL = "https://www.vinmec.com/vie/chuyen-gia-y-te/page_{i}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VinmecCrawler/1.0; +https://example.com/bot)"
}

def clean_text(s):
    return " ".join(s.split()) if s else ""

def crawl_page(i):
    url = URL_TMPL.format(i=i)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    section = soup.select_one("section.doctor_cate")
    if not section:
        return []

    items = []
    for li in section.select("ul#doctor-list > li.flex"):
        name_tag = li.select_one("a.list_name_doctor")
        profile_tag = li.select_one("a.list_name_doctor")
        img_tag = li.select_one("a.thumbblock img")
        degree_tag = li.select_one("div.icon_list_doctor.degree")
        special_tag = li.select_one("div.icon_list_doctor.special")
        hospital_tag = li.select_one("div.icon_list_doctor.hospital a")

        name = clean_text(name_tag.get_text()) if name_tag else ""
        profile_url = urljoin(BASE, profile_tag["href"]) if profile_tag and profile_tag.has_attr("href") else ""
        img_url = urljoin(BASE, img_tag["src"]) if img_tag and img_tag.has_attr("src") else ""
        degree = clean_text(degree_tag.get_text()) if degree_tag else ""
        special = clean_text(special_tag.get_text()) if special_tag else ""
        hospital = clean_text(hospital_tag.get_text()) if hospital_tag else ""
        hospital_url = urljoin(BASE, hospital_tag["href"]) if hospital_tag and hospital_tag.has_attr("href") else ""

        items.append({
            "name": name,
            "profile_url": profile_url,
            "img_url": img_url,
            "degree": degree,
            "special": special,
            "hospital": hospital,
            "hospital_url": hospital_url,
            "page": i,
        })
    return items

def main():
    all_rows = []
    for i in range(1, 21):
        rows = crawl_page(i)
        all_rows.extend(rows)
        time.sleep(0.8)  # nhẹ nhàng với server

    out_path = "/home/duckduck/dev/work/VinUni/Day5-Hackathon-X2-C401/data/vinmec_doctors.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_rows)} rows to {out_path}")

if __name__ == "__main__":
    main()
