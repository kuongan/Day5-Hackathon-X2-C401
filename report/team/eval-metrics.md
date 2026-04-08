# Eval metrics + threshold

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
