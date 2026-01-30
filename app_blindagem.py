import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 3.4: Projeção de Renda", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.4")

# --- 2. SISTEMA DE FAVORITOS ---
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return f.read()
    return "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f:
        f.write(texto)
    st.sidebar.success("✅ Favoritos salvos!")

# --- 3. BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações")
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area("Lista de Tickers:", value=lista_inicial, height=150)

if st.sidebar.button("💾 Salvar Favoritos"):
    salvar_favoritos(tickers_input)

st.sidebar.divider()
m_graham_min = st.sidebar.slider("Margem Graham (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Yield Bazin (%)", 4, 12, 6)

# --- 4. FUNÇÃO DE COLETA ---
def get_data_v3(ticker):
    t_clean = ticker.strip().upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    try:
        stock = yf.Ticker(t_sa)
        info = stock.info
        if 'currentPrice' not in info: return None
        preco = info.get('currentPrice', 0)
        dy_raw = info.get('dividendYield', 0) or 0
        dy_corrigido = dy_raw if dy_raw < 1.0 else dy_raw / 100
        return {
            "Ação": t_clean, "Preço": preco, "LPA": info.get('trailingEps', 0) or 0,
            "VPA": info.get('bookValue', 0) or 0, "DY %": dy_corrigido * 100,
            "Div_Anual": preco * dy_corrigido, "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0, "Liquidez_Corr": info.get('currentRatio', 0) or 0
        }
    except: return None

# --- 5. INTERFACE EM ABAS ---
tab1, tab2 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda & Aportes"])

with tab1:
    if st.button("🚀 Analisar Mercado"):
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        lista_dados = []
        bar = st.progress(0)
        for i, t in enumerate(lista):
            d = get_data_v3(t)
            if d: lista_dados.append(d)
            bar.progress((i + 1) / len(lista))
        
        if lista_dados:
            df = pd.DataFrame(lista_dados)
            df['Graham_Justo'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
            df['Margem_Graham'] = ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100
            df['Bazin_Teto'] = df['Div_Anual'] / (y_bazin_min / 100)
            df['Score'] = ((df['ROE'] > 0.10).astype(int) + (df['Margem_Liq'] > 0.10).astype(int) + 
                          (df['Liquidez_Corr'] > 1.0).astype(int) + (df['LPA'] > 0).astype(int))
            
            def definir_status(row):
                if row['Margem_Graham'] >= m_graham_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
                    return "💎 BLINDADA"
                return "⚠️ Observar" if row['Margem_Graham'] > 0 or row['Preço'] <= row['Bazin_Teto'] else "🛑 Reprovada"

            df['STATUS'] = df.apply(definir_status, axis=1)
            df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])

            st.plotly_chart(px.scatter(df, x="Margem_Graham", y="Score", text="Ação", color="STATUS", size="DY %",
                             color_discrete_map={"💎 BLINDADA": "#00cc66", "⚠️ Observar": "#ffcc00", "🛑 Reprovada": "#ff4d4d"}), use_container_width=True)

            st.dataframe(df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS']].style.format({
                'Preço': 'R$ {:.2f}', 'DY %': '{:.2f}%', 'Graham_Justo': 'R$ {:.2f}', 'Margem_Graham': '{:.1f}%', 'Bazin_Teto': 'R$ {:.2f}'
            }), use_container_width=True)

with tab2:
    st.subheader("⚖️ Planejador de Renda Passiva")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        novo_aporte = st.number_input("Valor do Novo Aporte (R$):", min_value=0.0, value=100.0, step=100.0)
    
    lista_rebal = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    
    if 'df_rebal' not in st.session_state:
        st.session_state.df_rebal = pd.DataFrame({
            'Ação': lista_rebal,
            'Qtd Atual': [0] * len(lista_rebal),
            'Peso Alvo (%)': [round(100/len(lista_rebal), 1)] * len(lista_rebal)
        })

    df_usuario = st.data_editor(st.session_state.df_rebal, use_container_width=True, num_rows="dynamic")
    
    if st.button("📊 Projetar Renda e Rebalancear"):
        with st.spinner('Calculando projeções...'):
            lista_dados_rebal = []
            for t in df_usuario['Ação']:
                d = get_data_v3(t)
                if d: lista_dados_rebal.append({'Ação': t, 'Preço': d['Preço'], 'Div_Anual': d['Div_Anual']})
            
            if lista_dados_rebal:
                df_precos = pd.DataFrame(lista_dados_rebal)
                df_merged = pd.merge(df_usuario, df_precos, on='Ação')
                
                df_merged['Valor Atual'] = df_merged['Qtd Atual'] * df_merged['Preço']
                patrimonio_existente = df_merged['Valor Atual'].sum()
                patrimonio_total_novo = patrimonio_existente + novo_aporte
                
                df_merged['Valor Alvo'] = patrimonio_total_novo * (df_merged['Peso Alvo (%)'] / 100)
                df_merged['Diferença (R$)'] = df_merged['Valor Alvo'] - df_merged['Valor Atual']
                
                # Cálculo de Compra e Renda
                df_merged['Comprar (Qtd)'] = (df_merged['Diferença (R$)'] / df_merged['Preço']).apply(lambda x: max(0, np.floor(x)))
                df_merged['Qtd Final'] = df_merged['Qtd Atual'] + df_merged['Comprar (Qtd)']
                df_merged['Renda Anual Proj.'] = df_merged['Qtd Final'] * df_merged['Div_Anual']
                df_merged['Renda Mensal Média'] = df_merged['Renda Anual Proj.'] / 12
                
                # Métricas de Resumo
                total_mensal = df_merged['Renda Mensal Média'].sum()
                total_anual = df_merged['Renda Anual Proj.'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Patrimônio Total", f"R$ {patrimonio_total_novo:,.2f}")
                c2.metric("Renda Mensal Média", f"R$ {total_mensal:,.2f}")
                c3.metric("Renda Anual Estimada", f"R$ {total_anual:,.2f}")
                
                st.write("### Sugestão de Alocação e Projeção Individual")
                st.dataframe(df_merged[['Ação', 'Preço', 'Qtd Final', 'Peso Alvo (%)', 'Comprar (Qtd)', 'Renda Mensal Média']].style.format({
                    'Preço': 'R$ {:.2f}', 'Peso Alvo (%)': '{:.1f}%', 'Renda Mensal Média': 'R$ {:.2f}'
                }).highlight_max(subset=['Renda Mensal Média'], color='#1e2630'), use_container_width=True)
                
                st.info(f"💡 Com este aporte e configuração, sua carteira passará a render, em média, **R$ {total_mensal:.2f} por mês**.")
