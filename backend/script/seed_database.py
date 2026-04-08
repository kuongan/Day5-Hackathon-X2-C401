import json
import random
import re
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

DB_FILENAME = "medical_chatbot.db"
DOCTORS_FILENAME = "vinmec_doctors.json"
MEDICINES_FILENAME = "vinmec_medicines.json"
BODY_CONTENT_FILENAME = "vinmec_body_content.json"
DISEASES_FILENAME = "vinmec_benh.json"


def slugify(text: str) -> str:
    if not text:
        return ""
    value = text.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def load_json(file_path: Path):
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"[ERROR] Khong tim thay file: {file_path}")
    except json.JSONDecodeError as exc:
        print(f"[ERROR] JSON khong hop le ({file_path}): {exc}")
    except Exception as exc:
        print(f"[ERROR] Loi khi doc file {file_path}: {exc}")
    return []


def degree_level(degree: str) -> int:
    if not degree:
        return 1

    normalized = degree.lower()
    if "phó giáo sư" in normalized:
        return 4
    if "giáo sư" in normalized:
        return 5
    if "tiến sĩ" in normalized:
        return 3
    if "thạc sĩ" in normalized:
        return 2
    return 1


def first_non_empty(data: dict, keys: list[str], default: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        value_str = str(value).strip()
        if value_str:
            return value_str
    return default


def infer_sql_type(values: list) -> str:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "TEXT"

    is_int = True
    is_numeric = True
    for value in non_null:
        if isinstance(value, bool):
            is_int = False
            is_numeric = False
            break
        if isinstance(value, int):
            continue
        if isinstance(value, float):
            is_int = False
            continue
        is_int = False
        is_numeric = False
        break

    if is_int:
        return "INTEGER"
    if is_numeric:
        return "REAL"
    return "TEXT"


def create_tables(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS patients;
        DROP TABLE IF EXISTS time_slots;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS medicines;
        DROP TABLE IF EXISTS body_articles;
        DROP TABLE IF EXISTS diseases;
        DROP TABLE IF EXISTS specialties;
        DROP TABLE IF EXISTS hospitals;

        CREATE TABLE specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE
        );

        CREATE TABLE hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            profile_url TEXT,
            img_url TEXT,
            degree TEXT,
            degree_level INTEGER NOT NULL,
            specialty_id INTEGER,
            hospital_id INTEGER,
            consultation_fee INTEGER NOT NULL,
            languages TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            FOREIGN KEY (specialty_id) REFERENCES specialties(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        );

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            full_name TEXT NOT NULL,
            phone TEXT,
            dob TEXT,
            gender TEXT,
            insurance_code TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE NOT NULL,
            patient_id INTEGER REFERENCES patients(id),
            doctor_id INTEGER REFERENCES doctors(id),
            time_slot_id INTEGER REFERENCES time_slots(id),
            reason TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            cancelled_reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            slot_date TEXT NOT NULL,
            slot_start TEXT NOT NULL,
            slot_end TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT,
            tag TEXT,
            form TEXT,
            drug_group TEXT,
            indications TEXT,
            contraindications TEXT,
            precautions TEXT,
            side_effects TEXT,
            dosage TEXT,
            notes TEXT,
            search_text TEXT
        );

        CREATE TABLE body_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            description TEXT,
            content TEXT,
            sections TEXT,
            breadcrumb TEXT,
            scraped_at TEXT,
            search_text TEXT
        );

        CREATE INDEX idx_appointments_doctor ON appointments(doctor_id, status);
        CREATE INDEX idx_slots_doctor_date ON time_slots(doctor_id, slot_date, status);
        """
    )


def seed_specialties_and_hospitals(cursor: sqlite3.Cursor, doctors_data: list[dict]) -> tuple[dict, dict]:
    specialty_names = sorted({(item.get("special") or "").strip() for item in doctors_data if (item.get("special") or "").strip()})
    hospital_names = sorted({(item.get("hospital") or "").strip() for item in doctors_data if (item.get("hospital") or "").strip()})

    specialty_rows = [(name, slugify(name)) for name in specialty_names]
    cursor.executemany(
        "INSERT INTO specialties (name, slug) VALUES (?, ?)",
        specialty_rows,
    )

    hospital_url_map = {}
    for item in doctors_data:
        hospital_name = (item.get("hospital") or "").strip()
        hospital_url = (item.get("hospital_url") or "").strip()
        if hospital_name and hospital_name not in hospital_url_map:
            hospital_url_map[hospital_name] = hospital_url

    hospital_rows = [(name, hospital_url_map.get(name, "")) for name in hospital_names]
    cursor.executemany(
        "INSERT INTO hospitals (name, url) VALUES (?, ?)",
        hospital_rows,
    )

    cursor.execute("SELECT id, name FROM specialties")
    specialty_lookup = {name: sid for sid, name in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM hospitals")
    hospital_lookup = {name: hid for hid, name in cursor.fetchall()}

    print(f"[INFO] Da nap {len(specialty_lookup)} chuyen khoa")
    print(f"[INFO] Da nap {len(hospital_lookup)} benh vien")

    return specialty_lookup, hospital_lookup


def seed_doctors(
    cursor: sqlite3.Cursor,
    doctors_data: list[dict],
    specialty_lookup: dict,
    hospital_lookup: dict,
) -> int:
    rows = []
    for item in doctors_data:
        hospital_name = (item.get("hospital") or "").strip()
        specialty_name = (item.get("special") or "").strip()
        raw_degree = (item.get("degree") or "").strip()

        fee = random.randrange(300_000, 2_000_001, 100_000)
        langs = ["vi", "en"] if random.random() < 0.3 else ["vi"]

        rows.append(
            (
                (item.get("name") or "").strip(),
                (item.get("profile_url") or "").strip(),
                (item.get("img_url") or "").strip(),
                raw_degree,
                degree_level(raw_degree),
                specialty_lookup.get(specialty_name),
                hospital_lookup.get(hospital_name),
                fee,
                json.dumps(langs, ensure_ascii=False),
                1,
            )
        )

    cursor.executemany(
        """
        INSERT INTO doctors (
            name, profile_url, img_url, degree, degree_level,
            specialty_id, hospital_id, consultation_fee, languages, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    print(f"[INFO] Da nap {len(rows)} bac si")
    return len(rows)


def seed_time_slots(cursor: sqlite3.Cursor) -> int:
    cursor.execute("SELECT id FROM doctors")
    doctor_ids = [row[0] for row in cursor.fetchall()]

    slot_starts = [
        time(8, 0),
        time(8, 30),
        time(9, 0),
        time(9, 30),
        time(14, 0),
        time(14, 30),
        time(15, 0),
        time(15, 30),
    ]

    today = date.today()
    rows = []
    for doctor_id in doctor_ids:
        for day_offset in range(7):
            slot_day = today + timedelta(days=day_offset)
            for start_time in slot_starts:
                start_dt = datetime.combine(slot_day, start_time)
                end_dt = start_dt + timedelta(minutes=30)
                status = "available"
                rows.append(
                    (
                        doctor_id,
                        slot_day.isoformat(),
                        start_dt.time().strftime("%H:%M"),
                        end_dt.time().strftime("%H:%M"),
                        status,
                    )
                )

    cursor.executemany(
        """
        INSERT INTO time_slots (doctor_id, slot_date, slot_start, slot_end, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )

    print(f"[INFO] Da tao {len(rows)} lich kham")
    return len(rows)


def build_mock_patient(index: int) -> tuple[str, str, str, str, str]:
    first_names = [
        "Nguyen",
        "Tran",
        "Le",
        "Pham",
        "Hoang",
        "Phan",
        "Vu",
        "Dang",
        "Bui",
        "Do",
    ]
    middle_names = ["Van", "Thi", "Duc", "Minh", "Ngoc", "Thanh", "Quoc", "Bao"]
    last_names = [
        "An",
        "Binh",
        "Chau",
        "Dung",
        "Giang",
        "Hanh",
        "Hoa",
        "Hung",
        "Khanh",
        "Lan",
        "Linh",
        "Nam",
        "Nga",
        "Phong",
        "Trang",
        "Tuan",
    ]

    full_name = f"{random.choice(first_names)} {random.choice(middle_names)} {random.choice(last_names)}"
    phone = f"09{random.randint(10000000, 99999999)}"

    start_date = date(1965, 1, 1)
    end_date = date(2006, 12, 31)
    delta_days = (end_date - start_date).days
    dob = start_date + timedelta(days=random.randint(0, delta_days))
    gender = random.choice(["male", "female", "other"])

    insurance_code = ""
    if random.random() < 0.75:
        insurance_code = f"BHYT{random.randint(10000000, 99999999)}"

    session_id = f"session-{index:06d}"
    return session_id, full_name, phone, dob.isoformat(), gender, insurance_code


def seed_patients_and_appointments(cursor: sqlite3.Cursor) -> tuple[int, int]:
    cursor.execute(
        """
        SELECT id, doctor_id, slot_date, slot_start
        FROM time_slots
        ORDER BY slot_date, slot_start, id
        """
    )
    all_slots = cursor.fetchall()

    if not all_slots:
        print("[WARN] Khong co time slot, bo qua tao appointments/patients")
        return 0, 0

    # Keep pre-seeded booking data at a manageable size for demos/testing.
    min_target = 100
    max_target = 200
    target_count = random.randint(min_target, max_target)
    target_count = min(target_count, len(all_slots))

    selected_slots = random.sample(all_slots, target_count)
    selected_slots.sort(key=lambda x: (x[2], x[3], x[0]))

    # Only slots used by an appointment are marked as booked.
    selected_ids = [slot[0] for slot in selected_slots]
    cursor.executemany(
        "UPDATE time_slots SET status = 'booked' WHERE id = ?",
        [(sid,) for sid in selected_ids],
    )

    patient_rows = []
    appointment_rows = []

    booking_date_prefix = datetime.now().strftime("%Y%m%d")
    reason_templates = [
        "Kham tong quat",
        "Tai kham theo hen",
        "Tu van trieu chung moi",
        "Danh gia ket qua can lam sang",
        "Kiem tra tien trinh dieu tri",
    ]

    for idx, slot in enumerate(selected_slots, start=1):
        time_slot_id, doctor_id, _, _ = slot

        session_id, full_name, phone, dob, gender, insurance_code = build_mock_patient(idx)
        patient_rows.append((session_id, full_name, phone, dob, gender, insurance_code))

        booking_code = f"VMC-{booking_date_prefix}-{idx:04d}"
        status = "confirmed" if random.random() < 0.7 else "pending"
        reason = random.choice(reason_templates)
        notes = "Dat lich tu chatbot"

        # patient_id is assigned in insertion order, so it aligns with idx here.
        appointment_rows.append(
            (
                booking_code,
                idx,
                doctor_id,
                time_slot_id,
                reason,
                status,
                notes,
                "",
            )
        )

    cursor.executemany(
        """
        INSERT INTO patients (session_id, full_name, phone, dob, gender, insurance_code)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        patient_rows,
    )

    cursor.executemany(
        """
        INSERT INTO appointments (
            booking_code, patient_id, doctor_id, time_slot_id,
            reason, status, notes, cancelled_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        appointment_rows,
    )

    print(f"[INFO] Da tao {len(patient_rows)} patients (gioi han 100-200)")
    print(f"[INFO] Da tao {len(appointment_rows)} appointments va danh dau slot booked tuong ung")
    return len(patient_rows), len(appointment_rows)


def seed_medicines(cursor: sqlite3.Cursor, medicines_data: list[dict]) -> int:
    rows = []

    for item in medicines_data:
        name = first_non_empty(item, ["Ten", "Name", "name"])
        url = first_non_empty(item, ["URL", "url"])
        tag = first_non_empty(item, ["Tag", "tag"])

        form = first_non_empty(item, ["Dạng bào chế - biệt dược", "Dạng và hàm lượng", "form"])
        drug_group = first_non_empty(item, ["Nhóm thuốc – Tác dụng", "Nhóm thuốc - Tác dụng", "drug_group"])
        indications = first_non_empty(item, ["Chỉ định", "indications"])
        contraindications = first_non_empty(item, ["Chống chỉ định", "contraindications"])
        precautions = first_non_empty(item, ["Thận trọng", "precautions"])
        side_effects = first_non_empty(item, ["Tác dụng không mong muốn", "Tác dụng phụ", "side_effects"])
        dosage = first_non_empty(item, ["Liều và cách dùng", "Cách sử dụng", "dosage"])

        notes_chunks = [
            first_non_empty(item, ["Chú ý khi sử dụng", "Lưu ý khi sử dụng", "Hướng dẫn sử dụng", "notes"]),
            first_non_empty(item, ["Tài liệu tham khảo"]),
        ]
        notes = "\n\n".join([chunk for chunk in notes_chunks if chunk])

        search_text = " ".join([part for part in [name, drug_group, indications] if part]).strip()

        rows.append(
            (
                name,
                url,
                tag,
                form,
                drug_group,
                indications,
                contraindications,
                precautions,
                side_effects,
                dosage,
                notes,
                search_text,
            )
        )

    cursor.executemany(
        """
        INSERT INTO medicines (
            name, url, tag, form, drug_group, indications,
            contraindications, precautions, side_effects,
            dosage, notes, search_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    print(f"[INFO] Da nap {len(rows)} thuoc")
    return len(rows)


def seed_body_articles(cursor: sqlite3.Cursor, body_data: list[dict]) -> int:
    rows = []
    for item in body_data:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        description = (item.get("description") or "").strip()
        content = (item.get("content") or "").strip()
        sections = json.dumps(item.get("sections") or [], ensure_ascii=False)
        breadcrumb = (item.get("breadcrumb") or "").strip()
        scraped_at = (item.get("scraped_at") or "").strip()
        search_text = " ".join([part for part in [title, description, content] if part]).strip()

        rows.append((title, url, description, content, sections, breadcrumb, scraped_at, search_text))

    cursor.executemany(
        """
        INSERT INTO body_articles (
            title, url, description, content, sections,
            breadcrumb, scraped_at, search_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    print(f"[INFO] Da nap {len(rows)} bai viet co the nguoi")
    return len(rows)


def create_and_seed_diseases(cursor: sqlite3.Cursor, diseases_data: list[dict]) -> int:
    if not diseases_data:
        print("[WARN] Khong co du lieu benh de nap")
        return 0

    all_keys = sorted({key for item in diseases_data if isinstance(item, dict) for key in item.keys()})
    if not all_keys:
        print("[WARN] Du lieu benh khong co key hop le")
        return 0

    key_values = {key: [] for key in all_keys}
    for item in diseases_data:
        if not isinstance(item, dict):
            continue
        for key in all_keys:
            key_values[key].append(item.get(key))

    column_defs = []
    for key in all_keys:
        sql_type = infer_sql_type(key_values[key])
        safe_name = f'"{key}"'
        column_defs.append(f"{safe_name} {sql_type}")

    # Add search_text for semantic/keyword retrieval in chatbot flow.
    ddl = (
        "CREATE TABLE diseases ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + ", ".join(column_defs)
        + ", search_text TEXT"
        ")"
    )
    cursor.execute(ddl)

    insert_columns = [f'"{key}"' for key in all_keys] + ["search_text"]
    insert_sql = (
        "INSERT INTO diseases ("
        + ", ".join(insert_columns)
        + ") VALUES ("
        + ", ".join(["?"] * len(insert_columns))
        + ")"
    )

    rows = []
    for item in diseases_data:
        if not isinstance(item, dict):
            continue

        values = []
        for key in all_keys:
            value = item.get(key)
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value, ensure_ascii=False))
            else:
                values.append(value)

        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        detail_sections = item.get("detail_sections")
        detail_text = ""
        if isinstance(detail_sections, list):
            chunk = []
            for section in detail_sections:
                if not isinstance(section, dict):
                    continue
                sec_title = str(section.get("title") or "").strip()
                content = section.get("content")
                if isinstance(content, list):
                    sec_text = " ".join(str(x).strip() for x in content if str(x).strip())
                else:
                    sec_text = str(content or "").strip()
                if sec_title:
                    chunk.append(sec_title)
                if sec_text:
                    chunk.append(sec_text)
            detail_text = " ".join(chunk)

        search_text = " ".join(part for part in [title, url, detail_text] if part)
        values.append(search_text)
        rows.append(tuple(values))

    cursor.executemany(insert_sql, rows)
    cursor.execute("CREATE INDEX idx_diseases_title ON diseases(title)")

    print(f"[INFO] Da tao bang diseases voi {len(all_keys)} cot du lieu")
    print(f"[INFO] Da nap {len(rows)} benh vao diseases")
    return len(rows)


def main() -> None:
    random.seed(42)

    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"

    db_path = data_dir / DB_FILENAME
    doctors_path = data_dir / DOCTORS_FILENAME
    medicines_path = data_dir / MEDICINES_FILENAME
    body_content_path = data_dir / BODY_CONTENT_FILENAME
    diseases_path = data_dir / DISEASES_FILENAME

    doctors_data = load_json(doctors_path)
    medicines_data = load_json(medicines_path)
    body_data = load_json(body_content_path)
    diseases_data = load_json(diseases_path)

    if not doctors_data:
        print("[ERROR] Khong co du lieu bac si. Dung seed.")
        return

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        create_tables(cursor)
        specialty_lookup, hospital_lookup = seed_specialties_and_hospitals(cursor, doctors_data)
        doctors_count = seed_doctors(cursor, doctors_data, specialty_lookup, hospital_lookup)
        slots_count = seed_time_slots(cursor)
        patients_count, appointments_count = seed_patients_and_appointments(cursor)
        medicines_count = seed_medicines(cursor, medicines_data)
        body_count = seed_body_articles(cursor, body_data)
        diseases_count = create_and_seed_diseases(cursor, diseases_data)

        conn.commit()

    print("[DONE] Seed database thanh cong")
    print(f"[SUMMARY] DB: {db_path}")
    print(f"[SUMMARY] Chuyen khoa: {len(specialty_lookup)}")
    print(f"[SUMMARY] Benh vien: {len(hospital_lookup)}")
    print(f"[SUMMARY] Bac si: {doctors_count}")
    print(f"[SUMMARY] Lich kham: {slots_count}")
    print(f"[SUMMARY] Benh nhan: {patients_count}")
    print(f"[SUMMARY] Lich hen: {appointments_count}")
    print(f"[SUMMARY] Thuoc: {medicines_count}")
    print(f"[SUMMARY] Bai viet co the nguoi: {body_count}")
    print(f"[SUMMARY] Benh: {diseases_count}")


if __name__ == "__main__":
    main()
