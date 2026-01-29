import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 3.5: Ações & FIIs", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { background-color: #00cc66; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.5")

# --- 2. SISTEMA DE FAVORITOS ---
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f: return f.read()
    return "SAPR11, BBSE3, BBAS3, PETR4, HGLG11, KNIP11, VISC11, TAEE11"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f: f.write(texto)
    st.sidebar.success("✅ Favoritos salvos!")

# --- 3. BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações")
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area("Lista de Tickers (Ações ou FIIs):", value=lista_inicial, height=150)

if st.sidebar.button("💾 Salvar Favoritos"):
    salvar_favoritos(tickers_input)

st.sidebar.divider()
m_graham_min = st.sidebar.slider("Margem Graham/Ações (%)", 0, 50, 20)
y_min_desejado = st.sidebar.slider("Yield Mínimo Desejado (%)", 4, 12, 8)

# --- 4. MOTOR DE INTELIGÊNCIA HÍBRIDO ---
def get_data_v3_5(ticker):
    t_clean = ticker.strip().upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    try:
        stock = yf.Ticker(t_sa)
        info = stock.info
        if 'currentPrice' not in info: return None
        
        preco = info.get('currentPrice', 0)
        dy_raw = info.get('dividendYield', 0) or info.get('trailingAnnualDividendYield', 0) or 0
        dy_corrigido = dy_raw if dy_raw < 1.0 else dy_raw / 100
        
        # Detectar se é FII (Fundos Imobiliários no Yahoo costumam ter quoteType 'EQUITY' mas industry específica)
        is_fii = False
        if "Real Estate" in info.get('industry', '') or "REIT" in info.get('quoteType', ''):
            is_fii = True
        elif t_clean.endswith('11') and t_clean not in ['SAPR11', 'KLBN11', 'TAEE11', 'BPAC11', 'SANB11']:
            is_fii = True

        return {
            "Ação": t_clean, "Preço": preco, "is_fii": is_fii,
            "LPA": info.get('trailingEps', 0) or 0, "VPA": info.get('bookValue', 0) or 0,
            "P_VP": info.get('priceToBook', 0) or 0, "DY %": dy_corrigido * 100,
            "Div_Anual": preco * dy_corrigido, "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0, "Liquidez_Corr": info.get('currentRatio', 0) or 0
        }
    except: return None

# --- 5. INTERFACE EM ABAS ---
tab1, tab2 = st.tabs(["🔍 Rastreador Híbrido", "💰 Gestor de Renda & Aportes"])

with tab1:
    if st.button("🚀 Analisar Mercado"):
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        lista_dados = []
        bar = st.progress(0)
        for i, t in enumerate(lista):
            d = get_data_v3_5(t)
            if d: lista_dados.append(d)
            bar.progress((i + 1) / len(lista))
        
        if lista_dados:
            df = pd.DataFrame(lista_dados)
            # Lógica Ações
            df['Graham_Justo'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
            df['Margem_Seg'] = np.where(df['is_fii'], (1 - df['P_VP']) * 100, ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100)
            
            # Score de Saúde (Adaptado para FIIs: foca em P/VP e DY)
            def calcular_score(row):
                if row['is_fii']:
                    s = 0
                    if row['P_VP'] <= 1.05: s += 2
                    if row['DY %'] >= y_min_desejado: s += 2
                    return s
                return ((row['ROE'] > 0.10).astype(int) + (row['Margem_Liq'] > 0.10).astype(int) + 
                        (row['Liquidez_Corr'] > 1.0).astype(int) + (row['LPA'] > 0).astype(int))

            df['Score'] = df.apply(calcular_score, axis=1)
            
            def definir_status(row):
                if row['is_fii']:
                    return "💎 BLINDADA" if row['P_VP'] <= 1.0 and row['DY %'] >= y_min_desejado else "⚠️ Observar"
                if row['Margem_Seg'] >= m_graham_min and row['Score'] >= 3:
                    return "💎 BLINDADA"
                return "⚠️ Observar" if row['Margem_Seg'] > 0 else "🛑 Reprovada"

            df['STATUS'] = df.apply(definir_status, axis=1)
            
            st.plotly_chart(px.scatter(df, x="Margem_Seg", y="Score", text="Ação", color="STATUS", size="DY %",
                             labels={"Margem_Seg": "Margem de Segurança / Desconto P/VP (%)"}), use_container_width=True)

            st.dataframe(df[['Ação', 'Preço', 'DY %', 'P_VP', 'Margem_Seg', 'Score', 'STATUS']].style.format({
                'Preço': 'R$ {:.2f}', 'DY %': '{:.2f}%', 'P_VP': '{:.2f}', 'Margem_Seg': '{:.1f}%'
            }), use_container_width=True)

with tab2:
    st.subheader("⚖️ Planejador de Renda Passiva (Ações & FIIs)")
    novo_aporte = st.number_input("Valor do Novo Aporte (R$):", min_value=0.0, value=100.0, step=100.0)
    
    if 'df_rebal' not in st.session_state:
        st.session_state.df_rebal = pd.DataFrame({'Ação': [t.strip().upper() for t in tickers_input.split(',') if t.strip()],
                                                 'Qtd Atual': [0] * len(tickers_input.split(',')),
                                                 'Peso Alvo (%)': [10.0] * len(tickers_input.split(','))})

    df_usuario = st.data_editor(st.session_state.df_rebal, use_container_width=True)
    
    if st.button("📊 Projetar Renda Híbrida"):
        lista_precos = []
        for t in df_usuario['Ação']:
            d = get_data_v3_5(t)
            if d: lista_precos.append({'Ação': t, 'Preço': d['Preço'], 'Div_Anual': d['Div_Anual']})
        
        df_p = pd.DataFrame(lista_precos)
        df_merged = pd.merge(df_usuario, df_p, on='Ação')
        df_merged['Valor Atual'] = df_merged['Qtd Atual'] * df_merged['Preço']
        total_novo = df_merged['Valor Atual'].sum() + novo_aporte
        
        df_merged['Comprar (Qtd)'] = ((total_novo * (df_merged['Peso Alvo (%)'] / 100) - df_merged['Valor Atual']) / df_merged['Preço']).apply(lambda x: max(0, np.floor(x)))
        df_merged['Renda Mensal'] = (df_merged['Qtd Atual'] + df_merged['Comprar (Qtd)']) * df_merged['Div_Anual'] / 12
        
        st.metric("Renda Mensal Média Projetada", f"R$ {df_merged['Renda Mensal'].sum():,.2f}")
        st.dataframe(df_merged[['Ação', 'Preço', 'Comprar (Qtd)', 'Renda Mensal']].style.format({'Preço': 'R$ {:.2f}', 'Renda Mensal': 'R$ {:.2f}'}))
