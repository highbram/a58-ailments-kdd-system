"""Ailments Knowledge Discovery System - UHS Jaja (Group A58). Flask + SQLite backend."""
import csv, io, json, os, re, sqlite3
from functools import wraps
from flask import Flask, Response, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "uhs.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
AGES, TYPES, SEXES = ("<18", "18-24", "25-34", "35+"), ("Student", "Staff", "Dependant"), ("M", "F")


# ---------- database ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    con = sqlite3.connect(DB)
    with open(os.path.join(BASE, "schema.sql")) as f:
        con.executescript(f.read())
    if not con.execute("SELECT 1 FROM user").fetchone():
        for u, p, r in (("admin", "admin123", "Admin"), ("analyst", "analyst123", "Analyst")):
            con.execute("INSERT INTO user(username,password_hash,role) VALUES(?,?,?)",
                        (u, generate_password_hash(p), r))
    con.commit()
    con.close()


# ---------- helpers ----------
def need(role=None):
    def deco(fn):
        @wraps(fn)
        def wrap(*a, **kw):
            if "uid" not in session:
                return jsonify(error="Login required"), 401
            if role and session["role"] != role:
                return jsonify(error="Access denied"), 403
            return fn(*a, **kw)
        return wrap
    return deco


def audit(action):
    db().execute("INSERT INTO audit_log(user_id,action) VALUES(?,?)", (session.get("uid"), action))


def check_visit(d):
    """Return an error message, or None if the visit data is valid."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.get("date", "")): return "Date must be YYYY-MM-DD"
    if not re.fullmatch(r"P\d{3}", d.get("patient", "")): return "Patient code must look like P012"
    if d.get("age") not in AGES: return "Invalid age group"
    if d.get("sex") not in SEXES: return "Invalid sex"
    if d.get("type") not in TYPES: return "Invalid patient type"
    if not str(d.get("complaint", "")).strip() or not str(d.get("treatment", "")).strip():
        return "Complaint and treatment are required"
    return None


def insert_visit(d):
    """Insert one visit + diagnosis. Returns (ok, message)."""
    err = check_visit(d)
    if err: return False, err
    c = db()
    ail = c.execute("SELECT ailment_id FROM ailment WHERE ailment_name=?", (d.get("ailment"),)).fetchone()
    if not ail: return False, "Unknown ailment"
    dup = c.execute("""SELECT 1 FROM visit v JOIN diagnosis g USING(visit_id)
                       WHERE v.patient_code=? AND v.visit_date=? AND g.ailment_id=?""",
                    (d["patient"], d["date"], ail["ailment_id"])).fetchone()
    if dup: return False, "Duplicate visit"
    c.execute("INSERT OR IGNORE INTO patient VALUES(?,?,?,?)", (d["patient"], d["age"], d["sex"], d["type"]))
    cur = c.execute("INSERT INTO visit(patient_code,visit_date,complaint) VALUES(?,?,?)",
                    (d["patient"], d["date"], d["complaint"].strip()))
    c.execute("INSERT INTO diagnosis(visit_id,ailment_id,treatment_given) VALUES(?,?,?)",
              (cur.lastrowid, ail["ailment_id"], d["treatment"].strip()))
    return True, "ok"


BASE_Q = """FROM visit v JOIN patient p USING(patient_code)
            JOIN diagnosis g USING(visit_id) JOIN ailment a USING(ailment_id)"""


# ---------- auth ----------
@app.post("/api/login")
def login():
    d = request.get_json(force=True, silent=True) or {}
    u = db().execute("SELECT * FROM user WHERE username=?", (str(d.get("username", "")).lower(),)).fetchone()
    if not u or not check_password_hash(u["password_hash"], str(d.get("password", ""))):
        return jsonify(error="Invalid username or password"), 401
    session.update(uid=u["user_id"], role=u["role"], name=u["username"])
    audit("Login"); db().commit()
    return jsonify(user=u["username"], role=u["role"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/ailments")
@need()
def ailments():
    return jsonify([r["ailment_name"] for r in db().execute("SELECT ailment_name FROM ailment")])


# ---------- visits ----------
@app.post("/api/visits")
@need()
def add_visit():
    ok, msg = insert_visit(request.get_json(force=True, silent=True) or {})
    if not ok: return jsonify(error=msg), 400
    audit("Added visit"); db().commit()
    return jsonify(ok=True), 201


@app.get("/api/visits")
@need()
def list_visits():
    q, args = "SELECT v.visit_id id, v.visit_date date, v.patient_code patient, p.patient_type type, p.age_group age, a.ailment_name ailment " + BASE_Q + " WHERE 1=1", []
    if request.args.get("ailment"): q += " AND a.ailment_name=?"; args.append(request.args["ailment"])
    if request.args.get("patient"): q += " AND v.patient_code LIKE ?"; args.append("%" + request.args["patient"].upper() + "%")
    q += " ORDER BY v.visit_date DESC LIMIT ?"; args.append(min(int(request.args.get("limit", 40)), 500))
    return jsonify([dict(r) for r in db().execute(q, args)])


@app.delete("/api/visits/<int:vid>")
@need("Admin")
def delete_visit(vid):
    db().execute("DELETE FROM visit WHERE visit_id=?", (vid,))
    audit(f"Deleted visit {vid}"); db().commit()
    return jsonify(ok=True)


@app.post("/api/import")
@need()
def import_csv():
    """Body: CSV text with rows date,patient,age,sex,type,ailment,complaint,treatment."""
    ok = bad = 0
    for r in csv.reader(io.StringIO(request.get_data(as_text=True))):
        if len(r) < 8: bad += 1; continue
        keys = ("date", "patient", "age", "sex", "type", "ailment", "complaint", "treatment")
        good, _ = insert_visit({k: v.strip() for k, v in zip(keys, r)})
        ok, bad = (ok + 1, bad) if good else (ok, bad + 1)
    audit(f"Import: {ok} ok, {bad} rejected"); db().commit()
    return jsonify(imported=ok, rejected=bad)


# ---------- statistics and mining ----------
@app.get("/api/stats")
@need()
def stats():
    c = db()
    grp = lambda col: {r["k"]: r["n"] for r in c.execute(f"SELECT {col} k, COUNT(*) n {BASE_Q} GROUP BY k ORDER BY n DESC")}
    return jsonify(total=c.execute("SELECT COUNT(*) FROM visit").fetchone()[0],
                   patients=c.execute("SELECT COUNT(*) FROM patient").fetchone()[0],
                   by_ailment=grp("a.ailment_name"), by_type=grp("p.patient_type"), by_age=grp("p.age_group"),
                   by_month=grp("substr(v.visit_date,1,7)"))


def record_run(technique, params, patterns):
    cur = db().execute("INSERT INTO mining_run(user_id,technique,parameters) VALUES(?,?,?)",
                       (session["uid"], technique, json.dumps(params)))
    for desc, s, cf, lf in patterns:
        db().execute("INSERT INTO pattern(run_id,description,support,confidence,lift) VALUES(?,?,?,?,?)",
                     (cur.lastrowid, desc, s, cf, lf))
    audit(f"Ran {technique}"); db().commit()


@app.get("/api/trend")
@need()
def trend():
    a = request.args.get("ailment", "")
    rows = db().execute(f"SELECT substr(v.visit_date,1,7) m, COUNT(*) n {BASE_Q} WHERE a.ailment_name=? GROUP BY m ORDER BY m", (a,))
    data = [dict(r) for r in rows]
    if data: record_run("trend", {"ailment": a}, [(f"{a} peaked in {max(data, key=lambda r: r['n'])['m']}", None, None, None)])
    return jsonify(data)


@app.get("/api/seasonal")
@need()
def seasonal():
    rows = db().execute(f"SELECT a.ailment_name a, substr(v.visit_date,6,2) m, COUNT(*) n {BASE_Q} GROUP BY a, m")
    peak = {}
    for r in rows:
        if r["a"] not in peak or r["n"] > peak[r["a"]]["cases"]:
            peak[r["a"]] = {"month": int(r["m"]), "cases": r["n"]}
    record_run("seasonal", {}, [(f"{a} peaks in month {p['month']}", None, None, None) for a, p in peak.items()])
    return jsonify(peak)


@app.get("/api/rules")
@need()
def rules():
    """Association rules A -> B over each patient's set of ailments."""
    sup, conf = float(request.args.get("support", 3)) / 100, float(request.args.get("confidence", 30)) / 100
    baskets = {}
    for r in db().execute(f"SELECT v.patient_code p, a.ailment_name a {BASE_Q}"):
        baskets.setdefault(r["p"], set()).add(r["a"])
    n = len(baskets) or 1
    single, pair = {}, {}
    for s in baskets.values():
        for a in s:
            single[a] = single.get(a, 0) + 1
            for b in s:
                if a != b: pair[(a, b)] = pair.get((a, b), 0) + 1
    out = []
    for (a, b), k in pair.items():
        s, c = k / n, k / single[a]
        if s >= sup and c >= conf:
            out.append({"if": a, "then": b, "support": round(s, 3), "confidence": round(c, 3), "lift": round(c / (single[b] / n), 2)})
    out.sort(key=lambda r: -r["lift"])
    out = out[:12]
    record_run("association", {"support": sup, "confidence": conf}, [(f"{r['if']} -> {r['then']}", r["support"], r["confidence"], r["lift"]) for r in out])
    return jsonify(patients=n, rules=out)


@app.get("/api/audit")
@need("Admin")
def audit_log():
    rows = db().execute("SELECT l.timestamp, u.username, l.action FROM audit_log l LEFT JOIN user u USING(user_id) ORDER BY log_id DESC LIMIT 30")
    return jsonify([dict(r) for r in rows])


@app.get("/")
def home():
    return send_from_directory(os.path.join(BASE, "static"), "index.html")


@app.get("/api/me")
def me():
    if "uid" not in session:
        return jsonify(error="Login required"), 401
    return jsonify(user=session["name"], role=session["role"])


@app.get("/api/export")
@need()
def export_csv():
    out = io.StringIO()
    w = csv.writer(out)
    for r in db().execute("""SELECT v.visit_date, v.patient_code, p.age_group, p.sex, p.patient_type,
                             a.ailment_name, v.complaint, g.treatment_given """ + BASE_Q + " ORDER BY v.visit_date"):
        w.writerow(list(r))
    audit("Exported CSV"); db().commit()
    return Response(out.getvalue(), mimetype="text/csv")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
