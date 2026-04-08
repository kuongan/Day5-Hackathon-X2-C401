
# Top 3 failure modes for Vinmec chatbot

Liệt kê cách product có thể fail — không phải list features.

> **"Failure mode nào user KHÔNG BIẾT bị sai? Đó là cái nguy hiểm nhất."**

---

## Template Spec Draft

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | **Triage sai mức độ:** User mô tả triệu chứng nguy hiểm (đau ngực, khó thở) kèm câu hỏi thủ tục bình thường. | AI phân loại thành "đặt lịch khám thường", hướng dẫn khám vào ngày hôm sau. **User không biết AI đánh giá sai**, trì hoãn việc đi cấp cứu. | Thêm lớp Rule-based Keyword Scanner. Nếu match "red-flag words" (ngực, thở, máu...), override AI và bật cảnh báo đỏ + Nút gọi Hotline cấp cứu ngay lập tức. |
| 2 | **RAG hallucination về giá/bảo hiểm:** User hỏi về chi phí dịch vụ chuyên sâu hoặc bảo lãnh viện phí. | AI tự bịa câu trả lời hoặc lấy nhầm chính sách cũ. User đinh ninh là đúng, đến viện bị từ chối bảo lãnh, gây khủng hoảng niềm tin và CSKH. | Bắt buộc đính kèm link nguồn (URL) gốc từ website Vinmec và timestamp (Ngày cập nhật) dưới câu trả lời. Thêm disclaimer yêu cầu xác nhận tại quầy. |
| 3 | **Phantom Booking (Lỗi API):** User chốt lịch, bot sinh ra text "Đặt lịch thành công" nhưng API gọi vào hệ thống viện bị lỗi/timeout ngầm. | User