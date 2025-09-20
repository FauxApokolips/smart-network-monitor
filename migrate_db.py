import sqlite3

# Path to DB
DB_PATH = "packets.db"

# Connect to DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Drop old table (⚠ this will delete old data)
cursor.execute("DROP TABLE IF EXISTS packets")

# Create new enriched schema
cursor.execute("""
CREATE TABLE IF NOT EXISTS packets (
    time TEXT,
    src TEXT,
    dst TEXT,
    proto TEXT,
    length INTEGER,
    flags TEXT,
    dns_query TEXT,
    src_country TEXT,
    src_city TEXT,
    src_lat REAL,
    src_lon REAL,
    src_asn TEXT,
    src_org TEXT,
    dst_country TEXT,
    dst_city TEXT,
    dst_lat REAL,
    dst_lon REAL,
    dst_asn TEXT,
    dst_org TEXT,
    threat TEXT
)
""")

conn.commit()
conn.close()

print("✅ packets.db schema migrated successfully (old data removed).")
