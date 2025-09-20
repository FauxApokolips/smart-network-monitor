import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import pydeck as pdk
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ----------------- Page Setup -----------------
st.set_page_config(page_title="Smart Network Monitor", layout="wide")
st.title("📡 Smart Network Monitor (Lite) + GeoIP + ASN + Alerts")
st.caption("Live traffic, anomaly detection, ASN/Org filters, and global flows")

# ----------------- Auto-refresh -----------------
refresh_rate = st.sidebar.slider("🔄 Refresh Interval (seconds)", 1, 10, 3, 1)
st_autorefresh(interval=refresh_rate * 1000, key="refresh")

# ----------------- SQL Loader -----------------
def query_data(limit=5000):
    conn = sqlite3.connect("packets.db", check_same_thread=False)
    df = pd.read_sql_query("SELECT * FROM packets ORDER BY rowid DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    return df.iloc[::-1].reset_index(drop=True)

# ----------------- Session State -----------------
if "last_alert_at" not in st.session_state:
    st.session_state["last_alert_at"] = datetime.min

# ----------------- Controls -----------------
c1, c2, c3 = st.columns(3)
with c1:
    enable_alerts = st.toggle("Enable Alerts", True)
with c2:
    contamination = st.slider("Anomaly Sensitivity", 0.01, 0.3, 0.10, 0.01)
with c3:
    cooldown_min = st.slider("Alert Cooldown (minutes)", 1, 60, 10, 1)

# ----------------- Load Data -----------------
df = query_data()

if df.empty:
    st.warning("⚠ No packet data yet. Run snm_capture.py.")
else:
    # ----------------- Sidebar Filters -----------------
    st.sidebar.header("🔍 Filters")
    proto_filter = st.sidebar.multiselect("Protocol", sorted(df["proto"].dropna().unique()))
    src_country = st.sidebar.multiselect("Source Country", sorted(df["src_country"].dropna().unique()))
    dst_country = st.sidebar.multiselect("Destination Country", sorted(df["dst_country"].dropna().unique()))
    ip_filter = st.sidebar.text_input("Filter IP (src/dst)")
    asn_filter = st.sidebar.multiselect("Source ASN/Org", 
        sorted(df[["src_asn","src_org"]].dropna().apply(lambda x: f"{x['src_asn']} - {x['src_org']}", axis=1).unique()))
    dst_asn_filter = st.sidebar.multiselect("Destination ASN/Org", 
        sorted(df[["dst_asn","dst_org"]].dropna().apply(lambda x: f"{x['dst_asn']} - {x['dst_org']}", axis=1).unique()))

    # ----------------- Apply Filters -----------------
    df_filtered = df.copy()
    if proto_filter: df_filtered = df_filtered[df_filtered["proto"].isin(proto_filter)]
    if src_country: df_filtered = df_filtered[df_filtered["src_country"].isin(src_country)]
    if dst_country: df_filtered = df_filtered[df_filtered["dst_country"].isin(dst_country)]
    if ip_filter: df_filtered = df_filtered[(df_filtered["src"] == ip_filter) | (df_filtered["dst"] == ip_filter)]
    if asn_filter: 
        df_filtered = df_filtered[df_filtered.apply(lambda x: f"{x['src_asn']} - {x['src_org']}" in asn_filter, axis=1)]
    if dst_asn_filter: 
        df_filtered = df_filtered[df_filtered.apply(lambda x: f"{x['dst_asn']} - {x['dst_org']}" in dst_asn_filter, axis=1)]

    # ----------------- Enriched Table -----------------
    st.subheader("📄 Enriched Packets (last 20, filtered)")
    st.dataframe(
        df_filtered[
            ["time","src","dst","proto","length","flags","dns_query",
             "src_country","src_city","src_asn","src_org",
             "dst_country","dst_city","dst_asn","dst_org"]
        ].tail(20), use_container_width=True
    )

    # ----------------- World Map -----------------
    st.subheader("🌍 Network Traffic Flows (Threats in Red)")
    df_geo = df_filtered[
        (df_filtered["src_lat"] != 0.0) & 
        (df_filtered["dst_lat"] != 0.0) &
        (df_filtered["src_city"] != "Unknown (NoGeo)") &
        (df_filtered["dst_city"] != "Unknown (NoGeo)")
    ].tail(2000)

    if not df_geo.empty:
        arc_layer = pdk.Layer(
            "ArcLayer",
            data=df_geo,
            get_source_position=["src_lon", "src_lat"],
            get_target_position=["dst_lon", "dst_lat"],
            get_source_color=[0, 128, 200, 160],
            get_target_color=[200, 0, 0, 160],  # threats in red
            get_width="length / 200",
            pickable=True
        )
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.concat([
                df_geo.rename(columns={"src_lon": "lon", "src_lat": "lat"})[["lat", "lon"]],
                df_geo.rename(columns={"dst_lon": "lon", "dst_lat": "lat"})[["lat", "lon"]],
            ]),
            get_position=["lon","lat"],
            get_color=[0,200,200,160],
            get_radius=20000
        )
        st.pydeck_chart(pdk.Deck(
            layers=[arc_layer, scatter_layer],
            initial_view_state=pdk.ViewState(latitude=20, longitude=0, zoom=1),
            tooltip={"html":"<b>{src}</b> → <b>{dst}</b><br/>"
                            "{src_country} ({src_asn}) → {dst_country} ({dst_asn})"}
        ))
    else:
        st.info("No valid flows with coordinates yet.")

    # ----------------- Traffic Over Time -----------------
    st.subheader("📈 Traffic Over Time (bytes per tick)")
    traffic = df_filtered.groupby("time")["length"].sum().reset_index().tail(200)
    if not traffic.empty:
        model = IsolationForest(contamination=contamination, random_state=42)
        traffic["anomaly"] = model.fit_predict(traffic[["length"]])
        anomalies = traffic[traffic["anomaly"] == -1]

        base = alt.Chart(traffic).mark_line(color="steelblue").encode(
            x="time:T", y="length:Q", tooltip=["time", "length"]
        )
        if not anomalies.empty:
            dots = alt.Chart(anomalies).mark_point(color="red", size=80).encode(
                x="time:T", y="length:Q", tooltip=["time","length"]
            )
            st.altair_chart(base + dots, use_container_width=True)

            # 🚨 External-only Alerts
            recent_ext = df_geo.tail(1)
            if enable_alerts and not recent_ext.empty:
                if datetime.now() - st.session_state["last_alert_at"] > timedelta(minutes=cooldown_min):
                    st.error(f"🚨 Anomaly detected in external traffic! Src={recent_ext['src'].values[0]} Dst={recent_ext['dst'].values[0]}")
                    st.session_state["last_alert_at"] = datetime.now()
        else:
            st.altair_chart(base, use_container_width=True)

    # ----------------- Top Stats -----------------
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🌍 Top Source Countries")
        st.bar_chart(df_filtered["src_country"].value_counts().head(5))
    with c2:
        st.subheader("🔑 Protocol Distribution")
        st.bar_chart(df_filtered["proto"].value_counts())
    with c3:
        st.subheader("🏢 Top Organizations (Dst)")
        st.bar_chart(df_filtered["dst_org"].value_counts().head(5))
