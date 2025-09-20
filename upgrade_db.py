# upgrade_db.py
import sqlite3
from datetime import datetime

# Connect to SQLite
conn = sqlite3.connect("packets.db")
cursor = conn.cursor()

# Step 1: Ensure all timestamps use full datetime
cursor.execute("SELECT rowid, time FROM packets")
rows = cursor.fetchall()

updated = 0
for rowid, t in rows:
    # If it's just HH:MM:SS (length == 8)
    if len(t) == 8 and ":" in t:
        new_time = datetime.now().strftime("%Y-%m-%d") + " " + t
        cursor.execute("UPDATE packets SET time = ? WHERE rowid = ?", (new_time, rowid))
        updated += 1

conn.commit()
print(f"✅ Upgraded {updated} rows to full datetime format")

# Step 2: Add an index on `time` if it doesn’t exist already
try:
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON packets(time)")
    conn.commit()
    print("✅ Index on `time` column created/verified")
except Exception as e:
    print("⚠️ Could not create index:", e)

conn.close()
