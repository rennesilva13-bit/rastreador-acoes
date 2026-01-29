import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Configuração de Estilo e Layout
st.set_page_config(page_title="Rastreador Blindagem 3.0", layout="wide")

# CSS para melhorar o visual das tabelas
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 5px;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.0")
st.markdown("Análise de Valor (Graham), Renda (Bazin) e Saúde Financeira em tempo real.")

# --- 2. BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações de Análise")
tickers_input = st.sidebar.text_area(
    "Tickers (separe por vírgula):", 
    "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3, ITSA4"
)
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Yield Bazin Desejado (%)", 4, 12, 6)

# --- 3. MOTOR DE INTELIGÊNCIA ---

def get_data_v3(ticker):
    t_clean = ticker.strip().upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    
    try:
        stock = yf.Ticker(t_sa)
        info = stock.info
        if 'currentPrice' not in info: return None

        preco = info.get('currentPrice', 0)
        
        # Correção de Dividend Yield (Evita os 1200% de erro)
        dy_raw = info.get('dividendYield', 0) or 0
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
            "Liquidez_Corr": info.get('currentRatio', 0) or 0,
            "Setor": info.get('sector', 'N/A')
        }
    except: return None

# --- 4. EXECUÇÃO ---

if st.sidebar.button("🚀 Iniciar Rastreamento"):
    lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
    lista_dados = []
    
    bar_progresso = st.progress(0)
    for i, t in enumerate(lista):
        d = get_data_v3(t)
        if d: lista_dados.append(d)
        bar_progresso.progress((i + 1) / len(lista))
    
    if lista_dados:
        df = pd.DataFrame(lista_dados)
        
        # Cálculos Matemáticos
        df['Graham_Justo'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
        df['Margem_Graham'] = ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100
        df['Bazin_Teto'] = df['Div_Anual'] / (y_bazin_min / 100)
        
        # Score de Saúde (0-4)
        df['Score'] = (
            (df['ROE'] > 0.10).astype(int) + 
            (df['Margem_Liq'] > 0.10).astype(int) + 
            (df['Liquidez_Corr'] > 1.0).astype(int) + 
            (df['LPA'] > 0).astype(int)
        )
        
        def definir_status(row):
            if row['Margem_Graham'] >= m_graham_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
                return "💎 BLINDADA"
            elif row['Margem_Graham'] > 0 or row['Preço'] <= row['Bazin_Teto']:
                return "⚠️ Observar"
            return "🛑 Reprovada"

        df['STATUS'] = df.apply(definir_status, axis=1)
        df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])

        # --- INTERFACE DE RESULTADOS ---
        
        st.subheader("📊 Mapa de Oportunidades")
        fig = px.scatter(
            df, x="Margem_Graham", y="Score", text="Ação", color="STATUS",
            size="DY %", hover_data=['Preço', 'DY %'],
            labels={"Margem_Graham": "Margem de Segurança Graham (%)", "Score": "Saúde Financeira (0-4)"},
            color_discrete_map={"💎 BLINDADA": "#00cc66", "⚠️ Observar": "#ffcc00", "🛑 Reprovada": "#ff4d4d"}
        )
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Tabela de Dados Fundamentais")
        
        # Formatação para exibição
        df_view = df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS']].copy()
        
        st.dataframe(
            df_view.style.format({
                'Preço': 'R$ {:.2f}', 'DY %': '{:.2f}%',
                'Graham_Justo': 'R$ {:.2f}', 'Margem_Graham': '{:.1f}%',
                'Bazin_Teto': 'R$ {:.2f}'
            }).applymap(lambda x: 'background-color: #1e2630; color: #00cc66; font-weight: bold' if x == '💎 BLINDADA' else '', subset=['STATUS']),
            use_container_width=True
        )

        # Botão de Exportação
        st.divider()
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar Análise para Excel (CSV)",
            data=csv,
            file_name='carteira_blindada_3.0.csv',
            mime='text/csv',
        )
        
    else:
        st.error("Nenhum dado encontrado. Verifique os tickers.")
else:
    st.info("💡 Dica: Insira os seus tickers e clique em 'Rodar Análise' para ver o mapa de oportunidades.")
