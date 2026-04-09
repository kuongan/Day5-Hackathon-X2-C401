# Prototype — AI trợ lý Vinmec đa tác vụ

## Mô tả
Hệ thống trợ lý y tế thông minh tích hợp đa chức năng nhằm hỗ trợ người dùng hỏi đáp sức khỏe, tra cứu thông tin thuốc và tìm kiếm bác sĩ chuyên khoa. Hệ thống giúp phân loại bệnh, gợi ý hướng xử lý ban đầu và tự động hóa quy trình đặt lịch khám, giúp tối ưu hóa tương tác giữa bệnh nhân và cơ sở y tế thông qua giao diện trực quan và các tác vụ AI phối hợp.
## Level: Level: Functional Prototype
- Frontend: Ứng dụng Web hoàn chỉnh xây dựng bằng React, Vite và Tailwind CSS.

- Backend: Hệ thống API hiệu năng cao với FastAPI, tích hợp các Agents và Tools xử lý logic y tế.

- Data & AI: Sử dụng cơ sở dữ liệu SQLite cho thông tin y khoa và FAISS để truy xuất tìm kiếm bác sĩ theo triệu chứng/bệnh lý.

## Links 
- Source Code: Thư mục backend/ và frontend/ trong dự án.

- Tài liệu dự án: Xem chi tiết tại thư mục report/ (bao gồm Canvas, User Stories, Failure Modes, ROI).

- Cơ sở dữ liệu: data/medical_chatbot.db và các chỉ mục tại data/faiss/.
- Prompt test log: xem file prompt-tests.md

## Tools 
- Ngôn ngữ & Framework: Python 3.11+, Node.js 18+.

- Backend: FastAPI, Agents, Tools, Schema.

- Frontend: React, Vite, Tailwind CSS.

- Thư viện AI/Data: FAISS (truy xuất dữ liệu), LLM (thông qua cấu trúc Agent), SQLite.

## Phân công (mẫu)
| Thành viên | Phần | Output |
|-----------|------|--------|
| An | chat agent + back end script | chat agent, back end/ script |
| Triển | Canvas + Medicine agent | Medicine agent, prompt-tests, spec-final.md |
| Yến | User 4 path + orchestration-agent | spec-final.md, orchestration-agent, demo slide  |
| Châu | Booking agent + Eval metrics + ROI + demo slides | booking-agent, spec-final.md |
| Minh | connect backend với frontend dùng fast api + test ui ux | front end, api, backend/api, backend/utils |
| Việt |  crawl data, front end, test | front end, data |