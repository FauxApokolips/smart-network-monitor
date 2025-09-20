import sqlite3

# open the database
conn = sqlite3.connect("packets.db")
cursor = conn.cursor()

# check how many rows have coordinates
cursor.execute("SELECT COUNT(*) FROM packets WHERE src_lat IS NOT NULL AND dst_lat IS NOT NULL;")
count = cursor.fetchone()[0]

print(f"✅ Rows with coordinates: {count}")

# show last 5 packets with lat/lon
cursor.execute("""
SELECT time, src, dst, src_country, src_city, src_lat, src_lon, dst_country, dst_city, dst_lat, dst_lon
FROM packets
ORDER BY rowid DESC
LIMIT 5;
""")
rows = cursor.fetchall()

print("\n🔎 Last 5 enriched packets:")
for r in rows:
    print(r)

conn.close()
