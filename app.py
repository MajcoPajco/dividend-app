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
        "company_name": "Názov firmy",
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
