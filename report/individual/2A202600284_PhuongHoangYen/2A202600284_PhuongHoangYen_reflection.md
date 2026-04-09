### reflection.md

# Individual reflection — Phương Hoàng Yến (2A202600284)

## 1. Role
- Làm slide
- Viết orchestration agent
- Làm phần 2 SPEC user-stories

## 2. Đóng góp cụ thể
- Thiết kế slide giới thiệu về bản SPEC cho đề tài
- Viết và test phần orchestration agent gồm 3 tools là hiểu query, điều phối sub-agent và tổng hợp check lỗi output từ sub-agent và trả về người dùng
- Viết phần user-stories cho SPEC của nhóm

## 3. SPEC mạnh/yếu
- Mạnh nhất: user-stories: low-confidence: nhóm nghĩ ra các test case thử thách agent trong việc user cung cấp thông tin mơ hồ --> agent nhận ra và hỏi kĩ hơn thay vì cố ép sang một câu trả lời khác
- Yếu nhất: Fail mode - Prompt chưa quá hoàn chỉnh, các trường hợp mà user prompt có một số tình trạng nguy hiểm chưa được AI tư vấn đi khám ngay lập tức. Scope của project chưa có tính thực tiễn cao
## 4. Đóng góp khác


## 5. Điều học được
- Cách xây dựng agent từ bước lên ý tưởng --> xây dựng pipeline các agent + tool
- Cách load module không sài import
- Cách tổ chức dự án chuẩn từ model -> product. Trước hackathon chỉ tập trung vào xây dựng model 

## 6. Nếu làm lại
- Sẽ tập trung brainstorm vài ý tưởng nữa cho đề bài. Connect với các nhóm làm cùng domain để khảo sát và tham khảo ý tưởng. Xây dựng system prompt chặt chẽ hơn vì kết quả cuối của model phụ thuộc nhiều vào nó.

## 7. AI giúp gì / AI sai gì
- **Giúp:** dùng Copilot hỗ trợ gen code cho phần orchestration agent. Dùng gemini để test khả năng của AI trong lĩnh vực này để tìm ra các điểm đột phá
- **Sai/mislead:** 
    + Copilot không xử lý và detect được việc có 1 package đặt tên là "chat-agent" -> dẫn tới import không thành công package, coder phải tự xử lý bằng sử dụng load module hoặc đổi tên folder
    