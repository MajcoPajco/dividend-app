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

# ---------- NASTAVENIA STĹPCOV ----------

with st.sidebar.expander("Premenovanie stĺpcov"):
    for key, default_label in st.session_state.column_labels.items():
        new_label = st.text_input(f"Názov stĺpca pre '{key}'", value=default_label)
        st.session_state.column_labels[key] = new_label

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
dividend_history_rows = []
upcoming_ex_div_rows = []

current_year = datetime.now().year

for pos in st.session_state.portfolio:
    ticker = pos["ticker"]
    shares = pos["shares"]

    try:
        t = yf.Ticker(ticker)

        # Aktuálna cena
        hist = t.history(period="1d")
        if hist.empty:
            price = None
        else:
            price = float(hist["Close"].iloc[-1])

        info = getattr(t, "info", {})
        exchange = info.get("exchange", "neznáme")
        currency = info.get("currency", "neznáme")

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
            else:
                annual_div_per_share = 0.0

            if price and annual_div_per_share > 0:
                dividend_yield_pct = annual_div_per_share / price * 100
            else:
                dividend_yield_pct = 0.0

            annual_div_total = annual_div_per_share * shares

            # Budúca (najbližšia) dividenda – berieme poslednú ako reprezentatívnu
            future_div_total = last_amount * shares
            if price and last_amount > 0:
                future_div_yield_pct = last_amount / price * 100
            else:
                future_div_yield_pct = 0.0

            # História dividend v aktuálnom roku (mesačné súčty)
            div_df = dividends.to_frame(name="div_per_share")
            div_df["date"] = div_df.index
            div_df["year"] = div_df["date"].dt.year
            div_df["month"] = div_df["date"].dt.month
            div_df["div_total"] = div_df["div_per_share"] * shares

            current_year_div = div_df[div_df["year"] == current_year]
            monthly_sum = (
                current_year_div.groupby("month")["div_total"].sum().reset_index()
            )
            monthly_sum["ticker"] = ticker

            for _, row in monthly_sum.iterrows():
                dividend_history_rows.append(
                    {
                        "ticker": ticker,
                        "month": int(row["month"]),
                        "div_total": float(row["div_total"]),
                    }
                )

            # Odhad najbližšieho ex-div dátumu na základe frekvencie
            if freq_text == "mesačne":
                next_ex_div_date = last_date + timedelta(days=30)
            elif freq_text == "kvartálne":
                next_ex_div_date = last_date + timedelta(days=90)
            elif freq_text == "polročne":
                next_ex_div_date = last_date + timedelta(days=180)
            elif freq_text == "ročne":
                next_ex_div_date = last_date + timedelta(days=365)
            else:
                next_ex_div_date = None

            if next_ex_div_date:
                upcoming_ex_div_rows.append(
                    {
                        "ticker": ticker,
                        "next_ex_div_date": next_ex_div_date.date(),
                        "div_yield_pct": dividend_yield_pct,
                        "next_div_amount_total": future_div_total,
                    }
                )

        all_rows.append(
            {
                "ticker": ticker,
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
                "dividendovy_vynos_%": dividend_yield_pct,
                "buduca_div_na_akciu": last_amount,
                "buduca_div_spolu": future_div_total,
                "buduci_div_vynos_%": future_div_yield_pct,
                "next_ex_div_date": next_ex_div_date.date() if next_ex_div_date else None,
            }
        )

    except Exception as e:
        st.error(f"Chyba pri spracovaní tickeru {ticker}: {e}")

# ---------- DETAILNÁ TABUĽKA ----------

if all_rows:
    st.subheader("Detailné informácie o akciách")
    details_df = pd.DataFrame(all_rows)

    # Premenovanie stĺpcov podľa nastavení
    rename_map = {
        col: st.session_state.column_labels.get(col, col)
        for col in details_df.columns
    }
    details_df = details_df.rename(columns=rename_map)

    st.dataframe(details_df, use_container_width=True)

# ---------- GRAF MESAČNÝCH DIVIDEND ----------

if dividend_history_rows:
    st.subheader(f"História vyplatených dividend v roku {current_year}")

    hist_df = pd.DataFrame(dividend_history_rows)
    total_monthly = hist_df.groupby("month")["div_total"].sum().reset_index()
    total_monthly["month_name"] = total_monthly["month"].apply(
        lambda m: datetime(current_year, m, 1).strftime("%b")
    )

    st.bar_chart(
        data=total_monthly.set_index("month_name")["div_total"],
        use_container_width=True,
    )

    with st.expander("Detail podľa tickerov"):
        st.dataframe(hist_df, use_container_width=True)
else:
    st.info("Nemám históriu dividend pre aktuálny rok (možno ticker nevypláca dividendy alebo chýbajú dáta).")

# ---------- ZOZNAM BUDÚCICH (ODHADOVANÝCH) EX-DIV DÁTUMOV ----------

if upcoming_ex_div_rows:
    st.subheader("Odhad najbližších Ex-div dátumov (na základe histórie)")

    upcoming_df = pd.DataFrame(upcoming_ex_div_rows)
    upcoming_df = upcoming_df.sort_values("next_ex_div_date")

    st.dataframe(upcoming_df, use_container_width=True)
else:
    st.info("Z histórie sa nepodarilo odhadnúť najbližšie Ex-div dátumy.")
