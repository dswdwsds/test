import cloudscraper
from bs4 import BeautifulSoup
import time
import json
import os
from urllib.parse import urljoin
import concurrent.futures

# ===== إعداد CloudScraper =====
scraper = cloudscraper.create_scraper()

# ===== جمع روابط الأنمي =====
def collect_anime_links(start_url):
    anime_links = []

    # تحميل روابط محفوظة سابقًا (إن وُجدت)
    if os.path.exists("anime_links_all_pages.json"):
        with open("anime_links_all_pages.json", "r", encoding="utf-8") as f:
            anime_links = json.load(f)

    seen = set(anime_links)
    page_number = 1

    while True:
        print(f"📄 استخراج الصفحة {page_number}...")

        url = f"{start_url}page/{page_number}/"
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"⚠️ لم يتم الوصول للصفحة {page_number}. انتهاء التصفح.")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("div.anime-card-container h3 a")
        if not cards:
            print("✅ لا توجد صفحات إضافية.")
            break

        new_found = 0
        for card in cards:
            link = card.get("href", "").strip()
            if link and link not in seen:
                seen.add(link)
                anime_links.append(link)
                new_found += 1

                # حفظ فوري لكل رابط جديد
                with open("anime_links_all_pages.json", "w", encoding="utf-8") as f:
                    json.dump(anime_links, f, ensure_ascii=False, indent=2)

        print(f"➕ تم إضافة {new_found} روابط جديدة")
        page_number += 1
        time.sleep(1)

    anime_links = list(dict.fromkeys(anime_links))

    with open("anime_links.json", "w", encoding="utf-8") as f:
        json.dump(anime_links, f, ensure_ascii=False, indent=2)

    return anime_links

# ===== استخراج أول حلقة من كل أنمي =====
def extract_first_episode(anime_url, already_done):
    if anime_url in already_done:
        return None

    try:
        response = scraper.get(anime_url)
        soup = BeautifulSoup(response.text, "html.parser")

        ep_link = soup.select_one('#DivEpisodesList div a')
        if ep_link:
            link = ep_link.get("href", "").strip()
            print(f"✅ {link}")
            return link
        else:
            print(f"❌ لم يتم العثور على رابط الحلقة في: {anime_url}")
            return None
    except Exception as e:
        print(f"⚠️ خطأ في {anime_url}: {e}")
        return None

# ===== البرنامج الرئيسي =====
if __name__ == "__main__":
    start_url = "https://4y.qsybd.shop/قائمة-الانمي/"

    anime_links = collect_anime_links(start_url)

    # تحميل روابط الحلقات المحفوظة مسبقًا
    if os.path.exists("first_episodes_only.json"):
        with open("first_episodes_only.json", "r", encoding="utf-8") as f:
            already_done_links = json.load(f)
    else:
        already_done_links = []

    print(f"🔄 سيتم تخطي {len(already_done_links)} حلقة محفوظة مسبقًا.\n")

    # ✅ تنفيذ المهام على دفعات 10 باستخدام ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(extract_first_episode, url, already_done_links) for url in anime_links]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result and result not in already_done_links:
                already_done_links.append(result)

                # حفظ فوري بعد كل حلقة جديدة
                with open("first_episodes_only.json", "w", encoding="utf-8") as f:
                    json.dump(already_done_links, f, ensure_ascii=False, indent=2)

    print(f"\n✅ تم استخراج {len(already_done_links)} روابط حلقات أولى.")
