import json
import time
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
import yfinance as yf
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests

try:
    import gspread
    from google.oauth2.service_account import Credentials as _GoogleCredentials
except Exception:
    gspread = None
    _GoogleCredentials = None

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=600_000, limit=None, key="autorefresh")
except Exception:
    pass

st.set_page_config(
    page_title="Svetove burzy - otvaracie hodiny",
    page_icon="📈",
    layout="wide",
)

BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

EXCHANGES = [
    {"name": "New York Stock Exchange", "code": "NYSE",
     "city": "New York", "country": "USA",
     "tz": "America/New_York", "open": "09:30", "close": "16:00",
     "flag": "🇺🇸"},
    {"name": "NASDAQ", "code": "NASDAQ",
     "city": "New York", "country": "USA",
     "tz": "America/New_York", "open": "09:30", "close": "16:00",
     "flag": "🇺🇸"},
    {"name": "Toronto Stock Exchange", "code": "TSX",
     "city": "Toronto", "country": "Kanada",
     "tz": "America/Toronto", "open": "09:30", "close": "16:00",
     "flag": "🇨🇦"},
    {"name": "London Stock Exchange", "code": "LSE",
     "city": "Londyn", "country": "Spojene kralovstvo",
     "tz": "Europe/London", "open": "08:00", "close": "16:30",
     "flag": "🇬🇧"},
    {"name": "Euronext Paris", "code": "EPA",
     "city": "Pariz", "country": "Francuzsko",
     "tz": "Europe/Paris", "open": "09:00", "close": "17:30",
     "flag": "🇫🇷"},
    {"name": "Deutsche Boerse (Xetra)", "code": "FRA",
     "city": "Frankfurt", "country": "Nemecko",
     "tz": "Europe/Berlin", "open": "09:00", "close": "17:30",
     "flag": "🇩🇪"},
    {"name": "SIX Swiss Exchange", "code": "SIX",
     "city": "Zurich", "country": "Svajciarsko",
     "tz": "Europe/Zurich", "open": "09:00", "close": "17:30",
     "flag": "🇨🇭"},
    {"name": "Tokyo Stock Exchange", "code": "TSE",
     "city": "Tokio", "country": "Japonsko",
     "tz": "Asia/Tokyo", "open": "09:00", "close": "15:00",
     "flag": "🇯🇵"},
    {"name": "Hong Kong Stock Exchange", "code": "HKEX",
     "city": "Hongkong", "country": "Cina",
     "tz": "Asia/Hong_Kong", "open": "09:30", "close": "16:00",
     "flag": "🇭🇰"},
    {"name": "Shanghai Stock Exchange", "code": "SSE",
     "city": "Sanghaj", "country": "Cina",
     "tz": "Asia/Shanghai", "open": "09:30", "close": "15:00",
     "flag": "🇨🇳"},
    {"name": "Bombay Stock Exchange", "code": "BSE",
     "city": "Bombaj", "country": "India",
     "tz": "Asia/Kolkata", "open": "09:15", "close": "15:30",
     "flag": "🇮🇳"},
    {"name": "Australian Securities Exchange", "code": "ASX",
     "city": "Sydney", "country": "Australia",
     "tz": "Australia/Sydney", "open": "10:00", "close": "16:00",
     "flag": "🇦🇺"},
]

EXTRA_MARKETS_BY_CODE = {
    "OSL": {"name": "Oslo Bors", "code": "OSL",
            "city": "Oslo", "country": "Norsko",
            "tz": "Europe/Oslo", "open": "09:00", "close": "16:25",
            "flag": "🇳🇴"},
    "STO": {"name": "Nasdaq Stockholm", "code": "STO",
            "city": "Stokholm", "country": "Svedsko",
            "tz": "Europe/Stockholm", "open": "09:00", "close": "17:25",
            "flag": "🇸🇪"},
    "HEL": {"name": "Nasdaq Helsinki", "code": "HEL",
            "city": "Helsinki", "country": "Finsko",
            "tz": "Europe/Helsinki", "open": "10:00", "close": "18:30",
            "flag": "🇫🇮"},
    "CPH": {"name": "Nasdaq Copenhagen", "code": "CPH",
            "city": "Kodan", "country": "Dansko",
            "tz": "Europe/Copenhagen", "open": "09:00", "close": "17:00",
            "flag": "🇩🇰"},
    "MIL": {"name": "Borsa Italiana", "code": "MIL",
            "city": "Milano", "country": "Taliansko",
            "tz": "Europe/Rome", "open": "09:00", "close": "17:30",
            "flag": "🇮🇹"},
    "MCE": {"name": "Bolsa de Madrid", "code": "MCE",
            "city": "Madrid", "country": "Spanielsko",
            "tz": "Europe/Madrid", "open": "09:00", "close": "17:30",
            "flag": "🇪🇸"},
    "VIE": {"name": "Wiener Boerse", "code": "VIE",
            "city": "Vieden", "country": "Rakusko",
            "tz": "Europe/Vienna", "open": "09:00", "close": "17:30",
            "flag": "🇦🇹"},
    "WSE": {"name": "Warsaw Stock Exchange", "code": "WSE",
            "city": "Varsava", "country": "Polsko",
            "tz": "Europe/Warsaw", "open": "09:00", "close": "17:50",
            "flag": "🇵🇱"},
    "PRA": {"name": "Prague Stock Exchange", "code": "PRA",
            "city": "Praha", "country": "Cesko",
            "tz": "Europe/Prague", "open": "09:00", "close": "16:20",
            "flag": "🇨🇿"},
    "AMS": {"name": "Euronext Amsterdam", "code": "AMS",
            "city": "Amsterdam", "country": "Holandsko",
            "tz": "Europe/Amsterdam", "open": "09:00", "close": "17:30",
            "flag": "🇳🇱"},
    "BRU": {"name": "Euronext Brussels", "code": "BRU",
            "city": "Brusel", "country": "Belgicko",
            "tz": "Europe/Brussels", "open": "09:00", "close": "17:30",
            "flag": "🇧🇪"},
    "LIS": {"name": "Euronext Lisbon", "code": "LIS",
            "city": "Lisabon", "country": "Portugalsko",
            "tz": "Europe/Lisbon", "open": "09:00", "close": "17:30",
            "flag": "🇵🇹"},
}

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
    "LSE": ("London Stock Exchange", "Spojene kralovstvo"),
    "IOB": ("London Stock Exchange (IOB)", "Spojene kralovstvo"),
    "PAR": ("Euronext Paris", "Francuzsko"),
    "AMS": ("Euronext Amsterdam", "Holandsko"),
    "BRU": ("Euronext Brussels", "Belgicko"),
    "LIS": ("Euronext Lisbon", "Portugalsko"),
    "GER": ("Deutsche Boerse (Xetra)", "Nemecko"),
    "FRA": ("Frankfurt Stock Exchange", "Nemecko"),
    "BER": ("Berlin Stock Exchange", "Nemecko"),
    "SWX": ("SIX Swiss Exchange", "Svajciarsko"),
    "EBS": ("SIX Swiss Exchange", "Svajciarsko"),
    "MIL": ("Borsa Italiana", "Taliansko"),
    "MCE": ("Bolsa de Madrid", "Spanielsko"),
    "STO": ("Nasdaq Stockholm", "Svedsko"),
    "CPH": ("Nasdaq Copenhagen", "Dansko"),
    "HEL": ("Nasdaq Helsinki", "Finsko"),
    "OSL": ("Oslo Bors", "Norsko"),
    "VIE": ("Wiener Boerse", "Rakusko"),
    "WSE": ("Warsaw Stock Exchange", "Polsko"),
    "PRA": ("Prague Stock Exchange", "Cesko"),
    "JPX": ("Tokyo Stock Exchange", "Japonsko"),
    "TYO": ("Tokyo Stock Exchange", "Japonsko"),
    "HKG": ("Hong Kong Stock Exchange", "Cina"),
    "SHH": ("Shanghai Stock Exchange", "Cina"),
    "SHZ": ("Shenzhen Stock Exchange", "Cina"),
    "NSI": ("National Stock Exchange of India", "India"),
    "BSE": ("Bombay Stock Exchange", "India"),
    "ASX": ("Australian Securities Exchange", "Australia"),
    "SAO": ("B3 (Brazilia)", "Brazilia"),
    "MEX": ("Bolsa Mexicana de Valores", "Mexiko"),
    "JNB": ("Johannesburg Stock Exchange", "Juzna Afrika"),
    "TLV": ("Tel Aviv Stock Exchange", "Izrael"),
    "SES": ("Singapore Exchange", "Singapur"),
    "KSC": ("Korea Exchange (KOSPI)", "Juzna Korea"),
    "KOE": ("Korea Exchange (KOSDAQ)", "Juzna Korea"),
}


def lookup_exchange(exchange_code, fallback_name=None):
    if exchange_code and exchange_code in EXCHANGE_INFO:
        return EXCHANGE_INFO[exchange_code]
    return (fallback_name or exchange_code or "N/A", "N/A")


# ── Formatovacie helper funkcie (SK locale – desatinna ciarka) ────────────────

def parse_qty_input(text):
    """
    Bezpecne sparsuje mnozstvo.
    Akceptuje '1,5' aj '1.5' – obe davaju float 1.5.
    Vracia float alebo None pre prazdny/neplatny vstup.
    """
    if text is None:
        return None
    s = str(text).strip().replace("\xa0", "").replace(" ", "")
    s = s.replace(",", ".")   # SK desatinna ciarka -> bodka
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt_num(val, decimals=2):
    """Cislo so SK desatinnou ciarkou. Pre None/NaN vrati 'N/A'."""
    if val is None:
        return "N/A"
    try:
        fval = float(val)
        if pd.isna(fval):
            return "N/A"
        return "{:.{}f}".format(fval, decimals).replace(".", ",")
    except Exception:
        return "N/A"


def fmt_curr(val, currency, decimals=4):
    """Penazna hodnota so SK desatinnou ciarkou."""
    n = fmt_num(val, decimals)
    if n == "N/A":
        return "N/A"
    return (n + " " + str(currency)).strip()


def fmt_pct(val, decimals=2):
    """Percentualná hodnota so SK desatinnou ciarkou."""
    n = fmt_num(val, decimals)
    if n == "N/A":
        return "N/A"
    return n + " %"


def format_qty(q):
    """
    Mnozstvo na zobrazenie: bez koncovych nul, SK desatinna ciarka.
    NIKDY nepouzivat na ukladanie – len na display!
    1.5 -> '1,5' | 1.0 -> '1' | 0.00100 -> '0,001'
    """
    try:
        fq = float(q)
    except Exception:
        return "0"
    s = "{:.5f}".format(fq).rstrip("0").rstrip(".")
    return (s if s else "0").replace(".", ",")


def _pct_change_over_period(hist, months=None, years=None):
    if hist is None or len(hist) == 0:
        return None
    try:
        last_date = hist.index[-1]
        last_price = float(hist.iloc[-1])
        if pd.isna(last_price):
            return None
        offset = pd.DateOffset(years=years) if years else pd.DateOffset(months=months)
        target_date = last_date - offset
        past_price = hist.asof(target_date)
        if past_price is None:
            return None
        if isinstance(past_price, float) and pd.isna(past_price):
            return None
        past_price = float(past_price)
        if past_price == 0 or pd.isna(past_price):
            return None
        result = (last_price - past_price) / past_price * 100
        return None if pd.isna(result) else result
    except Exception:
        return None


def format_growth(val):
    """Rast v % so SK desatinnou ciarkou. Pr.: 1.23 -> '+1,23 %'"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    sign = "+" if val >= 0 else ""
    return (sign + "{:.2f} %".format(val)).replace(".", ",")


def growth_cell_html(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    cls = "growth-pos" if val >= 0 else "growth-neg"
    return '<span class="' + cls + '">' + format_growth(val) + "</span>"


# ── Suborove cesty a GSheets ──────────────────────────────────────────────────

HOLDINGS_FILE = Path(__file__).resolve().parent / "holdings_data.json"
GSHEET_HEADER = ["Ticker", "Qty", "Exchange"]


def _find_or_create_holdings_ws(sh):
    """
    Najde list (tab) s holdings.

    KLUCOVA OPRAVA: povodny kod hladal presne list nazvany "Holdings"
    a ak ho nenasiel, TICHO vytvoril novy PRAZDNY list s tymto nazvom.
    Ak realne data boli v liste s inym nazvom (napr. "List1", "Harok1",
    "Sheet1"...), appka sa "uspesne pripojila" k spravnemu zositu, ale
    citala/zapisovala do noveho prazdneho listu -> portfolio vyzeralo
    prazdne aj ked v Google Sheets data vidno.

    Postup:
    1. Presna zhoda nazvu "Holdings".
    2. Case-insensitive zhoda nazvu.
    3. List, ktoreho hlavicka (1. riadok) obsahuje stlpce
       Ticker/Qty/Exchange (case-insensitive) - pokryje aj ine
       pomenovanie listu.
    4. Ak nic z toho, a zosit ma iba jeden list, pouzije ten (nez aby
       vytvoril druhy, prazdny, a "zatienil" existujuce data).
    5. Az na koniec: vytvori novy list "Holdings" s hlavickou.
    """
    all_ws = sh.worksheets()

    for ws in all_ws:
        if ws.title == "Holdings":
            return ws
    for ws in all_ws:
        if ws.title.strip().lower() == "holdings":
            return ws

    expected = {"ticker", "qty", "exchange"}
    for ws in all_ws:
        try:
            header = {str(h).strip().lower() for h in ws.row_values(1)}
        except Exception:
            continue
        if expected.issubset(header):
            return ws

    if len(all_ws) == 1:
        return all_ws[0]

    ws = sh.add_worksheet(title="Holdings", rows=200, cols=3)
    ws.update([GSHEET_HEADER], value_input_option="RAW")
    return ws


@st.cache_resource(show_spinner=False)
def _connect_gsheet():
    if gspread is None or _GoogleCredentials is None:
        return None, {"ok": False, "detail": "Kniznica gspread nie je nainstalovana."}
    if "gcp_service_account" not in st.secrets:
        return None, {"ok": False, "detail": "V st.secrets chyba gcp_service_account."}
    if "gsheet_url" not in st.secrets:
        return None, {"ok": False, "detail": "V st.secrets chyba gsheet_url."}
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = _GoogleCredentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(st.secrets["gsheet_url"])
        ws = _find_or_create_holdings_ws(sh)
        all_vals = ws.get_all_values()
        n_rows = max(len(all_vals) - 1, 0)
        header_row = all_vals[0] if all_vals else []
        sample_row = all_vals[1] if len(all_vals) > 1 else []
        has_header = bool(header_row) and "ticker" in [
            str(c).strip().lower() for c in header_row
        ]
        return ws, {
            "ok": True,
            "detail": ("Pripojene k: " + sh.title + " / list: " + ws.title
                       + " (" + str(n_rows) + " riadkov dat)"),
            "header_row": header_row,
            "sample_row": sample_row,
            "has_header": has_header,
        }
    except Exception as e:
        return None, {"ok": False,
                      "detail": "Chyba: " + type(e).__name__ + ": " + str(e)}


def _read_holdings_rows(ws):
    """
    Cita riadky z listu POZICNE (stlpec A=Ticker, B=Qty, C=Exchange),
    nezavisle od toho, ci ma list hlavicku alebo nie.

    KLUCOVA OPRAVA: povodny kod pouzival ws.get_all_records(), ktory
    VZDY berie 1. riadok ako hlavicku so stlpcami "Ticker"/"Qty"/
    "Exchange". Ak realny hárok ziadnu hlavicku nema (data zacinaju
    hned na 1. riadku, napr. "AAPL, 3,22535, NASDAQ"), get_all_records
    si "Ticker"/"Qty"/"Exchange" nazvy stlpcov jednoducho vymysli
    z prveho riadku dat (napr. stlpec sa vola doslova "AAPL") a
    VSETKY riadky sa potom ticho zahodia, lebo ziadny stlpec sa
    nevola "Ticker".

    Tu citame vzdy surove hodnoty (get_all_values), zisti sa, ci prvy
    riadok vyzera ako hlavicka (obsahuje bunku "ticker", case-insens.)
    - ak ano, preskoci sa; ak nie, berie sa ako data. Hodnoty sa citaju
    ako stringy, takze SK format "2,1" sa spracuje cez parse_qty_input.
    """
    all_vals = ws.get_all_values()
    if not all_vals:
        return []
    first_row = [str(c).strip().lower() for c in all_vals[0]]
    has_header = "ticker" in first_row
    data_rows = all_vals[1:] if has_header else all_vals
    records = []
    for row in data_rows:
        if not any(str(c).strip() for c in row):
            continue
        row = list(row) + ["", "", ""]
        records.append({"ticker": row[0], "qty": row[1], "exchange": row[2]})
    return records


def load_holdings():
    ws, status = _connect_gsheet()
    st.session_state["gsheet_status"] = status
    if ws is not None:
        try:
            records = _read_holdings_rows(ws)
            result = {}
            for r in records:
                # Case-insensitive pristup k stlpcom - ak ma hlavicka
                # v Google Sheets ine velke/male pismena (napr. "ticker"
                # miesto "Ticker"), nechceme ticho zahodit vsetky riadky.
                r_norm = {str(k).strip().lower(): v for k, v in r.items()}
                tkr = str(r_norm.get("ticker", "")).strip().upper()
                if not tkr:
                    continue
                raw_qty = r_norm.get("qty", 0)
                if raw_qty == "" or raw_qty is None:
                    qty = 0.0
                else:
                    # parse_qty_input zvladne int, float aj string
                    # vrátane SK formatu "2,1"
                    parsed = parse_qty_input(str(raw_qty))
                    qty = parsed if parsed is not None else 0.0
                result[tkr] = {
                    "qty": qty,
                    "exchange": r_norm.get("exchange", ""),
                }
            return result
        except Exception as e:
            st.session_state["gsheet_status"] = {
                "ok": False,
                "detail": "Chyba citania GSheets: " + str(e),
            }
    if not HOLDINGS_FILE.exists():
        return {}
    try:
        with open(HOLDINGS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def save_holdings(holdings, exchanges):
    """
    Ulozi holdings.
    value_input_option='RAW' = GSheets ulozi Python float presne tak
    ako je (2.1), bez localnej interpretacie desatinneho oddelovaca.
    """
    ws, status = _connect_gsheet()
    st.session_state["gsheet_status"] = status
    if ws is not None:
        try:
            rows = [GSHEET_HEADER] + [
                [tkr, float(qty), exchanges.get(tkr, "")]
                for tkr, qty in holdings.items()
            ]
            ws.clear()
            ws.update(rows, value_input_option="RAW")
            n = str(len(holdings))
            t = datetime.now().strftime("%H:%M:%S")
            st.session_state["gsheet_last_write"] = {
                "ok": True,
                "detail": "Ulozene do GSheets (" + n + " pozicii) o " + t,
            }
            return
        except Exception as e:
            st.session_state["gsheet_last_write"] = {
                "ok": False,
                "detail": "Zapis GSheets ZLYHAL: " + str(e),
            }
    else:
        st.session_state["gsheet_last_write"] = {
            "ok": False,
            "detail": "GSheets nie je pripojeny - lokalny subor.",
        }
    data = {
        tkr: {"qty": float(qty), "exchange": exchanges.get(tkr, "")}
        for tkr, qty in holdings.items()
    }
    try:
        with open(HOLDINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_status(exchange, now_utc):
    tz = ZoneInfo(exchange["tz"])
    now_local = now_utc.astimezone(tz)
    open_h, open_m = map(int, exchange["open"].split(":"))
    close_h, close_m = map(int, exchange["close"].split(":"))
    today_open = now_local.replace(
        hour=open_h, minute=open_m, second=0, microsecond=0)
    today_close = now_local.replace(
        hour=close_h, minute=close_m, second=0, microsecond=0)
    is_weekday = now_local.weekday() < 5
    is_open = is_weekday and today_open <= now_local < today_close
    if is_open:
        return {"is_open": True, "delta": now_local - today_open,
                "local_time": now_local}
    candidate = today_open if (is_weekday and now_local < today_open) \
        else today_open + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return {"is_open": False, "delta": candidate - now_local,
            "local_time": now_local}


def format_delta(delta):
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return str(hours) + " h " + "{:02d}".format(minutes) + " min"


class _LookupMiss(Exception):
    pass


@st.cache_data(ttl=1800, show_spinner=False)
def get_fx_to_usd_rate(currency):
    if not currency:
        return None
    pence_factor = 1.0
    curr_norm = currency
    if currency == "GBp":
        curr_norm = "GBP"
        pence_factor = 0.01
    if curr_norm.upper() == "USD":
        return 1.0
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": curr_norm.upper(), "to": "USD"},
            timeout=8,
        )
        if resp.status_code == 200:
            rate = resp.json().get("rates", {}).get("USD")
            if rate:
                return float(rate) * pence_factor
    except Exception:
        pass
    try:
        t = yf.Ticker(curr_norm.upper() + "USD=X")
        info = t.info or {}
        rate = info.get("regularMarketPrice") or info.get("previousClose")
        if rate:
            return float(rate) * pence_factor
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def _lookup_isin_by_ticker_cached(ticker_clean):
    isin = yf.Ticker(ticker_clean).isin
    if not isin or isin.upper() in ("NA", "-", "NONE", ""):
        raise _LookupMiss("no isin for " + ticker_clean)
    return isin.upper()


def lookup_isin_by_ticker(ticker):
    ticker_clean = (ticker or "").strip().upper()
    if not ticker_clean:
        return None
    try:
        return _lookup_isin_by_ticker_cached(ticker_clean)
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _lookup_ticker_by_isin_cached(isin_clean):
    search = yf.Search(isin_clean, max_results=10, news_count=0)
    quotes = search.quotes or []
    if not quotes:
        raise _LookupMiss("no quotes for " + isin_clean)
    preferred = [q for q in quotes if q.get("quoteType") in ("EQUITY", "ETF")]
    best = (preferred or quotes)[0]
    symbol = best.get("symbol")
    if not symbol:
        raise _LookupMiss("no symbol for " + isin_clean)
    return {
        "symbol": symbol,
        "name": best.get("shortname") or best.get("longname") or symbol,
        "exchange": best.get("exchDisp") or "",
    }


def lookup_ticker_by_isin(isin):
    isin_clean = (isin or "").strip().upper()
    if not isin_clean:
        return None
    try:
        return _lookup_ticker_by_isin_cached(isin_clean)
    except Exception:
        return None


def estimate_dividend_frequency(dividends):
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
        return "Mesacne"
    elif avg_gap <= 135:
        return "Stvrtrocne"
    elif avg_gap <= 250:
        return "Polrocne"
    elif avg_gap <= 450:
        return "Rocne"
    return "Nepravidelne"


_FREQ_BADGE_CLASS = {
    "Stvrtrocne": "freq-quarterly",
    "Mesacne": "freq-monthly",
    "Rocne": "freq-yearly",
    "Polrocne": "freq-semiannual",
}


def freq_badge_html(freq):
    cls = _FREQ_BADGE_CLASS.get(freq)
    if cls:
        return '<span class="freq-badge ' + cls + '">' + freq + "</span>"
    return freq


def _normalize_yield_pct(raw):
    if raw is None:
        return None
    try:
        val = float(raw)
    except Exception:
        return None
    if val <= 0:
        return None
    return val * 100 if val <= 1 else val


def _parse_stock_info(ticker, info, dividends):
    price = (info.get("currentPrice")
             or info.get("regularMarketPrice")
             or info.get("previousClose"))
    if price is None:
        return None
    name = info.get("shortName") or info.get("longName") or ticker
    currency = info.get("currency") or ""
    exchange_code = info.get("exchange") or ""
    exchange_name, country = lookup_exchange(
        exchange_code, info.get("fullExchangeName"))
    frequency = estimate_dividend_frequency(dividends)
    last_div_amount = float(dividends.iloc[-1]) \
        if (dividends is not None and len(dividends) > 0) else None
    ex_div_date = None
    ex_div_ts = info.get("exDividendDate")
    if ex_div_ts:
        try:
            ex_div_date = datetime.fromtimestamp(
                ex_div_ts, tz=timezone.utc).date()
        except Exception:
            pass
    pay_div_date = None
    pay_div_ts = info.get("dividendDate")
    if pay_div_ts:
        try:
            pay_div_date = datetime.fromtimestamp(
                pay_div_ts, tz=timezone.utc).date()
        except Exception:
            pass
    annual_rate = info.get("dividendRate")
    if annual_rate is None and last_div_amount is not None:
        annual_rate = last_div_amount * 4
    if (currency == "GBp" and annual_rate is not None
            and last_div_amount and annual_rate < last_div_amount):
        annual_rate *= 100
    dividend_yield_pct = None
    if annual_rate is not None and price:
        dividend_yield_pct = annual_rate / price * 100
    if dividend_yield_pct is None:
        dividend_yield_pct = _normalize_yield_pct(info.get("dividendYield"))
    if dividend_yield_pct is None:
        dividend_yield_pct = _normalize_yield_pct(
            info.get("trailingAnnualDividendYield"))
    return {
        "ticker": ticker, "name": name, "currency": currency,
        "price": float(price), "exchange": exchange_name,
        "exchange_code": exchange_code, "country": country,
        "last_div_amount": last_div_amount,
        "ex_div_date": ex_div_date, "pay_div_date": pay_div_date,
        "annual_rate": annual_rate,
        "dividend_yield_pct": dividend_yield_pct,
        "frequency": frequency,
        "dividends_history": dividends,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_stock_data_cached(ticker):
    """
    Stiahne vsetky potrebne udaje pre jeden ticker.

    KLUCOVA OPRAVA (stabilita pri velkom mnozstve drzanych akcii):
    Povodny kod robil PRE KAZDY TICKER 3 samostatne sietove volania na
    Yahoo Finance (t.info, t.dividends, t.history pre rast). Pri
    portfoliu so ~167 akciami to znamena stovky poziadaviek v rychlom
    slede - to takmer isto vyvola rate-limiting/blokovanie zo strany
    Yahoo (vysledok: vacsina tickerov vrati prazdne/neuplne data a
    appka ich ticho vyhodi ako "N/A", zatial co nahodne uspesne/
    vyrovnavacou pamatou pokryte tickery funguju normalne).

    Tu sa dividendy aj historia ceny pre vypocet rastu ziskaju z
    JEDNEHO volania t.history(actions=True) namiesto dvoch
    samostatnych - t.j. 2 sietove volania na ticker miesto 3.
    Cache TTL je zvyseny (30 min), aby sa pri velkom portfoliu
    tato zatazujuca davka neopakovala prilis casto.
    """
    t = yf.Ticker(ticker)
    info = t.info or {}

    try:
        hist_full = t.history(
            period="6y", interval="1d", auto_adjust=False, actions=True)
    except Exception:
        hist_full = None

    if hist_full is not None and "Close" in hist_full.columns:
        close_hist = hist_full["Close"].dropna()
    else:
        close_hist = None

    if (hist_full is not None and "Dividends" in hist_full.columns
            and len(hist_full) > 0):
        dividends = hist_full["Dividends"]
        dividends = dividends[dividends > 0]
    else:
        dividends = pd.Series(dtype=float)

    rec = _parse_stock_info(ticker, info, dividends)
    if rec is None:
        raise _LookupMiss("no price data for " + ticker)
    rec["growth"] = {
        "1m": _pct_change_over_period(close_hist, months=1),
        "3m": _pct_change_over_period(close_hist, months=3),
        "6m": _pct_change_over_period(close_hist, months=6),
        "1y": _pct_change_over_period(close_hist, years=1),
        "5y": _pct_change_over_period(close_hist, years=5),
    }
    # Male oneskorenie LEN pri realnom sietovom fetchi (nie pri zasahu
    # do cache) - znizuje riziko, ze sa pri velkom portfoliu narazi na
    # rate-limit Yahoo Finance.
    time.sleep(0.12)
    return rec


def fetch_stock_data(ticker):
    try:
        return _fetch_stock_data_cached(ticker)
    except Exception as e:
        errs = st.session_state.setdefault("_fetch_errors", {})
        errs[ticker] = type(e).__name__ + ": " + str(e)[:200]
        return None


# ── Projekcia buducich dividend ─────────────────────────────────────────────

FREQ_INTERVAL_DAYS = {
    "Mesacne": 30,
    "Stvrtrocne": 91,
    "Polrocne": 182,
    "Rocne": 365,
}

# Priemerny typicky odstup medzi ex-div datumom a datumom vyplaty,
# pouzity LEN ako odhad, ked Yahoo Finance neposkytuje potvrdeny
# buduci datum vyplaty. Skutocny odstup sa lisi podla firmy/burzy
# (zvycajne cca 2-4 tyzdne pri US akciach).
PAYOUT_LAG_DAYS_ESTIMATE = 21


def project_future_dividend_dates(rec, today, horizon_end, max_events=12):
    """
    Vrati zoznam ocakavanych buducich ex-div terminov pre danu akciu.

    Prvy termin (ak existuje) je OFICIALNE OZNAMENY buduci ex-div datum
    (rec['ex_div_date']) - teda uz potvrdena udalost. Vsetky dalsie
    terminy su len ODHAD, dopocitany na zaklade zistenej frekvencie
    vyplacania (rec['frequency']) a poslednej znamej vysky dividendy
    (rec['last_div_amount']). Ak akcia nema ziadny potvrdeny buduci
    ex-div datum, projekcia sa zacne od posledneho historickeho datumu
    + interval podla frekvencie.

    Vracia zoznam dictov {"date": date, "confirmed": bool}, zoradenych
    chronologicky, orezany na 'horizon_end' a max 'max_events' poloziek.
    """
    if rec.get("last_div_amount") is None:
        return []

    interval = FREQ_INTERVAL_DAYS.get(rec.get("frequency"))
    events = []
    cursor = None

    known_date = rec.get("ex_div_date")
    if known_date is not None and today <= known_date <= horizon_end:
        events.append({"date": known_date, "confirmed": True})
        cursor = known_date
    else:
        divs = rec.get("dividends_history")
        if divs is not None and len(divs) > 0 and interval:
            candidate = divs.index[-1].date() + timedelta(days=interval)
            guard = 0
            while candidate <= today and guard < 200:
                candidate += timedelta(days=interval)
                guard += 1
            if candidate <= horizon_end:
                events.append({"date": candidate, "confirmed": False})
                cursor = candidate

    if cursor is None or not interval:
        return events

    while len(events) < max_events:
        cursor = cursor + timedelta(days=interval)
        if cursor > horizon_end:
            break
        events.append({"date": cursor, "confirmed": False})

    return events


def make_usd_bar_chart(series, x_title, height=320, bar_color="#2f6fed"):
    """
    Postavi Altair bar chart so zvacsenym pismom na osiach a s tooltip-om
    formatovanym ako mena (znacka $, presne 2 desatinne miesta).
    'series' je pandas Series so sumami v USD, indexovana napr. mesiacom
    alebo rokom ('x_title' je nazov tejto osi).
    """
    df_plot = series.reset_index()
    df_plot.columns = [x_title, "Suma (USD)"]
    return (
        alt.Chart(df_plot)
        .mark_bar(color=bar_color)
        .encode(
            x=alt.X(
                x_title + ":O",
                title=x_title,
                sort=None,
                axis=alt.Axis(labelFontSize=14, titleFontSize=16,
                               labelAngle=-60),
            ),
            y=alt.Y(
                "Suma (USD):Q",
                title="Suma (USD)",
                axis=alt.Axis(labelFontSize=14, titleFontSize=16,
                               format="$,.2f"),
            ),
            tooltip=[
                alt.Tooltip(x_title + ":O", title=x_title),
                alt.Tooltip("Suma (USD):Q", title="Suma (USD)",
                            format="$,.2f"),
            ],
        )
        .properties(height=height)
        .configure_axis(labelFontSize=14, titleFontSize=16)
    )


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown(
    "<style>.block-container{padding-top:1.2rem;}"
    " h3{margin-bottom:0.4rem;}</style>",
    unsafe_allow_html=True,
)
st.markdown("### Dividend tracker")

now_utc = datetime.now(ZoneInfo("UTC"))

st.markdown(
    "<style>"
    ".board-wrap{background:#fff;border-radius:10px;padding:0;"
    "border:1px solid #e3e6ea;overflow:hidden;}"
    ".board{width:100%;border-collapse:collapse;border-spacing:0;"
    "font-family:'Courier New',Consolas,monospace;}"
    ".board th{text-align:left;padding:8px 16px;font-size:11.5px;"
    "letter-spacing:.1em;color:#8a93a1;text-transform:uppercase;"
    "border-bottom:1px solid #e3e6ea;background:#fafbfc;}"
    ".board td{padding:6px 16px;font-size:15px;letter-spacing:.02em;"
    "white-space:nowrap;line-height:1.1;border-bottom:1px solid #f0f1f3;}"
    ".board tr:last-child td{border-bottom:none;}"
    ".board tbody tr:hover td{background:#f2f5fa;}"
    ".row-open td{color:#15a24a;}.row-closed td{color:#e0362b;}"
    ".code-cell{font-weight:700;}"
    ".freq-badge{display:inline-block;padding:2px 10px;"
    "border-radius:999px;font-size:13px;font-weight:600;}"
    ".freq-quarterly{background:#e7f0fe;color:#2f5fd6;}"
    ".freq-monthly{background:#e3f7ea;color:#1c9350;}"
    ".freq-yearly{background:#f2e9fb;color:#7c3fc9;}"
    ".freq-semiannual{background:#fceceb;color:#c2453c;}"
    ".growth-pos{color:#15a24a;font-weight:600;}"
    ".growth-neg{color:#e0362b;font-weight:600;}"
    ".section-note{font-size:15px;line-height:1.55;color:#5b6472;"
    "margin-bottom:12px;}"
    ".chart-label{font-size:17px;font-weight:700;color:#1a1f28;"
    "margin:4px 0 8px 0;}"
    "#vg-tooltip-element{font-size:16px !important;line-height:1.5 !important;}"
    "#vg-tooltip-element table td{font-size:16px !important;"
    "padding:3px 8px !important;}"
    "#vg-tooltip-element table th{font-size:16px !important;}"
    "</style>",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────

if "holdings" not in st.session_state:
    _loaded = load_holdings()
    st.session_state.holdings = {
        tkr: rec.get("qty", 0) for tkr, rec in _loaded.items()
    }
    st.session_state.holdings_exchange = {
        tkr: rec.get("exchange", "") for tkr, rec in _loaded.items()
    }

if "holdings_exchange" not in st.session_state:
    st.session_state.holdings_exchange = {}

# ── Nacitanie dat akcii ───────────────────────────────────────────────────────

st.session_state["_fetch_errors"] = {}
stock_records = {}
if st.session_state.holdings:
    with st.spinner(
        "Nacitavam data pre " + str(len(st.session_state.holdings))
        + " akcii z Yahoo Finance (pri velkom portfoliu to moze "
        "chvilu trvat)..."
    ):
        for _tkr in list(st.session_state.holdings):
            _rec = fetch_stock_data(_tkr)
            if _rec is not None:
                stock_records[_tkr] = _rec
                st.session_state.holdings_exchange[_tkr] = _rec["exchange"]

# ============================================================
# SEKCIA 1 – PREHLAD BURZ
# ============================================================

existing_cities = {ex["city"] for ex in EXCHANGES}
owned_codes = {rec.get("exchange_code")
               for rec in stock_records.values()
               if rec.get("exchange_code")}
extras = []
for _code in owned_codes:
    _ex_info = EXTRA_MARKETS_BY_CODE.get(_code)
    if not _ex_info or _ex_info["city"] in existing_cities:
        continue
    extras.append(_ex_info)
    existing_cities.add(_ex_info["city"])

results = [(ex, get_status(ex, now_utc)) for ex in EXCHANGES + extras]
results.sort(key=lambda item: (not item[1]["is_open"], item[1]["delta"]))

row_parts = []
for ex, status in results:
    local_time_str = status["local_time"].strftime("%H:%M")
    if status["is_open"]:
        stav = "OTVORENE &mdash; " + format_delta(status["delta"]).upper()
        row_class = "row-open"
    else:
        stav = "ZATVORENE &mdash; O " + format_delta(status["delta"]).upper()
        row_class = "row-closed"
    row_parts.append(
        "<tr class=\"" + row_class + "\">"
        "<td class=\"code-cell\">" + ex["flag"] + " " + ex["code"] + "</td>"
        "<td>" + ex["city"] + "</td>"
        "<td>" + ex["country"] + "</td>"
        "<td>" + local_time_str + "</td>"
        "<td>&#9679; " + stav + "</td>"
        "</tr>"
    )

st.markdown(
    "<div class=\"board-wrap\"><table class=\"board\"><thead><tr>"
    "<th>Burza</th><th>Mesto</th><th>Stat</th>"
    "<th>Miestny cas</th><th>Stav</th>"
    "</tr></thead><tbody>" + "".join(row_parts) + "</tbody></table></div>",
    unsafe_allow_html=True,
)

# ============================================================
# SEKCIA 2 – PRIDAT / ODOBRAT AKCIU
# ============================================================

_gs_status = st.session_state.get(
    "gsheet_status",
    {"ok": False, "detail": "Pripojenie sa este vykonava..."},
)
_gs_lw = st.session_state.get("gsheet_last_write", {"ok": None, "detail": ""})
_NL = chr(10)

if _gs_status["ok"]:
    _sline = ("Ukladanie: **Google Sheets** ("
              + str(_gs_status.get("detail", "")) + ")")
else:
    _sline = ("Ukladanie: **lokalny subor** - GSheets nie je aktivny ("
              + str(_gs_status.get("detail", "")) + ")")

if _gs_lw.get("ok") is False:
    _sline += "  " + _NL + "Posledny zapis: " + str(_gs_lw.get("detail", ""))
elif _gs_lw.get("ok") is True:
    _sline += "  " + _NL + str(_gs_lw.get("detail", ""))

with st.expander("Diagnostika ukladania dat", expanded=not _gs_status["ok"]):
    st.markdown(_sline)
    if _gs_status.get("header_row") is not None:
        st.caption(
            "Zistena hlavicka (1. riadok listu): "
            + str(_gs_status.get("header_row"))
        )
        st.caption(
            "Ukazka 2. riadku (prve data): "
            + str(_gs_status.get("sample_row"))
        )
        st.caption(
            "Appka ocakava stlpce presne: Ticker, Qty, Exchange "
            "(na velkosti pismen nezalezi, ale nazov musi byt tento)."
        )
        if _gs_status.get("has_header"):
            st.caption("Hlavicka rozpoznana - riadok 1 sa preskakuje.")
        else:
            st.caption(
                "Hlavicka NEBOLA rozpoznana - vsetky riadky vratane "
                "1. sa citaju ako data (stlpec A=Ticker, B=Qty, C=Exchange)."
            )
    st.caption(
        "Pripojenie na GSheets sa skusa len raz za bezanie appky. "
        "Ak si zmenil opravnenia alebo dopisal data priamo v Google Sheets, "
        "pouzi tlacidlo nizsie."
    )
    _dcol1, _dcol2 = st.columns(2)
    with _dcol1:
        if st.button("Skusit pripojenie na GSheets znova"):
            _connect_gsheet.clear()
            _, _fresh = _connect_gsheet()
            st.session_state["gsheet_status"] = _fresh
            if _fresh.get("ok"):
                _reloaded = load_holdings()
                st.session_state.holdings = {
                    tkr: rec.get("qty", 0) for tkr, rec in _reloaded.items()
                }
                st.session_state.holdings_exchange = {
                    tkr: rec.get("exchange", "") for tkr, rec in _reloaded.items()
                }
            st.rerun()
    with _dcol2:
        if st.button("Nacitat portfolio znova z GSheets"):
            _reloaded = load_holdings()
            st.session_state.holdings = {
                tkr: rec.get("qty", 0) for tkr, rec in _reloaded.items()
            }
            st.session_state.holdings_exchange = {
                tkr: rec.get("exchange", "") for tkr, rec in _reloaded.items()
            }
            st.rerun()
    st.divider()
    st.caption("Stiahni aktualny stav portfolia ako JSON.")
    _bdata = json.dumps(
        {tkr: {"qty": float(qty),
               "exchange": st.session_state.holdings_exchange.get(tkr, "")}
         for tkr, qty in st.session_state.holdings.items()},
        ensure_ascii=False, indent=2,
    )
    st.download_button(
        "Stiahnut zalohu portfolia (JSON)",
        data=_bdata,
        file_name="holdings_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json",
        mime="application/json",
    )

st.markdown("#### Pridat / odobrat akciu")


def _sync_isin_from_ticker():
    t = (st.session_state.get("add_ticker_field") or "").strip().upper()
    st.session_state["add_ticker_field"] = t
    if t:
        isin = lookup_isin_by_ticker(t)
        if isin:
            st.session_state["add_isin_field"] = isin
            st.session_state["add_sync_msg"] = None
        else:
            st.session_state["add_sync_msg"] = (
                "info",
                "ISIN pre ticker sa nepodarilo dohladat. "
                "Zadaj ho rucne – ISIN nie je nutny, staci ticker.",
            )


def _sync_ticker_from_isin():
    i = (st.session_state.get("add_isin_field") or "").strip().upper()
    st.session_state["add_isin_field"] = i
    if i:
        info = lookup_ticker_by_isin(i)
        if info:
            st.session_state["add_ticker_field"] = info["symbol"].upper()
            st.session_state["add_sync_msg"] = None
        else:
            st.session_state["add_sync_msg"] = (
                "warning",
                "Ticker pre ISIN sa nepodarilo najst. "
                "Skontroluj ISIN alebo zadaj ticker rucne.",
            )


def _on_add_stock_click():
    ticker_clean = (
        st.session_state.get("add_ticker_field") or ""
    ).strip().upper()
    isin_clean = (
        st.session_state.get("add_isin_field") or ""
    ).strip().upper()

    # Parsovanie mnozstva – akceptuje ',' aj '.' ako desatinnu ciarku
    qty_raw = str(st.session_state.get("add_qty_field") or "").strip()
    qty_val = parse_qty_input(qty_raw)

    if not ticker_clean and isin_clean:
        info = lookup_ticker_by_isin(isin_clean)
        if info:
            ticker_clean = info["symbol"].upper()
            st.session_state["add_ticker_field"] = ticker_clean

    if not ticker_clean:
        st.session_state["add_stock_msg"] = (
            "warning", "Zadaj ticker alebo ISIN akcie.")
        return

    if qty_val is None or qty_val == 0:
        if qty_raw and qty_raw not in ("0", "0,0", "0.0", "0,00", "0.00"):
            msg = ("Neplatne mnozstvo '{}'. "
                   "Zadaj cislo, napr. 1,5 alebo -0,5.").format(qty_raw)
        else:
            msg = "Zadaj mnozstvo rozne od 0."
        st.session_state["add_stock_msg"] = ("warning", msg)
        return

    if qty_val > 0:
        # NAKUP
        new_data = fetch_stock_data(ticker_clean)
        if new_data is None:
            st.session_state["add_stock_msg"] = (
                "error", "Ticker " + ticker_clean + " sa nepodarilo najst.")
            return
        current = float(st.session_state.holdings.get(ticker_clean, 0))
        new_total = current + qty_val
        # Ulozenie ako Python float – NIKDY ako formatovany string
        st.session_state.holdings[ticker_clean] = new_total
        st.session_state.holdings_exchange[ticker_clean] = (
            new_data.get("exchange", ""))
        save_holdings(
            st.session_state.holdings,
            st.session_state.holdings_exchange,
        )
        st.session_state["add_stock_msg"] = (
            "success",
            "Pridane: " + format_qty(qty_val) + " ks " + ticker_clean
            + " (" + new_data["name"] + "). Celkovo: "
            + format_qty(new_total) + " ks.",
        )
    else:
        # PREDAJ
        current_qty = float(
            st.session_state.holdings.get(ticker_clean, 0))
        if current_qty <= 0:
            st.session_state["add_stock_msg"] = (
                "info",
                "Akcia " + ticker_clean
                + " nie je vlastnena, nie je co odobrat.",
            )
            return
        remove_qty = abs(qty_val)
        new_qty = current_qty - remove_qty
        if new_qty <= 0:
            del st.session_state.holdings[ticker_clean]
            st.session_state.holdings_exchange.pop(ticker_clean, None)
            extra = " (pozicia vynulovana)" if remove_qty > current_qty else ""
            st.session_state["add_stock_msg"] = (
                "success",
                "Odobrate vsetkych " + format_qty(current_qty)
                + " ks " + ticker_clean + "." + extra,
            )
        else:
            st.session_state.holdings[ticker_clean] = new_qty
            st.session_state["add_stock_msg"] = (
                "success",
                "Odobrate " + format_qty(remove_qty) + " ks "
                + ticker_clean + ". Novy stav: "
                + format_qty(new_qty) + " ks.",
            )
        save_holdings(
            st.session_state.holdings,
            st.session_state.holdings_exchange,
        )

    st.session_state["add_ticker_field"] = ""
    st.session_state["add_isin_field"] = ""
    st.session_state["add_qty_field"] = ""


c1, c2, c3, c4 = st.columns([2.3, 2.3, 1.6, 1])
with c1:
    st.text_input("Ticker", placeholder="Ticker, napr. AAPL",
                  label_visibility="collapsed", key="add_ticker_field",
                  on_change=_sync_isin_from_ticker)
with c2:
    st.text_input("ISIN", placeholder="ISIN, napr. US0378331005",
                  label_visibility="collapsed", key="add_isin_field",
                  on_change=_sync_ticker_from_isin)
with c3:
    st.text_input("Mnozstvo", placeholder="Mnozstvo, napr. 1,5",
                  label_visibility="collapsed", key="add_qty_field")
with c4:
    st.button("Pridat", use_container_width=True,
              on_click=_on_add_stock_click)

st.caption(
    "Staci vyplnit ticker ALEBO ISIN. "
    "Kladne = nakup, zaporne = predaj. "
    "Desatinna ciarka aj bodka su prijate (1,5 = 1.5)."
)

_m = st.session_state.pop("add_sync_msg", None)
if _m:
    getattr(st, _m[0])(_m[1])
_m = st.session_state.pop("add_stock_msg", None)
if _m:
    getattr(st, _m[0])(_m[1])

# ============================================================
# SEKCIA 3 – MOJE AKCIE  (len na zobrazenie, bez zapisu spat)
# ============================================================

st.markdown("#### Moje akcie")

_fetch_errs = st.session_state.get("_fetch_errors", {})
if st.session_state.holdings and _fetch_errs:
    _n_fail = len(_fetch_errs)
    _n_total = len(st.session_state.holdings)
    with st.expander(
        "Nepodarilo sa nacitat data pre " + str(_n_fail) + " z "
        + str(_n_total) + " akcii", expanded=False
    ):
        st.caption(
            "Toto zvycajne znamena docasne rate-limitovanie/blokovanie "
            "zo strany Yahoo Finance (najma pri velkom mnozstve akcii "
            "naraz), prip. neplatny/delistovany ticker. Skus "
            "'Nacitat portfolio znova z GSheets' o par minut - "
            "uz nacitane tickery ostanu v cache 30 min a nebudu sa "
            "sťahovat znova."
        )
        _sample = list(_fetch_errs.items())[:15]
        for _tk, _msg in _sample:
            st.caption("**" + _tk + "**: " + _msg)
        if _n_fail > len(_sample):
            st.caption("... a dalsich " + str(_n_fail - len(_sample)) + ".")

if not st.session_state.holdings:
    st.info("Zatial nemas pridane ziadne akcie. Pridaj prvu vyssie.")
else:
    rows_h = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None:
            rows_h.append({
                "Ticker": tkr,
                "Meno firmy": tkr,
                "Burza": st.session_state.holdings_exchange.get(tkr) or "N/A",
                "Stat": "N/A",
                "Aktualna cena": "N/A",
                "Rast 1M [%]": "N/A", "Rast 3M [%]": "N/A",
                "Rast 6M [%]": "N/A", "Rast 1R [%]": "N/A",
                "Rast 5R [%]": "N/A", "Div.Rocne[%]": "N/A",
                "Mnozstvo": format_qty(float(qty)),
            })
        else:
            growth = rec.get("growth") or {}
            pa = None
            if rec.get("annual_rate") and rec.get("price"):
                pa = rec["annual_rate"] / rec["price"] * 100
            rows_h.append({
                "Ticker": tkr,
                "Meno firmy": rec["name"],
                "Burza": rec["exchange"],
                "Stat": rec["country"],
                "Aktualna cena": fmt_curr(rec["price"], rec["currency"], 2),
                "Rast 1M [%]": format_growth(growth.get("1m")),
                "Rast 3M [%]": format_growth(growth.get("3m")),
                "Rast 6M [%]": format_growth(growth.get("6m")),
                "Rast 1R [%]": format_growth(growth.get("1y")),
                "Rast 5R [%]": format_growth(growth.get("5y")),
                "Div.Rocne[%]": fmt_pct(pa),
                "Mnozstvo": format_qty(float(qty)),
            })

    df_h = pd.DataFrame(rows_h)
    _gcols = ["Rast 1M [%]", "Rast 3M [%]", "Rast 6M [%]",
               "Rast 1R [%]", "Rast 5R [%]"]

    def _style_g(val):
        if not val or val == "N/A":
            return ""
        try:
            fv = float(
                str(val).replace(" ", "").replace("%", "").replace(",", "."))
            if fv > 0:
                return "color:#15a24a;font-weight:600;"
            if fv < 0:
                return "color:#e0362b;font-weight:600;"
        except Exception:
            pass
        return ""

    try:
        styled_h = df_h.style.map(_style_g, subset=_gcols)
    except AttributeError:
        styled_h = df_h.style.applymap(_style_g, subset=_gcols)

    # Vsetky stlpce su disabled – data_editor sluzi len na zobrazenie.
    # Ziadna slucka neupdatuje session_state z editora.
    # Mnozstvo sa meni VYLUCNE cez formular vyssie.
    st.data_editor(
        styled_h,
        column_config={
            "Ticker":        st.column_config.TextColumn(disabled=True),
            "Meno firmy":    st.column_config.TextColumn(disabled=True),
            "Burza":         st.column_config.TextColumn(disabled=True),
            "Stat":          st.column_config.TextColumn(disabled=True),
            "Aktualna cena": st.column_config.TextColumn(disabled=True),
            "Rast 1M [%]":   st.column_config.TextColumn(disabled=True),
            "Rast 3M [%]":   st.column_config.TextColumn(disabled=True),
            "Rast 6M [%]":   st.column_config.TextColumn(disabled=True),
            "Rast 1R [%]":   st.column_config.TextColumn(disabled=True),
            "Rast 5R [%]":   st.column_config.TextColumn(disabled=True),
            "Div.Rocne[%]":  st.column_config.TextColumn(disabled=True),
            "Mnozstvo":      st.column_config.TextColumn(
                disabled=True,
                help="Mnozstvo zmen cez formular 'Pridat / odobrat akciu'."),
        },
        hide_index=True,
        use_container_width=True,
        height=740,
        key="holdings_editor",
    )

# ============================================================
# Spolocny vypocet: najblizsi buduci ex-div termin pre kazdu drzanu akciu
# (KLUCOVA OPRAVA: pouziva rovnaku projekciu ako Sekcia 7 - Yahoo Finance
# totiz vo vacsine pripadov vracia v poli 'exDividendDate'/'dividendDate'
# len POSLEDNY UZ PRESLY termin, nie buduci. Priamy filter "iba ak je v
# buducnosti" preto skoro vzdy vsetko vyradil a sekcie boli prazdne.
# project_future_dividend_dates pouzije potvrdeny buduci datum, ak
# existuje, inak ho DOPOCITA z frekvencie vyplacania a historie.)
# ============================================================

_today_div = datetime.now(timezone.utc).date()
_horizon_div = (pd.Timestamp(_today_div) + pd.DateOffset(months=12)).date()

next_ex_event_by_ticker = {}
for _tkr in st.session_state.holdings:
    _rec = stock_records.get(_tkr)
    if _rec is None:
        continue
    _events = project_future_dividend_dates(_rec, _today_div, _horizon_div,
                                             max_events=1)
    if _events:
        next_ex_event_by_ticker[_tkr] = _events[0]

# ============================================================
# SEKCIA 4 – NAJBLIZZSIE EX-DIV DATUMY
# ============================================================

st.markdown("#### Najblizzsie Ex-Div datumy")
st.markdown(
    "<div class=\"section-note\">Ak akcia nema oficialne oznameny buduci "
    "Ex-Div datum, termin je ODHADNUTY na zaklade zistenej frekvencie "
    "vyplacania - oznacene znackou 'Odhad'. Skutocny datum sa moze "
    "zmenit.</div>",
    unsafe_allow_html=True,
)

if not st.session_state.holdings:
    st.info("Pridaj akcie vyssie, aby sa tu zobrazil prehlad dividend.")
else:
    div_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        ev = next_ex_event_by_ticker.get(tkr)
        if rec is None or ev is None:
            continue
        price = rec["price"]
        last_div = rec["last_div_amount"]
        annual_rate = rec["annual_rate"]
        currency = rec["currency"]
        pct_last = (last_div / price * 100
                    if last_div is not None and price else None)
        pct_annual = rec.get("dividend_yield_pct")
        if pct_annual is None and annual_rate is not None and price:
            pct_annual = annual_rate / price * 100
        div_rows.append({
            "ticker": tkr, "name": rec["name"],
            "ex_date": ev["date"], "confirmed": ev["confirmed"],
            "frequency": rec["frequency"],
            "last_div": last_div, "annual_rate": annual_rate,
            "pct_last": pct_last, "pct_annual": pct_annual,
            "expected": last_div, "currency": currency,
            "growth": rec.get("growth") or {},
        })

    if not div_rows:
        st.info(
            "Pre drzane akcie sa nepodarilo urcit ani odhadnut buduci "
            "Ex-Div datum (chyba historia dividend alebo frekvencia)."
        )
    else:
        div_rows.sort(key=lambda r: r["ex_date"])
        div_rows = div_rows[:40]
        div_row_parts = []
        for r in div_rows:
            last_div_str = fmt_curr(r["last_div"], r["currency"], 4)
            if r["last_div"] is not None and r["currency"].upper() != "USD":
                rl = get_fx_to_usd_rate(r["currency"])
                if rl:
                    last_div_str += (" (~ USD "
                                     + fmt_num(r["last_div"] * rl, 4) + ")")
            pct_last_str = fmt_pct(r["pct_last"])
            pct_annual_str = fmt_pct(r["pct_annual"])
            if r["annual_rate"] is not None:
                curr = r["currency"]
                annual_div_str = fmt_curr(r["annual_rate"], curr, 4)
                if curr.upper() != "USD":
                    ra = get_fx_to_usd_rate(curr)
                    if ra:
                        annual_div_str += (" (~ USD "
                                           + fmt_num(r["annual_rate"] * ra, 2) + ")")
            else:
                annual_div_str = "N/A"
            if r["expected"] is not None:
                curr = r["currency"]
                expected_str = fmt_curr(r["expected"], curr, 4)
                if curr.upper() != "USD":
                    re2 = get_fx_to_usd_rate(curr)
                    if re2:
                        expected_str += (" (~ USD "
                                         + fmt_num(r["expected"] * re2, 4) + ")")
            else:
                expected_str = "N/A"
            g = r.get("growth") or {}
            status_html = (
                "<span class=\"freq-badge freq-monthly\">Potvrdene</span>"
                if r["confirmed"] else
                "<span class=\"freq-badge freq-quarterly\">Odhad</span>"
            )
            div_row_parts.append(
                "<tr>"
                "<td class=\"code-cell\">" + r["ticker"] + "</td>"
                "<td>" + r["name"] + "</td>"
                "<td>1 ks</td>"
                "<td>" + r["ex_date"].strftime("%d/%m/%y") + "</td>"
                "<td>" + status_html + "</td>"
                "<td>" + freq_badge_html(r["frequency"]) + "</td>"
                "<td>" + growth_cell_html(g.get("1m")) + "</td>"
                "<td>" + growth_cell_html(g.get("3m")) + "</td>"
                "<td>" + growth_cell_html(g.get("6m")) + "</td>"
                "<td>" + growth_cell_html(g.get("1y")) + "</td>"
                "<td>" + growth_cell_html(g.get("5y")) + "</td>"
                "<td>" + last_div_str + "</td>"
                "<td>" + annual_div_str + "</td>"
                "<td>" + pct_last_str + "</td>"
                "<td>" + pct_annual_str + "</td>"
                "<td>" + expected_str + "</td>"
                "</tr>"
            )
        st.markdown(
            "<div class=\"board-wrap\"><table class=\"board\"><thead><tr>"
            "<th>Ticker</th><th>Meno</th><th>Mnozstvo</th>"
            "<th>Ex-Div Date</th><th>Status</th><th>Frekvencia</th>"
            "<th>Rast 1M</th><th>Rast 3M</th><th>Rast 6M</th>"
            "<th>Rast 1R</th><th>Rast 5R</th>"
            "<th>Dividenda/akcia</th><th>Rocna divi./akcia</th>"
            "<th>% k cene</th><th>Div Yield</th>"
            "<th>Ocak. vynos/akcia</th>"
            "</tr></thead><tbody>"
            + "".join(div_row_parts)
            + "</tbody></table></div>",
            unsafe_allow_html=True,
        )

# ============================================================
# SEKCIA 5 – VYPLACANE DIVIDENDY
# ============================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### Vyplacane dividendy")
st.markdown(
    "<div class=\"section-note\">Ak Yahoo Finance neposkytuje potvrdeny "
    "buduci datum vyplaty, datum je ODHADNUTY ako najblizsi (potvrdeny "
    "alebo odhadnuty) Ex-Div termin + priblizny bezny odstup "
    + str(PAYOUT_LAG_DAYS_ESTIMATE) + " dni - oznacene znackou 'Odhad'. "
    "Skutocny datum vyplaty sa moze lisit.</div>",
    unsafe_allow_html=True,
)

if not st.session_state.holdings:
    st.info("Pridaj akcie vyssie, aby sa tu zobrazil prehlad vyplat.")
else:
    today_pay = datetime.now(timezone.utc).date()
    pay_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None:
            continue
        confirmed_pay_date = rec.get("pay_div_date")
        if confirmed_pay_date is not None and confirmed_pay_date >= today_pay:
            pay_date = confirmed_pay_date
            confirmed_pay = True
        else:
            ev = next_ex_event_by_ticker.get(tkr)
            if ev is None:
                continue
            pay_date = ev["date"] + timedelta(days=PAYOUT_LAG_DAYS_ESTIMATE)
            confirmed_pay = False
        price = rec["price"]
        last_div = rec["last_div_amount"]
        annual_rate = rec["annual_rate"]
        currency = rec["currency"]
        pct_annual = rec.get("dividend_yield_pct")
        if pct_annual is None and annual_rate is not None and price:
            pct_annual = annual_rate / price * 100
        total_div = (last_div * float(qty)) if last_div is not None else None
        pay_rows.append({
            "ticker": tkr, "name": rec["name"],
            "qty": float(qty), "pay_date": pay_date,
            "confirmed": confirmed_pay,
            "frequency": rec["frequency"], "pct_annual": pct_annual,
            "last_div": last_div, "total_div": total_div,
            "currency": currency,
        })

    if not pay_rows:
        st.info(
            "Pre drzane akcie sa nepodarilo urcit ani odhadnut buduci "
            "datum vyplaty dividendy."
        )
    else:
        pay_rows.sort(key=lambda r: r["pay_date"])
        pay_rows = pay_rows[:30]
        pay_row_parts = []
        for r in pay_rows:
            pct_annual_str = fmt_pct(r["pct_annual"])
            last_div_str = fmt_curr(r["last_div"], r["currency"], 4)
            if r["total_div"] is not None:
                curr = r["currency"]
                total_div_str = fmt_curr(r["total_div"], curr, 2)
                if curr.upper() != "USD":
                    r3 = get_fx_to_usd_rate(curr)
                    if r3:
                        total_div_str += (" (~ USD "
                                          + fmt_num(r["total_div"] * r3, 2) + ")")
            else:
                total_div_str = "N/A"
            status_html = (
                "<span class=\"freq-badge freq-monthly\">Potvrdene</span>"
                if r["confirmed"] else
                "<span class=\"freq-badge freq-quarterly\">Odhad</span>"
            )
            pay_row_parts.append(
                "<tr>"
                "<td class=\"code-cell\">" + r["ticker"] + "</td>"
                "<td>" + r["name"] + "</td>"
                "<td>" + format_qty(r["qty"]) + " ks</td>"
                "<td>" + r["pay_date"].strftime("%d/%m/%y") + "</td>"
                "<td>" + status_html + "</td>"
                "<td>" + freq_badge_html(r["frequency"]) + "</td>"
                "<td>" + pct_annual_str + "</td>"
                "<td>" + last_div_str + "</td>"
                "<td>" + total_div_str + "</td>"
                "</tr>"
            )
        st.markdown(
            "<div class=\"board-wrap\"><table class=\"board\"><thead><tr>"
            "<th>Ticker</th><th>Meno</th><th>Mnozstvo</th>"
            "<th>Div Date</th><th>Status</th><th>Frekvencia</th>"
            "<th>Rocny Div Yield</th>"
            "<th>Dividenda/akcia</th><th>Dividenda/spolu</th>"
            "</tr></thead><tbody>"
            + "".join(pay_row_parts)
            + "</tbody></table></div>",
            unsafe_allow_html=True,
        )

# ============================================================
# SEKCIA 6 – HISTORIA VYPLATENYCH DIVIDEND (posledne roky)
# ============================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### Historia vyplatenych dividend")
st.markdown(
    "<div class=\"section-note\">Odhad na zaklade AKTUALNE drzaneho "
    "mnozstva akcii a oficialnych historickych ex-div datumov a vysok "
    "dividend. Appka nesleduje historicke zmeny velkosti pozicie, takze "
    "ide o priblizny prepocet (akoby si dane mnozstvo akcii drzal/a "
    "pocas celeho obdobia), nie o realnu historiu tvojich vlastnych "
    "vyplat. Prepocet na USD pouziva aktualny FX kurz, nie "
    "historicky.</div>",
    unsafe_allow_html=True,
)

if not st.session_state.holdings:
    st.info("Pridaj akcie vyssie, aby sa tu zobrazila historia dividend.")
else:
    today_h = datetime.now(timezone.utc).date()
    start_h = (pd.Timestamp(today_h) - pd.DateOffset(years=5)).date()

    hist_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None:
            continue
        divs = rec.get("dividends_history")
        if divs is None or len(divs) == 0:
            continue
        currency = rec["currency"]
        fx = get_fx_to_usd_rate(currency) or 1.0
        qty_f = float(qty)
        for ts, amount in divs.items():
            d = ts.date()
            if d < start_h or d > today_h:
                continue
            amount = float(amount)
            if amount <= 0:
                continue
            hist_rows.append({
                "date": d, "ticker": tkr, "qty": qty_f,
                "amount_per_share": amount, "currency": currency,
                "amount_local": amount * qty_f,
                "amount_usd": amount * qty_f * fx,
            })

    if not hist_rows:
        st.info("Za poslednych 5 rokov sa nenasli ziadne vyplatene dividendy pre drzane akcie.")
    else:
        df_hist = pd.DataFrame(hist_rows)
        df_hist["month"] = df_hist["date"].apply(lambda d: d.strftime("%Y-%m"))
        df_hist["year"] = df_hist["date"].apply(lambda d: d.year)

        monthly_hist = df_hist.groupby("month")["amount_usd"].sum().sort_index()
        total_hist = df_hist["amount_usd"].sum()
        n_years_covered = max(df_hist["year"].nunique(), 1)

        current_year = today_h.year
        ytd_hist = df_hist[df_hist["year"] == current_year]["amount_usd"].sum()
        months_elapsed = today_h.month
        avg_month_ytd = ytd_hist / months_elapsed if months_elapsed else 0.0

        colH1, colH2 = st.columns([1, 3])
        with colH1:
            st.metric("Spolu za 5 rokov (odhad)", fmt_curr(total_hist, "USD", 2))
            st.metric(
                "Priemerne rocne",
                fmt_curr(total_hist / n_years_covered, "USD", 2),
            )
            st.metric(
                "Priemerne mesacne (rok " + str(current_year) + ")",
                fmt_curr(avg_month_ytd, "USD", 2),
                help=(
                    "Sucet dividend od zaciatku roku " + str(current_year)
                    + " do dnes, delene poctom doterajsich mesiacov ("
                    + str(months_elapsed) + ")."
                ),
            )
        with colH2:
            st.markdown(
                "<div class=\"chart-label\">Mesacny prijem z dividend (USD)</div>",
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_usd_bar_chart(monthly_hist, "month"),
                use_container_width=True,
            )

        with st.expander("Detailny prehlad podla akcie a mesiaca"):
            pivot_hist = df_hist.pivot_table(
                index="month", columns="ticker",
                values="amount_usd", aggfunc="sum", fill_value=0.0,
            ).sort_index()
            st.dataframe(
                pivot_hist.style.format("{:.2f}"),
                use_container_width=True,
            )

# ============================================================
# SEKCIA 7 – OCAKAVANE BUDUCE DIVIDENDOVE PRIJMY
# ============================================================

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("#### Ocakavane buduce dividendove prijmy")
st.markdown(
    "<div class=\"section-note\">Prvy termin pri kazdej akcii je "
    "oficialne oznameny buduci ex-div datum (ak je dostupny) - teda uz "
    "potvrdena udalost. Dalsie terminy su len ODHAD, dopocitany na "
    "zaklade zistenej frekvencie vyplacania a poslednej znamej vysky "
    "dividendy na akciu. Skutocna vyska aj datum buducich vyplat sa "
    "mozu zmenit.</div>",
    unsafe_allow_html=True,
)

if not st.session_state.holdings:
    st.info("Pridaj akcie vyssie, aby sa tu zobrazila projekcia dividend.")
else:
    today_f = datetime.now(timezone.utc).date()
    horizon_f = (pd.Timestamp(today_f) + pd.DateOffset(months=12)).date()

    proj_rows = []
    for tkr, qty in st.session_state.holdings.items():
        rec = stock_records.get(tkr)
        if rec is None:
            continue
        events = project_future_dividend_dates(rec, today_f, horizon_f)
        if not events:
            continue
        currency = rec["currency"]
        fx = get_fx_to_usd_rate(currency) or 1.0
        last_div = rec.get("last_div_amount") or 0.0
        qty_f = float(qty)
        for ev in events:
            proj_rows.append({
                "date": ev["date"], "ticker": tkr, "name": rec["name"],
                "qty": qty_f, "amount_per_share": last_div,
                "currency": currency,
                "amount_local": last_div * qty_f,
                "amount_usd": last_div * qty_f * fx,
                "confirmed": ev["confirmed"],
            })

    if not proj_rows:
        st.info(
            "Pre drzane akcie nie su dostupne data na projekciu "
            "buducich dividend."
        )
    else:
        df_proj = pd.DataFrame(proj_rows)
        df_proj["month"] = df_proj["date"].apply(lambda d: d.strftime("%Y-%m"))
        monthly_proj = df_proj.groupby("month")["amount_usd"].sum().sort_index()
        total_proj = df_proj["amount_usd"].sum()

        colF1, colF2 = st.columns([1, 3])
        with colF1:
            st.metric("Ocakavane za 12 mesiacov", fmt_curr(total_proj, "USD", 2))
        with colF2:
            st.markdown(
                "<div class=\"chart-label\">Ocakavany mesacny prijem z "
                "dividend (USD)</div>",
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_usd_bar_chart(monthly_proj, "month"),
                use_container_width=True,
            )

        df_proj_sorted = df_proj.sort_values("date")
        proj_row_parts = []
        for _, r in df_proj_sorted.iterrows():
            amt_usd_str = fmt_curr(r["amount_usd"], "USD", 2)
            amt_local_str = fmt_curr(r["amount_local"], r["currency"], 2)
            status_html = (
                "<span class=\"freq-badge freq-monthly\">Potvrdene</span>"
                if r["confirmed"] else
                "<span class=\"freq-badge freq-quarterly\">Odhad</span>"
            )
            proj_row_parts.append(
                "<tr>"
                "<td class=\"code-cell\">" + r["ticker"] + "</td>"
                "<td>" + r["name"] + "</td>"
                "<td>" + r["date"].strftime("%d/%m/%y") + "</td>"
                "<td>" + status_html + "</td>"
                "<td>" + format_qty(r["qty"]) + " ks</td>"
                "<td>" + amt_local_str + "</td>"
                "<td>" + amt_usd_str + "</td>"
                "</tr>"
            )
        with st.expander("Detailny prehlad ocakavanych vyplat", expanded=False):
            st.markdown(
                "<div class=\"board-wrap\"><table class=\"board\"><thead><tr>"
                "<th>Ticker</th><th>Meno</th><th>Datum</th><th>Status</th>"
                "<th>Mnozstvo</th><th>Suma/menou</th><th>Suma (USD)</th>"
                "</tr></thead><tbody>"
                + "".join(proj_row_parts)
                + "</tbody></table></div>",
                unsafe_allow_html=True,
            )
