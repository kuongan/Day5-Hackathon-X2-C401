from langchain_core import tools
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import unicodedata
import uuid

import faiss
import numpy as np

from backend.utils.llm_manager import get_embeddings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "medical_chatbot.db"
DATA_DIR = Path(os.getenv("MEDICAL_DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()
FAISS_DIR = PROJECT_ROOT / "data" / "faiss"
DOCTOR_SPECIALTY_INDEX_PATH = FAISS_DIR / "doctors_specialty.index"
DOCTOR_SPECIALTY_MAPPING_PATH = FAISS_DIR / "doctors_specialty_mapping.json"

_DOCTOR_INDEX = None
_DOCTOR_MAPPING = None


# ======================
# DB helper
# ======================
def get_connection():
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Booking database file not found: {DATA_DIR}. "
            "Set MEDICAL_DB_PATH if your database is in a different location."
        )
    return sqlite3.connect(str(DATA_DIR))


def _load_doctor_specialty_index():
    global _DOCTOR_INDEX, _DOCTOR_MAPPING
    if _DOCTOR_INDEX is not None and _DOCTOR_MAPPING is not None:
        return _DOCTOR_INDEX, _DOCTOR_MAPPING

    if not DOCTOR_SPECIALTY_INDEX_PATH.exists() or not DOCTOR_SPECIALTY_MAPPING_PATH.exists():
        return None, None

    _DOCTOR_INDEX = faiss.read_index(str(DOCTOR_SPECIALTY_INDEX_PATH))
    with DOCTOR_SPECIALTY_MAPPING_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    _DOCTOR_MAPPING = payload if isinstance(payload, list) else []
    return _DOCTOR_INDEX, _DOCTOR_MAPPING


def _search_specialty_ids(query: str, top_k: int = 5) -> list[int]:
    index, mapping = _load_doctor_specialty_index()
    if index is None or not mapping:
        return []

    embeddings = get_embeddings(model_name="text-embedding-3-small")
    query_vector = np.array([embeddings.embed_query(query)], dtype="float32")
    distances, indices = index.search(query_vector, top_k)

    specialty_ids: list[int] = []
    for raw_idx in indices[0]:
        idx = int(raw_idx)
        if idx < 0 or idx >= len(mapping):
            continue
        metadata = mapping[idx].get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        specialty_id = metadata.get("id")
        if isinstance(specialty_id, int) and specialty_id not in specialty_ids:
            specialty_ids.append(specialty_id)
    return specialty_ids


# ======================
# Load doctors
# ======================
def _load_doctors():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM doctors;")
        rows = cursor.fetchall()

    return {doctor_id: name for doctor_id, name in rows}


def _normalize_vietnamese_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    normalized = normalized.replace("đ", "d").replace("Đ", "D")
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(normalized.lower().split())


def _get_doctor_id_by_name(doctor_name: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM doctors WHERE name=?;", (doctor_name,))
        result = cursor.fetchone()
        if result:
            return result[0]

        cursor.execute("SELECT id, name FROM doctors;")
        rows = cursor.fetchall()

    normalized_target = _normalize_vietnamese_text(doctor_name)
    for doctor_id, name in rows:
        if _normalize_vietnamese_text(name) == normalized_target:
            return doctor_id

    for doctor_id, name in rows:
        normalized_name = _normalize_vietnamese_text(name)
        if normalized_target and normalized_target in normalized_name:
            return doctor_id

    return None


def _fetch_doctors_by_specialties(specialty_ids: list[int]) -> list[dict]:
    if not specialty_ids:
        return []

    placeholders = ",".join("?" for _ in specialty_ids)
    sql = f"""
        SELECT
            d.id,
            COALESCE(d.name, ''),
            COALESCE(s.name, ''),
            COALESCE(h.name, '')
        FROM doctors d
        LEFT JOIN specialties s ON s.id = d.specialty_id
        LEFT JOIN hospitals h ON h.id = d.hospital_id
        WHERE d.specialty_id IN ({placeholders})
        ORDER BY d.name
    """

    with get_connection() as conn:
        rows = conn.execute(sql, specialty_ids).fetchall()

    return [
        {
            "doctor_id": int(row[0]),
            "doctor_name": str(row[1]),
            "specialty": str(row[2]),
            "hospital": str(row[3]),
        }
        for row in rows
    ]


def _search_doctors(query: str, top_k: int = 5) -> dict:
    normalized_query = _normalize_vietnamese_text(query)
    matched_id = _get_doctor_id_by_name(query)
    if matched_id is not None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    d.id,
                    COALESCE(d.name, ''),
                    COALESCE(s.name, ''),
                    COALESCE(h.name, '')
                FROM doctors d
                LEFT JOIN specialties s ON s.id = d.specialty_id
                LEFT JOIN hospitals h ON h.id = d.hospital_id
                WHERE d.id = ?
                """,
                (matched_id,),
            ).fetchone()
        if row:
            return {
                "query": query,
                "total": 1,
                "results": [
                    {
                        "doctor_id": int(row[0]),
                        "doctor_name": str(row[1]),
                        "specialty": str(row[2]),
                        "hospital": str(row[3]),
                    }
                ],
                "search_mode": "doctor_name_exact_or_fuzzy",
            }

    specialty_ids = _search_specialty_ids(query=query, top_k=max(top_k, 5))
    if specialty_ids:
        doctors = _fetch_doctors_by_specialties(specialty_ids)
        if normalized_query:
            exact_name_candidates = [
                item for item in doctors
                if normalized_query in _normalize_vietnamese_text(item["doctor_name"])
            ]
            if exact_name_candidates:
                doctors = exact_name_candidates
        return {
            "query": query,
            "total": len(doctors[:top_k]),
            "results": doctors[:top_k],
            "search_mode": "faiss_specialty",
            "specialty_ids": specialty_ids,
        }

    return {
        "query": query,
        "total": 0,
        "results": [],
        "search_mode": "none",
    }


# ======================
# Load time slots
# ======================
def _load_time_slots(doctor_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT slot_date, slot_start, status FROM time_slots WHERE doctor_id=?;",
            (doctor_id,)
        )
        rows = cursor.fetchall()

    result = {}
    for date, time_start, status in rows:
        result.setdefault(date, []).append((time_start, status))
    return result


def get_appointment_id(doctor_id: int, date: str, time_start: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM time_slots 
            WHERE doctor_id=? AND slot_date=? AND slot_start=? AND status='available'
        """, (doctor_id, date, time_start))
        result = cursor.fetchone()

    return result[0] if result else None


# ======================
# TOOLS
# ======================
@tools.tool("get_doctors", description="Retrieve all available doctors")
def get_doctors(query: str = "", top_k: int = 5) -> dict:
    if query.strip():
        try:
            return _search_doctors(query=query, top_k=top_k)
        except Exception as exc:
            return {
                "query": query,
                "total": 0,
                "results": [],
                "warning": f"doctor search failed: {exc}",
            }

    doctors = _load_doctors()
    return {
        "query": "",
        "total": len(doctors),
        "results": [
            {"doctor_id": doctor_id, "doctor_name": name}
            for doctor_id, name in doctors.items()
        ],
        "search_mode": "all",
    }


@tools.tool("check_appointment", description="Check if a specific appointment slot is available")
def check_appointment(doctor_name: str, date: str, time_start: str) -> bool:
    doctor_id = _get_doctor_id_by_name(doctor_name)
    if doctor_id is None:
        return False

    try:
        datetime.strptime(f"{date} {time_start}", "%Y-%m-%d %H:%M")
    except ValueError:
        return False

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status FROM time_slots
            WHERE doctor_id=? AND slot_date=? AND slot_start=?;
        """, (doctor_id, date, time_start))

        result = cursor.fetchone()

    if not result:
        return False

    status = result[0]
    return status == "available"


@tools.tool("create_appointment", description="Create a new appointment")
def create_appointment(doctor_name: str, date: str, time_start: str) -> dict:
    doctor_id = _get_doctor_id_by_name(doctor_name)
    if doctor_id is None:
        return {}

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            SELECT id
            FROM time_slots
            WHERE doctor_id=? AND slot_date=? AND slot_start=? AND status='available'
            """,
            (doctor_id, date, time_start),
        )
        slot_row = cursor.fetchone()
        if not slot_row:
            conn.rollback()
            return {}

        time_slot_id = int(slot_row[0])

        # Lock row (important if multi-user)
        cursor.execute("""
            SELECT id, doctor_id, slot_date, slot_start, slot_end, status
            FROM time_slots
            WHERE id=?;
        """, (time_slot_id,))
        time_slot = cursor.fetchone()

        if not time_slot or time_slot[5] != "available":
            conn.rollback()
            return {}

        # Update
        cursor.execute("""
            UPDATE time_slots
            SET status='booked'
            WHERE id=?;
        """, (time_slot_id,))

        booking_code = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        cursor.execute(
            """
            INSERT INTO appointments (
                booking_code,
                doctor_id,
                time_slot_id,
                reason,
                status,
                notes,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                booking_code,
                doctor_id,
                time_slot_id,
                "Booking from booking_agent",
                "confirmed",
                "Created by booking_agent.create_appointment",
            ),
        )
        appointment_row_id = int(cursor.lastrowid)

        conn.commit()

        cursor.execute("SELECT name FROM doctors WHERE id=?;", (doctor_id,))
        doctor = cursor.fetchone()

    return {
        "id": appointment_row_id,
        "booking_code": booking_code,
        "time_slot_id": time_slot[0],
        "doctor_id": doctor_id,
        "doctor_name": doctor[0] if doctor else "Unknown",
        "date": time_slot[2],
        "time_start": time_slot[3],
        "time_end": time_slot[4],
        "status": "booked",
        "appointment_status": "confirmed",
    }


@tools.tool("seek_doctor_by_disease", description="Search for doctors based on disease/symptom and return recommended doctors with their details")
def seek_doctor_by_disease(disease: str, top_k: int = 5) -> dict:
    """
    Search for doctors based on disease or symptom.
    Returns a list of recommended doctors with name, specialty, and hospital.
    
    Args:
        disease: Disease name or symptom (e.g., "đau bụng", "pain in stomach")
        top_k: Number of top doctors to return (default 5)
    
    Returns:
        dict with recommended doctors and their details
    """
    try:
        specialty_ids = _search_specialty_ids(query=disease, top_k=max(top_k, 5))
        if specialty_ids:
            doctors = _fetch_doctors_by_specialties(specialty_ids)
            return {
                "success": True,
                "disease": disease,
                "total": len(doctors[:top_k]),
                "doctors": doctors[:top_k],
                "search_mode": "faiss_specialty",
                "message": f"Tìm thấy {len(doctors[:top_k])} bác sĩ phù hợp với triệu chứng '{disease}'"
            }
        else:
            return {
                "success": False,
                "disease": disease,
                "total": 0,
                "doctors": [],
                "message": f"Không tìm thấy bác sĩ phù hợp cho triệu chứng '{disease}'. Vui lòng thử lại với triệu chứng khác."
            }
    except Exception as exc:
        return {
            "success": False,
            "disease": disease,
            "total": 0,
            "doctors": [],
            "error": str(exc),
            "message": f"Lỗi khi tìm kiếm bác sĩ: {exc}"
        }


@tools.tool("get_doctor_available_slots", description="Get available time slots for a doctor")
def get_doctor_available_slots(doctor_name: str, days_ahead: int = 7) -> dict:
    """
    Get available appointment slots for a specific doctor.
    
    Args:
        doctor_name: Name of the doctor
        days_ahead: Number of days to check ahead (default 7)
    
    Returns:
        dict with available time slots by date
    """
    try:
        doctor_id = _get_doctor_id_by_name(doctor_name)
        if doctor_id is None:
            return {
                "success": False,
                "doctor_name": doctor_name,
                "message": f"Không tìm thấy bác sĩ: {doctor_name}"
            }
        
        time_slots = _load_time_slots(doctor_id)
        if not time_slots:
            return {
                "success": False,
                "doctor_name": doctor_name,
                "message": f"Không có lịch trống cho bác sĩ {doctor_name}"
            }
        
        # Filter available slots
        available_slots = {}
        for date, slots in time_slots.items():
            available = [time_start for time_start, status in slots if status == "available"]
            if available:
                available_slots[date] = available
        
        if not available_slots:
            return {
                "success": False,
                "doctor_name": doctor_name,
                "message": f"Không có lịch trống cho bác sĩ {doctor_name}"
            }
        
        return {
            "success": True,
            "doctor_name": doctor_name,
            "available_slots": available_slots,
            "message": f"Lịch trống cho bác sĩ {doctor_name}"
        }
    except Exception as exc:
        return {
            "success": False,
            "doctor_name": doctor_name,
            "error": str(exc),
            "message": f"Lỗi khi lấy lịch trống: {exc}"
        }


# ======================
# TEST
# ======================
if __name__ == "__main__":
    print(check_appointment.invoke({
        'doctor_name': "Đỗ Tất Cường",
        'date': "2026-04-08",
        'time_start': "08:00"
    }))

    print(create_appointment.invoke({
        'doctor_name': "Đỗ Tất Cường",
        'date': "2026-04-08",
        'time_start': "08:00"
    }))