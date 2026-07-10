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

# POZNÁMKA: Streamlit Markdown si riadky odsadené 4+ medzerami môže pomýliť
# s blokom kódu a HTML potom zobrazí ako čistý text. Preto sa celé HTML
# skladá bez odsadenia (na jeden "riadok" na tag), nikdy ako viacriadkový
# odsadený reťazec.
BOARD_CSS = (
    "<style>"
    ".board-wrap{background:#0b0f14;border-radius:10px;padding:6px 0;border:1px solid #1e2530;}"
    ".board{width:100%;border-collapse:collapse;font-family:'Courier New',Consolas,monospace;}"
    ".board th{text-align:left;padding:8px 18px;font-size:12px;letter-spacing:0.12em;"
    "color:#5b6674;text-transform:uppercase;border-bottom:1px solid #1e2530;}"
    ".board td{padding:9px 18px;font-size:16px;letter-spacing:0.05em;white-space:nowrap;}"
    ".row-open td{color:#2ee66b;text-shadow:0 0 6px rgba(46,230,107,0.35);}"
    ".row-closed td{color:#ff4d4d;text-shadow:0 0 6px rgba(255,77,77,0.25);}"
    ".board tr{border-bottom:1px solid #161b22;}"
    ".code-cell{font-weight:700;}"
    "</style>"
)
st.markdown(BOARD_CSS, unsafe_allow_html=True)

results = [(ex, get_status(ex, now_utc)) for ex in EXCHANGES]

# Zoradenie: otvorené burzy hore, potom podľa najbližšieho času do otvorenia
results.sort(key=lambda item: (not item[1]["is_open"], item[1]["delta"]))

row_parts = []
for ex, status in results:
    local_time_str = status["local_time"].strftime("%H:%M")
    row_class = "row-open" if status["is_open"] else "row-closed"

    if status["is_open"]:
        stav = f"● OTVORENÉ — {format_delta(status['delta']).upper()}"
    else:
        stav = f"● ZATVORENÉ — O {format_delta(status['delta']).upper()}"

    row_parts.append(
        f'<tr class="{row_class}">'
        f'<td class="code-cell">{ex["flag"]} {ex["code"]}</td>'
        f'<td>{local_time_str}</td>'
        f'<td>{stav}</td>'
        f'</tr>'
    )

table_html = (
    '<div class="board-wrap"><table class="board">'
    '<thead><tr><th>Burza</th><th>Miestny čas</th><th>Stav</th></tr></thead>'
    f'<tbody>{"".join(row_parts)}</tbody>'
    '</table></div>'
)

st.markdown(table_html, unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "⚠️ Poznámka: aplikácia nezohľadňuje štátne sviatky ani obedné prestávky niektorých ázijských búrz "
    "(napr. Tokio, Hongkong, Šanghaj). Časy otvorenia/zatvorenia sú orientačné podľa bežného obchodného kalendára."
)
