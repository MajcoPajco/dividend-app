import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Automatické obnovovanie stránky každú minútu (ak je knižnica dostupná)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60_000, limit=None, key="autorefresh")
except Exception:
    pass

st.set_page_config(
    page_title="Svetové burzy - otváracie hodiny",
    page_icon="📈",
    layout="wide",
)

BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

# Zoznam najznámejších búrz: názov, kód, mesto, časové pásmo, čas otvorenia/zatvorenia (miestny čas burzy)
EXCHANGES = [
    {"name": "New York Stock Exchange", "code": "NYSE", "city": "New York, USA",
     "tz": "America/New_York", "open": "09:30", "close": "16:00", "flag": "🇺🇸"},
    {"name": "NASDAQ", "code": "NASDAQ", "city": "New York, USA",
     "tz": "America/New_York", "open": "09:30", "close": "16:00", "flag": "🇺🇸"},
    {"name": "Toronto Stock Exchange", "code": "TSX", "city": "Toronto, Kanada",
     "tz": "America/Toronto", "open": "09:30", "close": "16:00", "flag": "🇨🇦"},
    {"name": "London Stock Exchange", "code": "LSE", "city": "Londýn, Spojené kráľovstvo",
     "tz": "Europe/London", "open": "08:00", "close": "16:30", "flag": "🇬🇧"},
    {"name": "Euronext Paris", "code": "EPA", "city": "Paríž, Francúzsko",
     "tz": "Europe/Paris", "open": "09:00", "close": "17:30", "flag": "🇫🇷"},
    {"name": "Deutsche Börse (Xetra)", "code": "FRA", "city": "Frankfurt, Nemecko",
     "tz": "Europe/Berlin", "open": "09:00", "close": "17:30", "flag": "🇩🇪"},
    {"name": "SIX Swiss Exchange", "code": "SIX", "city": "Zürich, Švajčiarsko",
     "tz": "Europe/Zurich", "open": "09:00", "close": "17:30", "flag": "🇨🇭"},
    {"name": "Tokyo Stock Exchange", "code": "TSE", "city": "Tokio, Japonsko",
     "tz": "Asia/Tokyo", "open": "09:00", "close": "15:00", "flag": "🇯🇵"},
    {"name": "Hong Kong Stock Exchange", "code": "HKEX", "city": "Hongkong",
     "tz": "Asia/Hong_Kong", "open": "09:30", "close": "16:00", "flag": "🇭🇰"},
    {"name": "Shanghai Stock Exchange", "code": "SSE", "city": "Šanghaj, Čína",
     "tz": "Asia/Shanghai", "open": "09:30", "close": "15:00", "flag": "🇨🇳"},
    {"name": "Bombay Stock Exchange", "code": "BSE", "city": "Bombaj, India",
     "tz": "Asia/Kolkata", "open": "09:15", "close": "15:30", "flag": "🇮🇳"},
    {"name": "Australian Securities Exchange", "code": "ASX", "city": "Sydney, Austrália",
     "tz": "Australia/Sydney", "open": "10:00", "close": "16:00", "flag": "🇦🇺"},
]


def get_status(exchange: dict, now_utc: datetime) -> dict:
    """Zistí, či je burza otvorená, a vráti časový rozdiel (do otvorenia / od otvorenia)."""
    tz = ZoneInfo(exchange["tz"])
    now_local = now_utc.astimezone(tz)

    open_h, open_m = map(int, exchange["open"].split(":"))
    close_h, close_m = map(int, exchange["close"].split(":"))

    today_open = now_local.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    today_close = now_local.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

    is_weekday = now_local.weekday() < 5  # pondelok-piatok
    is_open = is_weekday and today_open <= now_local < today_close

    if is_open:
        delta = now_local - today_open
        return {"is_open": True, "delta": delta, "local_time": now_local}

    # Burza je zatvorená - nájdeme najbližší budúci čas otvorenia
    if is_weekday and now_local < today_open:
        candidate = today_open
    else:
        candidate = today_open + timedelta(days=1)

    # Preskočíme víkend (sobota=5, nedeľa=6)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)

    delta = candidate - now_local
    return {"is_open": False, "delta": delta, "local_time": now_local}


def format_delta(delta: timedelta) -> str:
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} h {minutes:02d} min"


# --------------------------- UI ---------------------------

st.title("📈 Prehľad svetových búrz")

now_utc = datetime.now(ZoneInfo("UTC"))
now_bratislava = now_utc.astimezone(BRATISLAVA_TZ)

st.markdown(
    f"##### 🇸🇰 Aktuálny čas v Bratislave: **{now_bratislava.strftime('%H:%M:%S')}** "
    f"({now_bratislava.strftime('%d.%m.%Y')})"
)

st.caption(
    "Údaje sa aktualizujú automaticky každú minútu. 🟢 Zelenou farbou sú burzy, ktoré sú práve otvorené "
    "(zobrazuje sa, ako dlho už obchodovanie prebieha). 🔴 Červenou farbou sú zatvorené burzy "
    "(zobrazuje sa čas zostávajúci do otvorenia)."
)

st.markdown(
    """
    <style>
    .exchange-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14.5px;
    }
    .exchange-table th {
        text-align: left;
        padding: 6px 12px;
        border-bottom: 2px solid rgba(128, 128, 128, 0.35);
        opacity: 0.65;
        font-weight: 600;
        font-size: 12.5px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .exchange-table td {
        padding: 7px 12px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.15);
        white-space: nowrap;
    }
    .row-open td { color: #22c55e; font-weight: 600; }
    .row-closed td { color: #ef4444; font-weight: 600; }
    .status-badge { font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

results = [(ex, get_status(ex, now_utc)) for ex in EXCHANGES]

# Zoradenie: otvorené burzy hore, potom podľa najbližšieho času do otvorenia
results.sort(key=lambda item: (not item[1]["is_open"], item[1]["delta"]))

rows_html = ""
for ex, status in results:
    local_time_str = status["local_time"].strftime("%H:%M")
    row_class = "row-open" if status["is_open"] else "row-closed"

    if status["is_open"]:
        stav = "🟢 Otvorené"
        info = f"už {format_delta(status['delta'])}"
    else:
        stav = "🔴 Zatvorené"
        info = f"otvára o {format_delta(status['delta'])}"

    rows_html += f"""
        <tr class="{row_class}">
            <td>{ex['flag']} {ex['name']} ({ex['code']})</td>
            <td>{ex['city']}</td>
            <td>{local_time_str}</td>
            <td class="status-badge">{stav}</td>
            <td>{info}</td>
        </tr>
    """

table_html = f"""
<table class="exchange-table">
    <thead>
        <tr>
            <th>Burza</th>
            <th>Mesto</th>
            <th>Miestny čas</th>
            <th>Stav</th>
            <th>Info</th>
        </tr>
    </thead>
    <tbody>
        {rows_html}
    </tbody>
</table>
"""

st.markdown(table_html, unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "⚠️ Poznámka: aplikácia nezohľadňuje štátne sviatky ani obedné prestávky niektorých ázijských búrz "
    "(napr. Tokio, Hongkong, Šanghaj). Časy otvorenia/zatvorenia sú orientačné podľa bežného obchodného kalendára."
)
