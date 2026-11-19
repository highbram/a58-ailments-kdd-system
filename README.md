# A58 Ailments KDD System: Backend

Flask + SQLite server for the University Hospital Service, Jaja project.

## Run it
```
pip install flask
python seed.py     # optional: loads test data (not real hospital records)
python app.py
```
Folder layout: `app.py`, `schema.sql`, `seed.py`, and `static/index.html` (the web interface) — all included in this folder.
Open http://127.0.0.1:5000 in your browser. The server creates `uhs.db` from `schema.sql` on first run.
Default accounts (change before any real use): `admin / admin123`, `analyst / analyst123`.

## API
| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | /api/login, /api/logout | any | Session login (hashed passwords) |
| GET | /api/ailments | any | Ailment list |
| POST | /api/visits | any | Add a validated visit |
| GET | /api/visits?ailment=&patient=&limit= | any | Filtered records |
| DELETE | /api/visits/<id> | Admin | Delete a visit |
| POST | /api/import | any | CSV body: date,patient,age,sex,type,ailment,complaint,treatment |
| GET | /api/stats | any | Totals and groupings for the dashboard |
| GET | /api/trend?ailment= | any | Monthly counts for one ailment |
| GET | /api/seasonal | any | Peak month per ailment |
| GET | /api/rules?support=3&confidence=30 | any | Association rules (saved to mining_run and pattern) |
| GET | /api/audit | Admin | Audit log |

## Quick test
```
curl -c jar -X POST localhost:5000/api/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'
curl -b jar -X POST localhost:5000/api/visits -H "Content-Type: application/json" -d '{"date":"2026-09-30","patient":"P012","age":"18-24","sex":"F","type":"Student","ailment":"Malaria","complaint":"Fever","treatment":"Antimalarial"}'
curl -b jar localhost:5000/api/stats
```

## Before real use
- Set the `SECRET_KEY` environment variable and change the default passwords.
- Serve over HTTPS and get written approval from the University Hospital Service before loading real records.
- Keep only anonymised patient codes in this database.
