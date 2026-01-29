import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. Configuração e Estilo
st.set_page_config(page_title="Rastreador Pro: Blindagem", layout="wide")

st.title("🛡️ Protocolo de Segurança: Versão 2.0")
st.markdown("Análise quantitativa baseada em **Graham**, **Bazin** e **Saúde Financeira**.")

# --- 2. BARRA LATERAL ---
st.sidebar.header("Configurações")
tickers_input = st.sidebar.text_area(
    "Tickers (separe por vírgula):", 
    "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3"
)
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Yield Bazin Desejado (%)", 4, 12, 6)

# --- 3. MOTOR DE CÁLCULO ---

def get_data_v2(ticker):
    t_clean = ticker.strip().upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    
    try:
        stock = yf.Ticker(t_sa)
        info = stock.info
        if 'currentPrice' not in info: return None

        preco = info.get('currentPrice', 0)
        
        # Correção Robusta de Dividend Yield
        dy_raw = info.get('dividendYield', 0) or 0
        # Se o Yahoo retornar 0.14 (14%), mantemos. Se retornar 14.0 (14%), ajustamos.
        dy_corrigido = dy_raw if dy_raw < 1.0 else dy_raw / 100
        
        return {
            "Ação": t_clean,
            "Preço": preco,
            "LPA": info.get('trailingEps', 0) or 0,
            "VPA": info.get('bookValue', 0) or 0,
            "DY %": dy_corrigido * 100,
            "Div_Anual": preco * dy_corrigido,
            "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0,
            "Liquidez_Corr": info.get('currentRatio', 0) or 0
        }
    except: return None

if st.sidebar.button("🚀 Rodar Análise"):
    lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
    lista_dados = []
    
    with st.spinner('Escaneando a B3...'):
        for t in lista:
            d = get_data_v2(t)
            if d: lista_dados.append(d)
    
    if lista_dados:
        df = pd.DataFrame(lista_dados)
        
        # Cálculos de Graham e Bazin
        # Preço Justo Graham = sqrt(22.5 * LPA * VPA)
        df['Graham_Justo'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
        df['Margem_Graham'] = ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100
        
        # Preço Teto Bazin = Dividendo / Taxa
        df['Bazin_Teto'] = df['Div_Anual'] / (y_bazin_min / 100)
        
        # Score de Saúde (0-4)
        df['Score'] = (
            (df['ROE'] > 0.10).astype(int) + 
            (df['Margem_Liq'] > 0.10).astype(int) + 
            (df['Liquidez_Corr'] > 1.0).astype(int) + 
            (df['LPA'] > 0).astype(int)
        )
        
        # Lógica de Status
        def definir_status(row):
            if row['Margem_Graham'] >= m_graham_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
                return "💎 BLINDADA"
            elif row['Margem_Graham'] > 0 or row['Preço'] <= row['Bazin_Teto']:
                return "⚠️ Observar"
            return "🛑 Reprovada"

        df['STATUS'] = df.apply(definir_status, axis=1)
        
        # Ordenação: Blindadas primeiro, depois por Margem Graham
        df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])

        # Formatação para Exibição
        df_display = df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS']].copy()
        
        # Aplicando cores
        def color_margem(val):
            color = 'green' if float(val.replace('%','')) > 0 else 'red'
            return f'color: {color}'

        st.dataframe(
            df_display.style.format({
                'Preço': 'R$ {:.2f}',
                'DY %': '{:.2f}%',
                'Graham_Justo': 'R$ {:.2f}',
                'Margem_Graham': '{:.1f}%',
                'Bazin_Teto': 'R$ {:.2f}'
            }).map(lambda x: 'background-color: #1e2630' if x == '💎 BLINDADA' else '', subset=['STATUS']),
            use_container_width=True
        )
        
        st.success("Análise Concluída! As empresas no topo são as que possuem maior margem e saúde financeira.")
    else:
        st.error("Erro ao coletar dados. Verifique sua conexão ou os tickers.")
