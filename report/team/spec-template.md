# SPEC — AI Product Hackathon

**Nhóm:** X2
**Track:** ☒ Vinmec 

**Problem statement:** *Bệnh nhân mất thời gian chờ đợi và dễ đăng ký nhầm chuyên khoa do không hiểu triệu chứng; Agent AI giúp phân loại khoa chính xác, kết nối trực tiếp với hệ thống đặt lịch thời gian thực và giải thích đơn thuốc an toàn.*

---

## 1. AI Product Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Câu hỏi** |User nào? Pain gì? AI giải gì?| Khi AI sai thì sao? User sửa bằng cách nào?| Cost/latency bao nhiêu? Risk chính?|
| **Trả lời** |User: Bệnh nhân Vinmec. Pain: Không biết chọn khoa phù hợp; quá tải thủ tục; mơ hồ về đơn thuốc sau khám. AI giải: Chatbot phân loại triệu chứng/đặt lịch & giải thích chỉ định an toàn khi dùng thuốc. | Khi AI gợi ý sai khoa: Hệ thống luôn hiển thị nút "Kết nối tư vấn viên" hoặc "Khám tổng quát". Khi giải thích thuốc: AI luôn kèm disclaimer và dẫn nguồn từ dược điển Vinmec. | Cost: ~$0.05/session. Latency: < 3s. Risk: Hallucination về bệnh lý nguy hiểm (AI tự chẩn đoán). Cần lớp Guardrail để chặn các câu hỏi về kê đơn.|

**Automation hay augmentation?** ☒ Augmentation

Justify: Hệ thống đóng vai trò "Trợ lý". Bệnh nhân vẫn là người quyết định đặt lịch và bác sĩ/dược sĩ là người chịu trách nhiệm cuối cùng về chuyên môn y tế.

**Learning signal:**

1. User correction đi vào đâu? 
-> Dữ liệu triệu chứng bị phân loại sai được tag bởi bác sĩ tại quầy.

2. Product thu signal gì để biết tốt lên hay tệ đi? 

   -> Task Completion Rate: Tỷ lệ đặt lịch thành công qua Agent.

   -> Tỷ lệ bệnh nhân phải đổi khoa sau khi đã được AI hướng dẫn (Misclassification rate).
   
   -> Compliance Rate: Tỷ lệ người dùng hiểu và tuân thủ đơn thuốc (thông qua khảo sát/nhắc lịch).

3. Data thuộc loại nào? ☒ User-specific · ☒ Domain-specific · ☒ Real-time · ☒ Human-judgment

Có marginal value không? -> Rất cao. Model base không có dữ liệu lịch trực thực tế của bác sĩ Vinmec và kiến thức đặc thù về các gói khám, danh mục thuốc/phác đồ nội bộ của hệ thống y tế Vinmec.

