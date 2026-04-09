from langchain_core import tools
import sqlite3
from datetime import datetime

DATA_DIR = "../../../data/medical_chatbot.db"


# ======================
# DB helper
# ======================
def get_connection():
    return sqlite3.connect(DATA_DIR)


# ======================
# Load doctors
# ======================
def _load_doctors():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM doctors;")
        rows = cursor.fetchall()

    return {doctor_id: name for doctor_id, name in rows}


def _get_doctor_id_by_name(doctor_name: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM doctors WHERE name=?;", (doctor_name,))
        result = cursor.fetchone()
    return result[0] if result else None


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
def get_doctors() -> dict:
    return _load_doctors()


@tools.tool("check_appointment", description="Check if a specific appointment slot is available")
def check_appointment(doctor_name: str, date: str, time_start: str) -> bool:
    doctor_id = _get_doctor_id_by_name(doctor_name)
    if doctor_id is None:
        return False

    try:
        requested_dt = datetime.strptime(f"{date} {time_start}", "%Y-%m-%d %H:%M")
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

    appointment_id = get_appointment_id(doctor_id, date, time_start)
    if appointment_id is None:
        return {}

    with get_connection() as conn:
        cursor = conn.cursor()

        # Lock row (important if multi-user)
        cursor.execute("""
            SELECT id, doctor_id, slot_date, slot_start, slot_end, status
            FROM time_slots
            WHERE id=?;
        """, (appointment_id,))
        time_slot = cursor.fetchone()

        if not time_slot or time_slot[5] != "available":
            return {}

        # Update
        cursor.execute("""
            UPDATE time_slots
            SET status='booked'
            WHERE id=?;
        """, (appointment_id,))
        conn.commit()

        cursor.execute("SELECT name FROM doctors WHERE id=?;", (doctor_id,))
        doctor = cursor.fetchone()

    return {
        "id": time_slot[0],
        "doctor_id": doctor_id,
        "doctor_name": doctor[0] if doctor else "Unknown",
        "date": time_slot[2],
        "time_start": time_slot[3],
        "time_end": time_slot[4],
        "status": "booked"
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