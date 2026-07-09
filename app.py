import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividendový cockpit", layout="wide")

st.title("Dividendový cockpit")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

def infer_frequency(dividends):
    if len(dividends) < 2:
        return "neznáme"
    dates = dividends.index.to_pydatetime()
    deltas = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
    avg = sum(deltas) / len(deltas)
    if avg < 45: return "mesačne"
    if avg < 140: return "kvartálne"
    if avg < 300: return "polročne"
    return "ročne"

def freq_per_year(freq):
    return {"mesačne":12, "kvartálne":4, "polročne":2, "ročne":1}.get(freq, 0)

st.sidebar.header("Pridaj akciu")
with st.sidebar.form("add"):
    t = st.text_input("Ticker").strip().upper()
    s = st.number_input("Množstvo", min_value=0.0, step=1.0)
    if st.form_submit_button("Pridať"):
        if t and s > 0:
            st.session_state.portfolio.append({"ticker": t, "shares": s})
            st.success(f"Pridané {t}")
        else:
            st.error("Zadaj ticker a množstvo > 0")

if not st.session_state.portfolio:
    st.info("Pridaj akcie v ľavom paneli.")
    st.stop()

rows = []
hist_rows = []
ex_rows = []
year = datetime.now().year

for pos in st.session_state.portfolio:
    ticker = pos["ticker"]
    shares = pos["shares"]

    try:
        t = yf.Ticker(ticker)
        price = t.history(period="1d")["Close"].iloc[-1]
        info = t.info
        exchange = info.get("exchange", "neznáme")
        currency = info.get("currency", "neznáme")

        dividends = t.dividends
        if dividends.empty:
            rows.append({
                "ticker": ticker,
                "burza": exchange,
                "mena": currency,
                "mnozstvo": shares,
                "aktualna_cena": price,
                "hodnota_pozicie": price * shares,
                "posledna_dividenda_na_akciu": None,
                "frekvencia": "neznáme",
                "rocna_div_na_akciu": 0,
                "rocna_div_spolu": 0,
                "dividendovy_vynos_%": 0
            })
            continue

        last_amount = dividends.iloc[-1]
        last_date = dividends.index[-1].to_pydatetime()

        freq = infer_frequency(dividends)
        fpy = freq_per_year(freq)
        annual = last_amount * fpy
        yield_pct = annual / price * 100 if annual > 0 else 0
        annual_total = annual * shares

        df = dividends.to_frame("div_per_share")
        df["date"] = df.index
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["div_total"] = df["div_per_share"] * shares

        cy = df[df["year"] == year]
        monthly = cy.groupby("month")["div_total"].sum().reset_index()

        for _, r in monthly.iterrows():
            hist_rows.append({
                "ticker": ticker,
                "month": int(r["month"]),
                "div_total": float(r["div_total"])
            })

        if freq == "mesačne":
            next_ex = last_date + timedelta(days=30)
        elif freq == "kvartálne":
            next_ex = last_date + timedelta(days=90)
        elif freq == "polročne":
            next_ex = last_date + timedelta(days=180)
        elif freq == "ročne":
            next_ex = last_date + timedelta(days=365)
        else:
            next_ex = None

        if next_ex:
            ex_rows.append({
                "ticker": ticker,
                "next_ex_div_date": next_ex.date(),
                "div_yield_pct": yield_pct,
                "next_div_amount_total": last_amount * shares
            })

        rows.append({
            "ticker": ticker,
            "burza": exchange,
            "mena": currency,
            "mnozstvo": shares,
            "aktualna_cena": price,
            "hodnota_pozicie": price * shares,
            "posledna_dividenda_na_akciu": last_amount,
            "posledny_div_datum": last_date.date(),
            "frekvencia": freq,
            "rocna_div_na_akciu": annual,
            "rocna_div_spolu": annual_total,
            "dividendovy_vynos_%": yield_pct
        })

    except Exception as e:
        st.error(f"Chyba pri {ticker}: {e}")

st.subheader("Detail akcií")
st.dataframe(pd.DataFrame(rows), use_container_width=True)

if hist_rows:
    st.subheader(f"Dividendy {year}")
    h = pd.DataFrame(hist_rows)
    m = h.groupby("month")["div_total"].sum().reset_index()
    m["month_name"] = m["month"].apply(lambda x: datetime(year, x, 1).strftime("%b"))
    st.bar_chart(m.set_index("month_name")["div_total"])
else:
    st.info("Žiadna história dividend.")

if ex_rows:
    st.subheader("Najbližšie odhadované Ex-div dátumy")
    st.dataframe(pd.DataFrame(ex_rows), use_container_width=True)
