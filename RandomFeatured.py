import random
import  json

with open('data/book.json', 'r', encoding='utf-8') as f:
    books = json.load(f)

# Đặt tất cả về False trước
for book in books:
    book["featured"] = False

# Chọn ngẫu nhiên 5 cuốn làm nổi bật
for book in random.sample(books, k=min(4, len(books))):
    book["featured"] = True

with open('data/book.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=2)

print("✅ Đã random 4 sách nổi bật và thêm 'featured': true.")
