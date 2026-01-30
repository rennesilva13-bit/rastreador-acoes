import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import time
import random
from datetime import datetime
import warnings

# Configuração da Página
st.set_page_config(page_title="Blindagem Pro", layout="wide")
warnings.filterwarnings('ignore')

# --- 1. MÁSCARA DE NAVEGADOR (O SEGREDO DO DESBLOQUEIO) ---
def criar_sessao_camuflada():
    """Cria uma sessão que finge ser um navegador Chrome"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

# --- 2. FUNÇÃO DE COLETA DE DADOS ---
@st.cache_data(ttl=600, show_spinner=False)
def buscar_dados(ticker):
    """Busca dados usando a sessão camuflada"""
    ticker_clean = ticker.strip().upper().replace('.SA', '')
    yahoo_ticker = f"{ticker_clean}.SA"
    
    # Cria a sessão falsa
    session = criar_sessao_camuflada()
    
    try:
        # Passa a sessão "falsa" para o yfinance
        acao = yf.Ticker(yahoo_ticker, session=session)
        
        # Tenta pegar preço (Fast Info)
        preco = 0.0
        try:
            if hasattr(acao, 'fast_info'):
                preco = acao.fast_info.last_price
        except:
            pass
            
        # Se falhar, tenta histórico (método clássico)
        if preco is None or preco <= 0:
            hist = acao.history(period='1d')
            if not hist.empty:
                preco = hist['Close'].iloc[-1]
        
        if preco <= 0:
            return None, "Preço inacessível"

        # Tenta pegar Fundamentos (Info)
        info = acao.info
        
        if not info or 'regularMarketPrice' not in info:
            # Às vezes o Yahoo retorna info vazia se bloqueado, tentamos forçar erro
            if not info: raise ValueError("Info vazia")

        # Processar dados
        dy = info.get('dividendYield', 0)
        dy_percent = (dy * 100) if dy and dy < 1 else (dy if dy else 0)
        
        dados = {
            "Ação": ticker_clean,
            "Preço": float(preco),
            "DY %": float(dy_percent),
            "LPA": float(info.get('trailingEps', 0) or 0),
            "VPA": float(info.get('bookValue', 0) or 0),
            "ROE": float(info.get('returnOnEquity', 0) or 0),
            "Margem_Liq": float(info.get('profitMargins', 0) or 0),
            "Liquidez_Corr": float(info.get('currentRatio', 0) or 0),
        }
        
        # Calcular Graham e Bazin
        lpa = dados['LPA']
        vpa = dados['VPA']
        dados['Graham'] = np.sqrt(22.5 * lpa * vpa) if lpa > 0 and vpa > 0 else 0
        dados['Bazin'] = (dados['Preço'] * (dados['DY %']/100)) / 0.06 # Teto 6%
        
        return dados, None

    except Exception as e:
        return None, f"Erro: {str(e)[:100]}"

# --- 3. INTERFACE SIMPLIFICADA ---
st.title("🛡️ Blindagem Financeira (Modo Camuflado)")

# Sidebar
tickers_text = st.sidebar.text_area("Tickers", value="ITSA4, BBSE3, PETR4, VALE3, CMIG4", height=100)
tickers = [t.strip() for t in tickers_text.split(',') if t.strip()]

if st.button("🚀 Analisar Agora", type="primary"):
    if not tickers:
        st.error("Digite os tickers na barra lateral")
    else:
        results = []
        errors = []
        bar = st.progress(0)
        
        for i, t in enumerate(tickers):
            # Delay aleatório para parecer humano (IMPORTANTE)
            time.sleep(random.uniform(1.5, 3.0)) 
            
            d, e = buscar_dados(t)
            if d: results.append(d)
            else: errors.append(f"{t}: {e}")
            bar.progress((i+1)/len(tickers))
            
        bar.empty()
        
        if results:
            df = pd.DataFrame(results)
            
            # Formatação
            st.subheader("📊 Resultado da Análise")
            
            # Colorir o dataframe
            def highlight_row(row):
                if row['Preço'] < row['Graham'] and row['DY %'] > 6:
                    return ['background-color: #1e3d2f'] * len(row)
                return [''] * len(row)

            st.dataframe(
                df.style.apply(highlight_row, axis=1).format({
                    "Preço": "R$ {:.2f}",
                    "Graham": "R$ {:.2f}",
                    "Bazin": "R$ {:.2f}",
                    "DY %": "{:.2f}%",
                    "ROE": "{:.2f}",
                }), 
                use_container_width=True,
                height=400
            )
        
        if errors:
            with st.expander("Erros"):
                for err in errors: st.write(err)

st.caption("Nota: Se der erro, aguarde 15min para o Yahoo desbloquear seu IP.")
