# CS311: Interview-Application-Project

Hệ thống hỗ trợ người dùng **chuẩn bị tốt cho phỏng vấn** thông qua các luồng luyện tập (flow), gợi ý cải thiện và các chức năng liên quan đến hồ sơ (resume), lưu trữ dữ liệu người dùng, tìm kiếm ngữ nghĩa (vector search) và tích hợp LLM (Azure OpenAI).

---

## Mục tiêu dự án

- Hỗ trợ người dùng luyện phỏng vấn có hệ thống (câu hỏi, chủ đề, kịch bản).
- Tích hợp LLM để sinh câu hỏi, phản hồi, đánh giá và gợi ý cải thiện (tùy theo tính năng hiện có).
- Hỗ trợ truy xuất ngữ nghĩa (embeddings + vector store) để tìm nội dung liên quan trong tài liệu/câu hỏi.
- Lưu trữ & quản lý dữ liệu (người dùng, lịch sử luyện tập, cấu hình).
- Kiến trúc tách Frontend/Backend rõ ràng, thuận tiện teamwork và mở rộng.

---

## Thành viên

| MSSV     | Họ Tên              |
|----------|---------------------|
| 23521319 | Nông Nhựt Quy        |
| 23521190 | Trương Thiên Phú     |
| 23521123 | Lê Nguyễn Quỳnh Như  |

---

## Yêu cầu môi trường

- Python 3.10+ (khuyến nghị 3.10 hoặc 3.11)
- Node.js 18+ và npm
- Git (tùy chọn)

---

## Cấu trúc thư mục

```
.
├── cs311be/   # Backend (Python)
└── cs311fe/   # Frontend (JavaScript/Node)
```

---

## Thiết lập & chạy dự án

Dự án gồm 2 phần chạy song song:
- Backend chạy ở Terminal 1
- Frontend chạy ở Terminal 2

### 1) Backend (Python)

Mở Terminal 1, vào thư mục backend:

```powershell
cd cs311be
```

#### Bước 1 — Tạo file `.env`

Nếu repo có sẵn file mẫu:

```powershell
Copy-Item .env.example .env
# hoặc
Copy-Item .env.template .env
```

Nếu không có file mẫu, tạo `cs311be/.env` và dán mẫu dưới đây, sau đó điền giá trị.

#### Bước 2 — Cài đặt thư viện

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Bước 3 — Chạy backend

```powershell
python -m main.py
```


---

### 2) Frontend (Node.js)

Mở Terminal 2, vào thư mục frontend:

```powershell
cd cs311fe
```

Cài đặt thư viện:

```powershell
npm install
```

Chạy frontend:

```powershell
npm run dev
```

> Nếu frontend dùng lệnh khác (ví dụ `npm start`), chạy theo script trong `cs311fe/package.json`.

---

## Quy trình chạy nhanh (tóm tắt)

1. Terminal 1:
   - `cd cs311be`
   - tạo `.env`
   - `python -m venv .venv` → activate → `pip install -r requirements.txt`
   - chạy backend
2. Terminal 2:
   - `cd cs311fe`
   - `npm install`
   - chạy frontend

---

## File môi trường `.env`

Tạo file `cs311be/.env`:


---

## Lưu ý

- Nếu gặp lỗi thiếu biến môi trường, kiểm tra lại file `.env`.
- Nếu cổng bị trùng, đổi port trong file cấu hình hoặc `.env`.
- Không commit file `.env` lên repo công khai.

---

## Khó khăn & thách thức

- Dễ phát sinh lỗi cấu hình do tích hợp nhiều service (Azure OpenAI, MongoDB, ChromaDB, Email, JWT).
- Đồng bộ API giữa frontend và backend: thay đổi response/endpoint có thể làm UI lỗi.
- Quản lý token/cost khi dùng LLM: cần tối ưu prompt/context và caching nếu có.
- Retrieval chất lượng: chunking và cấu hình vector search ảnh hưởng trực tiếp đến kết quả.

---

## Định hướng phát triển trong tương lai

- Ngân hàng câu hỏi theo ngành/vị trí/level.
- Mô phỏng phỏng vấn theo kịch bản (session + timer + tổng kết).
- Chấm điểm theo rubric (STAR method, clarity, completeness...).
- Tối ưu tìm kiếm ngữ nghĩa (rerank, caching, chunking tốt hơn).
- Docker hóa và triển khai CI/CD để deploy nhanh.

---

## License

Dự án phục vụ mục đích học tập.
