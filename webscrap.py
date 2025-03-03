import requests
import json
import time
import os
import base64
import csv
import re

# =============================================================================
# GitHub API erişimi için token ayarlanıyor.
# Token'ınızı GITHUB_TOKEN ortam değişkeni üzerinden veya doğrudan aşağıdaki değere ekleyebilirsiniz.
# =============================================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "Github-Token")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# =============================================================================
# search_repositories: GitHub'da verilen query ile repository araması yapar.
# Parametreler:
#   - query: Aranacak anahtar kelime (örneğin "flutter")
#   - per_page: Sayfa başına çekilecek repo sayısı
#   - page: Kaçıncı sayfayı çekmek istediğimiz
# Dönen JSON, arama sonuçlarını içerir.
# =============================================================================
def search_repositories(query, per_page=30, page=1):
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "per_page": per_page, "page": page}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Repository arama hatası ({response.status_code}): {response.text}")
        return None

# =============================================================================
# get_repo_tree: Belirtilen repository'nin tüm dosya ağacını (recursive) çeker.
# Parametreler:
#   - owner: Repository sahibi
#   - repo: Repository adı
#   - branch: İncelenecek branch (varsayılan "master")
# Dönen JSON, repository içindeki tüm dosyaların listesini içerir.
# =============================================================================
def get_repo_tree(owner, repo, branch="master"):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"{owner}/{repo} için tree çekme hatası ({response.status_code}): {response.text}")
        return None

# =============================================================================
# get_file_content: Belirtilen repository içindeki dosyanın içeriğini çeker.
# GitHub API, dosya içeriğini base64 ile kodlanmış olarak döner; bu nedenle decode işlemi yapıyoruz.
# Parametreler:
#   - owner: Repository sahibi
#   - repo: Repository adı
#   - file_path: Dosyanın repository içindeki yolu (örn: "lib/main.dart")
# Dönen değer, dosyanın decode edilmiş içeriğidir.
# =============================================================================
def get_file_content(owner, repo, file_path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        content_json = response.json()
        if "content" in content_json and content_json.get("encoding") == "base64":
            try:
                content = base64.b64decode(content_json["content"]).decode('utf-8', errors='replace')
                return content
            except Exception as e:
                print(f"Decode hatası: {e}")
                return None
        else:
            return None
    else:
        print(f"{owner}/{repo} - {file_path} dosyası çekilemedi ({response.status_code}): {response.text}")
        return None

# =============================================================================
# remove_comments: Kod içeriğindeki tek satır (//) ve çok satırlı (/* ... */) yorumları kaldırır.
# =============================================================================
def remove_comments(code):
    # Çok satırlı yorumları kaldır
    code_no_multiline = re.sub(r'/\*[\s\S]*?\*/', '', code)
    # Tek satırlı yorumları kaldır
    code_no_single = re.sub(r'//.*', '', code_no_multiline)
    # Boş satırları ve gereksiz boşlukları temizle
    cleaned_code = "\n".join([line.rstrip() for line in code_no_single.splitlines() if line.strip() != ""])
    return cleaned_code

# =============================================================================
# main: Fine-tuning veri seti oluşturma sürecini yönetir.
#
# Adımlar:
#   1. "flutter" query'siyle repo araması yapılır.
#   2. Her repo için repository bilgileri (sahibi, adı, branch, açıklaması) alınır.
#   3. Repository'nin dosya ağacı çekilir ve .dart uzantılı dosyalar hedeflenir.
#   4. Her dosyanın içeriği çekilir, yorumlar kaldırılır ve prompt–completion formatındaki veri
#      tek bir "text" sütununda birleştirilir.
#   5. Her kayıt CSV dosyasına "text" sütunu altında yazılır.
# =============================================================================
def main():
    query = "flutter"      # Aranacak anahtar kelime
    per_page = 10          # Demo amaçlı, sayfa başına 10 repo çekiliyor (gerektiğinde artırabilirsiniz)
    total_pages = 1        # Demo için 1 sayfa; büyük veri setleri için bu değeri yükseltin.
    output_file = "flutter_code_finetune_data.csv"

    # CSV dosyasını yazma modunda açıyoruz; header olarak tek sütun "text" belirleniyor.
    with open(output_file, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["text"])  # Header satırı

        for page in range(1, total_pages + 1):
            print(f"Sayfa {page} çekiliyor...")
            search_results = search_repositories(query, per_page, page)
            if not search_results or "items" not in search_results:
                continue

            for repo_item in search_results["items"]:
                owner = repo_item["owner"]["login"]
                repo_name = repo_item["name"]
                default_branch = repo_item.get("default_branch", "master")
                repo_description = repo_item.get("description", "Açıklama yok")
                print(f"Repo işleniyor: {owner}/{repo_name} (branch: {default_branch})")
                tree = get_repo_tree(owner, repo_name, default_branch)
                if not tree or "tree" not in tree:
                    continue

                # Repository içindeki dosya ağacında .dart dosyalarını hedefliyoruz.
                for item in tree["tree"]:
                    if item["type"] == "blob" and item["path"].endswith(".dart"):
                        file_path = item["path"]
                        print(f"  Dosya çekiliyor: {file_path}")
                        code = get_file_content(owner, repo_name, file_path)
                        if code:
                            # Yorum satırlarını kaldırarak temizlenmiş kodu elde et.
                            code = remove_comments(code)
                            # Prompt ve completion içeriklerini birleştiriyoruz.
                            prompt_text = (f"# Repository: {owner}/{repo_name}\n"
                                           f"# Branch: {default_branch}\n"
                                           f"# Açıklama: {repo_description}\n"
                                           f"# Dosya: {file_path}\n"
                                           f"# Aşağıdaki kodu incele ve işlevini anlamaya çalış:\n"
                                           f"### CODE STARTS HERE\n")
                            completion_text = code + "\n### CODE ENDS HERE"
                            # İki kısmı tek metin olarak birleştiriyoruz.
                            combined_text = prompt_text + completion_text
                            writer.writerow([combined_text])
                        # API rate limitlerine takılmamak için kısa bekleme (yarım saniye)
                        time.sleep(0.5)
                # Her repo arasında ek bekleme (1 saniye)
                time.sleep(1)
            # Her sayfa arasında bekleme (2 saniye)
            time.sleep(2)

    print(f"Veriler {output_file} dosyasına kaydedildi.")

# =============================================================================
# main() fonksiyonu, fine-tuning veri seti oluşturma sürecini başlatır.
# Jupyter Notebook'ta bu hücre çalıştırıldığında tüm süreç otomatik olarak başlar.
# =============================================================================
main()