import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. Configuração da Página
st.set_page_config(page_title="Rastreador Carteira Blindada", layout="wide")

st.title("🛡️ Rastreador de Ações: O Protocolo de Segurança")
st.markdown("""
Este app busca automatizar sua análise. Ele calcula o **Preço Justo (Graham)**, 
o **Preço Teto (Bazin)** e um **Score de Saúde** baseado em rentabilidade e solvência.
""")

# --- 2. BARRA LATERAL (Entradas e Filtros) ---
st.sidebar.header("Configurações de Filtro")
# Tickers sugeridos baseados no seu histórico de interesse
tickers_input = st.sidebar.text_area(
    "Digite os Tickers (separados por vírgula):", 
    "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3"
)
margem_graham_req = st.sidebar.slider("Margem de Segurança Graham Mínima (%)", 0, 50, 30)
yield_bazin_req = st.sidebar.slider("Yield Mínimo Desejado Bazin (%)", 4, 12, 6)

# --- 3. FUNÇÕES DE COLETA E CÁLCULO ---

def get_data(ticker):
    """Busca dados em tempo real no Yahoo Finance"""
    ticker_sa = ticker.strip().upper()
    if not ticker_sa.endswith(".SA"):
        ticker_sa += ".SA"
    
    try:
        stock = yf.Ticker(ticker_sa)
        info = stock.info
        
        if 'currentPrice' not in info:
            return None

        price = info.get('currentPrice', 0)
        lpa = info.get('trailingEps', 0)
        vpa = info.get('bookValue', 0)
        
        # Coleta de Dividendos
        dy_decimal = info.get('dividendYield', 0)
        if dy_decimal is None: dy_decimal = 0
        
        return {
            "Ticker": ticker.strip().upper(),
            "Preço Atual": price,
            "LPA": lpa,
            "VPA": vpa,
            "DY %": dy_decimal * 100,
            "Div. Anual": price * dy_decimal,
            "ROE": info.get('returnOnEquity', 0),
            "Margem Líq.": info.get('profitMargins', 0),
            "Liquidez Corr.": info.get('currentRatio', 0)
        }
    except:
        return None

def processar_analise(lista_tickers):
    resultados = []
    
    for t in lista_tickers:
        dados = get_data(t)
        if dados:
            # Cálculo Graham
            if dados['LPA'] > 0 and dados['VPA'] > 0:
                v_graham = (22.5 * dados['LPA'] * dados['VPA'])**0.5
                m_graham = ((v_graham - dados['Preço Atual']) / v_graham) * 100
            else:
                v_graham = 0
                m_graham = -999

            # Cálculo Bazin
            taxa_bazin = yield_bazin_req / 100
            t_bazin = dados['Div. Anual'] / taxa_bazin if taxa_bazin > 0 else 0

            # Score de Saúde (0 a 4)
            score = 0
            if dados['ROE'] > 0.10: score += 1
            if dados['Margem Líq.'] > 0.10: score += 1
            if dados['Liquidez Corr.'] > 1.0: score += 1
            if dados['LPA'] > 0: score += 1
            
            # Lógica de Status
            if m_graham >= margem_graham_req and dados['Preço Atual'] <= t_bazin and score >= 3:
                status = "💎 BLINDADA"
            elif m_graham >= 0 or dados['Preço Atual'] <= t_bazin:
                status = "⚠️ Observar"
            else:
                status = "🛑 Reprovada"

            resultados.append({
                "Ação": dados['Ticker'],
                "Preço": dados['Preço Atual'],
                "DY %": dados['DY %'],
                "Graham (Justo)": v_graham,
                "Margem Graham": m_graham,
                "Bazin (Teto)": t_bazin,
                "Score Saúde": score,
                "STATUS": status
            })
    return pd.DataFrame(resultados)

# --- 4. EXECUÇÃO E INTERFACE ---

if st.sidebar.button("🔍 Rodar Protocolo de Segurança"):
    lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
    
    with st.spinner('Analisando fundamentos...'):
        df_final = processar_analise(lista)
        
        if not df_final.empty:
            st.subheader("Resultado do Rastreamento")
            
            # Formatação da Tabela
            df_view = df_final.copy()
            df_view['Preço'] = df_view['Preço'].map('R$ {:.2f}'.format)
            df_view['DY %'] = df_view['DY %'].map('{:.2f}%'.format)
            df_view['Graham (Justo)'] = df_view['Graham (Justo)'].map('R$ {:.2f}'.format)
            df_view['Margem Graham'] = df_view['Margem Graham'].map('{:.1f}%'.format)
            df_view['Bazin (Teto)'] = df_view['Bazin (Teto)'].map('R$ {:.2f}'.format)

            def highlight_status(val):
                if val == "💎 BLINDADA": return 'background-color: #d4edda; color: #155724'
                if val == "⚠️ Observar": return 'background-color: #fff3cd; color: #856404'
                return 'background-color: #f8d7da; color: #721c24'

            st.dataframe(df_view.style.applymap(highlight_status, subset=['STATUS']), use_container_width=True)
            
            # Dicas de Interpretação
            with st.expander("Clique para entender os critérios"):
                st.write("""
                - **Graham**: Preço Justo com base no lucro e patrimônio.
                - **Bazin**: Preço Teto para garantir o Yield mínimo selecionado.
                - **Score Saúde**: Analisa se a empresa é lucrativa (LPA > 0), rentável (ROE > 10%), 
                  eficiente (Margem > 10%) e solvente (Liquidez > 1.0).
                """)
        else:
            st.error("Nenhuma ação encontrada. Verifique os códigos digitados.")
else:
    st.info("Ajuste os filtros ao lado e clique em 'Rodar Protocolo de Segurança' para começar.")
