import os
import requests
from bs4 import BeautifulSoup
import re, json

BASE_URL = 'https://cachep.vn/collections/top-sach-ban-chay-nhat'
IMG_DIR = 'static/images'
DATA_DIR = 'data'
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0'}
book_data = []
NUM_PAGES = 6

for page in range(1, NUM_PAGES+1):
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    print(f"🔄 Đang crawl trang {page}: {url}")
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    books = soup.select('div.product-item-col')

    for book in books:
        try:
            title_tag = book.select_one('.product-title')
            price_tag = book.select_one('.current-price')
            img_tag = book.select_one('img')
            link_tag = book.select_one('a')

            if not (title_tag and img_tag and link_tag):
                continue

            title = title_tag.get_text(strip=True)
            price = price_tag.get_text(strip=True) if price_tag else "0đ"
            img_url = img_tag['data-src'] if 'data-src' in img_tag.attrs else img_tag['src']
            product_link = "https://cachep.vn" + link_tag['href']

            # Vào trang chi tiết sản phẩm để lấy genre
            detail_res = requests.get(product_link, headers=headers)
            detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
            breadcrumb = detail_soup.select('ul.breadcrumb a')
            genre = breadcrumb[1].get_text(strip=True) if len(breadcrumb) > 1 else "Không rõ"

            clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
            filename = f"{clean_title}.png"
            filepath = os.path.join(IMG_DIR, filename)

            if not os.path.exists(filepath):
                full_img_url = "https:" + img_url if img_url.startswith("//") else img_url
                img_data = requests.get(full_img_url).content
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                print(f"📘 Đã lưu: {filename}")
            else:
                print(f"⚠️ Ảnh đã tồn tại: {filename}")

            if not any(b["title"] == title for b in book_data):
                book_data.append({
                    "title": title,
                    "price": price,
                    "image": filename,
                    "genre": genre
                })

        except Exception as e:
            print(f"❌ Lỗi khi xử lý sách: {e}")

# Ghi file JSON
json_path = os.path.join(DATA_DIR, 'book.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(book_data, f, ensure_ascii=False, indent=2)

print(f"✅ Đã lưu tổng cộng {len(book_data)} sách vào {json_path}")
