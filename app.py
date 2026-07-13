from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone
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

# Zoznam najznámejších búrz: názov, kód, mesto, štát, časové pásmo, čas otvorenia/zatvorenia (miestny čas burzy)
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

# Mapovanie burzového kódu (tak, ako ho vracia Yahoo Finance / yfinance v poli "exchange")
# na čitateľný názov burzy a štát, v ktorom burza sídli. Pokrýva najbežnejšie burzy;
# ak kód nie je v mape, použije sa "fullExchangeName" z Yahoo Finance ako názov a "N/A" ako štát.
EXCHANGE_INFO = {
    "NMS": ("NASDAQ", "USA"),
    "NGM": ("NASDAQ", "USA"),
    "NCM": ("NASDAQ", "USA"),
    "NYQ": ("NYSE", "USA"),
    "ASE": ("NYSE American", "USA"),
    "PCX": ("NYSE Arca", "USA"),
    "BATS": ("Cboe BZX", "USA"),
    "PNK": ("OTC Pink", "USA"),
    "TOR": ("Toronto Stock Exchange", "Kanada"),
    "VAN": ("TSX Venture Exchange", "Kanada"),
    "LSE": ("London Stock Exchange", "Spojené kráľovstvo"),
    "IOB": ("London Stock Exchange (IOB)", "Spojené kráľovstvo"),
    "PAR": ("Euronext Paris", "Francúzsko"),
    "AMS": ("Euronext Amsterdam", "Holandsko"),
    "BRU": ("Euronext Brussels", "Belgicko"),
    "LIS": ("Euronext Lisbon", "Portugalsko"),
    "GER": ("Deutsche Börse (Xetra)", "Nemecko"),
    "FRA": ("Frankfurt Stock Exchange", "Nemecko"),
    "BER": ("Berlin Stock Exchange", "Nemecko"),
    "SWX": ("SIX Swiss Exchange", "Švajčiarsko"),
    "EBS": ("SIX Swiss Exchange", "Švajčiarsko"),
    "MIL": ("Borsa Italiana", "Taliansko"),
    "MCE": ("Bolsa de Madrid", "Španielsko"),
    "STO": ("Nasdaq Stockholm", "Švédsko"),
    "CPH": ("Nasdaq Copenhagen", "Dánsko"),
    "HEL": ("Nasdaq Helsinki", "Fínsko"),
    "OSL": ("Oslo Børs", "Nórsko"),
    "VIE": ("Wiener Börse", "Rakúsko"),
    "WSE": ("Warsaw Stock Exchange", "Poľsko"),
    "PRA": ("Prague Stock Exchange", "Česko"),
    "JPX": ("Tokyo Stock Exchange", "Japonsko"),
    "TYO": ("Tokyo Stock Exchange", "Japonsko"),
    "HKG": ("Hong Kong Stock Exchange", "Čína"),
    "SHH": ("Shanghai Stock Exchange", "Čína"),
    "SHZ": ("Shenzhen Stock Exchange", "Čína"),
    "NSI": ("National Stock Exchange of India", "India"),
    "BSE": ("Bombay Stock Exchange", "India"),
    "ASX": ("Australian Securities Exchange", "Austrália"),
    "SAO": ("B3 (Brazília)", "Brazília"),
    "MEX": ("Bolsa Mexicana de Valores", "Mexiko"),
    "JNB": ("Johannesburg Stock Exchange", "Južná Afrika"),
    "TLV": ("Tel Aviv Stock Exchange", "Izrael"),
    "SES": ("Singapore Exchange", "Singapur"),
    "KSC": ("Korea Exchange (KOSPI)", "Južná Kórea"),
    "KOE": ("Korea Exchange (KOSDAQ)", "Južná Kórea"),
}


def lookup_exchange(exchange_code: str | None, fallback_name: str | None = None) -> tuple[str, str]:
    """Vráti (názov burzy, štát) na základe burzového kódu z Yahoo Finance.

    Ak kód nepoznáme, použije sa fallback_name (napr. "fullExchangeName" z yfinance)
    ako názov burzy a štát sa označí ako "N/A".
    """
    if exchange_code and exchange_code in EXCHANGE_INFO:
        return EXCHANGE_INFO[exchange_code]
    return (fallback_name or exchange_code or "N/A", "N/A")


def format_qty(q: float) -> str:
    """Zobrazí množstvo bez zbytočných nulových desatinných miest (max. 4)."""
    s = f"{q:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


# --------------------------- Perzistencia portfólia ---------------------------
# Držané akcie sa ukladajú do JSON súboru vedľa app.py, aby sa pri ďalšom
# spustení aplikácie nemuseli zadávať znova. Ukladá sa Ticker, Burza a Množstvo;
# ostatné údaje (cena, meno, dividendy...) sa vždy nanovo stiahnu z internetu.
HOLDINGS_FILE = Path(__file__).resolve().parent / "holdings_data.json"


def load_holdings() -> dict:
    """Načíta uložené portfólio zo súboru (ak existuje).

    Vráti slovník v tvare {ticker: {"qty": float, "exchange": str}}.
    Pri akomkoľvek probléme (chýbajúci/poškodený súbor) vráti prázdny slovník.
    """
    if not HOLDINGS_FILE.exists():
        return {}
    try:
        with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def save_holdings(holdings: dict, exchanges: dict) -> None:
    """Uloží aktuálne portfólio (ticker, burza, množstvo) do súboru na disku."""
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

# Zmenšenie horného odsadenia stránky, aby bola tabuľka čo najvyššie
st.markdown(
    "<style>.block-container{padding-top:1.2rem;} h3{margin-bottom:0.4rem;}</style>",
    unsafe_allow_html=True,
)

st.markdown("### 📊 Dividend tracker")

now_utc = datetime.now(ZoneInfo("UTC"))

# POZNÁMKA: Streamlit Markdown si riadky odsadené 4+ medzerami môže pomýliť
# s blokom kódu a HTML potom zobrazí ako čistý text. Preto sa celé HTML
# skladá bez odsadenia (na jeden "riadok" na tag), nikdy ako viacriadkový
# odsadený reťazec.
BOARD_CSS = (
    "<style>"
    ".board-wrap{background:#ffffff;border-radius:10px;padding:0;border:1px solid #e3e6ea;"
    "overflow:hidden;}"
    ".board{width:100%;border-collapse:collapse;border-spacing:0;"
    "font-family:'Courier New',Consolas,monospace;}"
    ".board th{text-align:left;padding:8px 16px;font-size:11.5px;letter-spacing:0.1em;"
    "color:#8a93a1;text-transform:uppercase;border-bottom:1px solid #e3e6ea;"
    "background:#fafbfc;}"
    ".board td{padding:6px 16px;font-size:15px;letter-spacing:0.02em;white-space:nowrap;"
    "line-height:1.1;border-bottom:1px solid #f0f1f3;}"
    ".board tr:last-child td{border-bottom:none;}"
    ".row-open td{color:#15a24a;}"
    ".row-closed td{color:#e0362b;}"
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
        f'<td>{ex["city"]}</td>'
        f'<td>{ex["country"]}</td>'
        f'<td>{local_time_str}</td>'
        f'<td>{stav}</td>'
        f'</tr>'
    )

table_html = (
    '<div class="board-wrap"><table class="board">'
    '<thead><tr><th>Burza</th><th>Mesto</th><th>Štát</th><th>Miestny čas</th><th>Stav</th></tr></thead>'
    f'<tbody>{"".join(row_parts)}</tbody>'
    '</table></div>'
)

st.markdown(table_html, unsafe_allow_html=True)


# ============================================================
# DIVIDEND TRACKER
# ============================================================

if "holdings" not in st.session_state:
    _loaded = load_holdings()
    st.session_state.holdings = {tkr: rec.get("qty", 0) for tkr, rec in _loaded.items()}
    st.session_state.holdings_exchange = {tkr: rec.get("exchange", "") for tkr, rec in _loaded.items()}

if "holdings_exchange" not in st.session_state:
    st.session_state.holdings_exchange = {}


def estimate_dividend_frequency(dividends) -> str:
    """Odhadne frekvenciu vyplácania dividend na základe priemerného odstupu
    medzi poslednými výplatami (max. posledných 8 záznamov z histórie)."""
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
    """Čistá (bez siete) funkcia, ktorá spracuje surové dáta z yfinance do prehľadného záznamu."""
    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    if price is None:
        return None

    name = info.get("shortName") or info.get("longName") or ticker
    currency = info.get("currency") or ""

    exchange_code = info.get("exchange") or ""
    exchange_name, country = lookup_exchange(exchange_code, info.get("fullExchangeName"))

    frequency = estimate_dividend_frequency(dividends)

    last_div_amount = None
    last_div_date = None
    if dividends is not None and len(dividends) > 0:
        last_div_amount = float(dividends.iloc[-1])
        last_div_date = dividends.index[-1].date()

    ex_div_date = None
    ex_div_ts = info.get("exDividendDate")
    if ex_div_ts:
        try:
            ex_div_date = datetime.fromtimestamp(ex_div_ts, tz=timezone.utc).date()
        except Exception:
            ex_div_date = None
    # POZOR: zámerne sa tu nerobí fallback na posledný historický dátum dividendy.
    # Sekcia 3 má zobrazovať iba oficiálne oznámený (Yahoo Finance) Ex-Div dátum.

    annual_rate = info.get("dividendRate")
    if annual_rate is None and last_div_amount is not None:
        # Odhad pri chýbajúcom údaji - predpoklad štvrťročnej výplaty
        annual_rate = last_div_amount * 4

    return {
        "ticker": ticker,
        "name": name,
        "currency": currency,
        "price": float(price),
        "exchange": exchange_name,
        "country": country,
        "last_div_amount": last_div_amount,
        "ex_div_date": ex_div_date,
        "annual_rate": annual_rate,
        "frequency": frequency,
    }


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_data(ticker: str):
    """Stiahne údaje o akcii (cena, meno, dividendy) cez yfinance. Vráti None pri chybe/neplatnom tickeri."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        dividends = t.dividends
        return _parse_stock_info(ticker, info, dividends)
    except Exception:
        return None


# --------- Sekcia 1: Pridanie akcie ---------
st.markdown("#### ➕ Pridať akciu")

with st.form(key="add_stock_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        ticker_in = st.text_input(
            "Ticker", placeholder="napr. AAPL", label_visibility="collapsed"
        )
    with c2:
        qty_in = st.number_input(
            "Množstvo",
            step=0.0001,
            value=None,
            format="%.4f",
            placeholder="Množstvo",
            label_visibility="collapsed",
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
            st.error(f"Ticker „{ticker_clean}“ sa nepodarilo nájsť.")
        else:
            st.session_state.holdings[ticker_clean] = (
                st.session_state.holdings.get(ticker_clean, 0) + qty_in
            )
            st.session_state.holdings_exchange[ticker_clean] = new_data.get("exchange", "")
            save_holdings(st.session_state.holdings, st.session_state.holdings_exchange)
            st.success(f"Pridané: {format_qty(qty_in)} ks {ticker_clean} ({new_data['name']})")
    else:
        # qty_in < 0 -> pokus o odobratie akcií z portfólia
        current_qty = st.session_state.holdings.get(ticker_clean, 0)
        if current_qty <= 0:
            st.info(f"Akcia „{ticker_clean}“ nie je momentálne vlastnená, nie je čo odobrať.")
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

# Načítanie dát pre všetky držané akcie (zdieľané pre sekciu 2 aj 3)
stock_records = {}
for _tkr in st.session_state.holdings:
    _rec = fetch_stock_data(_tkr)
    if _rec is not None:
        stock_records[_tkr] = _rec
        st.session_state.holdings_exchange[_tkr] = _rec["exchange"]


# --------- Sekcia 2: Moje akcie (editovateľná tabuľka) ---------
st.markdown("#### 💼 Moje akcie")

if not st.session_state.holdings:
    st.info("Zatiaľ nemáš pridané žiadne akcie. Pridaj prvú vyššie.")
else:
    holdings_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None:
            price_str = "N/A"
            name = tkr
            exchange_str = st.session_state.holdings_exchange.get(tkr) or "N/A"
            country_str = "N/A"
        else:
            price_str = f"{rec['price']:.2f} {rec['currency']}".strip()
            name = rec["name"]
            exchange_str = rec["exchange"]
            country_str = rec["country"]
        holdings_rows.append(
            {
                "Ticker": tkr,
                "Meno firmy": name,
                "Burza": exchange_str,
                "Štát": country_str,
                "Aktuálna cena": price_str,
                "Množstvo": qty,
            }
        )

    holdings_df = pd.DataFrame(holdings_rows)

    edited_df = st.data_editor(
        holdings_df,
        column_config={
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Meno firmy": st.column_config.TextColumn(disabled=True),
            "Burza": st.column_config.TextColumn(disabled=True),
            "Štát": st.column_config.TextColumn(disabled=True),
            "Aktuálna cena": st.column_config.TextColumn(disabled=True),
            "Množstvo": st.column_config.NumberColumn(
                min_value=0.0, step=0.0001, format="%.4f"
            ),
        },
        hide_index=True,
        use_container_width=True,
        key="holdings_editor",
    )

    for _, row in edited_df.iterrows():
        st.session_state.holdings[row["Ticker"]] = float(row["Množstvo"])

    save_holdings(st.session_state.holdings, st.session_state.holdings_exchange)


# --------- Sekcia 3: Najbližšie Ex-Div dátumy ---------
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
        # Zobrazujeme len akcie s oficiálne oznámeným Ex-Div dátumom, ktorý je dnes alebo v budúcnosti.
        if rec["ex_div_date"] < today:
            continue

        price = rec["price"]
        last_div = rec["last_div_amount"]
        annual_rate = rec["annual_rate"]
        currency = rec["currency"]

        pct_last = (last_div / price * 100) if (last_div is not None and price) else None
        pct_annual = (annual_rate / price * 100) if (annual_rate is not None and price) else None
        expected = (last_div * qty) if last_div is not None else None

        div_rows.append(
            {
                "ticker": tkr,
                "name": rec["name"],
                "qty": qty,
                "ex_date": rec["ex_div_date"],
                "frequency": rec["frequency"],
                "last_div": last_div,
                "pct_last": pct_last,
                "pct_annual": pct_annual,
                "expected": expected,
                "currency": currency,
            }
        )

    if not div_rows:
        st.info("Žiadna z pridaných akcií nemá aktuálne oficiálne oznámený budúci Ex-Div dátum.")
    else:
        div_rows.sort(key=lambda r: r["ex_date"])

        div_row_parts = []
        for r in div_rows:
            last_div_str = (
                f"{r['last_div']:.2f} {r['currency']}".strip()
                if r["last_div"] is not None else "N/A"
            )
            pct_last_str = f"{r['pct_last']:.2f} %" if r["pct_last"] is not None else "N/A"
            pct_annual_str = f"{r['pct_annual']:.2f} %" if r["pct_annual"] is not None else "N/A"
            expected_str = (
                f"{r['expected']:.2f} {r['currency']}".strip()
                if r["expected"] is not None else "N/A"
            )
            date_str = r["ex_date"].strftime("%d/%m/%y")

            div_row_parts.append(
                '<tr>'
                f'<td class="code-cell">{r["ticker"]}</td>'
                f'<td>{r["name"]}</td>'
                f'<td>{format_qty(r["qty"])} ks</td>'
                f'<td>{date_str}</td>'
                f'<td>{r["frequency"]}</td>'
                f'<td>{last_div_str}</td>'
                f'<td>{pct_last_str}</td>'
                f'<td>{pct_annual_str}</td>'
                f'<td>{expected_str}</td>'
                '</tr>'
            )

        div_table_html = (
            '<div class="board-wrap"><table class="board">'
            '<thead><tr>'
            '<th>Ticker</th><th>Meno</th><th>Množstvo</th><th>Ex-Div Date</th><th>Frekvencia</th>'
            '<th>Dividenda/akcia</th><th>% k cene</th><th>% ročne</th><th>Očak. výnos</th>'
            '</tr></thead>'
            f'<tbody>{"".join(div_row_parts)}</tbody>'
            '</table></div>'
        )

        st.markdown(div_table_html, unsafe_allow_html=True)
