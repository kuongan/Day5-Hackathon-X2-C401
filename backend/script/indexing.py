import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import faiss  
import numpy as np  
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()  

@dataclass
class IndexItem:
    text: str
    metadata: Dict[str, Any]


def get_project_paths() -> Tuple[Path, Path, Path]:
    project_root = Path(__file__).resolve().parents[2]
    db_path = project_root / "data" / "medical_chatbot.db"
    faiss_dir = project_root / "data" / "faiss"
    return project_root, db_path, faiss_dir


def get_openai_api_key() -> str:
    key = (os.getenv("openai_api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Missing openai_api_key / OPENAI_API_KEY in environment")
    return key


def discover_schema(conn: sqlite3.Connection) -> Dict[str, List[str]]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]

    schema: Dict[str, List[str]] = {}
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        schema[table] = [row[1] for row in cur.fetchall()]

    print("[INFO] Discovered tables:", ", ".join(tables))
    for table, cols in schema.items():
        print(f"[INFO] - {table}: {cols}")

    return schema


def safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _join_non_empty(parts: Iterable[str], sep: str = " ") -> str:
    clean = [str(p).strip() for p in parts if str(p).strip()]
    return sep.join(clean)


def build_diseases_body_items(conn: sqlite3.Connection, schema: Dict[str, List[str]]) -> List[IndexItem]:
    items: List[IndexItem] = []
    cur = conn.cursor()

    # diseases table
    if "diseases" in schema:
        cols = schema["diseases"]
        select_cols = [c for c in ["id", "title", "url", "detail_sections", "search_text"] if c in cols]
        if select_cols:
            cur.execute(f"SELECT {', '.join(select_cols)} FROM diseases")
            for row in cur.fetchall():
                data = dict(zip(select_cols, row))
                sections_text = ""
                parsed_sections = safe_json_loads(data.get("detail_sections"))
                if isinstance(parsed_sections, list):
                    chunks: List[str] = []
                    for sec in parsed_sections:
                        if not isinstance(sec, dict):
                            continue
                        sec_title = str(sec.get("title") or "").strip()
                        sec_content = sec.get("content")
                        if isinstance(sec_content, list):
                            sec_text = _join_non_empty([str(x) for x in sec_content])
                        else:
                            sec_text = str(sec_content or "").strip()
                        if sec_title:
                            chunks.append(sec_title)
                        if sec_text:
                            chunks.append(sec_text)
                    sections_text = _join_non_empty(chunks)

                title = str(data.get("title") or "").strip()
                description = ""
                if "search_text" in data and isinstance(data.get("search_text"), str):
                    description = str(data.get("search_text") or "").strip()

                text = _join_non_empty([title, description, sections_text])
                if not text:
                    continue
                items.append(
                    IndexItem(
                        text=text,
                        metadata={
                            "source": "diseases",
                            "id": data.get("id"),
                            "title": title,
                            "url": str(data.get("url") or "").strip(),
                        },
                    )
                )

    # body_articles table
    if "body_articles" in schema:
        cols = schema["body_articles"]
        select_cols = [c for c in ["id", "title", "url", "description", "content", "sections"] if c in cols]
        if select_cols:
            cur.execute(f"SELECT {', '.join(select_cols)} FROM body_articles")
            for row in cur.fetchall():
                data = dict(zip(select_cols, row))
                title = str(data.get("title") or "").strip()
                description = str(data.get("description") or "").strip()
                content = str(data.get("content") or "").strip()

                section_text = ""
                parsed_sections = safe_json_loads(data.get("sections"))
                if isinstance(parsed_sections, list):
                    chunk: List[str] = []
                    for sec in parsed_sections:
                        if not isinstance(sec, dict):
                            continue
                        chunk.append(str(sec.get("heading") or "").strip())
                        chunk.append(str(sec.get("text") or "").strip())
                    section_text = _join_non_empty(chunk)

                text = _join_non_empty([title, description, section_text, content])
                if not text:
                    continue
                items.append(
                    IndexItem(
                        text=text,
                        metadata={
                            "source": "body_articles",
                            "id": data.get("id"),
                            "title": title,
                            "url": str(data.get("url") or "").strip(),
                        },
                    )
                )

    print(f"[INFO] diseases_body items: {len(items)}")
    return items


def build_medicine_items(conn: sqlite3.Connection, schema: Dict[str, List[str]]) -> List[IndexItem]:
    if "medicines" not in schema:
        return []

    cur = conn.cursor()
    cols = schema["medicines"]
    select_cols = [
        c
        for c in [
            "id",
            "name",
            "url",
            "tag",
            "form",
            "drug_group",
            "indications",
            "contraindications",
            "precautions",
            "side_effects",
            "dosage",
            "notes",
        ]
        if c in cols
    ]

    cur.execute(f"SELECT {', '.join(select_cols)} FROM medicines")
    items: List[IndexItem] = []
    for row in cur.fetchall():
        data = dict(zip(select_cols, row))
        text = _join_non_empty(
            [
                str(data.get("name") or ""),
                str(data.get("tag") or ""),
                str(data.get("form") or ""),
                str(data.get("drug_group") or ""),
                str(data.get("indications") or ""),
                str(data.get("contraindications") or ""),
                str(data.get("precautions") or ""),
                str(data.get("side_effects") or ""),
                str(data.get("dosage") or ""),
                str(data.get("notes") or ""),
            ]
        )
        if not text:
            continue
        items.append(
            IndexItem(
                text=text,
                metadata={
                    "source": "medicines",
                    "id": data.get("id"),
                    "name": str(data.get("name") or "").strip(),
                    "url": str(data.get("url") or "").strip(),
                },
            )
        )

    print(f"[INFO] medicines items: {len(items)}")
    return items


def build_doctors_specialty_items(conn: sqlite3.Connection, schema: Dict[str, List[str]]) -> List[IndexItem]:
    if "doctors" not in schema:
        return []

    cur = conn.cursor()
    has_specialties = "specialties" in schema
    has_hospitals = "hospitals" in schema

    if has_specialties and has_hospitals:
        query = """
            SELECT
                s.id AS specialty_id,
                s.name AS specialty_name,
                s.slug AS specialty_slug,
                GROUP_CONCAT(DISTINCT d.name) AS doctor_names,
                GROUP_CONCAT(DISTINCT h.name) AS hospital_names
            FROM specialties s
            LEFT JOIN doctors d ON d.specialty_id = s.id
            LEFT JOIN hospitals h ON h.id = d.hospital_id
            GROUP BY s.id, s.name, s.slug
            ORDER BY s.name
        """
        cur.execute(query)
        rows = cur.fetchall()

        items: List[IndexItem] = []
        for specialty_id, specialty_name, specialty_slug, doctor_names, hospital_names in rows:
            text = _join_non_empty(
                [
                    str(specialty_name or ""),
                    str(specialty_slug or ""),
                    str(doctor_names or ""),
                    str(hospital_names or ""),
                    "Chuyen khoa y te Vinmec",
                ]
            )
            if not text:
                continue
            items.append(
                IndexItem(
                    text=text,
                    metadata={
                        "source": "specialties",
                        "id": specialty_id,
                        "specialty_name": str(specialty_name or "").strip(),
                    },
                )
            )
        print(f"[INFO] doctors_specialty items: {len(items)}")
        return items

    # Fallback if lookup tables are missing
    cur.execute("SELECT id, name, special, hospital FROM doctors")
    items = []
    for row in cur.fetchall():
        doctor_id, name, special, hospital = row
        text = _join_non_empty([str(special or ""), str(name or ""), str(hospital or "")])
        if not text:
            continue
        items.append(
            IndexItem(
                text=text,
                metadata={
                    "source": "doctors",
                    "id": doctor_id,
                    "doctor_name": str(name or "").strip(),
                    "specialty_name": str(special or "").strip(),
                },
            )
        )

    print(f"[INFO] doctors_specialty items (fallback): {len(items)}")
    return items


def embed_texts(texts: List[str], embeddings: OpenAIEmbeddings, batch_size: int = 64) -> np.ndarray:
    vectors: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        vectors.extend(embeddings.embed_documents(chunk))
        print(f"[INFO] Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    arr = np.array(vectors, dtype="float32")
    if arr.ndim != 2:
        raise RuntimeError("Embedding output has invalid shape")
    return arr


def _cache_paths(cache_prefix: Path) -> Tuple[Path, Path]:
    vectors_cache = cache_prefix.with_suffix(".vectors.npy")
    meta_cache = cache_prefix.with_suffix(".meta.json")
    return vectors_cache, meta_cache


def _load_cached_vectors(cache_prefix: Path) -> np.ndarray:
    vectors_cache, meta_cache = _cache_paths(cache_prefix)
    if not vectors_cache.exists() or not meta_cache.exists():
        return np.empty((0, 0), dtype="float32")

    arr = np.load(vectors_cache)
    if arr.ndim != 2:
        return np.empty((0, 0), dtype="float32")
    return arr.astype("float32")


def _save_cached_vectors(cache_prefix: Path, vectors: np.ndarray, total_texts: int, batch_size: int) -> None:
    vectors_cache, meta_cache = _cache_paths(cache_prefix)
    np.save(vectors_cache, vectors)
    meta = {
        "embedded_count": int(vectors.shape[0]),
        "total_texts": int(total_texts),
        "batch_size": int(batch_size),
        "saved_at": int(time.time()),
    }
    meta_cache.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_cache(cache_prefix: Path) -> None:
    vectors_cache, meta_cache = _cache_paths(cache_prefix)
    if vectors_cache.exists():
        vectors_cache.unlink()
    if meta_cache.exists():
        meta_cache.unlink()


def embed_texts_with_resume(
    texts: List[str],
    embeddings: OpenAIEmbeddings,
    cache_prefix: Path,
    batch_size: int = 64,
    max_retries: int = 6,
) -> np.ndarray:
    cached = _load_cached_vectors(cache_prefix)
    vectors: List[List[float]] = cached.tolist() if cached.size else []

    start_idx = len(vectors)
    total = len(texts)
    if start_idx > total:
        start_idx = 0
        vectors = []

    if start_idx > 0:
        print(f"[INFO] Resume embedding from {start_idx}/{total}")

    for i in range(start_idx, total, batch_size):
        chunk = texts[i : i + batch_size]

        success = False
        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                chunk_vectors = embeddings.embed_documents(chunk)
                vectors.extend(chunk_vectors)
                current = np.array(vectors, dtype="float32")
                _save_cached_vectors(cache_prefix, current, total_texts=total, batch_size=batch_size)
                print(f"[INFO] Embedded {min(i + batch_size, total)}/{total}")
                success = True
                break
            except Exception as exc:
                last_error = exc
                wait_seconds = min(30, 2 ** attempt)
                print(
                    f"[WARN] Embed batch failed ({i}-{min(i + batch_size, total)}), "
                    f"attempt {attempt}/{max_retries}: {exc}. Retry in {wait_seconds}s"
                )
                time.sleep(wait_seconds)

        if not success:
            raise RuntimeError(
                "Embedding failed after retries. Re-run script to resume from cache. "
                f"Last error: {last_error}"
            )

    arr = np.array(vectors, dtype="float32")
    if arr.ndim != 2:
        raise RuntimeError("Embedding output has invalid shape")
    return arr


def save_faiss_index(
    items: List[IndexItem],
    embeddings: OpenAIEmbeddings,
    index_path: Path,
    mapping_path: Path,
    cache_prefix: Path,
) -> None:
    if not items:
        print(f"[WARN] Skip empty index: {index_path.name}")
        return

    texts = [item.text for item in items]
    vectors = embed_texts_with_resume(texts, embeddings, cache_prefix=cache_prefix)

    dim = vectors.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

    faiss.write_index(index, str(index_path))

    mapping = []
    for idx, item in enumerate(items):
        mapping.append(
            {
                "position": idx,
                "metadata": item.metadata,
                "text_preview": item.text[:400],
            }
        )

    with mapping_path.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    _clear_cache(cache_prefix)

    print(f"[DONE] Saved index: {index_path}")
    print(f"[DONE] Saved mapping: {mapping_path}")


def main() -> None:
    _, db_path, faiss_dir = get_project_paths()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    faiss_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = faiss_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    api_key = get_openai_api_key()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)

    with sqlite3.connect(db_path) as conn:
        schema = discover_schema(conn)

        diseases_body_items = build_diseases_body_items(conn, schema)
        medicine_items = build_medicine_items(conn, schema)
        doctors_specialty_items = build_doctors_specialty_items(conn, schema)

    save_faiss_index(
        items=diseases_body_items,
        embeddings=embeddings,
        index_path=faiss_dir / "diseases_body.index",
        mapping_path=faiss_dir / "diseases_body_mapping.json",
        cache_prefix=cache_dir / "diseases_body",
    )
    save_faiss_index(
        items=medicine_items,
        embeddings=embeddings,
        index_path=faiss_dir / "medicines.index",
        mapping_path=faiss_dir / "medicines_mapping.json",
        cache_prefix=cache_dir / "medicines",
    )
    save_faiss_index(
        items=doctors_specialty_items,
        embeddings=embeddings,
        index_path=faiss_dir / "doctors_specialty.index",
        mapping_path=faiss_dir / "doctors_specialty_mapping.json",
        cache_prefix=cache_dir / "doctors_specialty",
    )

    print("[SUCCESS] Vector database initialization completed")


if __name__ == "__main__":
    main()
