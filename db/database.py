import sqlite3
from uuid import uuid4
from datetime import datetime

conn = sqlite3.connect("weights.db", check_same_thread=False)

conn.execute('''
CREATE TABLE IF NOT EXISTS weight_events (
    id TEXT PRIMARY KEY,
    timestamp TEXT,
    starting_weight REAL,
    final_weight REAL
)
''')
conn.commit()

def log_event(starting_weight, final_weight):
    conn.execute("INSERT INTO weight_events VALUES (?, ?, ?, ?)",
                 (str(uuid4()), datetime.now().isoformat(), starting_weight, final_weight))
    conn.commit()

def get_events(start, end):
    cur = conn.execute("SELECT * FROM weight_events WHERE timestamp BETWEEN ? AND ?", (start, end))
    return [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]

def get_all_events():
    cur = conn.execute("SELECT * FROM weight_events ORDER BY timestamp DESC")
    return [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]

def get_filtered_events(min_weight=None, max_weight=None, start=None, end=None):
    query = "SELECT * FROM weight_events WHERE 1=1"
    params = []
    if min_weight is not None:
        query += " AND final_weight >= ?"
        params.append(min_weight)
    if max_weight is not None:
        query += " AND final_weight <= ?"
        params.append(max_weight)
    if start is not None:
        query += " AND timestamp >= ?"
        params.append(start)
    if end is not None:
        query += " AND timestamp <= ?"
        params.append(end)
    query += " ORDER BY timestamp DESC"
    cur = conn.execute(query, tuple(params))
    return [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]