# create_database.py
import sqlite3
import csv
import os
from datetime import datetime

DB_FILE = "hospital_data.db"

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# --- Patients Table ---
cur.execute("""
CREATE TABLE IF NOT EXISTS patients (
    sno INTEGER PRIMARY KEY AUTOINCREMENT,
    mrd_no TEXT UNIQUE,
    doa TEXT,
    dod TEXT,
    name TEXT,
    age INTEGER,
    gender TEXT,
    department TEXT,
    type_of_admission TEXT,
    duration_of_stay REAL,
    outcome TEXT,
    smoking TEXT,
    alcohol TEXT,
    hb REAL,
    tlc REAL,
    platelets REAL,
    glucose REAL,
    anaemia TEXT,
    heart_failure TEXT,
    uti TEXT,
    chest_infection TEXT
)
""")

# --- Bed Details Table ---
cur.execute("""
CREATE TABLE IF NOT EXISTS beddetails (
    bed_serial TEXT PRIMARY KEY,
    department TEXT,
    occupied TEXT DEFAULT 'NO',
    patient_sno INTEGER,
            
    FOREIGN KEY(patient_sno) REFERENCES patients(sno)
)
""")

# --- Users Table ---
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
""")

# --- Create 50 beds per department ---
departments = ["General","ICU","Pediatrics","Maternity","Surgery"]
bed_count = 50  # beds per department

for dept in departments:
    for i in range(1, bed_count + 1):
        bed_id = f"BED-{dept[:3].upper()}-{i:03d}"
        cur.execute("INSERT OR IGNORE INTO beddetails (bed_serial, department) VALUES (?,?)", (bed_id, dept))

# --- Import data from admission.csv if available and assign beds ---
if os.path.exists("Admissiondat.csv"):
    with open("Admissiondata.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Calculate duration_of_stay if DOA and DOD are present
            duration = None
            if row.get("doa") and row.get("dod"):
                try:
                    doa_date = datetime.strptime(row["doa"], "%Y-%m-%d")
                    dod_date = datetime.strptime(row["dod"], "%Y-%m-%d")
                    duration = (dod_date - doa_date).days
                except Exception:
                    duration = None
            row["duration_of_stay"] = duration

            # Ensure type_of_admission exists in row (default to "Routine" if missing)
            if "type_of_admission" not in row or not row["type_of_admission"]:
                row["type_of_admission"] = "Routine"

            columns = ", ".join(row.keys())
            placeholders = ", ".join("?" * len(row))
            values = list(row.values())

            # Insert patient
            cur.execute(f"INSERT OR IGNORE INTO patients ({columns}) VALUES ({placeholders})", values)
            patient_sno = cur.lastrowid

            # Assign a free bed in the same department if available
            cur.execute("""
                SELECT bed_serial FROM beddetails
                WHERE department = ? AND occupied = 'NO'
                ORDER BY bed_serial ASC LIMIT 1
            """, (row.get("department"),))
            bed = cur.fetchone()
            if bed:
                cur.execute("""
                    UPDATE beddetails SET occupied = 'YES', patient_sno = ?
                    WHERE bed_serial = ?
                """, (patient_sno, bed[0]))

conn.commit()
conn.close()
print("✅ Database created with updated patients table (type_of_admission included), 50 beds per department, CSV imported, auto bed assignment, and duration of stay calculated")