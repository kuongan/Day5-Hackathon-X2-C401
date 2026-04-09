# Individual reflection - Nguyễn Trần Khương An (2A202600222)

## 1. Role
Đóng vai trò developer trong việc xây dựng luồng hệ thống, hỗ trợ crawl dữ liệu và phát triển tính năng chat agent.

## 2. Đóng góp cụ thể
- Thiết kế pipeline cho dự án, hỗ trợ phân công công việc, thuyết trình demo.
- Trực tiếp code các phần chính sau:
	- Xây dựng luồng xử lý cho chat agent (nhận input, định tuyến tác vụ và trả kết quả theo ngữ cảnh).
	- Hỗ trợ code phần crawl và chuẩn hóa dữ liệu đầu vào để phục vụ truy vấn/tra cứu.
    - Xây dựng relational database schema và tích hợp script indexing vector database. 
	- Chỉnh sửa prompt và tool wiring để agent hoạt động ổn định hơn trong các ca test.
- Tổng hợp, review code và hỗ trợ debug để đảm bảo chất lượng chung của sản phẩm.

## 3. SPEC mạnh/yếu
- Mạnh nhất: Mục Low confidence. Team đã xây dựng các test case cho tình huống người dùng cung cấp thiếu hoặc không rõ thông tin; khi đó chatbot cần chủ động hỏi lại để làm rõ.
- Yếu nhất: Mục Fail mode. Prompt chưa đủ hoàn thiện do thời gian ngắn nên chưa xây dựng long-term memory để lưu trữ tốt. 

## 4. Đóng góp khác
- Hướng dẫn, hỗ trợ các bạn trong việc code và fix bug.
- Kết hợp cùng các bạn tìm kiếm ý tưởng và research thị trường. 

## 5. Điều học được
Trước hackathon, mình nghĩ precision và recall chỉ là các metric kỹ thuật.
Sau khi thiết kế AI triage, mình hiểu rằng việc chọn metric là một quyết định sản phẩm:
- Với khoa cấp cứu, cần ưu tiên recall cao hơn vì bỏ sót ca nguy hiểm nghiêm trọng hơn false alarm.
- Với khoa chuyên sâu, cần ưu tiên precision cao hơn để tránh gợi ý sai và làm lãng phí thời gian của bệnh nhân.

Nói cách khác, metric không chỉ là engineering decision mà còn là product decision.

## 6. Nếu làm lại
Mình sẽ tối ưu prompt kỹ hơn và phát triển thêm các luồng bất lợi (edge cases) để tăng độ an toàn và tính thực tế của hệ thống.

## 7. AI giúp gì / AI sai gì
- Giúp: Claude hỗ trợ gợi ý schema; GitHub Copilot hỗ trợ code, giúp tiết kiệm thời gian triển khai.
- Sai/mislead: Claude từng gợi ý thêm tính năng "tìm kiếm bệnh viện gần nhất" cho chatbot. Ý tưởng này tốt, nhưng vượt quá scope của hackathon và có nguy cơ gây scope creep nếu không kiểm soát.

Bài học rút ra: AI rất tốt cho brainstorm, nhưng con người vẫn phải quyết định phạm vi thực thi phù hợp.
