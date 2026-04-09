# SPEC — AI Product Hackathon

**Nhóm:** Vinmec_B6
**Track:** ☑ Vinmec
**Problem statement (1 câu):** Bệnh nhân Vinmec thường không biết chọn khoa phù hợp, đối mặt với thủ tục quá tải và cảm thấy mơ hồ về đơn thuốc sau khi khám; Trợ lý AI sẽ giúp phân loại triệu chứng, đề xuất chuyên khoa, hỗ trợ đặt lịch và giải thích các chỉ định y tế.

---

## 1. AI Product Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Câu hỏi** | User nào? Pain gì? AI giải gì? | Khi AI sai thì sao? User sửa bằng cách nào? | Cost/latency bao nhiêu? Risk chính? |
| **Trả lời** | **User:** Bệnh nhân Vinmec.<br>**Pain:** Không biết chọn khoa, thủ tục quá tải, mơ hồ về đơn thuốc.<br>**AI:** Chatbot phân loại triệu chứng, đề xuất khoa, đặt lịch, giải thích thuốc, giúp rút ngắn thời gian và giảm tải front-desk. | **Khi AI sai:** Cung cấp fail-safe UI với nút "Kết nối tư vấn viên" khi độ tự tin thấp. Mọi giải thích thuốc đều có disclaimer và nguồn từ dược điển.<br>**Cách sửa:** Bệnh nhân là người ra quyết định cuối cùng; có các luồng đính chính thông tin để AI cập nhật lại ngữ cảnh. | **Cost:** ~$0.05 / session.<br>**Latency:** < 3s cho hội thoại cơ bản.<br>**Risk:** Hallucination (sai chẩn đoán), rò rỉ dữ liệu nhạy cảm, đề xuất thuốc không phù hợp. |

**Automation hay augmentation?** ☑ Augmentation
**Justify:** Trợ lý hỗ trợ, không thay thế bác sĩ. Bệnh nhân là người quyết định, và bác sĩ/dược sĩ là người chịu trách nhiệm chuyên môn cuối cùng.

**Learning signal:**
1. **User correction đi vào đâu?** Tương tác sửa lỗi (ví dụ: triệu chứng gốc + đính chính) được ghi vào log để cải thiện mô hình thông qua việc retrain hàng tuần.
2. **Product thu signal gì để biết tốt lên hay tệ đi?** Tỷ lệ User Success Rate, Intent Precision/Recall và User Satisfaction.
3. **Data thuộc loại nào?** ☑ Domain-specific (Dược điển Vinmec, dữ liệu chuyên khoa) · ☑ Human-judgment (Xác nhận/đính chính từ user).
   **Có marginal value không?** Có, việc thu thập log tương tác thực tế giữa bệnh nhân và bot giúp refine hệ thống phân loại intent ngày càng chính xác hơn với ngôn ngữ đời thường.

---

## 2. User Stories — 4 paths

### Feature A: Nhận đặt lịch khám

**Trigger:** User nhắn yêu cầu đặt khám → AI phân tích intent, thời gian, chuyên khoa → gợi ý khung giờ & bác sĩ.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy**<br>*(Confidence cao)* | User thấy gì? Flow kết thúc ra sao? | AI tự tin 95%, gợi ý đúng khoa/bác sĩ (VD: "Khoa Nhi — Bs. Trần Văn A, 10:00–10:30"). Hiện thẻ Xác nhận có nút "Chốt đặt lịch", user bấm và nhận mã khám. |
| **Low-confidence**<br>*(AI không chắc)* | System báo "không chắc" bằng cách nào? User quyết thế nào? | AI tự tin ~50%, bot hỏi thu hẹp (VD: "Bạn/Con có sốt, tiêu chảy hay khó thở không?"). User trả lời, AI cập nhật và gợi ý khoa chính xác hơn. |
| **Failure**<br>*(AI sai)* | User biết AI sai bằng cách nào? Recover ra sao? | AI nhầm nhưng tự tin (80%). Thẻ xác nhận hiển thị "Cơ sở đề xuất" giải thích ngắn. User đọc nhận ra sai và bấm nút "Không đúng" để sửa. |
| **Correction**<br>*(User sửa)* | User sửa bằng cách nào? Data đó đi vào đâu? | User chat lại tự nhiên (VD: "Không, chỉ mỏi cơ do ngồi máy tính"). Bot cập nhật intent, chuyển gợi ý sang "Khoa Cơ xương khớp" và lưu log để cải thiện mô hình. |

### Feature B: Tra cứu thuốc

**Trigger:** User nhập tên thuốc hoặc gửi ảnh hộp thuốc → AI nhận diện tên + truy xuất cơ sở dữ liệu dược.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy**<br>*(Confidence cao)* | User thấy gì? Flow kết thúc ra sao? | Match chính xác 95% (VD: "Panadol đỏ"). AI hiển thị tóm tắt tác dụng, cảnh báo chống chỉ định kèm nút "Xem chi tiết liều" và nguồn Dược thư. |
| **Low-confidence**<br>*(AI không chắc)* | System báo "không chắc" bằng cách nào? User quyết thế nào? | AI tự tin ~55%, hiện xác nhận "Bạn có ý là Amoxicillin?" kèm ảnh hộp và hai nút "Đúng" hoặc "Tìm thuốc khác". |
| **Failure**<br>*(AI sai)* | User biết AI sai bằng cách nào? Recover ra sao? | Bot hiển thị liều cho người lớn mà không rõ đối tượng. Mitigation: Luôn ghi "Liều tham khảo" và rào trước yêu cầu xác nhận độ tuổi. |
| **Correction**<br>*(User sửa)* | User sửa bằng cách nào? Data đó đi vào đâu? | User bổ sung "Bé 5 tuổi". AI cập nhật ngữ cảnh, kéo dữ liệu nhi khoa, trả liều & cảnh báo phù hợp. Tương tác được ghi log để retrain. |

---

## 3. Eval metrics + threshold

**Optimize precision hay recall?** ☑ Precision
**Tại sao?** Khi AI trả lời "có" thì phải đúng, hạn chế tối đa false positive vì đây là sai lầm nguy hiểm nhất trong y tế (nhầm thuốc, sai liều, sai chuyên khoa) ảnh hưởng trực tiếp đến sức khỏe và niềm tin. Thà AI báo "không chắc" còn hơn gợi ý sai.

| Metric | Threshold | Red flag (dừng khi) | Ý nghĩa |
|--------|-----------|---------------------|---------|
| **Intent Precision** | ≥ 95% | < 90% trong 1 tuần | Đúng intent dự đoán |
| **Intent Recall** | ≥ 90% | < 80% | Bắt được nhu cầu user |
| **Wrong-Action Rate** | ≤ 1% | > 2% | Thực hiện sai hành động |
| **User Success Rate** | ≥ 85% | < 75% | Hoàn thành mục tiêu |

---

## 4. Top 3 failure modes

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | **Triage Sai Mức Độ:** Triệu chứng nguy hiểm (đau ngực, khó thở) + câu hỏi thủ tục → AI phân loại thành "khám thường". | User trì hoãn cấp cứu, không biết AI sai. | Dùng Rule-based scanner + override + hiển thị nút Hotline cấp cứu. |
| 2 | **RAG Hallucination (Giá / Bảo Hiểm):** Hỏi chi phí hoặc bảo lãnh viện phí → AI bịa thông tin hoặc lấy chính sách cũ. | Bị từ chối bảo lãnh tại viện, gây khủng hoảng niềm tin. | Bắt buộc đính kèm URL nguồn + timestamp + disclaimer yêu cầu xác nhận tại quầy. |
| 3 | **Phantom Booking (Lỗi API Ngầm):** API lỗi/timeout ngầm → bot báo "thành công" nhưng lịch không được tạo. | User đến bệnh viện không có lịch khám, mất niềm tin nghiêm trọng. | Dùng Real-time API verification + xác nhận SMS + cơ chế retry. |

---

## 5. ROI 3 kịch bản

|   | Conservative (Thận trọng) | Realistic (Thực tế) | Optimistic (Lạc quan) |
|---|-------------|-----------|------------|
| **Assumption** | Queries/ngày: 500<br>Tỷ lệ giải quyết: 20% | Queries/ngày: 2,000<br>Tỷ lệ giải quyết: 50% | Queries/ngày: 5,000<br>Tỷ lệ giải quyết: 80% |
| **Cost** | ~ $15/ngày | ~ $30/ngày | ~ $60/ngày |
| **Benefit** | Giải quyết 100 queries/ngày, tiết kiệm ~8 giờ CSKH (~$24/ngày). | Giải quyết 1,000 queries/ngày, tiết kiệm ~83 giờ CSKH (~$249/ngày). | Giải quyết 4,000 queries/ngày, tiết kiệm ~333 giờ CSKH (~$1,000/ngày) + giảm 30% nhân sự trực đêm. |
| **Net** | +$9/ngày (chưa tính giá trị dữ liệu cho RAG). | +$219/ngày (~$6,500/tháng), đủ bù chi phí vận hành. | +$940/ngày (~$28,000/tháng). |

**Kill criteria:**
1. Tỷ lệ Task Resolution duy trì dưới 15% sau 4 tuần triển khai.
2. Chi phí API OpenAI vượt quá dự kiến (> 100 USD/ngày) đồng thời CSAT giảm xuống dưới 3.0/5.0.
3. Phát hiện rủi ro ảo giác (Hallucination) vượt quá 1% trong dữ liệu kiểm toán hàng tuần.

---

## 6. Mini AI spec (1 trang)

**Vinmec Smart Assistant**

Sản phẩm là một trợ lý ảo hỗ trợ bệnh nhân Vinmec giải quyết tình trạng quá tải thông tin và thủ tục. 
* **AI Role:** Hệ thống hoạt động theo nguyên tắc **Augmentation** — đóng vai trò trợ lý hỗ trợ phân tích ngôn ngữ tự nhiên, tuyệt đối không thay thế quyết định của bác sĩ hay chuyên gia y tế. 
* **Tính năng chính:** Bao gồm hai luồng cốt lõi: **Triage** (Chat triệu chứng để gợi ý chuyên khoa, đặt lịch khám) và **Dược thư** (Giải thích công dụng, liều dùng tham khảo và cảnh báo chống chỉ định của thuốc dựa trên cơ sở dữ liệu nội bộ).
* **Chất lượng (Quality):** Đặt mục tiêu tối thượng vào **Precision (≥ 95%)** thay vì Recall, áp dụng triết lý "thà báo không chắc còn hơn gợi ý sai" nhằm bảo vệ an toàn sức khỏe bệnh nhân.
* **Risk & Guardrails:** Rủi ro lớn nhất là AI bị ảo giác trong chẩn đoán hoặc cung cấp sai quy định bảo hiểm. Để kiểm soát, hệ thống tích hợp các rào chắn nghiêm ngặt: tự động kích hoạt Hotline cấp cứu khi phát hiện từ khóa nguy hiểm, và mọi thông tin tư vấn đều bắt buộc kèm theo URL nguồn và timestamp để đảm bảo tính minh bạch và truy xuất. Tương tác của người dùng khi đính chính thông tin sẽ tạo thành learning signal để liên tục cải thiện mô hình.