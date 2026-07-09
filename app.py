import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividendový cockpit", layout="wide")
st.title("Dividendový cockpit")

# ---------- SESSION STATE ----------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []  # list of dicts: {ticker, shares}

if "column_labels" not in st.session_state:
    st.session_state.column_labels = {
        "ticker": "Ticker",
        "burza": "Burza",
        "mena": "Mena",
        "mnozstvo": "Množstvo akcií",
        "aktualna_cena": "Aktuálna cena",
        "hodnota_pozicie": "Hodnota pozície",
        "posledna_dividenda_na_akciu": "Posledná div. na akciu",
        "posledny_div_datum": "Posledný div. dátum",
        "frekvencia": "Frekvencia",
        "rocna_div_na_akciu": "Ročná div. na akciu",
        "rocna_div_spolu": "Ročná div. spolu",
        "dividendovy_vynos_%": "Ročný div. výnos %",
        "buduca_div_na_akciu": "Budúca div. na akciu",
        "buduca_div_spolu": "Budúca div. spolu",
        "buduci_div_vynos_%": "Budúci div. výnos %",
        "next_ex_div_date": "Budúci Ex-div dátum",
        "company_name": "Názov firmy",
    }

# ---------- HELPER FUNKCIE ----------

def infer_frequency(dividends: pd.Series):
    if len(dividends) < 2:
        return "neznáme"
    dates = dividends.index.to_pydatetime()
    deltas = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    avg = sum(deltas) / len(deltas)
    if avg < 45:
        return "mesačne"
    if avg < 140:
        return "kvartálne"
    if avg < 300:
        return "polročne"
    return "ročne"

def freq_per_year(freq_text: str) -> int:
    return {"mesačne": 12, "kvartálne": 4, "polročne": 2, "ročne": 1}.get(freq_text, 0)

def add_units(df):
    """Pridá jednotky do tabuľky (%, USD, EUR, …)."""
    df = df.copy()

    # percentá
    pct_cols = ["dividendovy_vynos_%", "buduci_div_vynos_%"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2f} %" if pd.notna(x) else "")

    # mena
    if "mena" in df.columns:
        currency = df["mena"].iloc[0] if df["mena"].iloc[0] else ""
        money_cols = [
            "aktualna_cena",
            "hodnota_pozicie",
            "posledna_dividenda_na_akciu",
            "rocna_div_na_akciu",
            "rocna_div_spolu",
            "buduca_div_na_akciu",
            "buduca_div_spolu",
        ]
        for col in money_cols:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: f"{x:.2f} {currency}" if pd.notna(x) else ""
                )

    return df

# ---------- SIDEBAR: PRIDANIE AKCIE ----------

st.sidebar.header("Pridaj akciu do portfólia")

ticker_input = st.sidebar.text_input("Ticker (napr. MA, MA.TO, MA.DE)").strip().upper()
shares_input = st.sidebar.number_input("Množstvo akcií", min_value=0.0, step=1.0)

if st.sidebar.button("Pridať do portfólia"):
    if ticker_input and shares_input > 0:
        st.session_state.portfolio.append(
            {"ticker": ticker_input, "shares": shares_input}
        )
        st.sidebar.success(f"Pridané: {ticker_input} ({shares_input} ks)")
    else:
        st.sidebar.error("Zadaj ticker a množstvo väčšie ako 0.")

# ---------- HLAVNÁ ČASŤ: PORTFÓLIO ----------

st.subheader("Moje portfólio")

if not st.session_state.portfolio:
    st.info("Zatiaľ nemáš žiadne akcie v portfóliu. Pridaj ich v ľavom paneli.")
    st.stop()

portfolio_df = pd.DataFrame(st.session_state.portfolio)
st.dataframe(portfolio_df, use_container_width=True)

# ---------- MOŽNOSŤ UPRAVIŤ POČET AKCIÍ ----------

st.subheader("Upraviť množstvo akcií")

for i, pos in enumerate(st.session_state.portfolio):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.write(f"**{pos['ticker']}**")
    with col2:
        new_shares = st.number_input(
            f"Nové množstvo pre {pos['ticker']}",
            min_value=0.0,
            step=1.0,
            value=float(pos["shares"]),
            key=f"shares_edit_{i}",
        )
    with col3:
        if st.button("Uložiť", key=f"save_{i}"):
            st.session_state.portfolio[i]["shares"] = new_shares
            st.success(f"Množstvo pre {pos['ticker']} upravené na {new_shares}")

# ---------- SPRACOVANIE DÁT ----------

all_rows = []
official_div_rows = []

current_year = datetime.now().year

for pos in st.session_state.portfolio:
    ticker = pos["ticker"]
    shares = pos["shares"]

    try:
        t = yf.Ticker(ticker)

        # Aktuálna cena
        hist = t.history(period="1d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
        else:
            price = None

        info = getattr(t, "info", {})
        exchange = info.get("exchange", "neznáme")
        currency = info.get("currency", "USD")
        company_name = info.get("shortName", "")

        # Dividendy (história)
        dividends = t.dividends

        last_amount = None
        last_date = None
        freq_text = "neznáme"
        annual_div_per_share = 0.0
        dividend_yield_pct = 0.0
        annual_div_total = 0.0
        future_div_yield_pct = 0.0
        future_div_total = 0.0
        next_ex_div_date = None

        if dividends is not None and not dividends.empty:
            last_amount = float(dividends.iloc[-1])
            last_date = dividends.index[-1].to_pydatetime()

            freq_text = infer_frequency(dividends)
            freq_per_year_val = freq_per_year(freq_text)

            if freq_per_year_val > 0:
                annual_div_per_share = last_amount * freq_per_year_val

            if price and annual_div_per_share > 0:
                dividend_yield_pct = annual_div_per_share / price * 100

            annual_div_total = annual_div_per_share * shares

            # Budúca (najbližšia) dividenda – posledná ohlásená
            future_div_total = last_amount * shares
            if price and last_amount > 0:
                future_div_yield_pct = last_amount / price * 100

            # Ohlásené dividendy (oficiálne)
            official_div_rows.append({
                "ticker": ticker,
                "company_name": company_name,
                "ex_div_date": last_date.date(),
                "div_amount": last_amount,
                "div_amount_total": future_div_total,
                "div_yield_pct": future_div_yield_pct,
                "currency": currency
            })

            # Odhad najbližšieho ex-div dátumu
            if freq_text == "mesačne":
                next_ex_div_date = last_date + timedelta(days=30)
            elif freq_text == "kvartálne":
                next_ex_div_date = last_date + timedelta(days=90)
            elif freq_text == "polročne":
                next_ex_div_date = last_date + timedelta(days=180)
            elif freq_text == "ročne":
                next_ex_div_date = last_date + timedelta(days=365)

        all_rows.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "burza": exchange,
                "mena": currency,
                "mnozstvo": shares,
                "aktualna_cena": price,
                "hodnota_pozicie": price * shares if price else None,
                "posledna_dividenda_na_akciu": last_amount,
                "posledny_div_datum": last_date.date() if last_date else None,
                "frekvencia": freq_text,
                "rocna_div_na_akciu": annual_div_per_share,
                "rocna_div_spolu": annual_div_total,
