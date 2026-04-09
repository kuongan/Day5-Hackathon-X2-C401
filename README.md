# Day5-Hackathon-X2-C401

Nền tảng trợ lý y tế đa tác vụ  gồm backend FastAPI và frontend React/Vite. Hệ thống hỗ trợ hỏi đáp sức khỏe, tra cứu thuốc, tìm bác sĩ theo bệnh/triệu chứng và đặt lịch khám.

## Tính năng chính

- Hỏi đáp triệu chứng và gợi ý hướng xử lý ban đầu.
- Tra cứu thuốc, công dụng, liều dùng và thông tin liên quan.
- Tìm bác sĩ theo bệnh/triệu chứng bằng dữ liệu nội bộ và FAISS.
- Đặt lịch khám, kiểm tra lịch trống và tạo lịch hẹn.
- Giao tiếp qua API để tích hợp với frontend.


## Cấu trúc dự án

- `backend/`: FastAPI, agents, tools, schema và logic truy xuất dữ liệu.
- `frontend/`: Ứng dụng React + Vite + Tailwind.
- `data/`: CSDL SQLite và các file FAISS/index dùng cho tra cứu.
- `report/`: Tài liệu báo cáo, canvas và tài liệu đánh giá.

Phần `report/` tổng hợp toàn bộ nội dung trình bày dự án, gồm canvas sản phẩm, user stories, failure modes, ROI và báo cáo cá nhân/nhóm. Đây là nơi ghi lại mục tiêu, cách thiết kế giải pháp, phạm vi dữ liệu, các tình huống thất bại đã dự đoán và giá trị thực tế mà hệ thống mang lại trong bối cảnh hackathon.


## Yêu cầu môi trường

- Python 3.11+.
- Node.js 18+.
- Một file `.env` hoặc biến môi trường chứa khóa API/thiết lập LLM nếu dự án của bạn cần.

## Cài đặt

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Frontend

```powershell
cd frontend
npm install
```

## Chạy ứng dụng

### Backend

Từ thư mục gốc của dự án:

```powershell
uvicorn backend.main:app --reload
```

Backend mặc định chạy ở `http://localhost:8000`.

### Frontend

Từ thư mục `frontend`:

```powershell
npm run dev
```

Frontend mặc định chạy bằng Vite dev server.

## API chính

Tất cả endpoint nằm dưới tiền tố `/api/v1`.

- `GET /api/v1/health`: kiểm tra trạng thái hệ thống.
- `POST /api/v1/chat`: hỏi đáp y khoa tổng quát.
- `POST /api/v1/medicine`: tra cứu thuốc.
- `POST /api/v1/booking`: đặt lịch khám.
- `POST /api/v1/orchestration`: điều phối yêu cầu sang agent phù hợp.

## Dữ liệu và lưu ý

- File SQLite được đọc từ `data/medical_chatbot.db` mặc định.
- Các chỉ mục FAISS nằm trong `data/faiss/`.
- Booking agent yêu cầu bác sĩ, ngày và giờ hợp lệ trước khi tạo lịch.

## Kiểm thử nhanh

Bạn có thể chạy các script test nội bộ nếu cần kiểm tra flow đặt lịch:

```powershell
python test_booking_disease.py
python test_booking_confirmation.py
```
