import cloudscraper
from lxml import html
import re
import os
import json
from datetime import datetime
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_episode_data(ep_link, scraper, safe_title, anime_title, existing_titles):
    try:
        print(f"🔗 معالجة الحلقة: {ep_link}")
        ep_resp = scraper.get(ep_link)
        ep_resp.raise_for_status()
        ep_tree = html.fromstring(ep_resp.content)

        # العنوان الكامل من الصفحة
        title_elements = ep_tree.xpath('/html/body/div[3]/div/h3/text()')
        full_title = title_elements[0].strip() if title_elements else "حلقة غير معروفة"

        # استخراج نوع الحلقة ورقمها
        match = re.search(r"(الحلقة(?:\s+الخاصة)?|الفيلم|فيلم)\s*(\d+)", full_title, re.IGNORECASE)
        if match:
            ep_type = match.group(1).strip()
            episode_number = int(match.group(2))
            episode_title = f"{ep_type} {episode_number}"
        else:
            episode_number = None
            episode_title = full_title

        if episode_title in existing_titles:
            print(f"✅ الحلقة '{episode_title}' موجودة مسبقًا، تخطي.")
            return None

        # السيرفرات
        servers = []
        server_lis = ep_tree.xpath('//*[@id="episode-servers"]/li')
        for li in server_lis:
            try:
                server_name = li.xpath('.//a/text()')[0].strip()
                url = li.xpath('.//a/@data-ep-url')
                url = url[0] if url else li.xpath('.//a/@href')[0]
                if url.startswith("//"):
                    url = "https:" + url
                servers.append({
                    "serverName": server_name,
                    "url": url
                })
            except Exception:
                continue
        episode_number = int(re.search(r'\d+', episode_title).group()) if re.search(r'\d+', episode_title) else None

        # تجهيز البيانات
        ep_data = {
            "number": episode_number,
            "title": episode_title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "link": f"https://abdo12249.github.io/1/test1/المشاهده.html?id={safe_title}&episode={episode_number}",
            "image": f"https://abdo12249.github.io/1/images/{safe_title}.webp",
            "servers": servers
        }


        print(f"➕ تم استخراج: {episode_title}")
        return ep_data

    except Exception as e:
        print(f"❌ فشل استخراج الحلقة من {ep_link} بسبب: {e}")
        return None


def extract_base_title(raw_title):
    # إزالة " - الحلقة 1" أو " - فيلم" من نهاية العنوان
    return re.sub(r'\s*[-–]\s*(الحلقة|الفيلم|فيلم)\s*\d*$', '', raw_title.strip(), flags=re.IGNORECASE)


def scrape_single_anime(base_url):
    print(f"\n🔄 جاري استخراج أنمي من الرابط: {base_url}")
    scraper = cloudscraper.create_scraper()

    try:
        response = scraper.get(base_url)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ خطأ في جلب الصفحة الرئيسية: {e}")
        return

    tree = html.fromstring(response.content)
    episode_links = tree.xpath('//*[@id="ULEpisodesList"]/li/a/@href')
    if not episode_links:
        print("⚠️ لم يتم العثور على روابط الحلقات.")
        return

    # استخراج عنوان الأنمي
    title_elements = tree.xpath('/html/body/div[3]/div/h3/text()')
    raw_title = title_elements[0].strip() if title_elements else "عنوان غير معروف"
    anime_title = extract_base_title(raw_title)

    # إنشاء اسم ملف آمن
    cleaned_title = re.sub(r"مدبلجة\s*للعربية", "", anime_title, flags=re.IGNORECASE).strip()
    safe_title = re.sub(r'[\\/:*?"<>|]', "", cleaned_title)  # إزالة الرموز المحظورة في أسماء الملفات
    safe_title = safe_title.replace(" ", "-").lower()        # استبدال المسافات بشرطات وتحويل إلى حروف صغيرة
    safe_title = re.sub(r'[–—]', '-', safe_title)            # استبدال الشرطة الطويلة بشرطة عادية
    safe_title = re.sub(r'-?(الحلقة|فيلم|اوفا)-?\d*', '', safe_title)  # إزالة "الحلقة-1" أو "فيلم-1" أو "اوفا-3"
    safe_title = re.sub(r'-+', '-', safe_title).strip('-')   # تنظيف الشرطات المكررة وإزالة من البداية/النهاية



    # حفظ باسم ثابت
    filename = f"{safe_title}.json"
    os.makedirs("episodes", exist_ok=True)
    full_path = os.path.join("episodes", filename)

    all_episodes = []
    existing_titles = set()

    if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "episodes" in data:
                    all_episodes = data["episodes"]
                    existing_titles = {ep["title"] for ep in all_episodes}
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=30) as executor:
        future_to_link = {
            executor.submit(
                extract_episode_data,
                link,
                scraper,
                safe_title,
                anime_title,
                existing_titles
            ): link
            for link in episode_links
        }

        for future in as_completed(future_to_link):
            episode = future.result()
            if episode:
                all_episodes.append(episode)

    # ترتيب حسب الرقم إذا موجود
    def ep_sort(ep):
        return ep["number"] if isinstance(ep.get("number"), int) else 9999

    all_episodes.sort(key=ep_sort)

    result = {
        "animeTitle": anime_title,
        "episodes": all_episodes
    }

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ تم حفظ كل الحلقات في: {filename}")


def scrape_from_json_file(json_path):
    if not os.path.exists(json_path):
        print(f"❌ الملف غير موجود: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            anime_links = json.load(f)
        except Exception as e:
            print(f"❌ خطأ في قراءة ملف JSON: {e}")
            return

    if not isinstance(anime_links, list):
        print("❌ ملف JSON يجب أن يحتوي على قائمة من روابط الأنميات.")
        return

    print(f"🔄 بدء استخراج الحلقات من {len(anime_links)} أنمي...")
    for i, link in enumerate(anime_links, start=1):
        print(f"\n🌟 أنمي رقم {i}: {link}")
        scrape_single_anime(link)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❗ الرجاء تمرير مسار ملف JSON يحتوي على روابط الأنميات.")
        print("مثال:\npython script.py animes.json")
        sys.exit(1)

    json_file_path = sys.argv[1]
    scrape_from_json_file(json_file_path)
