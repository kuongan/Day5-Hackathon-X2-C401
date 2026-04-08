# Phân tích ROI 3 kịch bản: Vinmec AI Chatbot (Sử dụng OpenAI GPT-4o-mini)

**Bối cảnh:** Chatbot hỗ trợ triage (phân loại bệnh), giải đáp thủ tục và đặt lịch khám. Hệ thống sử dụng kiến trúc RAG kết hợp với LLM GPT-4o-mini để tối ưu tốc độ phản hồi và chi phí inference trên mỗi lượt chat.

---

## Bảng ước lượng ROI

|   | Conservative (Thận trọng) | Realistic (Thực tế) | Optimistic (Lạc quan) |
|---|-------------|-----------|------------|
| **Assumption** | 500 queries/ngày.<br>Tỷ lệ AI tự giải quyết thành công (Task Resolution): **20%** | 2,000 queries/ngày.<br>Tỷ lệ giải quyết thành công: **50%** | 5,000 queries/ngày.<br>Tỷ lệ giải quyết thành công: **80%** |
| **Cost** | ~$15/ngày<br>*(API GPT-4o-mini: $2 + Infra/Vector DB: $13)* | ~$30/ngày<br>*(API GPT-4o-mini: $10 + Infra: $20)* | ~$60/ngày<br>*(API GPT-4o-mini: $25 + Infra: $35)* |
| **Benefit** | Giải quyết 100 queries/ngày.<br>Tiết kiệm ~8 giờ làm việc của nhân viên CSKH (ước tính $3/giờ) = **$24/ngày**.<br>Giảm tải giờ cao điểm. | Giải quyết 1,000 queries/ngày.<br>Tiết kiệm ~83 giờ làm việc của CSKH = **$249/ngày**.<br>Tăng 5% tỷ lệ chốt lịch khám trực tuyến. | Giải quyết 4,000 queries/ngày.<br>Tiết kiệm ~333 giờ làm việc của CSKH = **$1,000/ngày**.<br>Giảm 30% nhân sự trực tổng đài ca đêm. |
| **Net** | **+$9/ngày**<br>*(Hòa vốn, chủ yếu thu thập data cho hệ thống RAG)* | **+$219/ngày**<br>*(~$6,500/tháng, đủ bù đắp chi phí team vận hành)* | **+$940/ngày**<br>*(~$28,000/tháng, sinh lời rõ rệt)* |

**Kill criteria (Khi nào nên dừng/Pivot?):** 1. Tỷ lệ Task Resolution (AI tự xử lý xong không cần chuyển người) duy trì **< 15%** sau 4 tuần launching.
2. Chi phí API OpenAI vượt quá mức dự kiến (> $100/ngày) nhưng CSAT (chỉ số hài lòng của khách hàng) rớt xuống dưới 3.0/5.0.
3. *Về mặt rủi ro (Red Flag):* Phát hiện model bị hallucinate (tư vấn sai chuyên môn y tế / sai giá tiền) **> 1%** trong tập dữ liệu audit hàng tuần, đe dọa trực tiếp đến trải nghiệm bệnh nhân.

---
*AI Product Canvas — Spec Draft — VinUni A20 — AI Thực Chiến · 2026*