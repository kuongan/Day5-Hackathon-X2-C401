# User stories — 4 paths

Mỗi feature AI chính = 1 bảng. AI trả lời xong → chuyện gì xảy ra? Viết cả 4 trường hợp.

---

## Template

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

---

## Ví dụ: AI phân loại email

### Feature: Gợi ý nhãn email (Urgent / Action-needed / FYI)

**Trigger:** Email mới đến → AI phân tích subject + sender + nội dung → gợi ý nhãn.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** | User thấy gì? Flow kết thúc ra sao? | Email từ sếp, subject "Deadline Friday" → AI gợi ý "Urgent" (confidence 95%) → hiện badge đỏ + lý do "từ sếp, chứa 'deadline'" → user thấy đúng, tiếp tục |
| **Low-confidence** | System báo bằng cách nào? | Newsletter tiêu đề "Action required" → AI không chắc Action-needed hay FYI (confidence 55%) → hiện 2 nhãn gợi ý + % → user chọn 1 |
| **Failure** | User biết sai bằng cách nào? | Email khiếu nại viết tiếng lóng → AI gắn "FYI" (confidence 80%) → user đọc inbox, thấy sai → sửa thành "Urgent" |
| **Correction** | User sửa bằng cách nào? Data đi vào đâu? | User kéo thả email sang nhãn đúng → ghi correction log (sender + pattern + nhãn sửa) → retrain cuối tuần |

---

## Lưu ý

- Viết **cả 4 path** — nhiều nhóm chỉ nghĩ happy path, bỏ quên 3 cái còn lại
- Path "Failure" quan trọng nhất: user biết AI sai bằng cách nào? Nếu không biết → nguy hiểm
- Path "Correction" = nguồn data cho feedback loop — thiết kế sớm, không để sau
- Mỗi path có câu hỏi thiết kế riêng, không copy-paste