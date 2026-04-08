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

## 2. User stories — 4 paths

### Feature: Nhận đặt lịch khám

**Trigger:** User nhắn tin yêu cầu đặt lịch → AI phân tích intent (ý định) + thời gian + chuyên khoa → gợi ý khung giờ/bác sĩ.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** — AI đúng, tự tin | User thấy gì? Flow kết thúc ra sao? | User nhắn "Con tôi bị ho và sốt" → AI phân tích và gợi ý "Khoa Nhi - Bác sĩ Trần Văn A" kèm giờ (confidence 95%) → hiện thẻ Xác nhận lịch với BS A → user bấm "Chốt đặt lịch", nhận mã khám. |
| **Low-confidence** — AI không chắc | System báo "không chắc" bằng cách nào? User quyết thế nào? | User nhắn "Tôi bị đau bụng" → AI phân vân (50%) → Bot hỏi thu hẹp phạm vi, hỏi thêm triệu chứng thu hẹp phạm vi → User chọn để Bot chốt khoa. |
| **Failure** — AI sai | User biết AI sai bằng cách nào? Recover ra sao? | User nhắn "Đau mỏi vai gáy". AI tự tin (80%) xếp vào Khoa Thần kinh. Để tránh user tin mù quáng, Thẻ xác nhận bắt buộc có dòng "Cơ sở đề xuất". VD: "Gợi ý Khoa Thần Kinh vì: Nghi ngờ đau vai gáy do chèn ép rễ thần kinh cổ". User đọc cơ sở này và nhận ra sai: "Ủa mình đâu có bị chèn ép hay tê bì tay gì đâu". |
| **Correction** — user sửa | User sửa bằng cách nào? Data đó đi vào đâu? | User chat phản hồi tự nhiên: "Không, tôi chỉ mỏi cơ do ngồi máy tính nhiều thôi" → Bot nhận ra bối cảnh mới, cập nhật lại thẻ thành "Khoa Cơ xương khớp". Data (triệu chứng gốc + lời đính chính của bệnh nhân) -> tiếp tục flow|

### Feature: Tra cứu thông tin thuốc

**Trigger:** User nhập tên thuốc/gửi ảnh hộp thuốc → AI nhận diện tên thuốc + truy xuất Dược thư/Database Y tế → trả thông tin về thuốc

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** — AI đúng, tự tin | User thấy gì? Flow kết thúc ra sao? | User hỏi "Panadol đỏ có tác dụng gì" → AI match đúng thuốc (confidence 95%) → hiện tóm tắt tác dụng + cảnh báo chống chỉ định bôi đỏ → user nắm thông tin, kết thúc. |
| **Low-confidence** — AI không chắc | System báo "không chắc" bằng cách nào? User quyết thế nào? | User gõ sai chính tả "Amocilin" → AI không chắc là Amoxicillin (confidence 55%) → hiện câu hỏi "Có phải ý bạn là Amoxicillin?" kèm ảnh hộp thuốc + nút "Đúng" / "Tìm thuốc khác" → user bấm nút. |
| **Failure** — AI sai | User biết AI sai bằng cách nào? Recover ra sao? | Bot trả lời liều dùng, nhưng luôn có câu rào trước (VD: "Đây là liều tham khảo dành cho người lớn"). User đọc xong sẽ giật mình nhận ra ngay điểm sai của máy: "À, nó đang tưởng mình là người lớn, trong khi mình đang tìm thuốc cho con nít". |
| **Correction** — user sửa | User sửa bằng cách nào? Data đó đi vào đâu? | Sửa bằng hội thoại tự nhiên: User chat lại: "Nhưng bé nhà tôi mới 5 tuổi" hoặc "Tôi đang có bầu uống được không?". AI lập tức cập nhật ngữ cảnh, lôi dữ liệu nhi khoa/phụ sản ra trả lời tiếp. Luồng chat này tự động được lưu vào log → retrain cuối tuần.|


# 3. Eval metrics + threshold

Chọn metrics, đặt threshold, xác định red flag. Câu hỏi quan trọng nhất: **optimize precision hay recall?**

## Precision hay recall?

x Precision — khi AI nói "có" thì thực sự đúng (ít false positive)
☐ Recall — tìm được hết những cái cần tìm (ít false negative)

**Tại sao?**

Vì trong bối cảnh y tế, nếu hệ thống tự tin trả sai hoặc đưa user tới hành động sai thì hậu quả có thể là:

- tra cứu sai thuốc / nhầm liều / nhầm chống chỉ định,
- đặt lịch sai chuyên khoa,
- gợi ý cơ sở khám không phù hợp,
- làm user mất thời gian, mất niềm tin, thậm chí ảnh hưởng sức khỏe.

## Metrics table (precision-first)

| Metric                                                                            |   Threshold | Red flag (dừng khi)                            |
| --------------------------------------------------------------------------------- | ----------: | ---------------------------------------------- |
| **Intent precision** (đúng intent / tổng intent dự đoán)                          |   **≥ 95%** | **< 90%** trong 1 tuần                         |
| **Recall của intent quan trọng** (bắt được nhu cầu user)                          |   **≥ 90%** | **< 80%**                                      |
| **Escalation / fallback rate** (chuyển sang hỏi lại khi không chắc)    |  **10–30%** | **> 40%** → gây phiền phức cho người dùng |
| **Wrong-action rate** (thực hiện sai hành động)                                   |    **≤ 1%** | **> 2%**                                       |
| **User success rate** (user hoàn thành được việc cần làm)                         |   **≥ 85%** | **< 75%**                                      |
| **User satisfaction**                                                             | **≥ 4.5/5** | **< 4.0/5**                                    |

## 4. Top 3 failure modes for Vinmec chatbot

Liệt kê cách product có thể fail — không phải list features.

> **"Failure mode nào user KHÔNG BIẾT bị sai? Đó là cái nguy hiểm nhất."**

---

## Template Spec Draft

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | **Triage sai mức độ:** User mô tả triệu chứng nguy hiểm (đau ngực, khó thở) kèm câu hỏi thủ tục bình thường. | AI phân loại thành "đặt lịch khám thường", hướng dẫn khám vào ngày hôm sau. **User không biết AI đánh giá sai**, trì hoãn việc đi cấp cứu. | Thêm lớp Rule-based Keyword Scanner. Nếu match "red-flag words" (ngực, thở, máu...), override AI và bật cảnh báo đỏ + Nút gọi Hotline cấp cứu ngay lập tức. |
| 2 | **RAG hallucination về giá/bảo hiểm:** User hỏi về chi phí dịch vụ chuyên sâu hoặc bảo lãnh viện phí. | AI tự bịa câu trả lời hoặc lấy nhầm chính sách cũ. User đinh ninh là đúng, đến viện bị từ chối bảo lãnh, gây khủng hoảng niềm tin và CSKH. | Bắt buộc đính kèm link nguồn (URL) gốc từ website Vinmec và timestamp (Ngày cập nhật) dưới câu trả lời. Thêm disclaimer yêu cầu xác nhận tại quầy. |
| 3 | **Phantom Booking (Lỗi API):** User chốt lịch, bot sinh ra text "Đặt lịch thành công" nhưng API gọi vào hệ thống viện bị lỗi/timeout ngầm. | User

## 5. ROI 3 kịch bản

|   | Conservative | Realistic | Optimistic |
|---|-------------|-----------|------------|
| **Assumption** | *100 user/ngày, 60% hài lòng* | *500 user/ngày, 80% hài lòng* | *2000 user/ngày, 90% hài lòng* |
| **Cost** | *$50/ngày inference* | *$200/ngày* | *$500/ngày* |
| **Benefit** | *Giảm 2h support/ngày* | *Giảm 8h/ngày* | *Giảm 20h, tăng retention 5%* |
| **Net** |   |   |   |

**Kill criteria:** *Khi nào nên dừng? VD: cost > benefit 2 tháng liên tục*

---

## 6. Mini AI spec (1 trang)

AI MINI SPEC: VINMEC SMART ASSISTANT
M
ục tiêu & Đối tượng
User: Bệnh nhân Vinmec.

- Value: Giải quyết 3 "nỗi đau": Chọn sai khoa, thủ tục đặt lịch lâu, và mơ hồ về đơn thuốc.

- AI Role: Augmentation (Trợ lý hỗ trợ, không thay thế bác sĩ).

- Tính năng chính & Flow

   - Triage: Chatbot hỏi đáp triệu chứng → Gợi ý chuyên khoa/Bác sĩ phù hợp (Precision > 95%).

   - Dược thư thông minh: nhận tên thuốc → Giải thích công dụng & Cảnh báo (kèm nguồn nội bộ Vinmec).

- Vòng lặp dữ liệu: Bác sĩ tại quầy xác nhận lại khoa khám → Data này dùng để giúp AI hiểu triệu chứng chuẩn hơn.

- Quản trị rủi ro (Risk)
Ưu tiên Precision: Thà AI báo không chắc để kết nối tư vấn viên còn hơn gợi ý sai.

- Guardrails: Tự động bật Hotline Cấp cứu nếu phát hiện từ khóa nguy hiểm (đau ngực, khó thở).

- Chống ảo giác (Hallucination): Luôn kèm link nguồn gốc và Timestamp của dữ liệu y khoa.

- Hiệu quả kinh tế (ROI)
Kịch bản thực tế: Phục vụ 500 khách/ngày, tiết kiệm 8h support nhân sự, tăng tỷ lệ đặt lịch thành công (Task Completion Rate) lên > 85%.

- Kill Criteria: Dừng dự án nếu chi phí vận hành vượt lợi ích trong 2 tháng hoặc sai sót chuyên môn > 1%.
