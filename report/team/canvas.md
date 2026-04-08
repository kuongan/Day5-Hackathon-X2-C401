# AI Product Canvas — VN Airlines Chatbot NEO

Điền Canvas cho product AI của nhóm. Mỗi ô có câu hỏi guide — trả lời trực tiếp, xóa phần in nghiêng khi điền.

---

## Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Câu hỏi guide** | User nào? Pain gì? AI giải quyết gì mà cách hiện tại không giải được? | Khi AI sai thì user bị ảnh hưởng thế nào? User biết AI sai bằng cách nào? User sửa bằng cách nào? | Cost bao nhiêu/request? Latency bao lâu? Risk chính là gì? |
| **Trả lời** | **- User:** Hành khách của VN Airlines đang cần xử lý vấn đề (đổi vé, mua hành lý).<br>**- Pain:** Phải tự đọc các chính sách (wall-of-text) dài dòng, khó hiểu hoặc phải chờ đợi tổng đài viên quá lâu.<br>**- AI giải quyết:** Sử dụng NLP (intent classification & slot-filling) để tự động thu thập thông tin (ví dụ: mã PNR) và xử lý tác vụ trực tiếp ngay trong cửa sổ chat, thay vì chỉ quăng link điều hướng ra ngoài web. | **- Hậu quả khi sai:** User nhận sai chính sách đổi trả hoặc bot thực hiện thao tác sai chuyến bay.<br>**- Cách nhận biết:** Cung cấp cho user một **UI Card** (thẻ tóm tắt thông tin chuyến bay & tác vụ) trước khi thực hiện bước tiếp theo để user đối chiếu.<br>**- Cách sửa:** Nút `[Chỉnh sửa thông tin]`, nút `[Kết nối nhân viên CSKH]`, và cơ chế phản hồi (Thumbs up/down). | **- Cost:** ~0.001$ - 0.005$/request nếu dùng các model tối ưu tốc độ (như Gemini Flash hoặc GPT-4o mini) kết hợp RAG.<br>**- Latency:** Cần < 2 giây để đảm bảo flow chat tự nhiên.<br>**- Risk chính:** AI bị hallucination bịa ra chính sách đổi vé không có thật, hoặc API kết nối với hệ thống Booking nội bộ của VNA bị chậm/lỗi. |

---

## Automation hay augmentation?

☐ Automation — AI làm thay, user không can thiệp
**☑ Augmentation — AI gợi ý, user quyết định cuối cùng**

**Justify:** Trong ngành hàng không, các tác vụ liên quan đến vé thường đi kèm với chi phí (phí đổi vé, chênh lệch giá). AI chỉ đóng vai trò phân tích ngôn ngữ tự nhiên (NLU) để hiểu người dùng muốn gì, đối chiếu quy định (RAG), và đưa ra mức phí/lựa chọn chuyến bay. **Hành động chốt cuối cùng (Xác nhận thanh toán/Đổi vé) bắt buộc phải do user tự click quyết định** để tránh rủi ro hệ thống tự động đổi sai lịch trình của khách.

---

## Learning signal

| # | Câu hỏi | Trả lời |
|---|---------|---------|
| 1 | User correction đi vào đâu? | Khi user bấm Thumbs down hoặc chọn fallback `[Gặp nhân viên]`, toàn bộ log hội thoại sẽ được lưu trữ để update lại cơ sở dữ liệu RAG (thêm các edge cases bị thiếu) hoặc để fine-tune lại model phân loại Intent. |
| 2 | Product thu signal gì để biết tốt lên hay tệ đi? | **Implicit signal:** Tỉ lệ Task Resolution Rate (User hoàn thành việc đổi vé mà không cần thoát chat).<br>**Explicit signal:** CSAT (Đánh giá sao) sau khi kết thúc hội thoại. |
| 3 | Data thuộc loại nào? | ☑ Domain-specific (Dữ liệu chính sách bay riêng của VNA)<br>☑ Human-judgment (Feedback đúng/sai từ user) |

**Có marginal value không?** (Model đã biết cái này chưa? Ai khác cũng thu được data này không?)
Có. Các Foundation Models (LLM) không thể tự biết được các quy định hành lý, chính sách giá vé nội bộ cập nhật liên tục của VN Airlines, và cấu trúc API hệ thống của hãng. Việc thu thập các queries thực tế của user (đặc biệt là các câu hỏi ngách/phức tạp khiến bot bị "lú") sẽ giúp hãng liên tục làm giàu vector database độc quyền của mình, tạo lợi thế cạnh tranh với các đối thủ khác.

---

*AI Product Canvas — Ngày 5 — VinUni A20 — AI Thực Chiến · 2026*