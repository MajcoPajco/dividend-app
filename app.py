import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividendový cockpit", layout="wide")
st.title("Dividendový cockpit")

# ---------- SESSION STATE ----------
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []  # list of dicts: {ticker, shares}
def infer_frequency(divs: pd.Series):
    if len(divs) < 2:
        return "neznáme"
    dates = divs.index.to_pydatetime()
    diffs = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    avg = sum(diffs) / len(diffs)
    if avg < 45:
        return "mesačne"
    if avg < 140:
        return "kvartálne"
    if avg < 300:
        return "polročne"
    return "ročne"

def freq_per_year(freq: str) -> int:
    return {"mesačne": 12, "kvartálne": 4, "polročne": 2, "ročne": 1}.get(freq, 0)

def format_eu_date(d):
    if d is None or pd.isna(d):
        return ""
    return d.strftime("%d-%m-%y")

def add_units(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # percentá
    pct_cols = ["dividendovy_vynos_%", "buduci_div_vynos_%"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2f} %" if pd.notna(x) else "")

    # mena
    if "mena" in df.columns and len(df) > 0:
        currency = df["mena"].iloc[0] or ""
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

    # dátumy do európskeho formátu
    date_cols = ["posledny_div_datum", "next_ex_div_date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: format_eu_date(x) if isinstance(x, datetime) else (x if isinstance(x, str) else "")
            )

    return df
st.sidebar.header("Pridaj akciu")

ticker = st.sidebar.text_input("Ticker (napr. MA, MA.TO)").strip().upper()
shares = st.sidebar.number_input("Množstvo akcií", min_value=0.0, step=1.0)

if st.sidebar.button("Pridať do portfólia"):
    if ticker and shares > 0:
        st.session_state.portfolio.append({"ticker": ticker, "shares": shares})
        st.sidebar.success(f"Pridané: {ticker} ({shares} ks)")
    else:
        st.sidebar.error("Zadaj ticker a množstvo väčšie ako 0.")
st.subheader("Detailné informácie o akciách")

if not st.session_state.portfolio:
    st.info("Zatiaľ nemáš žiadne akcie v portfóliu. Pridaj ich v ľavom paneli.")
    st.stop()

rows = []
official_rows = []

today = datetime.today().date()

for idx, pos in enumerate(st.session_state.portfolio, start=1):
    ticker = pos["ticker"]
    shares = pos["shares"]

    try:
        t = yf.Ticker(ticker)

        hist = t.history(period="1d")
        price = float(hist["Close"].iloc[-1]) if not hist.empty else None

        info = t.info
        currency = info.get("currency", "USD")
        company = info.get("shortName", "")
        exchange = info.get("exchange", "")

        divs = t.dividends

        last_amt = None
        last_date = None
        freq = "neznáme"
        annual = 0.0
        yield_pct = 0.0
        annual_total = 0.0
        future_yield = 0.0
        future_total = 0.0
        next_ex = None

        if divs is not None and not divs.empty:
            # posledná historická dividenda
            last_amt = float(divs.iloc[-1])
            last_date = divs.index[-1].to_pydatetime()

            freq = infer_frequency(divs)
            fpy = freq_per_year(freq)

            if fpy > 0:
                annual = last_amt * fpy

            if price and annual > 0:
                yield_pct = annual / price * 100

            annual_total = annual * shares

            future_total = last_amt * shares
            if price and last_amt > 0:
                future_yield = last_amt / price * 100

            # odhad najbližšieho ex-div dátumu (kvartálne +91 dní kvôli MA)
            if freq == "mesačne":
                next_ex = last_date + timedelta(days=30)
            elif freq == "kvartálne":
                next_ex = last_date + timedelta(days=91)
            elif freq == "polročne":
                next_ex = last_date + timedelta(days=180)
            elif freq == "ročne":
                next_ex = last_date + timedelta(days=365)

            # oficiálne / budúce ohlásené dividendy – tu berieme odhadovaný najbližší ex-div
            if next_ex:
                official_rows.append(
                    {
                        "poradie": idx,
                        "ticker": ticker,
                        "company_name": company,
                        "ex_div_date": next_ex.date(),
                        "div_amount": last_amt,
                        "div_amount_total": future_total,
                        "div_yield_pct": future_yield,
                        "currency": currency,
                    }
                )

        rows.append(
            {
                "poradie": idx,
                "ticker": ticker,
                "company_name": company,
                "burza": exchange,
                "mena": currency,
                "mnozstvo": shares,
                "aktualna_cena": price,
                "hodnota_pozicie": price * shares if price else None,
                "posledna_dividenda_na_akciu": last_amt,
                "posledny_div_datum": last_date,
                "frekvencia": freq,
                "rocna_div_na_akciu": annual,
                "rocna_div_spolu": annual_total,
                "dividendovy_vynos_%": yield_pct,
                "buduca_div_na_akciu": last_amt,
                "buduca_div_spolu": future_total,
                "buduci_div_vynos_%": future_yield,
                "next_ex_div_date": next_ex,
            }
        )

    except Exception as e:
        st.error(f"Chyba pri spracovaní tickeru {ticker}: {e}")
if rows:
    df = pd.DataFrame(rows)

    # európsky formát dátumov v DF (pred jednotkami)
    if "posledny_div_datum" in df.columns:
        df["posledny_div_datum"] = df["posledny_div_datum"].apply(
            lambda x: format_eu_date(x) if isinstance(x, datetime) else ""
        )
    if "next_ex_div_date" in df.columns:
        df["next_ex_div_date"] = df["next_ex_div_date"].apply(
            lambda x: format_eu_date(x) if isinstance(x, datetime) else ""
        )

    # pridanie jednotiek (%, mena)
    df = add_units(df)

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        key="detail_editor",
        column_config={
            "poradie": st.column_config.NumberColumn("Poradie", disabled=True),
            "ticker": st.column_config.TextColumn("Ticker", disabled=True),
            "company_name": st.column_config.TextColumn("Názov firmy", disabled=True),
            "burza": st.column_config.TextColumn("Burza", disabled=True),
            "mena": st.column_config.TextColumn("Mena", disabled=True),
            "mnozstvo": st.column_config.NumberColumn("Množstvo akcií"),
        },
    )

    # aktualizácia množstva akcií podľa editovanej tabuľky
    for i, row in edited_df.iterrows():
        st.session_state.portfolio[i]["shares"] = float(row["mnozstvo"])
st.subheader("Ohlásené / odhadované budúce dividendy")

if official_rows:
    div_df = pd.DataFrame(official_rows)

    # európsky formát dátumu
    div_df["ex_div_date"] = div_df["ex_div_date"].apply(
        lambda d: format_eu_date(datetime.combine(d, datetime.min.time()))
    )

    # jednotky
    div_df["div_amount"] = div_df.apply(
        lambda r: f"{r['div_amount']:.2f} {r['currency']}", axis=1
    )
    div_df["div_amount_total"] = div_df.apply(
        lambda r: f"{r['div_amount_total']:.2f} {r['currency']}", axis=1
    )
    div_df["div_yield_pct"] = div_df["div_yield_pct"].apply(
        lambda x: f"{x:.2f} %"
    )

    st.dataframe(div_df, use_container_width=True)
else:
    st.info("Žiadne budúce (odhadované) ex-div dátumy.")
