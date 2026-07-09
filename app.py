import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividendový cockpit", layout="wide")
st.title("Dividendový cockpit")

# ---------------- SESSION ----------------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# ---------------- HELPERS ----------------
def infer_frequency(divs):
    if len(divs) < 2:
        return "neznáme"
    dates = divs.index.to_pydatetime()
    diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
    avg = sum(diffs) / len(diffs)
    if avg < 45: return "mesačne"
    if avg < 140: return "kvartálne"
    if avg < 300: return "polročne"
    return "ročne"

def freq_per_year(freq):
    return {"mesačne":12,"kvartálne":4,"polročne":2,"ročne":1}.get(freq,0)

def add_units(df):
    df = df.copy()
    if "mena" in df.columns:
        cur = df["mena"].iloc[0] or ""
        money = ["aktualna_cena","hodnota_pozicie","posledna_dividenda_na_akciu",
                 "rocna_div_na_akciu","rocna_div_spolu","buduca_div_na_akciu",
                 "buduca_div_spolu"]
        for c in money:
            if c in df.columns:
                df[c] = df[c].apply(lambda x: f"{x:.2f} {cur}" if pd.notna(x) else "")
    pct = ["dividendovy_vynos_%","buduci_div_vynos_%"]
    for c in pct:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: f"{x:.2f} %" if pd.notna(x) else "")
    return df

# ---------------- SIDEBAR ----------------
st.sidebar.header("Pridaj akciu")
ticker = st.sidebar.text_input("Ticker (napr. MA, MA.TO)").strip().upper()
shares = st.sidebar.number_input("Množstvo", min_value=0.0, step=1.0)

if st.sidebar.button("Pridať"):
    if ticker and shares > 0:
        st.session_state.portfolio.append({"ticker":ticker,"shares":shares})
        st.sidebar.success(f"Pridané {ticker}")
    else:
        st.sidebar.error("Zadaj ticker a množstvo > 0")

# ---------------- PORTFOLIO ----------------
st.subheader("Moje portfólio")
if not st.session_state.portfolio:
    st.info("Zatiaľ nič nepridané.")
    st.stop()

st.dataframe(pd.DataFrame(st.session_state.portfolio), use_container_width=True)

# ---------------- EDIT SHARES ----------------
st.subheader("Upraviť množstvo akcií")
for i, pos in enumerate(st.session_state.portfolio):
    col1, col2, col3 = st.columns([2,2,1])
    with col1: st.write(pos["ticker"])
    with col2:
        new = st.number_input(f"Nové množstvo pre {pos['ticker']}",
                              min_value=0.0, step=1.0,
                              value=float(pos["shares"]),
                              key=f"edit_{i}")
    with col3:
        if st.button("Uložiť", key=f"save_{i}"):
            st.session_state.portfolio[i]["shares"] = new
            st.success("Uložené")

# ---------------- PROCESS DATA ----------------
rows = []
official = []

for pos in st.session_state.portfolio:
    t = yf.Ticker(pos["ticker"])
    hist = t.history(period="1d")
    price = float(hist["Close"].iloc[-1]) if not hist.empty else None

    info = t.info
    currency = info.get("currency","USD")
    company = info.get("shortName","")
    exchange = info.get("exchange","")

    divs = t.dividends
    last_amt = None
    last_date = None
    freq = "neznáme"
    annual = 0
    yield_pct = 0
    future_yield = 0
    future_total = 0
    next_ex = None

    if divs is not None and not divs.empty:
        last_amt = float(divs.iloc[-1])
        last_date = divs.index[-1].to_pydatetime()
        freq = infer_frequency(divs)
        fpy = freq_per_year(freq)
        annual = last_amt * fpy if fpy else 0
        yield_pct = (annual/price*100) if price else 0
        future_total = last_amt * pos["shares"]
        future_yield = (last_amt/price*100) if price else 0

        official.append({
            "ticker": pos["ticker"],
            "company_name": company,
            "ex_div_date": last_date.date(),
            "div_amount": last_amt,
            "div_amount_total": future_total,
            "div_yield_pct": future_yield,
            "currency": currency
        })

        if freq == "mesačne": next_ex = last_date + timedelta(days=30)
        elif freq == "kvartálne": next_ex = last_date + timedelta(days=90)
        elif freq == "polročne": next_ex = last_date + timedelta(days=180)
        elif freq == "ročne": next_ex = last_date + timedelta(days=365)

    rows.append({
        "ticker": pos["ticker"],
        "company_name": company,
        "burza": exchange,
        "mena": currency,
        "mnozstvo": pos["shares"],
        "aktualna_cena": price,
        "hodnota_pozicie": price*pos["shares"] if price else None,
        "posledna_dividenda_na_akciu": last_amt,
        "posledny_div_datum": last_date.date() if last_date else None,
        "frekvencia": freq,
        "rocna_div_na_akciu": annual,
        "rocna_div_spolu": annual*pos["shares"],
        "dividendovy_vynos_%": yield_pct,
        "buduca_div_na_akciu": last_amt,
        "buduca_div_spolu": future_total,
        "buduci_div_vynos_%": future_yield,
        "next_ex_div_date": next_ex.date() if next_ex else None
    })

# ---------------- DETAIL TABLE ----------------
st.subheader("Detailné informácie")
df = pd.DataFrame(rows)
df = add_units(df)
st.dataframe(df, use_container_width=True)

# ---------------- OFFICIAL DIVIDENDS ----------------
st.subheader("Ohlásené dividendy")
if official:
    div = pd.DataFrame(official)
    div["div_amount"] = div.apply(lambda r: f"{r['div_amount']:.2f} {r['currency']}", axis=1)
    div["div_amount_total"] = div.apply(lambda r: f"{r['div_amount_total']:.2f} {r['currency']}", axis=1)
    div["div_yield_pct"] = div["div_yield_pct"].apply(lambda x: f"{x:.2f} %")
    st.dataframe(div, use_container_width=True)
else:
    st.info("Žiadne ohlásené dividendy.")
