### reflection.md

```markdown
# Individual reflection — Nguyễn Minh Châu (AI20K001)

## 1. Role
Coder.

## 2. Đóng góp cụ thể
- Phụ trách crawl dữ liệu medicine trên trang web vinmec. Xây dựng pipeline crawl + parse HTML.
- Viết booking agent, system prompt cho booking agent.
- Hỗ trợ viết báo cáo (Eval Metrics). Phân tích trade-off giữa precision vs recall trong bối cảnh y tế.

## 3. SPEC mạnh/yếu
- Mạnh nhất: failure modes — nhóm nghĩ ra được case "triệu chứng chung chung"
  mà AI gợi ý quá rộng, và có mitigation cụ thể (hỏi thêm câu follow-up)
- Yếu nhất: ROI — 3 kịch bản các số liệu chỉ có thể dựa trên cảm giác, không dựa vào các số liệu thực
  Nên tách assumption rõ hơn.

## 4. Đóng góp khác
- Test các trường hợp prompt khác nhau.
  - Edge cases (triệu chứng mơ hồ, user hỏi nhiều intent cùng lúc)
  - Jailbreak nhẹ (hỏi ngoài scope y tế)
- Giúp hỗ trợ các thành viên viết agent.

## 5. Điều học được
- Model tốt ≠ hệ thống tốt
- Trước hackathon vẫn chưa biết cách code agent.
- Sau khi hackathon hiểu rõ hơn về các lệnh github và Git workflow (branch, merge, conflict).

## 6. Nếu làm lại
- Sẽ viết file agent dựa trên base agent và code có tổ chức hơn.
- Giới hạn scope chặt hơn, tránh over-engineering trong hackathon

## 7. AI giúp gì / AI sai gì
- **Giúp:** dùng Claude để brainstorm failure modes.
  Nhóm dùng Gemini để sinh prompt nhanh qua AI Studio để nhóm tiện chỉnh sửa phù hợp và nhanh hơn.
- **Sai/mislead:** Claude gợi ý thêm feature scope quá lớn cho hackathon. AI không hiểu context thực tế (time constraint, user behavior) -> cần filter lại bằng tư duy con người.
```