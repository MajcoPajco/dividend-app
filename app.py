import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividendový cockpit", layout="wide")
st.title("Dividendový cockpit")
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if "settings_open" not in st.session_state:
    st.session_state.settings_open = False
with st.sidebar:
    col1, col2 = st.columns([4,1])

    with col1:
        ticker = st.text_input("Ticker", key="ticker").strip().upper()
        shares = st.text_input("Množstvo akcií", key="shares").strip()

        if st.button("Pridať"):
            try:
                val = float(shares)
                if ticker and val > 0:
                    st.session_state.portfolio.append({"ticker": ticker, "shares": val})
                    st.success(f"Pridané {ticker}")

                    # FUNKČNÝ RESET
                    st.session_state.ticker = ""
                    st.session_state.shares = ""
                else:
                    st.error("Zadaj ticker a množstvo > 0")
            except:
                st.error("Zadaj platné číslo")

    with col2:
        if st.button("⚙️"):
            st.session_state.settings_open = not st.session_state.settings_open
if st.session_state.settings_open:
    st.sidebar.subheader("Nastavenia")

    all_cols = [
        "poradie","ticker","company_name","burza","mena","mnozstvo",
        "aktualna_cena","hodnota_pozicie","posledna_dividenda_na_akciu",
        "posledny_div_datum","frekvencia","rocna_div_na_akciu",
        "rocna_div_spolu","dividendovy_vynos_%","buduca_div_na_akciu",
        "buduca_div_spolu","buduci_div_vynos_%","next_ex_div_date",
        "ex_div_date","div_amount","div_amount_total","div_yield_pct"
    ]

    st.sidebar.write("Premenovanie stĺpcov:")
    for col in all_cols:
        st.sidebar.text_input(f"{col}", key=f"rename_{col}")
rows = []
official = []

for idx, pos in enumerate(st.session_state.portfolio, start=1):
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
    annual_total = 0
    future_yield = 0
    future_total = 0
    next_ex = None

    if divs is not None and not divs.empty:
        last_amt = float(divs.iloc[-1])
        last_date = divs.index[-1].to_pydatetime()

        # frekvencia
        dates = divs.index.to_pydatetime()
        diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        avg = sum(diffs) / len(diffs)
        if avg < 45: freq = "mesačne"
        elif avg < 140: freq = "kvartálne"
        elif avg < 300: freq = "polročne"
        else: freq = "ročne"

        # ďalší ex-div
        if freq == "mesačne": next_ex = last_date + timedelta(days=30)
        elif freq == "kvartálne": next_ex = last_date + timedelta(days=91)
        elif freq == "polročne": next_ex = last_date + timedelta(days=180)
        elif freq == "ročne": next_ex = last_date + timedelta(days=365)

        official.append({
            "poradie": str(idx),
            "ticker": pos["ticker"],
            "company_name": company,
            "ex_div_date": next_ex.strftime("%d-%m-%y") if next_ex else "",
            "div_amount": f"{last_amt:.2f}",
            "div_amount_total": f"{last_amt * pos['shares']:.2f}",
            "div_yield_pct": f"{(last_amt/price*100):.2f} %" if price else ""
        })

    rows.append({
        "poradie": str(idx),
        "ticker": pos["ticker"],
        "company_name": company,
        "burza": exchange,
        "mena": currency,
        "mnozstvo": pos["shares"],
        "aktualna_cena": f"{price:.2f} {currency}" if price else "",
        "hodnota_pozicie": f"{price*pos['shares']:.2f} {currency}" if price else "",
        "posledna_dividenda_na_akciu": f"{last_amt:.2f}" if last_amt else "",
        "posledny_div_datum": last_date.strftime("%d-%m-%y") if last_date else "",
        "frekvencia": freq,
        "rocna_div_na_akciu": f"{annual:.2f}",
        "rocna_div_spolu": f"{annual_total:.2f}",
        "dividendovy_vynos_%": f"{yield_pct:.2f} %",
        "buduca_div_na_akciu": f"{last_amt:.2f}" if last_amt else "",
        "buduca_div_spolu": f"{future_total:.2f}",
        "buduci_div_vynos_%": f"{future_yield:.2f} %",
        "next_ex_div_date": next_ex.strftime("%d-%m-%y") if next_ex else ""
    })
df = pd.DataFrame(rows)

edited = st.data_editor(
    df,
    hide_index=True,
    key="editor",
    column_config={
        "poradie": st.column_config.TextColumn("Poradie", disabled=True),
        "mnozstvo": st.column_config.NumberColumn("Množstvo akcií")
    }
)

# uloženie zmien
for i, row in edited.iterrows():
    st.session_state.portfolio[i]["shares"] = float(row["mnozstvo"])
st.subheader("Ohlásené dividendy")

if official:
    div_df = pd.DataFrame(official)
    st.dataframe(div_df, hide_index=True)
else:
    st.info("Žiadne ohlásené dividendy.")
