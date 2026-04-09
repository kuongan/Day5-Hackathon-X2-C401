### reflection.md

# Individual reflection — Trần Vọng Triển(2A202600320)

## 1. Role
Coder, BA

## 2. Đóng góp cụ thể
- Thiết kế Canvas trong spec và trực tiếp lập trình Medicine Agent.
- Viết tài liệu spec-final.md và thực hiện prompt-tests cho các tình huống tra cứu thuốc.

## 3. SPEC mạnh/yếu
- Mạnh nhất: Phần Low confidence. Nhóm đã chủ động thiết kế các test case cho tình huống người dùng cung cấp thiếu thông tin hoặc mô tả 

- Yếu nhất: Phần Failure modes. Do thời gian ngắn nên prompt chưa đủ chặt chẽ để có cơ chế sửa đúng các câu trả lời sai.

## 4. Đóng góp khác
- Tham gia kiểm thử (test agent) để phát hiện lỗi phản hồi và xử lý các Edge cases (triệu chứng mơ hồ, user hỏi nhiều intent cùng lúc).

- Hỗ trợ các thành viên trong nhóm fix bug code và tham gia chấm điểm, nhận xét nhóm khác để rút kinh nghiệm đối chiếu.
## 5. Điều học được
- Metric là quyết định sản phẩm: Hiểu rằng việc chọn Precision hay Recall phụ thuộc vào mục tiêu y tế.

- Kỹ năng kỹ thuật: Hiểu quy trình xây dựng AI Agent thực tế, cách vận hành Git workflow (branch, merge, conflict) và cách chuyển hóa dữ liệu thô thành tri thức cho AI.

## 6. Nếu làm lại
Sẽ tập trung tối ưu hóa phần ROI với các số liệu giả định sát thực tế hơn và dành thêm thời gian để sửa các lỗ hổng trong Failure modes, đặc biệt là các kịch bản cảnh báo rủi ro y tế nghiêm trọng.

## 7. AI giúp gì / AI sai gì
- Giúp: Sử dụng Copilot và Claude để hỗ trợ viết code Medicine Agent nhanh hơn và brainstorm các trường hợp edge case.

- Sai/mislead: AI yêu cầu quá nhiều thông tin đầu vào khiến thời gian chờ đợi lâu và khó kiểm soát code. Ngoài ra, AI thường gợi ý mở rộng scope dự án quá lớn, dễ gây loãng mục tiêu chính của Hackathon.