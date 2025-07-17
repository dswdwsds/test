import os
import base64
import requests
import json

# إعدادات GitHub
access_token = os.getenv("ACCESS_TOKEN")
repo_name = "abdo12249/1"
remote_folder = "test1/episodes"
local_folder = "episodes"
update_json_path = "1/الجديد.json"
update_json_url = "https://abdo12249.github.io/1/test1/episodes"

# رؤوس الطلبات
headers = {
    "Authorization": f"token {access_token}",
    "Accept": "application/vnd.github.v3+json"
}

def get_file_sha(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["sha"]
    return None

def upload_file(repo, local_path, remote_path):
    with open(local_path, "rb") as file:
        content = base64.b64encode(file.read()).decode("utf-8")

    sha = get_file_sha(repo, remote_path)
    url = f"https://api.github.com/repos/{repo}/contents/{remote_path}"
    data = {
        "message": f"Upload {os.path.basename(local_path)}",
        "content": content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)
    return response.status_code in [200, 201]

def load_current_update_json():
    url = f"https://raw.githubusercontent.com/{repo_name}/main/{update_json_path}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return json.loads(response.text).get("animes", [])
        except:
            print("⚠️ فشل قراءة الجديد.json (تنسيق غير صحيح)")
            return []
    return []

def save_updated_json_file(anime_urls):
    unique_urls = list(sorted(set(anime_urls)))
    payload = {
        "animes": unique_urls
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    sha = get_file_sha(repo_name, update_json_path)
    url = f"https://api.github.com/repos/{repo_name}/contents/{update_json_path}"
    data = {
        "message": "تحديث ملف الجديد.json",
        "content": b64_content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print("📄 تم تعديل الجديد.json ✅")
    else:
        print(f"❌ فشل تحديث الجديد.json: {response.text}")

def upload_all_json_files():
    if not os.path.exists(local_folder):
        print("❌ المجلد المحلي episodes غير موجود.")
        return

    anime_urls = load_current_update_json()
    uploaded_count = 0

    for filename in os.listdir(local_folder):
        if filename.endswith(".json"):
            local_path = os.path.join(local_folder, filename)
            remote_path = f"{remote_folder}/{filename}"
            file_url = f"{update_json_url}/{filename}"

            if file_url in anime_urls:
                print(f"🔁 موجود مسبقًا: {filename}")
                continue

            uploaded = upload_file(repo_name, local_path, remote_path)
            if uploaded:
                uploaded_count += 1
                print(f"[{uploaded_count}] ✅ تم رفع: {remote_path}")
                anime_urls.append(file_url)
                save_updated_json_file(anime_urls)
            else:
                print(f"❌ فشل رفع: {remote_path}")

# تشغيل
upload_all_json_files()
