"""Load SIMULATED sample visits so the dashboard and mining have data to show.
Run once:  python seed.py      (not real clinic data - replace with real records after approval)"""
import random, sqlite3
from app import DB, init_db, AGES, TYPES

init_db()
con = sqlite3.connect(DB)
if con.execute("SELECT 1 FROM visit").fetchone():
    raise SystemExit("Database already has visits; nothing seeded.")

ail = {n: i for i, n in con.execute("SELECT ailment_id, ailment_name FROM ailment")}
names = ["Malaria", "Typhoid fever", "Upper respiratory infection", "Hypertension", "Peptic ulcer",
         "Skin infection", "Migraine", "Urinary tract infection", "Allergy", "Injury/Sprain"]
r = random.Random(58)


def add(date, n, name, complaint):
    code = f"P{n:03d}"
    con.execute("INSERT OR IGNORE INTO patient VALUES(?,?,?,?)",
                (code, AGES[(n * 7) % 4], "F" if n % 2 else "M", TYPES[[0, 0, 0, 0, 1, 2][n % 6]]))
    vid = con.execute("INSERT INTO visit(patient_code,visit_date,complaint) VALUES(?,?,?)",
                      (code, date, complaint)).lastrowid
    con.execute("INSERT INTO diagnosis(visit_id,ailment_id,treatment_given) VALUES(?,?,?)",
                (vid, ail[name], "Prescribed"))


for _ in range(420):
    m = r.randrange(12)
    mo, yr = (9 + m) % 12, 2025 if m < 3 else 2026          # Oct 2025 .. Sep 2026
    w = [9 if 3 <= mo <= 9 else 3, 2.5, 9 if mo >= 10 or mo <= 1 else 3, 3, 2, 2, 2.5, 2, 1.5, 2]
    name = r.choices(names, w)[0]
    n, date = r.randint(1, 150), f"{yr}-{mo + 1:02d}-{r.randint(1, 27):02d}"
    add(date, n, name, "Routine consultation")
    if name == "Typhoid fever" and r.random() < .6: add(date, n, "Peptic ulcer", "Stomach pain")
    if name == "Upper respiratory infection" and r.random() < .4: add(date, n, "Allergy", "Rash/itching")

con.commit()
print("Seeded", con.execute("SELECT COUNT(*) FROM visit").fetchone()[0], "simulated visits.")
