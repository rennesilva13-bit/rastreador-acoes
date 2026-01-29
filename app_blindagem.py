import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Rastreador Carteira Blindada", layout="wide")

st.title("🛡️ Rastreador de Ações: O Protocolo de Segurança")
st.markdown("""
Este app analisa ações da B3 baseando-se nos filtros de **Benjamin Graham** (Valor Intrínseco), 
**Décio Bazin** (Dividendos) e Indicadores de **Saúde Financeira** (Inspirado em Piotroski/Altman).
""")

# --- BARRA LATERAL (Entradas) ---
st.sidebar.header("Configurações")
tickers_input = st.sidebar.text_area(
    "Digite os Tickers (separados por vírgula):", 
    "BBSE3, PETR4, VALE3, WEGE3, ITSA4, SAPR11, TAEE11, EGIE3"
)
margem_graham = st.sidebar.slider("Margem de Segurança Graham (%)", 0, 50, 30)
yield_bazin = st.sidebar.slider("Yield Mínimo Bazin (%)", 4, 10, 6)

# --- FUNÇÕES DE CÁLCULO ---

def get_data(ticker):
    """Baixa dados fundamentais do Yahoo Finance"""
    if not ticker.endswith(".SA"):
        ticker += ".SA"
    
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Tratamento de erro se a ação não existir
    if 'currentPrice' not in info:
        return None

    # Dados Básicos
    price = info.get('currentPrice', 0)
    lpa = info.get('trailingEps', 0)
    vpa = info.get('bookValue', 0)
    
    # Dados para Bazin (Dividendos últimos 12 meses)
    # Tenta pegar o yield informado, se não, tenta calcular do histórico
    dy_percent = info.get('dividendYield', 0)
    if dy_percent is None: dy_percent = 0
    dividend_ttm = price * dy_percent

    # Dados de Saúde (Proxies para Piotroski/Altman)
    roe = info.get('returnOnEquity', 0)
    divida_liquida_ebitda = info.get('debtToEquity', 0) # Aproximação usada aqui
    margem_liquida = info.get('profitMargins', 0)
    current_ratio = info.get('currentRatio', 0) # Liquidez Corrente

    return {
        "Ticker": ticker.replace(".SA", ""),
        "Preço Atual": price,
        "LPA": lpa,
        "VPA": vpa,
        "Div. 12m": dividend_ttm,
        "ROE": roe,
        "Margem Líq.": margem_liquida,
        "Liquidez Corr.": current_ratio,
        "Setor": info.get('sector', 'N/A')
    }

def calcular_indicadores(df):
    resultados = []
    
    for index, row in df.iterrows():
        # 1. Graham (Raiz Quadrada de 22.5 * LPA * VPA)
        try:
            val_graham = (22.5 * row['LPA'] * row['VPA'])**0.5
        except:
            val_graham = 0
        
        if np.isnan(val_graham): val_graham = 0
        
        margem_seguranca_graham = ((val_graham - row['Preço Atual']) / val_graham) * 100 if val_graham > 0 else -999

        # 2. Bazin (Dividendo / 0.06)
        # Ajuste: O usuário define a taxa mínima (ex: 6%)
        taxa_bazin = yield_bazin / 100
        teto_bazin = row['Div. 12m'] / taxa_bazin if taxa_bazin > 0 else 0
        margem_seguranca_bazin = ((teto_bazin - row['Preço Atual']) / teto_bazin) * 100 if teto_bazin > 0 else -999

        # 3. Score de Saúde (Simplificação do Piotroski/Altman para API Gratuita)
        # Pontuamos de 0 a 4 baseado em métricas chave
        score_saude = 0
        if row['ROE'] > 0.10: score_saude += 1        # Rentabilidade ok
        if row['Margem Líq.'] > 0.10: score_saude += 1 # Eficiência ok
        if row['Liquidez Corr.'] > 1.0: score_saude += 1 # Solvência Curto Prazo (Altman light)
        if row['LPA'] > 0: score_saude += 1            # Lucrativa
        
        # Filtro de Aprovação
        passou_graham = margem_seguranca_graham >= margem_graham
        passou_bazin = margem_seguranca_bazin >= 0 # Bazin aceitamos preço justo ou abaixo
        passou_saude = score_saude >= 3 # Exige pelo menos 3 de 4 na saúde
        
        status = "🛑 Reprovada"
        if passou_graham and passou_bazin and passou_saude:
            status = "💎 BLINDADA"
        elif passou_graham or passou_bazin:
            status = "⚠️ Observar"

        resultados.append({
            "Ação": row['Ticker'],
            "Preço": f"R$ {row['Preço Atual']:.2f}",
            "Graham (Justo)": f"R$ {val_graham:.2f}",
            "Margem Graham": f"{margem_seguranca_graham:.1f}%",
            "Bazin (Teto)": f"R$ {teto_bazin:.2f}",
            "Score Saúde (0-4)": score_saude,
            "STATUS": status
        })
        
    return pd.DataFrame(resultados)

# --- EXECUÇÃO PRINCIPAL ---

if st.sidebar.button("🔍 Analisar Ações"):
    tickers_list = [t.strip().upper() for t in tickers_input.split(',')]
    
    with st.spinner('Coletando dados da B3... (Isso pode levar alguns segundos)'):
        dados_brutos = []
        for t in tickers_list:
            d = get_data(t)
            if d:
                dados_brutos.append(d)
        
        if dados_brutos:
            df_bruto = pd.DataFrame(dados_brutos)
            df_final = calcular_indicadores(df_bruto)
            
            # Exibição
            st.subheader(f"Resultado da Análise ({len(df_final)} ativos)")
            
            # Estilizando a tabela
            def color_status(val):
                color = 'red'
                if val == '💎 BLINDADA': color = 'green'
                elif val == '⚠️ Observar': color = 'orange'
                return f'color: {color}; font-weight: bold'

            st.dataframe(df_final.style.map(color_status, subset=['STATUS']), use_container_width=True)
            
            st.info("""
            **Legenda do Score de Saúde (0-4):**
            Baseado em ROE > 10%, Margem Líquida > 10%, Liquidez Corrente > 1.0 e Lucro Positivo.
            Serve como um filtro rápido de Qualidade/Risco similar ao Piotroski/Altman.
            """)
            
            # Aviso importante
            st.warning("**Atenção:** Bancos e Seguradoras (BBSE3, ITSA4) podem aparecer distorcidos no método de Graham ou Liquidez Corrente. Analise o setor financeiro separadamente.")
            
        else:
            st.error("Nenhum dado encontrado. Verifique os códigos das ações.")

else:
    st.write("👈 Configure os filtros na barra lateral e clique em 'Analisar Ações'.")