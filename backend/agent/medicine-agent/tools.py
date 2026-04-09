"""
Medicine agent tools for drug information, dosage, and indications lookup.
Tools query SQLite database and use FAISS for similarity-based search.
"""
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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.append(str(PROJECT_ROOT))

from backend.utils.llm_manager import get_embeddings
from backend.model.agent.medicine import (
	DrugSearchInput,
	DosageSearchInput,
	IndicationSearchInput,
	ContraindicationInput,
	SideEffectsInput,
	MedicineDetailed,
	DosageInfo,
	MedicineIndicationResult,
	MedicineRetrievalResult,
	DosageRetrievalResult,
	IndicationRetrievalResult,
)


DATA_DIR = PROJECT_ROOT / "data"
FAISS_DIR = DATA_DIR / "faiss"
DB_PATH = DATA_DIR / "medical_chatbot.db"
MEDICINES_INDEX_PATH = FAISS_DIR / "medicines.index"
MEDICINES_MAPPING_PATH = FAISS_DIR / "medicines_mapping.json"


def _load_mapping(path: Path) -> List[Dict[str, Any]]:
	"""Load FAISS mapping file"""
	with path.open("r", encoding="utf-8") as f:
		payload = json.load(f)
	if not isinstance(payload, list):
		raise ValueError("Invalid mapping format: expected a list")
	return payload


def _extract_medicine_ids(
	distances: np.ndarray,
	indices: np.ndarray,
	mapping: Sequence[Dict[str, Any]],
) -> List[tuple[int, float]]:
	"""Extract medicine IDs from FAISS search results with distance scores"""
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
		if metadata.get("source") != "medicines":
			continue

		medicine_id = metadata.get("id")
		if isinstance(medicine_id, int):
			candidates.append((medicine_id, float(score)))

	# Keep lowest distance per medicine id
	best: Dict[int, float] = {}
	for medicine_id, score in candidates:
		if medicine_id not in best or score < best[medicine_id]:
			best[medicine_id] = score
	return sorted(best.items(), key=lambda item: item[1])


def _query_medicines_by_ids(medicine_ids: List[int], score_map: Dict[int, float]) -> List[MedicineDetailed]:
	"""Query medicines from SQLite by IDs and attach similarity scores"""
	if not medicine_ids:
		return []

	placeholders = ",".join("?" for _ in medicine_ids)
	sql = f"""
		SELECT
			id,
			name,
			url,
			form,
			drug_group,
			tag,
			indications,
			contraindications,
			precautions,
			side_effects,
			dosage,
			notes,
			search_text
		FROM medicines
		WHERE id IN ({placeholders})
	"""

	with sqlite3.connect(DB_PATH) as conn:
		rows = conn.execute(sql, medicine_ids).fetchall()

	medicines: List[MedicineDetailed] = []
	for row in rows:
		(
			medicine_id, name, url, form, drug_group, tag,
			indications, contraindications, precautions, side_effects,
			dosage, notes, search_text
		) = row
		
		medicines.append(
			MedicineDetailed(
				id=medicine_id,
				name=name,
				url=url,
				form=form,
				drug_group=drug_group,
				tag=tag,
				indications=indications,
				contraindications=contraindications,
				precautions=precautions,
				side_effects=side_effects,
				dosage=dosage,
				notes=notes,
				search_text=search_text,
				similarity_score=score_map.get(medicine_id, 9999.0),
			)
		)
	return sorted(medicines, key=lambda x: x.similarity_score or 9999.0)


@tool(args_schema=DrugSearchInput)
def get_drug_info(name: str, top_k: int = 5) -> str:
	"""
	Retrieve detailed drug information by name.
	Uses FAISS vector search for semantic similarity matching.
	
	Args:
		name: Tên thuốc cần tìm (drug name to search for)
		top_k: Số kết quả trả về (number of results to return)
	
	Returns:
		JSON string with medicine details including indications, contraindications, etc.
	"""
	if not DB_PATH.exists():
		result = MedicineRetrievalResult(
			query=name,
			total_hits=0,
			medicines=[],
			warning=f"Database not found: {DB_PATH}",
		)
		return result.model_dump_json(ensure_ascii=False)

	if not MEDICINES_INDEX_PATH.exists() or not MEDICINES_MAPPING_PATH.exists():
		result = MedicineRetrievalResult(
			query=name,
			total_hits=0,
			medicines=[],
			warning="Medicines FAISS index or mapping file is missing",
		)
		return result.model_dump_json(ensure_ascii=False)

	try:
		index = faiss.read_index(str(MEDICINES_INDEX_PATH))
		mapping = _load_mapping(MEDICINES_MAPPING_PATH)
		embeddings = get_embeddings(model_name="text-embedding-3-small")
		query_vector = np.array([embeddings.embed_query(name)], dtype="float32")

		distances, indices = index.search(query_vector, top_k)
		ranked = _extract_medicine_ids(distances=distances, indices=indices, mapping=mapping)
		score_map = {medicine_id: score for medicine_id, score in ranked}
		candidate_ids = [medicine_id for medicine_id, _ in ranked]

		medicines = _query_medicines_by_ids(medicine_ids=candidate_ids, score_map=score_map)
		result = MedicineRetrievalResult(
			query=name,
			total_hits=len(medicines),
			medicines=medicines,
			warning=None if medicines else "No matching medicines found",
		)
		return result.model_dump_json(ensure_ascii=False)
	except Exception as exc:
		result = MedicineRetrievalResult(
			query=name,
			total_hits=0,
			medicines=[],
			warning=f"Retrieval failed: {exc}",
		)
		return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=DosageSearchInput)
def get_dosage(medicine_name: str) -> str:
	"""
	Retrieve dosage information for a specific medicine.
	
	Args:
		medicine_name: Tên thuốc cần tìm liều lượng (medicine name)
	
	Returns:
		JSON string with dosage details for matching medicines
	"""
	if not DB_PATH.exists():
		result = DosageRetrievalResult(
			query=medicine_name,
			medicines=[],
			warning=f"Database not found: {DB_PATH}",
		)
		return result.model_dump_json(ensure_ascii=False)

	try:
		with sqlite3.connect(DB_PATH) as conn:
			# Use LIKE for flexible name matching
			sql = """
				SELECT id, name, form, dosage, url
				FROM medicines
				WHERE name LIKE ? OR search_text LIKE ?
				LIMIT 10
			"""
			search_pattern = f"%{medicine_name}%"
			rows = conn.execute(sql, (search_pattern, search_pattern)).fetchall()

		dosage_infos: List[DosageInfo] = []
		for row in rows:
			dosage_infos.append(
				DosageInfo(
					medicine_id=row[0],
					medicine_name=row[1],
					form=row[2],
					dosage=row[3],
					url=row[4],
				)
			)

		result = DosageRetrievalResult(
			query=medicine_name,
			medicines=dosage_infos,
			warning=None if dosage_infos else "No dosage information found for this medicine",
		)
		return result.model_dump_json(ensure_ascii=False)
	except Exception as exc:
		result = DosageRetrievalResult(
			query=medicine_name,
			medicines=[],
			warning=f"Dosage retrieval failed: {exc}",
		)
		return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=IndicationSearchInput)
def get_drugs_by_indication(indication: str, top_k: int = 5) -> str:
	"""
	Find drugs that are indicated for treating a specific condition or disease.
	Uses FAISS vector search to find semantically similar indications.
	
	Args:
		indication: Chỉ định bệnh/tình trạng cần tìm thuốc (indication/condition)
		top_k: Số kết quả trả về (number of results)
	
	Returns:
		JSON string with medicines matching the indication
	"""
	if not DB_PATH.exists():
		result = IndicationRetrievalResult(
			indication=indication,
			total_hits=0,
			medicines=[],
			warning=f"Database not found: {DB_PATH}",
		)
		return result.model_dump_json(ensure_ascii=False)

	if not MEDICINES_INDEX_PATH.exists() or not MEDICINES_MAPPING_PATH.exists():
		result = IndicationRetrievalResult(
			indication=indication,
			total_hits=0,
			medicines=[],
			warning="Medicines FAISS index or mapping file is missing",
		)
		return result.model_dump_json(ensure_ascii=False)

	try:
		index = faiss.read_index(str(MEDICINES_INDEX_PATH))
		mapping = _load_mapping(MEDICINES_MAPPING_PATH)
		embeddings = get_embeddings(model_name="text-embedding-3-small")
		query_vector = np.array([embeddings.embed_query(indication)], dtype="float32")

		distances, indices = index.search(query_vector, top_k)
		ranked = _extract_medicine_ids(distances=distances, indices=indices, mapping=mapping)
		score_map = {medicine_id: score for medicine_id, score in ranked}
		candidate_ids = [medicine_id for medicine_id, _ in ranked]

		# Query medicines with indications
		if candidate_ids:
			placeholders = ",".join("?" for _ in candidate_ids)
			sql = f"""
				SELECT
					id,
					name,
					form,
					drug_group,
					indications,
					url
				FROM medicines
				WHERE id IN ({placeholders})
			"""
			with sqlite3.connect(DB_PATH) as conn:
				rows = conn.execute(sql, candidate_ids).fetchall()

			medicines: List[MedicineIndicationResult] = []
			for row in rows:
				medicine_id = row[0]
				medicines.append(
					MedicineIndicationResult(
						medicine_id=medicine_id,
						medicine_name=row[1],
						form=row[2],
						drug_group=row[3],
						indications=row[4],
						url=row[5],
						relevance_score=score_map.get(medicine_id, 9999.0),
					)
				)
			medicines = sorted(medicines, key=lambda x: x.relevance_score or 9999.0)
		else:
			medicines = []

		result = IndicationRetrievalResult(
			indication=indication,
			total_hits=len(medicines),
			medicines=medicines,
			warning=None if medicines else "No medicines found for this indication",
		)
		return result.model_dump_json(ensure_ascii=False)
	except Exception as exc:
		result = IndicationRetrievalResult(
			indication=indication,
			total_hits=0,
			medicines=[],
			warning=f"Indication retrieval failed: {exc}",
		)
		return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=ContraindicationInput)
def get_contraindications(medicine_name: str) -> str:
	"""
	Get contraindications and precautions for a medicine.
	
	Args:
		medicine_name: Tên thuốc (medicine name)
	
	Returns:
		JSON string with contraindications and precautions
	"""
	if not DB_PATH.exists():
		return json.dumps({
			"medicine_name": medicine_name,
			"contraindications": None,
			"precautions": None,
			"warning": f"Database not found: {DB_PATH}",
		}, ensure_ascii=False)

	try:
		with sqlite3.connect(DB_PATH) as conn:
			sql = """
				SELECT id, name, contraindications, precautions, side_effects
				FROM medicines
				WHERE name LIKE ? OR search_text LIKE ?
				LIMIT 5
			"""
			search_pattern = f"%{medicine_name}%"
			rows = conn.execute(sql, (search_pattern, search_pattern)).fetchall()

		if rows:
			result = {
				"medicine_name": rows[0][1],
				"contraindications": rows[0][2],
				"precautions": rows[0][3],
				"side_effects": rows[0][4],
				"matches_count": len(rows),
			}
		else:
			result = {
				"medicine_name": medicine_name,
				"contraindications": None,
				"precautions": None,
				"side_effects": None,
				"warning": "No medicine found with this name",
			}
		return json.dumps(result, ensure_ascii=False)
	except Exception as exc:
		return json.dumps({
			"medicine_name": medicine_name,
			"error": str(exc),
		}, ensure_ascii=False)


@tool(args_schema=SideEffectsInput)
def get_side_effects(medicine_name: str) -> str:
	"""
	Get side effects and adverse reactions for a medicine.
	
	Args:
		medicine_name: Tên thuốc (medicine name)
	
	Returns:
		JSON string with side effects information
	"""
	if not DB_PATH.exists():
		return json.dumps({
			"medicine_name": medicine_name,
			"side_effects": None,
			"warning": f"Database not found: {DB_PATH}",
		}, ensure_ascii=False)

	try:
		with sqlite3.connect(DB_PATH) as conn:
			sql = """
				SELECT id, name, side_effects, precautions
				FROM medicines
				WHERE name LIKE ? OR search_text LIKE ?
				LIMIT 5
			"""
			search_pattern = f"%{medicine_name}%"
			rows = conn.execute(sql, (search_pattern, search_pattern)).fetchall()

		if rows:
			result = {
				"medicine_name": rows[0][1],
				"side_effects": rows[0][2],
				"precautions": rows[0][3],
				"matches_count": len(rows),
			}
		else:
			result = {
				"medicine_name": medicine_name,
				"side_effects": None,
				"warning": "No medicine found with this name",
			}
		return json.dumps(result, ensure_ascii=False)
	except Exception as exc:
		return json.dumps({
			"medicine_name": medicine_name,
			"error": str(exc),
		}, ensure_ascii=False)


if __name__ == "__main__":
	print("--- Testing Medicine Agent Tools ---\n")
	
	# Test 1: get_drug_info
	print("[TEST 1] get_drug_info - Search for a medicine")
	result = get_drug_info.invoke({"name": "paracetamol", "top_k": 3})
	data = json.loads(result)
	print(f"Query: {data.get('query')}")
	print(f"Total hits: {data.get('total_hits')}")
	if data.get('medicines'):
		for med in data['medicines'][:1]:
			print(f"  - {med['name']} (Form: {med['form']}, Group: {med['drug_group']})")
	
	# Test 2: get_dosage
	print("\n[TEST 2] get_dosage - Get dosage information")
	result = get_dosage.invoke({"medicine_name": "paracetamol"})
	data = json.loads(result)
	print(f"Query: {data.get('query')}")
	if data.get('medicines'):
		for med in data['medicines'][:1]:
			print(f"  - {med['medicine_name']}: {med['dosage']}")
	
	# Test 3: get_drugs_by_indication
	print("\n[TEST 3] get_drugs_by_indication - Find drugs for a condition")
	result = get_drugs_by_indication.invoke({"indication": "sốt cao", "top_k": 3})
	data = json.loads(result)
	print(f"Indication: {data.get('indication')}")
	print(f"Total hits: {data.get('total_hits')}")
	if data.get('medicines'):
		for med in data['medicines'][:1]:
			print(f"  - {med['medicine_name']} (Indication: {med['indications'][:50]}...)")
	
	# Test 4: get_contraindications
	print("\n[TEST 4] get_contraindications")
	result = get_contraindications.invoke({"medicine_name": "aspirin"})
	data = json.loads(result)
	print(f"Medicine: {data.get('medicine_name')}")
	if data.get('contraindications'):
		print(f"Contraindications: {data['contraindications'][:100]}...")
	
	# Test 5: get_side_effects
	print("\n[TEST 5] get_side_effects")
	result = get_side_effects.invoke({"medicine_name": "aspirin"})
	data = json.loads(result)
	print(f"Medicine: {data.get('medicine_name')}")
	if data.get('side_effects'):
		print(f"Side effects: {data['side_effects'][:100]}...")
