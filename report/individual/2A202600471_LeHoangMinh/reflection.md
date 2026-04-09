# Individual reflection — Lê Hoàng Minh (AI20K- 2A202600471)

## 1. Role
UX/UI designer + Connect backend với frontend sử dụng FastAPI

## 2. Đóng góp cụ thể
- Thiết kế UI cho sản phẩm và test prompt trên UI để đánh giá trải nghiệm người dùng
- Connect backend( các agent lên frontend)
- Ước tính ROI và Failure mode

## 3. SPEC mạnh/yếu
- Mạnh nhất: Low confidence - Team nghĩ ra các test case khi đưa thiếu thông tin hoặc không rõ ràng, chatbot cần phải hỏi lại thông tin 
- Yếu nhất: Fail mode - Prompt chưa quá hoàn chỉnh, các trường hợp mà user prompt có một só tình trạng nguy hiểm chưa được AI tư vấn đi khám ngay lập tực. Scope của project chưa có tính thực tiễn cao

## 4. Đóng góp khác
- Nghĩ prompt dựa theo các test case và test trên frontend

## 5. Điều học được
Trước hackathon nghĩ precision và recall chỉ là metric kỹ thuật.
Sau khi thiết kế AI triage mới hiểu: chọn recall cao hơn cho khoa cấp cứu
(bỏ sót nguy hiểm hơn false alarm) nhưng precision cao hơn cho khoa chuyên sâu
(gợi ý sai gây lãng phí thời gian bệnh nhân). Metric là product decision,
không chỉ engineering decision.

## 6. Nếu làm lại
Scope cần phải được đưa vào thực tiễn nhiều hơn, 
Prompt cần chỉn chu hơn
Cố gắng để process thinking và call tools của model nhanh hơn, hiện tại đang hơi lâu ~30-40s

## 7. AI giúp gì / AI sai gì
- **Giúp:** Dùng openai key cho model, dùng Gemini để gợi ý các edge case
- **Sai/mislead:** Chatbot chưa qua rõ ràng khi prompt của người dùng có tính nghiêm trọng đến tính mạng. Có lúc sẽ nói người dùng nên đi khám ngay, có lúc chỉ đưa ra thông tin về bệnh đó -> Chưa thống nhất