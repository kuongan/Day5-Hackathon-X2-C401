# Test 1

 "inputs": {
    "conversation_id": "chat-1775727212612",
    "question": "Thuốc paracetamol dùng cho trẻ 5 tuổi như thế nào?"
  },

    "outputs": {
    "answer": "Paracetamol là thuốc thường dùng để giảm đau và hạ sốt cho trẻ em. Đối với trẻ 5 tuổi, liều lượng khuyến cáo là khoảng 10-15 mg/kg trọng lượng cơ thể, cách 4-6 giờ nếu cần, không vượt quá 5 lần trong 24 giờ. Có nhiều dạng bào chế như viên nén, siro, và bột pha uống. Lưu ý không tự ý dùng cho trẻ dưới 2 tuổi và cần ngừng thuốc nếu có triệu chứng dị ứng hoặc nếu triệu chứng không cải thiện sau vài ngày. Hãy tham khảo ý kiến bác sĩ trước khi sử dụng để đảm bảo an toàn.",

"intent": "medicine",}
    "route_to": [
      "medicine"
    ],

  # Test 2

  "inputs": {
    "conversation_id": "default",
    "question": "có muối ăn nào thay thế loại muối ăn nacl ko"
  },

    "outputs": {
    "answer": "Hiện tại, tôi không thể cung cấp thông tin về các loại muối ăn thay thế cho NaCl (muối ăn thông thường) vì câu hỏi của bạn không liên quan đến sức khỏe hoặc bệnh lý. Nếu bạn có câu hỏi nào khác liên quan đến sức khỏe, hãy cho tôi biết nhé!",}

 "intent": "chat",
    "route_to": [
      "chat"
    ]

# Test 3

  "inputs": {
    "conversation_id": "default",
    "question": "Triệu chứng sốt cao có nguy hiểm không?"
  },

    "outputs": {
    "answer": "Triệu chứng sốt cao có thể là dấu hiệu của nhiều bệnh lý khác nhau, trong đó có sốt phát ban. Sốt phát ban thường không nguy hiểm và sẽ giảm triệu chứng cũng như hồi phục hoàn toàn nếu được nghỉ ngơi và điều trị đầy đủ. Tuy nhiên, trong một số trường hợp hiếm gặp, sốt quá cao có thể dẫn đến biến chứng nguy hiểm. Nếu bạn hoặc người thân gặp phải triệu chứng sốt cao kéo dài hoặc có các dấu hiệu khác như phát ban không chuyển biến tốt, cần gặp bác sĩ để được tư vấn và điều trị kịp thời. \n\nNguồn: [Vinmec](https://www.vinmec.com/vie/benh/sot-phat-ban-2970)\n\nNguon tham khao:\n- https://www.vinmec.com/vie/benh/sot-phat-ban-2970\n- https://www.vinmec.com/vie/benh/huyet-khoi-tinh-mach-sau-2964",
    }

 "intent": "chat",
    "route_to": [
      "chat" ]

# Test 4

  "inputs": {
    "conversation_id": "default",
    "question": "tôi muốn đặt lịch bác Đỗ Tát Cường vào ngày 10/4"
  },

    "outputs": {
    "answer": "Bác sĩ Đỗ Tất Cường, chuyên khoa Tim mạch, làm việc tại Trung tâm hồi sức và cấp cứu - Bệnh viện Đa khoa Vinmec Smart City. Dưới đây là lịch trống của bác sĩ vào ngày 10 tháng 4 năm 2026:\n\n- Ngày 10 tháng 4 năm 2026: 09:30, 14:00, 14:30, 15:00\n\nBạn muốn đặt lịch hẹn vào giờ nào?"  }

"intent": "booking",
    "route_to": [
      "booking"
    ]

# Test 5

"inputs": {
    "conversation_id": "default",
    "question": "Tôi bị ho kéo dài, nên đi khám gì?"},

    "outputs": {
    "answer": "Ho kéo dài có thể là triệu chứng của nhiều bệnh lý khác nhau, bao gồm các vấn đề về đường hô hấp như khí phế thũng, viêm phế quản mãn tính, hoặc các bệnh lý khác. Để xác định nguyên nhân chính xác và có phương pháp điều trị phù hợp, bạn nên đi khám bác sĩ chuyên khoa hô hấp.\n\nCác triệu chứng đi kèm như khó thở, ho có đờm, hoặc cảm giác nặng ngực cũng cần được chú ý. Bác sĩ có thể yêu cầu thực hiện các xét nghiệm như chụp X-quang phổi, hô hấp ký, hoặc xét nghiệm máu để chẩn đoán chính xác tình trạng của bạn.\n\nNếu bạn có các triệu chứng nghiêm trọng hoặc kéo dài, hãy gặp bác sĩ ngay để được tư vấn và điều trị kịp thời. \n\nNguồn tham khảo: [Vinmec](https://www.vinmec.com/vie/benh/hoi-chung-qt-keo-dai-3771), [Vinmec](https://www.vinmec.com/vie/benh/khi-phe-thung-3088).\n\nNguon tham khao:\n- https://www.vinmec.com/vie/benh/hoi-chung-qt-keo-dai-3771\n- https://www.vinmec.com/vie/benh/hoi-chung-klinefelter-3737\n- https://www.vinmec.com/vie/benh/khi-phe-thung-3088",
         }

"intent": "chat",
    "route_to": [
      "chat"
    ]
