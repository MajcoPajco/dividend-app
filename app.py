from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests

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

EXCHANGES = [
    {"name": "New York Stock Exchange", "code": "NYSE", "city": "New York", "country": "USA",
     "tz": "America/New_York", "open": "09:30", "close": "16:00", "flag": "🇺🇸"},
    {"name": "NASDAQ", "code": "NASDAQ", "city": "New York", "country": "USA",
     "tz": "America/New_York", "open": "09:30", "close": "16:00", "flag": "🇺🇸"},
    {"name": "Toronto Stock Exchange", "code": "TSX", "city": "Toronto", "country": "Kanada",
     "tz": "America/Toronto", "open": "09:30", "close": "16:00", "flag": "🇨🇦"},
    {"name": "London Stock Exchange", "code": "LSE", "city": "Londýn", "country": "Spojené kráľovstvo",
     "tz": "Europe/London", "open": "08:00", "close": "16:30", "flag": "🇬🇧"},
    {"name": "Euronext Paris", "code": "EPA", "city": "Paríž", "country": "Francúzsko",
     "tz": "Europe/Paris", "open": "09:00", "close": "17:30", "flag": "🇫🇷"},
    {"name": "Deutsche Börse (Xetra)", "code": "FRA", "city": "Frankfurt", "country": "Nemecko",
     "tz": "Europe/Berlin", "open": "09:00", "close": "17:30", "flag": "🇩🇪"},
    {"name": "SIX Swiss Exchange", "code": "SIX", "city": "Zürich", "country": "Švajčiarsko",
     "tz": "Europe/Zurich", "open": "09:00", "close": "17:30", "flag": "🇨🇭"},
    {"name": "Tokyo Stock Exchange", "code": "TSE", "city": "Tokio", "country": "Japonsko",
     "tz": "Asia/Tokyo", "open": "09:00", "close": "15:00", "flag": "🇯🇵"},
    {"name": "Hong Kong Stock Exchange", "code": "HKEX", "city": "Hongkong", "country": "Čína",
     "tz": "Asia/Hong_Kong", "open": "09:30", "close": "16:00", "flag": "🇭🇰"},
    {"name": "Shanghai Stock Exchange", "code": "SSE", "city": "Šanghaj", "country": "Čína",
     "tz": "Asia/Shanghai", "open": "09:30", "close": "15:00", "flag": "🇨🇳"},
    {"name": "Bombay Stock Exchange", "code": "BSE", "city": "Bombaj", "country": "India",
     "tz": "Asia/Kolkata", "open": "09:15", "close": "15:30", "flag": "🇮🇳"},
    {"name": "Australian Securities Exchange", "code": "ASX", "city": "Sydney", "country": "Austrália",
     "tz": "Australia/Sydney", "open": "10:00", "close": "16:00", "flag": "🇦🇺"},
]

EXTRA_MARKETS_BY_CODE = {
    "OSL": {"name": "Oslo Børs", "code": "OSL", "city": "Oslo", "country": "Nórsko",
            "tz": "Europe/Oslo", "open": "09:00", "close": "16:25", "flag": "🇳🇴"},
    "STO": {"name": "Nasdaq Stockholm", "code": "STO", "city": "Štokholm", "country": "Švédsko",
            "tz": "Europe/Stockholm", "open": "09:00", "close": "17:25", "flag": "🇸🇪"},
    "HEL": {"name": "Nasdaq Helsinki", "code": "HEL", "city": "Helsinki", "country": "Fínsko",
            "tz": "Europe/Helsinki", "open": "10:00", "close": "18:30", "flag": "🇫🇮"},
    "CPH": {"name": "Nasdaq Copenhagen", "code": "CPH", "city": "Kodaň", "country": "Dánsko",
            "tz": "Europe/Copenhagen", "open": "09:00", "close": "17:00", "flag": "🇩🇰"},
    "MIL": {"name": "Borsa Italiana", "code": "MIL", "city": "Miláno", "country": "Taliansko",
            "tz": "Europe/Rome", "open": "09:00", "close": "17:30", "flag": "🇮🇹"},
    "MCE": {"name": "Bolsa de Madrid", "code": "MCE", "city": "Madrid", "country": "Španielsko",
            "tz": "Europe/Madrid", "open": "09:00", "close": "17:30", "flag": "🇪🇸"},
    "VIE": {"name": "Wiener Börse", "code": "VIE", "city": "Viedeň", "country": "Rakúsko",
            "tz": "Europe/Vienna", "open": "09:00", "close": "17:30", "flag": "🇦🇹"},
    "WSE": {"name": "Warsaw Stock Exchange", "code": "WSE", "city": "Varšava", "country": "Poľsko",
            "tz": "Europe/Warsaw", "open": "09:00", "close": "17:50", "flag": "🇵🇱"},
    "PRA": {"name": "Prague Stock Exchange", "code": "PRA", "city": "Praha", "country": "Česko",
            "tz": "Europe/Prague", "open": "09:00", "close": "16:20", "flag": "🇨🇿"},
    "AMS": {"name": "Euronext Amsterdam", "code": "AMS", "city": "Amsterdam", "country": "Holandsko",
            "tz": "Europe/Amsterdam", "open": "09:00", "close": "17:30", "flag": "🇳🇱"},
    "BRU": {"name": "Euronext Brussels", "code": "BRU", "city": "Brusel", "country": "Belgicko",
            "tz": "Europe/Brussels", "open": "09:00", "close": "17:30", "flag": "🇧🇪"},
    "LIS": {"name": "Euronext Lisbon", "code": "LIS", "city": "Lisabon", "country": "Portugalsko",
            "tz": "Europe/Lisbon", "open": "09:00", "close": "17:30", "flag": "🇵🇹"},
}

EXCHANGE_INFO = {
    "NMS": ("NASDAQ", "USA"), "NGM": ("NASDAQ", "USA"), "NCM": ("NASDAQ", "USA"),
    "NYQ": ("NYSE", "USA"), "ASE": ("NYSE American", "USA"), "PCX": ("NYSE Arca", "USA"),
    "BATS": ("Cboe BZX", "USA"), "PNK": ("OTC Pink", "USA"),
    "TOR": ("Toronto Stock Exchange", "Kanada"), "VAN": ("TSX Venture Exchange", "Kanada"),
    "LSE": ("London Stock Exchange", "Spojené kráľovstvo"),
    "IOB": ("London Stock Exchange (IOB)", "Spojené kráľovstvo"),
    "PAR": ("Euronext Paris", "Francúzsko"), "AMS": ("Euronext Amsterdam", "Holandsko"),
    "BRU": ("Euronext Brussels", "Belgicko"), "LIS": ("Euronext Lisbon", "Portugalsko"),
    "GER": ("Deutsche Börse (Xetra)", "Nemecko"), "FRA": ("Frankfurt Stock Exchange", "Nemecko"),
    "BER": ("Berlin Stock Exchange", "Nemecko"), "SWX": ("SIX Swiss Exchange", "Švajčiarsko"),
    "EBS": ("SIX Swiss Exchange", "Švajčiarsko"), "MIL": ("Borsa Italiana", "Taliansko"),
    "MCE": ("Bolsa de Madrid", "Španielsko"), "STO": ("Nasdaq Stockholm", "Švédsko"),
    "CPH": ("Nasdaq Copenhagen", "Dánsko"), "HEL": ("Nasdaq Helsinki", "Fínsko"),
    "OSL": ("Oslo Børs", "Nórsko"), "VIE": ("Wiener Börse", "Rakúsko"),
    "WSE": ("Warsaw Stock Exchange", "Poľsko"), "PRA": ("Prague Stock Exchange", "Česko"),
    "JPX": ("Tokyo Stock Exchange", "Japonsko"), "TYO": ("Tokyo Stock Exchange", "Japonsko"),
    "HKG": ("Hong Kong Stock Exchange", "Čína"), "SHH": ("Shanghai Stock Exchange", "Čína"),
    "SHZ": ("Shenzhen Stock Exchange", "Čína"),
    "NSI": ("National Stock Exchange of India", "India"),
    "BSE": ("Bombay Stock Exchange", "India"),
    "ASX": ("Australian Securities Exchange", "Austrália"),
    "SAO": ("B3 (Brazília)", "Brazília"), "MEX": ("Bolsa Mexicana de Valores", "Mexiko"),
    "JNB": ("Johannesburg Stock Exchange", "Južná Afrika"),
    "TLV": ("Tel Aviv Stock Exchange", "Izrael"), "SES": ("Singapore Exchange", "Singapur"),
    "KSC": ("Korea Exchange (KOSPI)", "Južná Kórea"),
    "KOE": ("Korea Exchange (KOSDAQ)", "Južná Kórea"),
}


def lookup_exchange(exchange_code: str | None, fallback_name: str | None = None) -> tuple[str, str]:
    if exchange_code and exchange_code in EXCHANGE_INFO:
        return EXCHANGE_INFO[exchange_code]
    return (fallback_name or exchange_code or "N/A", "N/A")


def format_qty(q: float) -> str:
    s = f"{q:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


HOLDINGS_FILE = Path(__file__).resolve().parent / "holdings_data.json"


def load_holdings() -> dict:
    if not HOLDINGS_FILE.exists():
        return {}
    try:
        with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def save_holdings(holdings: dict, exchanges: dict) -> None:
    data = {
        tkr: {"qty": qty, "exchange": exchanges.get(tkr, "")}
        for tkr, qty in holdings.items()
    }
    try:
        with open(HOLDINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_status(exchange: dict, now_utc: datetime) -> dict:
    tz = ZoneInfo(exchange["tz"])
    now_local = now_utc.astimezone(tz)
    open_h, open_m = map(int, exchange["open"].split(":"))
    close_h, close_m = map(int, exchange["close"].split(":"))
    today_open = now_local.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    today_close = now_local.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
    is_weekday = now_local.weekday() < 5
    is_open = is_weekday and today_open <= now_local < today_close
    if is_open:
        return {"is_open": True, "delta": now_local - today_open, "local_time": now_local}
    if is_weekday and now_local < today_open:
        candidate = today_open
    else:
        candidate = today_open + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return {"is_open": False, "delta": candidate - now_local, "local_time": now_local}


def format_delta(delta: timedelta) -> str:
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} h {minutes:02d} min"


@st.cache_data(ttl=1800, show_spinner=False)
def get_fx_to_usd_rate(currency: str | None) -> float | None:
    """
    Vráti kurz: 1 jednotka currency = X USD.
    Špeciálny prípad: GBp (britské pence) = GBP × 0.01
    Primárny zdroj: frankfurter.app (zadarmo, bez API kľúča)
    Záložný zdroj: Yahoo Finance FX ticker
    """
    if not currency:
        return None

    # GBp = britské pence (Yahoo Finance používa 'GBp'), 1 GBp = 0.01 GBP
    pence_factor = 1.0
    curr_norm = currency
    if currency == "GBp":
        curr_norm = "GBP"
        pence_factor = 0.01

    if curr_norm.upper() == "USD":
        return 1.0

    # --- Primárny zdroj: frankfurter.app ---
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": curr_norm.upper(), "to": "USD"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get("rates", {}).get("USD")
            if rate:
                return float(rate) * pence_factor
    except Exception:
        pass

    # --- Záložný zdroj: Yahoo Finance FX ticker ---
    try:
        t = yf.Ticker(f"{curr_norm.upper()}USD=X")
        info = t.info or {}
        rate = info.get("regularMarketPrice") or info.get("previousClose")
        if rate:
            return float(rate) * pence_factor
    except Exception:
        pass

    return None


def estimate_dividend_frequency(dividends) -> str:
    if dividends is None or len(dividends) < 2:
        return "N/A"
    recent = dividends.iloc[-8:]
    if len(recent) < 2:
        return "N/A"
    dates = list(recent.index)
    gaps_days = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    if not gaps_days:
        return "N/A"
    avg_gap = sum(gaps_days) / len(gaps_days)
    if avg_gap <= 45:
        return "Mesačne"
    elif avg_gap <= 135:
        return "Štvrťročne"
    elif avg_gap <= 250:
        return "Polročne"
    elif avg_gap <= 450:
        return "Ročne"
    else:
        return "Nepravidelne"


def _parse_stock_info(ticker: str, info: dict, dividends) -> dict | None:
    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    if price is None:
        return None
    name = info.get("shortName") or info.get("longName") or ticker
    currency = info.get("currency") or ""
    exchange_code = info.get("exchange") or ""
    exchange_name, country = lookup_exchange(exchange_code, info.get("fullExchangeName"))
    frequency = estimate_dividend_frequency(dividends)
    last_div_amount = None
    if dividends is not None and len(dividends) > 0:
        last_div_amount = float(dividends.iloc[-1])
    ex_div_date = None
    ex_div_ts = info.get("exDividendDate")
    if ex_div_ts:
        try:
            ex_div_date = datetime.fromtimestamp(ex_div_ts, tz=timezone.utc).date()
        except Exception:
            ex_div_date = None
    annual_rate = info.get("dividendRate")
    if annual_rate is None and last_div_amount is not None:
        annual_rate = last_div_amount * 4
    return {
        "ticker": ticker,
        "name": name,
        "currency": currency,
        "price": float(price),
        "exchange": exchange_name,
        "exchange_code": exchange_code,
        "country": country,
        "last_div_amount": last_div_amount,
        "ex_div_date": ex_div_date,
        "annual_rate": annual_rate,
        "frequency": frequency,
    }


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(ticker: str):
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        dividends = t.dividends
        return _parse_stock_info(ticker, info, dividends)
    except Exception:
        return None


# ── UI setup ──────────────────────────────────────────────────────────────────

st.markdown(
    "<style>.block-container{padding-top:1.2rem;} h3{margin-bottom:0.4rem;}</style>",
    unsafe_allow_html=True,
)
st.markdown("### 📊 Dividend tracker")

now_utc = datetime.now(ZoneInfo("UTC"))

BOARD_CSS = (
    "<style>"
    ".board-wrap{background:#ffffff;border-radius:10px;padding:0;border:1px solid #e3e6ea;overflow:hidden;}"
    ".board{width:100%;border-collapse:collapse;border-spacing:0;"
    "font-family:'Courier New',Consolas,monospace;}"
    ".board th{text-align:left;padding:8px 16px;font-size:11.5px;letter-spacing:0.1em;"
    "color:#8a93a1;text-transform:uppercase;border-bottom:1px solid #e3e6ea;background:#fafbfc;}"
    ".board td{padding:6px 16px;font-size:15px;letter-spacing:0.02em;white-space:nowrap;"
    "line-height:1.1;border-bottom:1px solid #f0f1f3;}"
    ".board tr:last-child td{border-bottom:none;}"
    ".row-open td{color:#15a24a;}"
    ".row-closed td{color:#e0362b;}"
    ".code-cell{font-weight:700;}"
    "</style>"
)
st.markdown(BOARD_CSS, unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "holdings" not in st.session_state:
    _loaded = load_holdings()
    st.session_state.holdings = {tkr: rec.get("qty", 0) for tkr, rec in _loaded.items()}
    st.session_state.holdings_exchange = {tkr: rec.get("exchange", "") for tkr, rec in _loaded.items()}

if "holdings_exchange" not in st.session_state:
    st.session_state.holdings_exchange = {}

# ── Načítanie dát akcií (pred akýmkoľvek vykreslením) ────────────────────────

stock_records: dict = {}
for _tkr in list(st.session_state.holdings):
    _rec = fetch_stock_data(_tkr)
    if _rec is not None:
        stock_records[_tkr] = _rec
        st.session_state.holdings_exchange[_tkr] = _rec["exchange"]

# ============================================================
# SEKCIA 1 — PREHĽAD BÚRZ (najvyššie)
# ============================================================

existing_cities = {ex["city"] for ex in EXCHANGES}
owned_codes = {rec.get("exchange_code") for rec in stock_records.values() if rec.get("exchange_code")}
extras: list = []
for _code in owned_codes:
    _ex_info = EXTRA_MARKETS_BY_CODE.get(_code)
    if not _ex_info or _ex_info["city"] in existing_cities:
        continue
    extras.append(_ex_info)
    existing_cities.add(_ex_info["city"])

exchanges_display = EXCHANGES + extras
results = [(ex, get_status(ex, now_utc)) for ex in exchanges_display]
results.sort(key=lambda item: (not item[1]["is_open"], item[1]["delta"]))

row_parts = []
for ex, status in results:
    local_time_str = status["local_time"].strftime("%H:%M")
    row_class = "row-open" if status["is_open"] else "row-closed"
    stav = (
        f"● OTVORENÉ — {format_delta(status['delta']).upper()}"
        if status["is_open"]
        else f"● ZATVORENÉ — O {format_delta(status['delta']).upper()}"
    )
    row_parts.append(
        f'<tr class="{row_class}">'
        f'<td class="code-cell">{ex["flag"]} {ex["code"]}</td>'
        f'<td>{ex["city"]}</td><td>{ex["country"]}</td>'
        f'<td>{local_time_str}</td><td>{stav}</td>'
        f'</tr>'
    )

st.markdown(
    '<div class="board-wrap"><table class="board">'
    '<thead><tr><th>Burza</th><th>Mesto</th><th>Štát</th>'
    '<th>Miestny čas</th><th>Stav</th></tr></thead>'
    f'<tbody>{"".join(row_parts)}</tbody></table></div>',
    unsafe_allow_html=True,
)

# ============================================================
# SEKCIA 2 — PRIDAŤ AKCIU
# ============================================================

st.markdown("#### ➕ Pridať akciu")

with st.form(key="add_stock_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        ticker_in = st.text_input("Ticker", placeholder="napr. AAPL", label_visibility="collapsed")
    with c2:
        qty_in = st.number_input(
            "Množstvo", step=0.0001, value=None, format="%.4f",
            placeholder="Množstvo", label_visibility="collapsed",
        )
    with c3:
        submitted = st.form_submit_button("Pridať", use_container_width=True)

st.caption("💡 Kladné množstvo = nákup (pridanie). Záporné množstvo = predaj (odpočet z portfólia).")

if submitted:
    ticker_clean = ticker_in.strip().upper()
    if not ticker_clean:
        st.warning("Zadaj ticker akcie.")
    elif qty_in is None or qty_in == 0:
        st.warning("Zadaj množstvo rôzne od 0.")
    elif qty_in > 0:
        new_data = fetch_stock_data(ticker_clean)
        if new_data is None:
            st.error(f"Ticker „{ticker_clean}" sa nepodarilo nájsť.")
        else:
            st.session_state.holdings[ticker_clean] = (
                st.session_state.holdings.get(ticker_clean, 0) + qty_in
            )
            st.session_state.holdings_exchange[ticker_clean] = new_data.get("exchange", "")
            save_holdings(st.session_state.holdings, st.session_state.holdings_exchange)
            st.success(f"Pridané: {format_qty(qty_in)} ks {ticker_clean} ({new_data['name']})")
    else:
        current_qty = st.session_state.holdings.get(ticker_clean, 0)
        if current_qty <= 0:
            st.info(f"Akcia „{ticker_clean}" nie je momentálne vlastnená, nie je čo odobrať.")
        else:
            remove_qty = abs(qty_in)
            new_qty = current_qty - remove_qty
            if new_qty <= 0:
                del st.session_state.holdings[ticker_clean]
                st.session_state.holdings_exchange.pop(ticker_clean, None)
                extra_note = (
                    " (odobraté bolo viac, než si vlastnil, pozícia bola vynulovaná)"
                    if remove_qty > current_qty else ""
                )
                st.success(f"Odobraté všetkých {format_qty(current_qty)} ks {ticker_clean}.{extra_note}")
            else:
                st.session_state.holdings[ticker_clean] = new_qty
                st.success(
                    f"Odobraté {format_qty(remove_qty)} ks {ticker_clean}. "
                    f"Nový stav: {format_qty(new_qty)} ks."
                )
            save_holdings(st.session_state.holdings, st.session_state.holdings_exchange)

# ============================================================
# SEKCIA 3 — MOJE AKCIE
# ============================================================

st.markdown("#### 💼 Moje akcie")

if not st.session_state.holdings:
    st.info("Zatiaľ nemáš pridané žiadne akcie. Pridaj prvú vyššie.")
else:
    holdings_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None:
            price_str, name = "N/A", tkr
            exchange_str = st.session_state.holdings_exchange.get(tkr) or "N/A"
            country_str, div_rocne_str = "N/A", "N/A"
        else:
            price_str = f"{rec['price']:.2f} {rec['currency']}".strip()
            name, exchange_str, country_str = rec["name"], rec["exchange"], rec["country"]
            pct_annual = None
            if rec.get("annual_rate") is not None and rec.get("price"):
                pct_annual = (rec["annual_rate"] / rec["price"]) * 100
            div_rocne_str = f"{pct_annual:.2f} %" if pct_annual is not None else "N/A"

        holdings_rows.append({
            "Ticker": tkr, "Meno firmy": name, "Burza": exchange_str,
            "Štát": country_str, "Aktuálna cena": price_str,
            "Div.Rocne[%]": div_rocne_str, "Množstvo": format_qty(qty),
        })

    holdings_df = pd.DataFrame(holdings_rows)
    edited_df = st.data_editor(
        holdings_df,
        column_config={
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Meno firmy": st.column_config.TextColumn(disabled=True),
            "Burza": st.column_config.TextColumn(disabled=True),
            "Štát": st.column_config.TextColumn(disabled=True),
            "Aktuálna cena": st.column_config.TextColumn(disabled=True),
            "Div.Rocne[%]": st.column_config.TextColumn(disabled=True),
            "Množstvo": st.column_config.TextColumn(
                help="Zadaj množstvo. Desatinnú čiarku môžeš použiť bodkou alebo čiarkou."
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="holdings_editor",
    )

    for _, row in edited_df.iterrows():
        raw = str(row["Množstvo"]).replace(",", ".").strip()
        try:
            new_qty = float(raw)
        except Exception:
            new_qty = float(st.session_state.holdings.get(row["Ticker"], 0))
        st.session_state.holdings[row["Ticker"]] = max(0.0, new_qty)

    save_holdings(st.session_state.holdings, st.session_state.holdings_exchange)

# ============================================================
# SEKCIA 4 — NAJBLIŽŠIE EX-DIV DÁTUMY
# ============================================================

st.markdown("#### 📅 Najbližšie Ex-Div dátumy")

if not st.session_state.holdings:
    st.info("Pridaj akcie vyššie, aby sa tu zobrazil prehľad dividend.")
else:
    today = datetime.now(timezone.utc).date()
    div_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None or rec["ex_div_date"] is None:
            continue
        if rec["ex_div_date"] < today:
            continue
        price = rec["price"]
        last_div = rec["last_div_amount"]
        annual_rate = rec["annual_rate"]
        currency = rec["currency"]
        pct_last = (last_div / price * 100) if (last_div is not None and price) else None
        pct_annual = (annual_rate / price * 100) if (annual_rate is not None and price) else None
        expected = (last_div * qty) if last_div is not None else None
        div_rows.append({
            "ticker": tkr, "name": rec["name"], "qty": qty,
            "ex_date": rec["ex_div_date"], "frequency": rec["frequency"],
            "last_div": last_div, "pct_last": pct_last,
            "pct_annual": pct_annual, "expected": expected, "currency": currency,
        })

    if not div_rows:
        st.info("Žiadna z pridaných akcií nemá aktuálne oficiálne oznámený budúci Ex-Div dátum.")
    else:
        div_rows.sort(key=lambda r: r["ex_date"])
        div_row_parts = []
        for r in div_rows:
            last_div_str = (
                f"{r['last_div']:.4f} {r['currency']}".strip()
                if r["last_div"] is not None else "N/A"
            )
            pct_last_str = f"{r['pct_last']:.2f} %" if r["pct_last"] is not None else "N/A"
            pct_annual_str = f"{r['pct_annual']:.2f} %" if r["pct_annual"] is not None else "N/A"

            expected_str = "N/A"
            if r["expected"] is not None:
                curr = r["currency"]
                expected_str = f"{r['expected']:.2f} {curr}".strip()
                # Prepočet na USD pre všetky meny okrem USD (vrátane GBp)
                if curr and curr.upper() != "USD":
                    rate = get_fx_to_usd_rate(curr)
                    if rate is not None:
                        usd_amount = r["expected"] * rate
                        expected_str += f" (≈ USD {usd_amount:.2f})"

            div_row_parts.append(
                '<tr>'
                f'<td class="code-cell">{r["ticker"]}</td>'
                f'<td>{r["name"]}</td>'
                f'<td>{format_qty(r["qty"])} ks</td>'
                f'<td>{r["ex_date"].strftime("%d/%m/%y")}</td>'
                f'<td>{r["frequency"]}</td>'
                f'<td>{last_div_str}</td>'
                f'<td>{pct_last_str}</td>'
                f'<td>{pct_annual_str}</td>'
                f'<td>{expected_str}</td>'
                '</tr>'
            )

        st.markdown(
            '<div class="board-wrap"><table class="board"><thead><tr>'
            '<th>Ticker</th><th>Meno</th><th>Množstvo</th><th>Ex-Div Date</th>'
            '<th>Frekvencia</th><th>Dividenda/akcia</th>'
            '<th>% k cene</th><th>% ročne</th><th>Očak. výnos</th>'
            f'</tr></thead><tbody>{"".join(div_row_parts)}</tbody></table></div>',
            unsafe_allow_html=True,
        )
