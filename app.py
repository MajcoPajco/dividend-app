import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividendový cockpit", layout="wide")
st.title("Dividendový cockpit")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if "column_names" not in st.session_state:
    st.session_state.column_names = {}
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

def eu_date(d):
    if d is None: return ""
    return d.strftime("%d-%m-%y")

def add_units(df):
    df = df.copy()

    pct_cols = ["dividendovy_vynos_%","buduci_div_vynos_%"]
    for c in pct_cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda x: f"{x:.2f} %" if pd.notna(x) else "")

    if "mena" in df.columns:
        cur = df["mena"].iloc[0] or ""
        money_cols = [
            "aktualna_cena","hodnota_pozicie","posledna_dividenda_na_akciu",
            "rocna_div_na_akciu","rocna_div_spolu","buduca_div_na_akciu",
            "buduca_div_spolu"
        ]
        for c in money_cols:
            if c in df.columns:
                df[c] = df[c].apply(lambda x: f"{x:.2f} {cur}" if pd.notna(x) else "")

    return df
col_add, col_settings = st.sidebar.columns([3,1])

with col_add:
    ticker = st.text_input("Ticker (napr. MA, MA.TO)").strip().upper()
    shares = st.text_input("Množstvo akcií").strip()

    if st.button("Pridať"):
        try:
            shares_val = float(shares)
            if ticker and shares_val > 0:
                st.session_state.portfolio.append({"ticker":ticker,"shares":shares_val})
                st.success(f"Pridané {ticker}")
            else:
                st.error("Zadaj ticker a množstvo > 0")
        except:
            st.error("Zadaj platné číslo")

with col_settings:
    open_settings = st.button("⚙️")
if open_settings:
    st.sidebar.subheader("Nastavenia")

    st.sidebar.write("### Premenovanie stĺpcov")
    for col in st.session_state.column_names.keys() | {"poradie","ticker","company_name","burza","mena","mnozstvo","aktualna_cena","hodnota_pozicie","posledna_dividenda_na_akciu","posledny_div_datum","frekvencia","rocna_div_na_akciu","rocna_div_spolu","dividendovy_vynos_%","buduca_div_na_akciu","buduca_div_spolu","buduci_div_vynos_%","next_ex_div_date"}:
        new_name = st.sidebar.text_input(f"Názov pre '{col}'", value=st.session_state.column_names.get(col,col))
        st.session_state.column_names[col] = new_name

    st.sidebar.write("### Označenia búrz")
    st.sidebar.table(pd.DataFrame({
        "Yahoo kód":["NYQ","NMS","ASE","PCX","BATS","TSX","LSE","FRA","GER","MIL","SWX"],
        "Burza":["NYSE","NASDAQ","AMEX","NYSE Arca","BATS","Toronto","London","Frankfurt","Xetra","Milano","Swiss"]
    }))

    st.sidebar.write("### Označenia mien")
    st.sidebar.table(pd.DataFrame({
        "Kód":["USD","EUR","GBP","CHF","JPY","CAD","AUD"],
        "Mena":["Americký dolár","Euro","Britská libra","Švajčiarsky frank","Japonský jen","Kanadský dolár","Austrálsky dolár"]
    }))
st.subheader("Detailné informácie o akciách")

if not st.session_state.portfolio:
    st.info("Zatiaľ nič nepridané.")
    st.stop()

rows = []
official = []

today = datetime.today().date()

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

        freq = infer_frequency(divs)
        fpy = freq_per_year(freq)

        if fpy > 0:
            annual = last_amt * fpy

        if price and annual > 0:
            yield_pct = annual / price * 100

        annual_total = annual * pos["shares"]

        future_total = last_amt * pos["shares"]
        if price and last_amt > 0:
            future_yield = last_amt / price * 100

        # presnejší kvartálny posun
        if freq == "mesačne": next_ex = last_date + timedelta(days=30)
        elif freq == "kvartálne": next_ex = last_date + timedelta(days=91)
        elif freq == "polročne": next_ex = last_date + timedelta(days=180)
        elif freq == "ročne": next_ex = last_date + timedelta(days=365)

        if next_ex:
            official.append({
                "poradie": idx,
                "ticker": pos["ticker"],
                "company_name": company,
                "ex_div_date": eu_date(next_ex),
                "div_amount": last_amt,
                "div_amount_total": future_total,
                "div_yield_pct": future_yield
            })

    rows.append({
        "poradie": idx,
        "ticker": pos["ticker"],
        "company_name": company,
        "burza": exchange,
        "mena": currency,
        "mnozstvo": pos["shares"],
        "aktualna_cena": price,
        "hodnota_pozicie": price*pos["shares"] if price else None,
        "posledna_dividenda_na_akciu": last_amt,
        "posledny_div_datum": eu_date(last_date) if last_date else "",
        "frekvencia": freq,
        "rocna_div_na_akciu": annual,
        "rocna_div_spolu": annual_total,
        "dividendovy_vynos_%": yield_pct,
        "buduca_div_na_akciu": last_amt,
        "buduca_div_spolu": future_total,
        "buduci_div_vynos_%": future_yield,
        "next_ex_div_date": eu_date(next_ex) if next_ex else ""
    })
df = pd.DataFrame(rows)
df = add_units(df)

# Premenovanie stĺpcov
df = df.rename(columns=st.session_state.column_names)

edited_df = st.data_editor(
    df,
    use_container_width=True,
    key="detail_editor",
    column_config={
        "poradie": st.column_config.NumberColumn("Poradie", disabled=True),
        "ticker": st.column_config.TextColumn("Ticker", disabled=True),
        "company_name": st.column_config.TextColumn("Názov firmy", disabled=True),
        "burza": st.column_config.TextColumn("Burza", disabled=True),
        "mena": st.column_config.TextColumn("Mena", disabled=True),
        "mnozstvo": st.column_config.NumberColumn("Množstvo akcií"),
    }
)

# Uloženie zmien množstva
for i, row in edited_df.iterrows():
    st.session_state.portfolio[i]["shares"] = float(row["mnozstvo"])
st.subheader("Ohlásené dividendy")

if official:
    div_df = pd.DataFrame(official)

    div_df["div_amount"] = div_df["div_amount"].apply(lambda x: f"{x:.2f}")
    div_df["div_amount_total"] = div_df["div_amount_total"].apply(lambda x: f"{x:.2f}")
    div_df["div_yield_pct"] = div_df["div_yield_pct"].apply(lambda x: f"{x:.2f} %")

    st.dataframe(div_df, use_container_width=True)
else:
    st.info("Žiadne ohlásené dividendy.")
