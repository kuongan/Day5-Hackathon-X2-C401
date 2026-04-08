import sqlite3
from pathlib import Path

DB_FILENAME = "medical_chatbot.db"


def fetch_one(cursor: sqlite3.Cursor, query: str) -> int:
    cursor.execute(query)
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def print_check(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    db_path = root / "data" / DB_FILENAME
    if not db_path.exists():
        print(f"[FAIL] Khong tim thay DB: {db_path}")
        return

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        print(f"[INFO] DB: {db_path}")

        required_tables = [
            "specialties",
            "hospitals",
            "doctors",
            "time_slots",
            "patients",
            "appointments",
            "medicines",
            "body_articles",
            "diseases",
        ]

        for table in required_tables:
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,))
            print_check(f"Table {table}", cur.fetchone()[0] == 1)

        doctors = fetch_one(cur, "SELECT COUNT(*) FROM doctors")
        slots = fetch_one(cur, "SELECT COUNT(*) FROM time_slots")
        patients = fetch_one(cur, "SELECT COUNT(*) FROM patients")
        appointments = fetch_one(cur, "SELECT COUNT(*) FROM appointments")

        print("\n[INFO] Record count")
        print(f"- doctors: {doctors}")
        print(f"- time_slots: {slots}")
        print(f"- patients: {patients}")
        print(f"- appointments: {appointments}")

        expected_slots = doctors * 7 * 8
        print_check("Time slot total", slots == expected_slots, f"actual={slots}, expected={expected_slots}")

        booked_slots = fetch_one(cur, "SELECT COUNT(*) FROM time_slots WHERE status='booked'")
        available_slots = fetch_one(cur, "SELECT COUNT(*) FROM time_slots WHERE status='available'")

        print("\n[INFO] Slot status")
        print(f"- booked: {booked_slots}")
        print(f"- available: {available_slots}")
        print_check("Booked slots == appointments", booked_slots == appointments, f"booked={booked_slots}, appointments={appointments}")
        print_check("Patients == appointments", patients == appointments, f"patients={patients}, appointments={appointments}")

        missing_patient_link = fetch_one(
            cur,
            """
            SELECT COUNT(*)
            FROM appointments a
            LEFT JOIN patients p ON p.id = a.patient_id
            WHERE p.id IS NULL
            """,
        )
        print_check("All appointments have valid patient", missing_patient_link == 0, f"missing={missing_patient_link}")

        missing_slot_link = fetch_one(
            cur,
            """
            SELECT COUNT(*)
            FROM appointments a
            LEFT JOIN time_slots t ON t.id = a.time_slot_id
            WHERE t.id IS NULL
            """,
        )
        print_check("All appointments have valid slot", missing_slot_link == 0, f"missing={missing_slot_link}")

        doctor_slot_mismatch = fetch_one(
            cur,
            """
            SELECT COUNT(*)
            FROM appointments a
            JOIN time_slots t ON t.id = a.time_slot_id
            WHERE a.doctor_id != t.doctor_id
            """,
        )
        print_check("Appointment doctor matches slot doctor", doctor_slot_mismatch == 0, f"mismatch={doctor_slot_mismatch}")

        appt_on_non_booked_slot = fetch_one(
            cur,
            """
            SELECT COUNT(*)
            FROM appointments a
            JOIN time_slots t ON t.id = a.time_slot_id
            WHERE t.status != 'booked'
            """,
        )
        print_check("Appointments only on booked slots", appt_on_non_booked_slot == 0, f"count={appt_on_non_booked_slot}")

        duplicate_codes = fetch_one(
            cur,
            """
            SELECT COUNT(*) FROM (
                SELECT booking_code, COUNT(*) c
                FROM appointments
                GROUP BY booking_code
                HAVING c > 1
            )
            """,
        )
        print_check("Booking code uniqueness", duplicate_codes == 0, f"duplicate_groups={duplicate_codes}")

        print("\n[DONE] Kiem tra logic booking hoan tat")


if __name__ == "__main__":
    main()
