import sqlite3
import pyshark
import geoip2.database
import ipaddress
from datetime import datetime

# ---------- Private IP Check ----------
def is_private_ip(ip):
    try:
        return ipaddress.ip_address(ip).is_private
    except:
        return True

# ---------- GeoIP Enrichment ----------
def enrich_ip(ip, reader_city, reader_asn):
    if is_private_ip(ip):
        return {
            "country": "Private",
            "city": "LAN",
            "lat": 0.0,
            "lon": 0.0,
            "asn": None,
            "org": "Private Network"
        }
    try:
        city_response = reader_city.city(ip)
        asn_response = reader_asn.asn(ip)

        lat = city_response.location.latitude
        lon = city_response.location.longitude

        if lat is None or lon is None:
            return {
                "country": city_response.country.name or "Unknown",
                "city": "Unknown (NoGeo)",
                "lat": 0.0,
                "lon": 0.0,
                "asn": f"AS{asn_response.autonomous_system_number}" if asn_response.autonomous_system_number else None,
                "org": asn_response.autonomous_system_organization or "Unknown"
            }

        return {
            "country": city_response.country.name or "Unknown",
            "city": city_response.city.name or "Unknown",
            "lat": lat,
            "lon": lon,
            "asn": f"AS{asn_response.autonomous_system_number}" if asn_response.autonomous_system_number else None,
            "org": asn_response.autonomous_system_organization or "Unknown"
        }

    except Exception as e:
        print(f"[GeoIP Lookup Failed] {ip} → {e}")
        return {
            "country": "Unknown",
            "city": "Unknown (NoGeo)",
            "lat": 0.0,
            "lon": 0.0,
            "asn": None,
            "org": None
        }

# ---------- Setup Database ----------
conn = sqlite3.connect("packets.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS packets (
    time TEXT, src TEXT, dst TEXT, proto TEXT, length INTEGER, flags TEXT, dns_query TEXT,
    src_country TEXT, src_city TEXT, src_lat REAL, src_lon REAL, src_asn TEXT, src_org TEXT,
    dst_country TEXT, dst_city TEXT, dst_lat REAL, dst_lon REAL, dst_asn TEXT, dst_org TEXT
)
""")
conn.commit()

# ---------- Load GeoLite DBs ----------
reader_city = geoip2.database.Reader("GeoLite2-City.mmdb")
reader_asn = geoip2.database.Reader("GeoLite2-ASN.mmdb")

# ---------- Packet Capture ----------
print("📡 Capturing enriched packets with GeoIP + ASN... Press Ctrl+C to stop.")
cap = pyshark.LiveCapture(interface="Wi-Fi")  # adjust interface if needed

for pkt in cap.sniff_continuously():
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        src = pkt.ip.src if hasattr(pkt, "ip") else None
        dst = pkt.ip.dst if hasattr(pkt, "ip") else None
        proto = pkt.transport_layer if hasattr(pkt, "transport_layer") else "?"
        length = int(pkt.length) if hasattr(pkt, "length") else 0
        flags = getattr(pkt.tcp, "flags", None) if hasattr(pkt, "tcp") else None
        dns_query = getattr(pkt.dns, "qry_name", None) if hasattr(pkt, "dns") else None

        src_info = enrich_ip(src, reader_city, reader_asn) if src else {}
        dst_info = enrich_ip(dst, reader_city, reader_asn) if dst else {}

        cursor.execute("""
        INSERT INTO packets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ts, src, dst, proto, length, flags, dns_query,
            src_info.get("country"), src_info.get("city"), src_info.get("lat"), src_info.get("lon"),
            src_info.get("asn"), src_info.get("org"),
            dst_info.get("country"), dst_info.get("city"), dst_info.get("lat"), dst_info.get("lon"),
            dst_info.get("asn"), dst_info.get("org")
        ))
        conn.commit()

        print(f"[+] {src} → {dst} | {proto} | {src_info.get('country')} → {dst_info.get('country')}")

    except Exception as e:
        print("Packet parse error:", e)
