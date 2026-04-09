# Medicine Agent Implementation Guide

## Overview
`medicine-agent` là một LangGraph-based agent chuyên trợ người dùng tra cứu thông tin về thuốc, liều lượng, chỉ định, chống chỉ định, và tác dụng phụ.

## Architecture

### Project Structure
```
backend/
├── model/
│   ├── medicine.py              # Pydantic models for drug data
│   └── agent/
│       └── medicine.py          # Request/Response models for agent
├── agent/
│   ├── base_agent.py            # BaseAgent abstract class (LangGraph)
│   └── medicine-agent/
│       ├── agent.py             # MedicineQAAgent implementation
│       ├── tools.py             # 5 medicine query tools
│       └── prompt.py            # System prompt for agent
data/
├── medical_chatbot.db           # SQLite database with medicine data
└── faiss/
    ├── medicines.index          # FAISS vector index for medicines
    └── medicines_mapping.json    # FAISS ID-to-metadata mapping
```

## Models (backend/model/medicine.py)

### Input Models
- **DrugSearchInput**: Query schema for `get_drug_info` tool
  - `name`: str - Tên thuốc cần tìm
  - `top_k`: int (default=5) - Số kết quả trả về

- **DosageSearchInput**: Query schema for `get_dosage` tool
  - `medicine_name`: str - Tên thuốc cần tìm liều lượng

- **IndicationSearchInput**: Query schema for `get_drugs_by_indication` tool
  - `indication`: str - Tên bệnh/chỉ định cần tìm thuốc
  - `top_k`: int (default=5) - Số kết quả trả về

- **ContraindicationInput**: Query schema for `get_contraindications` tool
  - `medicine_name`: str - Tên thuốc cần kiểm tra

- **SideEffectsInput**: Query schema for `get_side_effects` tool
  - `medicine_name`: str - Tên thuốc cần kiểm tra

### Data Models
- **MedicineDetailed**: Chi tiết về một loại thuốc
  - id, name, form, drug_group, tag
  - indications, contraindications, precautions, side_effects, dosage
  - similarity_score: float (từ FAISS search)

- **MedicineRetrievalResult**: Kết quả truy vấn từ tools
  - query: str
  - total_hits: int
  - medicines: List[MedicineDetailed]
  - warning: Optional[str]

### Agent Models (backend/model/agent/medicine.py)
- **MedicineQARequest**: Request model
  - question: str

- **MedicineQAResponse**: Response model
  - answer: str - Câu trả lời từ agent
  - sources: List[str] - Danh sách URLs nguồn

## Tools (backend/agent/medicine-agent/tools.py)

Tất cả 5 tools lấy dữ liệu từ SQLite database và sử dụng FAISS cho vector search khi cần:

### 1. `get_drug_info(name, top_k=5)` 
**Mô tả:** Tìm kiếm chi tiết về thuốc theo tên  
**Input:** 
- name: Tên thuốc
- top_k: Số kết quả (1-20)

**Output:** JSON string với MedicineRetrievalResult
- Dùng FAISS vector search để tìm thuốc tương tự
- Trả về: id, name, form, drug_group, indications, contraindications, dosage, side_effects, etc.

### 2. `get_dosage(medicine_name)`
**Mô tả:** Tìm liều lượng sử dụng cho loại thuốc  
**Input:**
- medicine_name: Tên thuốc

**Output:** JSON với DosageRetrievalResult
- Trả về: medicine_id, medicine_name, form, dosage, url
- Flexible matching với LIKE query

### 3. `get_drugs_by_indication(indication, top_k=5)`
**Mô tả:** Tìm các thuốc để điều trị một bệnh/chỉ định  
**Input:**
- indication: Tên bệnh/tình trạng (vd: "sốt cao", "viêm họng")
- top_k: Số kết quả (1-20)

**Output:** JSON với IndicationRetrievalResult
- Dùng FAISS vector search trên indication field
- Trả về medicines với relevance_score

### 4. `get_contraindications(medicine_name)`
**Mô tả:** Lấy chống chỉ định và cảnh báo cho thuốc  
**Input:**
- medicine_name: Tên thuốc

**Output:** JSON response
- contraindications, precautions, side_effects
- matches_count: số lượng kết quả tìm thấy

### 5. `get_side_effects(medicine_name)`
**Mô tả:** Lấy tác dụng phụ của thuốc  
**Input:**
- medicine_name: Tên thuốc

**Output:** JSON response
- side_effects, precautions
- matches_count

## Agent Implementation (backend/agent/medicine-agent/agent.py)

### MedicineQAAgent Class
Kế thừa `BaseAgent[BaseAgentState]`:

```python
class MedicineQAAgent(BaseAgent[BaseAgentState]):
    def _get_tools(self) -> list[Any]:
        # Return 5 medicine query tools
        
    def _get_agent_prompt(self) -> str:
        # Return SYSTEM_PROMPT from prompt.py
        
    def _create_initial_state(self, query, conversation_id) -> BaseAgentState:
        # Create initial state with HumanMessage
        
    def _extract_result(self, state) -> MedicineQAResponse:
        # Extract answer and sources from final state
```

### Usage - Function Interface

```python
from backend.agent.medicine_agent.agent import ask_medicine_question

# Simple query
response = ask_medicine_question("Liều lượng paracetamol là gì?")
print(response.answer)
# Output: "Paracetamol 325mg tablets are typically dosed at..."
print(response.sources)
# ['http://example.com/medicine/paracetamol']
```

### Usage - Agent Direct

```python
from backend.agent.medicine_agent.agent import build_medicine_qa_agent

agent = build_medicine_qa_agent(
    model_name="gpt-4o-mini",
    temperature=0.0
)

result = agent.process(
    query="Thuốc aspirin có tác dụng gì?",
    conversation_id="user_123"
)
```

## System Prompt (backend/agent/medicine-agent/prompt.py)

Agent hướng dẫn để:
- Luôn sử dụng tools khi câu hỏi liên quan đến thuốc
- Chỉ trả lời dựa trên dữ liệu đã truy vấn
- Không self-hallucinate ngoài dữ liệu
- Khuyên người dùng gặp dược sĩ/bác sĩ khi cần
- Không thay thế lời tư vấn y tế chuyên nghiệp

## Database Schema (data/medical_chatbot.db)

Table `medicines`:
```sql
CREATE TABLE medicines (
    id INTEGER PRIMARY KEY,
    name TEXT,
    url TEXT,
    form TEXT,                  -- Dạng bào chế (tablet, injection, etc.)
    drug_group TEXT,            -- Nhóm thuốc (antibiotics, antipyretics, etc.)
    tag TEXT,
    indications TEXT,           -- Chỉ định sử dụng
    contraindications TEXT,     -- Chống chỉ định
    precautions TEXT,           -- Cảnh báo/lưu ý
    side_effects TEXT,          -- Tác dụng phụ
    dosage TEXT,                -- Liều lượng khuyến cáo
    notes TEXT,
    search_text TEXT            -- Text field cho full-text search
);
```

## FAISS Integration

### Vector Search
- **Index:** `data/faiss/medicines.index`
- **Mapping:** `data/faiss/medicines_mapping.json`
- **Embeddings:** text-embedding-3-small (OpenAI)

### Usage Pattern
1. Convert query text to vector (get_embeddings)
2. Search FAISS index for top_k matches
3. Extract medicine IDs từ mapping
4. Query SQLite để lấy full details
5. Rank results by similarity_score

## Testing

### Test Tools Directly
```python
from backend.agent.medicine_agent.tools import get_drug_info

result = get_drug_info.invoke({"name": "aspirin", "top_k": 3})
# Returns JSON string
data = json.loads(result)
```

### Test Agent
```python
from backend.agent.medicine_agent.agent import ask_medicine_question

response = ask_medicine_question("Aspirin có công dụng gì?")
```

## Integration with REST API

Example endpoint (backend/main.py):
```python
from fastapi import FastAPI
from backend.agent.medicine_agent.agent import ask_medicine_question

app = FastAPI()

@app.post("/api/medicine/ask")
async def query_medicine(question: str):
    response = ask_medicine_question(question)
    return {
        "answer": response.answer,
        "sources": response.sources
    }
```

## Error Handling

All tools return JSON with `warning` field if:
- Database file not found
- FAISS index missing
- No results found
- Other retrieval errors

Agent catches APIConnectionError (OpenAI) and returns friendly error message.

## Important Notes

1. **Folder naming:** `medicine-agent` uses hyphen, so it requires `importlib` for imports from outside
2. **Character encoding:** Đảm bảo UTF-8 encoding khi xử lý Vietnamese text
3. **Temperature:** Set to 0.0 để deterministic responses (strict adherence to tools)
4. **Memory:** Conversation history được lưu qua `conversation_id` khi enable_memory=True

## Future Enhancements

1. Drug interaction checker (check 2+ drugs together)
2. Allergen warnings
3. Price information
4. Pharmacy availability
5. Drug alternatives and substitutes
6. Clinical trial information
7. Drug manufacturer details
