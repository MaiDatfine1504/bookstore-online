import json

# Đọc dữ liệu từ book.json
with open('data/book.json', 'r', encoding='utf-8') as f:
    books = json.load(f)

# Thêm id cho từng sách (tăng dần từ 1)
for idx, book in enumerate(books, start=1):
    book['id'] = idx

# Ghi đè lại file book.json
with open('data/book.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=2)

print("✅ Đã thêm ID vào từng sách trong book.json")
