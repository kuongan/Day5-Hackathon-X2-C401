from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import sys
from typing import Any, Dict, List, Sequence

import faiss
import numpy as np
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.model.agent.chat import DiseaseArticle, DiseaseRetrievalResult, RetrieveDiseaseInput

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.append(str(PROJECT_ROOT))

from backend.utils.llm_manager import get_embeddings


DATA_DIR = PROJECT_ROOT / "data"
FAISS_DIR = DATA_DIR / "faiss"
DB_PATH = DATA_DIR / "medical_chatbot.db"
DISEASE_INDEX_PATH = FAISS_DIR / "diseases_body.index"
DISEASE_MAPPING_PATH = FAISS_DIR / "diseases_body_mapping.json"


def _load_mapping(path: Path) -> List[Dict[str, Any]]:
	with path.open("r", encoding="utf-8") as f:
		payload = json.load(f)
	if not isinstance(payload, list):
		raise ValueError("Invalid mapping format: expected a list")
	return payload


def _extract_candidate_ids(
	distances: np.ndarray,
	indices: np.ndarray,
	mapping: Sequence[Dict[str, Any]],
) -> List[tuple[int, float]]:
	candidates: List[tuple[int, float]] = []
	if distances.size == 0 or indices.size == 0:
		return candidates

	for score, raw_index in zip(distances[0], indices[0]):
		idx = int(raw_index)
		if idx < 0 or idx >= len(mapping):
			continue

		metadata = mapping[idx].get("metadata", {})
		if not isinstance(metadata, dict):
			continue
		if metadata.get("source") != "diseases":
			continue

		disease_id = metadata.get("id")
		if isinstance(disease_id, int):
			candidates.append((disease_id, float(score)))

	# Keep lowest distance per disease id.
	best: Dict[int, float] = {}
	for disease_id, score in candidates:
		if disease_id not in best or score < best[disease_id]:
			best[disease_id] = score
	return sorted(best.items(), key=lambda item: item[1])


def _query_articles(candidate_ids: List[int], score_map: Dict[int, float]) -> List[DiseaseArticle]:
	if not candidate_ids:
		return []

	placeholders = ",".join("?" for _ in candidate_ids)
	sql = f"""
		SELECT
			d.id,
			COALESCE(d.title, ''),
			COALESCE(d.search_text, ''),
			COALESCE(d.detail_sections, ''),
			COALESCE(d.url, b.url, '') AS source_url
		FROM diseases d
		LEFT JOIN body_articles b ON b.url = d.url
		WHERE d.id IN ({placeholders})
	"""

	with sqlite3.connect(DB_PATH) as conn:
		rows = conn.execute(sql, candidate_ids).fetchall()

	articles: List[DiseaseArticle] = []
	for disease_id, title, summary, detail_sections, source_url in rows:
		if not source_url:
			source_url = "Khong co nguon URL trong co so du lieu"
		articles.append(
			DiseaseArticle(
				disease_id=int(disease_id),
				title=str(title),
				summary=str(summary),
				detail_sections=str(detail_sections),
				source_url=str(source_url),
				score=score_map.get(int(disease_id), 9999.0),
			)
		)
	return sorted(articles, key=lambda item: item.score)


@tool(args_schema=RetrieveDiseaseInput)
def retrieve_disease_info(query: str, top_k: int = 3) -> str:
	"""Retrieve disease information from FAISS and join with SQLite article details."""
	if not DB_PATH.exists():
		result = DiseaseRetrievalResult(
			query=query,
			total_hits=0,
			articles=[],
			warning=f"Database not found: {DB_PATH}",
		)
		return result.model_dump_json(ensure_ascii=False)

	if not DISEASE_INDEX_PATH.exists() or not DISEASE_MAPPING_PATH.exists():
		result = DiseaseRetrievalResult(
			query=query,
			total_hits=0,
			articles=[],
			warning="Disease FAISS index or mapping file is missing",
		)
		return result.model_dump_json(ensure_ascii=False)

	try:
		index = faiss.read_index(str(DISEASE_INDEX_PATH))
		mapping = _load_mapping(DISEASE_MAPPING_PATH)
		embeddings = get_embeddings(model_name="text-embedding-3-small")
		query_vector = np.array([embeddings.embed_query(query)], dtype="float32")

		distances, indices = index.search(query_vector, top_k)
		ranked = _extract_candidate_ids(distances=distances, indices=indices, mapping=mapping)
		score_map = {disease_id: score for disease_id, score in ranked}
		candidate_ids = [disease_id for disease_id, _ in ranked]

		articles = _query_articles(candidate_ids=candidate_ids, score_map=score_map)
		result = DiseaseRetrievalResult(
			query=query,
			total_hits=len(articles),
			articles=articles,
			warning=None if articles else "No matching disease content found",
		)
		return result.model_dump_json(ensure_ascii=False)
	except Exception as exc:
		result = DiseaseRetrievalResult(
			query=query,
			total_hits=0,
			articles=[],
			warning=f"Retrieval failed: {exc}",
		)
		return result.model_dump_json(ensure_ascii=False)
	
if __name__ == "__main__":
    print("--- Đang bắt đầu test Tool: retrieve_disease_info ---")
    
    # 1. Định nghĩa câu hỏi test (Query)
    test_query = "Triệu chứng bệnh sốt xuất huyết là gì?"
    
    result_json = retrieve_disease_info.invoke({
        "query": test_query,
        "top_k": 3
    })
    
    # 3. Parse kết quả để hiển thị đẹp mắt
    result_data = json.loads(result_json)
    
    print(f"\n[QUERY]: {result_data.get('query')}")
    print(f"[TOTAL HITS]: {result_data.get('total_hits')}")
    
    if result_data.get('warning'):
        print(f"[WARNING]: {result_data.get('warning')}")
        
    if result_data.get('articles'):
        print("\n[DANH SÁCH BỆNH TÌM THẤY]:")
        for i, article in enumerate(result_data['articles'], 1):
            print(f"--- Kết quả {i} ---")
            print(f"ID: {article['disease_id']}")
            print(f"Tên bệnh: {article['title']}")
            print(f"Score: {article['score']:.4f}")
            print(f"URL: {article['source_url']}")
            print(f"Tóm tắt: {article['summary'][:100]}...")
    else:
        print("\n❌ Không tìm thấy bài viết nào khớp với câu hỏi.")