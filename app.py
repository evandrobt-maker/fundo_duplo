# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
from datetime import datetime
import streamlit as st

st.title("📊 Varredura de Ações da B3")

st.write(
    "Este app lê uma lista de tickers do arquivo **`IBOVDia_300925_sem_duplicadas.csv`**, "
    "baixa dados mensais do Yahoo Finance e mostra os resultados."
)

period = st.selectbox("Período para análise", ["1y", "2y", "5y"], index=1)

def baixar_mensal(ticker, period):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval="1mo",
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        st.error(f"[ERROR] Exception while downloading {ticker}: {e}")
        return None
    
    if df is None or df.empty:
        return None

    # garante índice em datetime limpo
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Data"

    # renomeia colunas
    df = df.rename(columns={
        "Open": "Abertura",
        "High": "Máxima",
        "Low": "Mínima",
        "Close": "Fechamento",
        "Volume": "Volume"
    })

    df["%_Fech_Abert"] = (df["Fechamento"] - df["Abertura"]).round(2)
    df["%_Max_Min"] = (df["Máxima"] - df["Mínima"]).round(2)
    df["%_FechAbert_vs_MaxMin"] = (
        (df["Fechamento"] - df["Abertura"]) /
        (df["Máxima"] - df["Mínima"]).abs()
    ).round(2) * 100
    df["Media6M_%Dif"] = df["%_Fech_Abert"].abs().rolling(window=6).mean().round(1)

    return df


if st.button("Rodar varredura"):
    # Lê os tickers do arquivo CSV
    try:
        with open("IBOVDia_300925_sem_duplicadas.csv", "r", encoding="utf-8") as f:
            tickers = [line.strip() for line in f if line.strip()]
        tickers = [t if t.endswith(".SA") else t + ".SA" for t in tickers]
    except FileNotFoundError:
        st.error("Arquivo `IBOVDia_300925_sem_duplicadas.csv` não encontrado no diretório do app.")
        st.stop()

    resultados = []
    for t in tickers:
        df = baixar_mensal(t, period)
        if df is not None:
            df["Ticker"] = t
            resultados.append(df)

            # aviso se mês anterior teve variação >85
            hoje = datetime.today()
            mes_atual = hoje.month
            ano_atual = hoje.year
            mes_ant = 12 if mes_atual == 1 else mes_atual - 1
            ano_ant = ano_atual - 1 if mes_atual == 1 else ano_atual
            df_mes_ant = df[(df.index.month == mes_ant) & (df.index.year == ano_ant)]
            if not df_mes_ant.empty:
                valor = df_mes_ant["%_FechAbert_vs_MaxMin"].iloc[0]
                if abs(valor) > 85:
                    st.warning(f"{t}: %_FechAbert_vs_MaxMin mês {mes_ant}/{ano_ant} = {valor}")

    if resultados:
        df_final = pd.concat(resultados)
        st.success("✅ Varredura concluída!")
        st.dataframe(df_final)
        st.download_button(
            "⬇️ Baixar CSV consolidado",
            data=df_final.to_csv().encode("utf-8"),
            file_name="mensal_todos.csv",
            mime="text/csv"
        )
    else:
        st.warning("Nenhum dado foi baixado.")