# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
from datetime import datetime
import streamlit as st

st.title("📊 Varredura de Ações da B3")

st.write(
    "Este app lê uma lista de tickers do arquivo **`IBOVDia_300925_sem_duplicadas.csv`**, "
    "baixa dados do Yahoo Finance e mostra um resumo consolidado."
)

# Período total de histórico a ser baixado
period = st.selectbox("Período para análise", ["1y", "2y", "5y", "10y"], index=2)

# Escolha do intervalo do candle: mensal ou anual
interval_label = st.selectbox(
    "Intervalo do candle",
    ["Mensal (1mo)", "Anual (1y)"],
    index=0
)

# Converte o label em valor do yfinance
interval = "1mo" if "1mo" in interval_label else "1y"


def baixar_dados(ticker, period, interval):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,   # <- aqui pode ser "1mo" ou "1y"
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        st.error(f"[ERROR] Exception while downloading {ticker}: {e}")
        return None
    
    if df is None or df.empty:
        return None

    # Ajusta índice
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Data"

    # Renomeia colunas
    df = df.rename(columns={
        "Open": "Abertura",
        "High": "Máxima",
        "Low": "Mínima",
        "Close": "Fechamento",
        "Volume": "Volume"
    })

    # Cria colunas de diferenças (como no seu código original)
    df["%_Fech_Abert"]   = (df["Fechamento"] - df["Abertura"]).round(2)
    df["%_Abert_Minim"]  = (df["Abertura"]   - df["Mínima"]).round(2)
    df["%_Max_Min"]      = (df["Máxima"]     - df["Mínima"]).round(2)

    df = df[[
        "Abertura", "Fechamento", "Máxima", "Mínima",
        "Volume", "%_Fech_Abert", "%_Abert_Minim", "%_Max_Min"
    ]]

    # Razão corpo / range do candle (em %)
    df["%_FechAbert_vs_MaxMin"] = (
        (df["Fechamento"] - df["Abertura"]).abs() /
        (df["Máxima"] - df["Mínima"]).abs()
    ).round(2) * 100

    # Média móvel 6 períodos (6 meses ou 6 anos, dependendo do interval)
    df["Media6M_%Dif"] = df["%_Fech_Abert"].abs().rolling(window=6).mean().round(1)

    # Ordena da data mais recente para a mais antiga
    df = df.sort_index(ascending=False)

    # -------------------------------
    # LÓGICA DO AVISO (MÊS/ANO ANTERIOR)
    # -------------------------------
    hoje = datetime.today()

    if interval == "1mo":
        # ---- modo MENSAL: usa mês anterior ----
        mes_atual = hoje.month
        ano_atual = hoje.year
        mes_ant = 12 if mes_atual == 1 else mes_atual - 1
        ano_ant = ano_atual - 1 if mes_atual == 1 else ano_atual

        df_prev = df[(df.index.month == mes_ant) & (df.index.year == ano_ant)]
        periodo_txt = f"mês {mes_ant}/{ano_ant}"

    elif interval == "1y":
        # ---- modo ANUAL: usa ano anterior ----
        ano_atual = hoje.year
        ano_ant = ano_atual - 1

        df_prev = df[df.index.year == ano_ant]
        periodo_txt = f"ano {ano_ant}"

    else:
        df_prev = pd.DataFrame()
        periodo_txt = "período anterior"

    if not df_prev.empty:
        abert_minim = df_prev["%_Abert_Minim"].iloc[0]
        fech_abert = df_prev["%_Fech_Abert"].iloc[0]
        if fech_abert != 0:
            ratio = abert_minim / fech_abert
            if 0.33 < ratio < 0.5:
                st.info(
                    f"{ticker.upper()} {periodo_txt} → "
                    f"Ratio(Abert_Minim/Fech_Abert) = {ratio:.2f}"
                )

    return df


if st.button("Rodar varredura"):
    try:
        with open("IBOVDia_300925_sem_duplicadas.csv", "r", encoding="utf-8") as f:
            tickers = [line.strip() for line in f if line.strip()]
        tickers = [t if t.endswith(".SA") else t + ".SA" for t in tickers]
    except FileNotFoundError:
        st.error("Arquivo `IBOVDia_300925_sem_duplicadas.csv` não encontrado no diretório do app.")
        st.stop()

    resultados = []
    failed = []

    for t in tickers:
        df = baixar_dados(t, period, interval)
        if df is None or df.empty:
            failed.append(t)
            continue

        df_copy = df.copy()
        df_copy["Ticker"] = t
        resultados.append(df_copy)

    if resultados:
        df_final = pd.concat(resultados)
        df_final = df_final.reset_index().rename(columns={"index": "Data"})
        df_final = df_final.sort_values(by=["Ticker", "Data"], ascending=[True, False])
        df_final = df_final.set_index(["Ticker", "Data"])

        st.success("✅ Varredura concluída!")
        st.dataframe(df_final)

        if failed:
            st.warning(f"Não foi possível baixar dados para: {', '.join(failed)}")
    else:
        st.warning("Nenhum dado foi baixado.")
