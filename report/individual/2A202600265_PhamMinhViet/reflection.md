# Individual reflection — Phạm Minh Việt

## 1. Vai trò
Data + frontend. Mình phụ trách crawl dữ liệu bệnh và bác sĩ, đồng thời tham gia xây dựng giao diện frontend cho sản phẩm.

## 2. Đóng góp cụ thể
- Crawl và chuẩn hóa dữ liệu cho bệnh, bác sĩ để phục vụ pipeline truy vấn của hệ thống.
- Hỗ trợ xây dựng frontend, hoàn thiện các màn hình chính để demo luồng chatbot.
- Tham gia kiểm thử agent bằng các tình huống thực tế để đánh giá khả năng phản hồi.

## 3. SPEC mạnh/yếu
- Mạnh nhất: phần low confidence. Nhóm đã chủ động thiết kế các test case cho tình huống người dùng cung cấp thiếu thông tin hoặc mô tả mơ hồ; khi đó chatbot cần hỏi lại để làm rõ trước khi đưa khuyến nghị.
- Yếu nhất: phần failure modes. Prompt chưa đủ chặt cho các trường hợp có dấu hiệu nguy hiểm, nên AI chưa luôn ưu tiên khuyến nghị đi khám ngay. Ngoài ra, scope dự án vẫn còn rộng và chưa thật sự sát thực tiễn triển khai.

## 4. Đóng góp khác
- Tham gia test agent để phát hiện các lỗi phản hồi và thiếu sót trong luồng hội thoại.
- Đi chấm điểm, nhận xét các nhóm khác để đối chiếu cách làm và rút kinh nghiệm cho nhóm mình.

## 5. Điều học được
- Học được quy trình crawl data và xử lý dữ liệu thô để đưa vào hệ thống AI.
- Nhận ra metric cần tối ưu phụ thuộc vào mục tiêu sản phẩm; với bài toán này, recall quan trọng hơn để hạn chế bỏ sót thông tin quan trọng.

## 6. Nếu làm lại
Mình sẽ bám sát ý tưởng ban đầu hơn và tập trung vào một vài tính năng cốt lõi thay vì mở rộng quá nhiều. Làm ít nhưng sâu sẽ giúp chất lượng sản phẩm tốt hơn.

## 7. AI giúp gì / AI sai gì
- Giúp: AI hỗ trợ tăng tốc cả frontend và backend, đồng thời gợi ý thêm nhiều test case hữu ích để kiểm thử agent.
- Sai/hạn chế: phần frontend phải chỉnh lại nhiều lần do code sinh ra chưa đồng nhất phong cách, dẫn đến các đoạn code khác nhau trong cùng codebase và tốn thời gian chuẩn hóa.