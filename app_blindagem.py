import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# ===== CONFIGURAÇÃO DA PÁGINA =====
st.set_page_config(
    page_title="Análise Quantitativa B3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== ESTILOS PERSONALIZADOS =====
st.markdown("""
<style>
    /* Paleta moderna: Azul-profundo + tons neutros */
    :root {
        --primary: #1e3a8a;
        --secondary: #0f172a;
        --accent: #3b82f6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --light: #f8fafc;
        --dark: #0f172a;
        --gray: #64748b;
    }
    
    /* Fundo gradiente sutil */
    .stApp {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
    }
    
    /* Cards métricas */
    div[data-testid="stMetric"] {
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        transition: transform 0.3s ease;
        border-left: 4px solid var(--accent);
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.12);
    }
    
    /* Botões modernos */
    .stButton>button {
        background: var(--accent);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: #2563eb;
        transform: scale(1.03);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }
    
    /* Tabela estilizada */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }
    .dataframe th {
        background-color: var(--primary) !important;
        color: white !important;
        font-weight: 600 !important;
    }
    .dataframe td {
        background-color: white !important;
    }
    
    /* Sidebar elegante */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: white;
    }
    [data-testid="stSidebar"] .stSelectbox, 
    [data-testid="stSidebar"] .stNumberInput {
        background-color: rgba(30, 41, 59, 0.7);
        border-radius: 10px;
    }
    
    /* Badges coloridos para indicadores */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    .badge-roe {
        background: linear-gradient(90deg, #10b981, #059669);
        color: white;
    }
    .badge-dy {
        background: linear-gradient(90deg, #3b82f6, #2563eb);
        color: white;
    }
    .badge-pl {
        background: linear-gradient(90deg, #8b5cf6, #7c3aed);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ===== CACHE DE DADOS =====
@st.cache_data(ttl=900, show_spinner=False)
def get_yahoo_data_cached(ticker):
    """Função otimizada para coleta de dados da B3"""
    ticker_clean = ticker.strip().upper().replace('.SA', '')
    yahoo_ticker = f"{ticker_clean}.SA"
    
    try:
        acao = yf.Ticker(yahoo_ticker)
        
        # 1. Preço atual (estratégia híbrida)
        preco_atual = 0.0
        try:
            if hasattr(acao, 'fast_info'):
                last_price = acao.fast_info.get('last_price')
                if last_price and last_price > 0:
                    preco_atual = last_price
            
            if preco_atual <= 0:
                hist = acao.history(period="1d")
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]
        except:
            pass
            
        if preco_atual <= 0:
            return None, "Preço não disponível"

        # 2. Fundamentos
        try:
            info = acao.info
        except Exception as e:
            return None, f"Erro ao obter fundamentos: {str(e)}"

        if not info:
            return None, "Informações fundamentais vazias"

        # 3. Processamento
        dy_val = info.get('dividendYield', 0)
        dividend_yield = (dy_val * 100) if dy_val and dy_val < 1 else (dy_val if dy_val else 0)

        dados = {
            "Ação": ticker_clean,
            "Preço": float(preco_atual),
            "DY %": float(dividend_yield),
            "LPA": float(info.get('trailingEps', 0) or 0),
            "VPA": float(info.get('bookValue', 0) or 0),
            "ROE": float((info.get('returnOnEquity', 0) or 0) * 100),
            "Margem_Liq": float((info.get('profitMargins', 0) or 0) * 100),
            "Liquidez_Corr": float(info.get('currentRatio', 0) or 0),
            "P/L": float(info.get('trailingPE', 0) or 0),
            "P/VP": float(info.get('priceToBook', 0) or 0),
            "Volume": float(info.get('averageVolume', 0) or 0),
            "Setor": info.get('sector', 'N/A'),
        }
        
        dados["Div_Anual"] = dados["Preço"] * (dados["DY %"] / 100)
        
        return dados, None

    except Exception as e:
        return None, f"Erro genérico: {str(e)}"

# ===== SIDEBAR - CONTROLES =====
with st.sidebar:
    st.markdown("<h2 style='color: white; text-align: center; margin-bottom: 2rem;'>🔍 Filtros de Análise</h2>", unsafe_allow_html=True)
    
    # Setores pré-definidos da B3
    setores_b3 = [
        "Todos", "Bancos", "Varejo", "Energia", "Mineração", 
        "Telecomunicações", "Saúde", "Construção", "Tecnologia", "Outros"
    ]
    setor_selecionado = st.selectbox("Setor", setores_b3, index=0)
    
    st.markdown("<hr style='border: 1px solid #334155;'>", unsafe_allow_html=True)
    
    # Filtros quantitativos
    col1, col2 = st.columns(2)
    with col1:
        min_dy = st.number_input("DY Mínimo (%)", min_value=0.0, max_value=30.0, value=4.0, step=0.5)
        min_roe = st.number_input("ROE Mínimo (%)", min_value=0.0, max_value=50.0, value=12.0, step=1.0)
    with col2:
        max_pl = st.number_input("P/L Máximo", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
        max_pvp = st.number_input("P/VP Máximo", min_value=0.0, max_value=5.0, value=1.5, step=0.1)
    
    st.markdown("<hr style='border: 1px solid #334155;'>", unsafe_allow_html=True)
    
    # Lista de tickers
    tickers_default = """PETR4\nVALE3\nITUB4\nBBDC4\nB3SA3\nMGLU3\nWEGE3\nABEV3\nBBAS3\nRENT3"""
    tickers_input = st.text_area("Tickers B3 (um por linha)", value=tickers_default, height=200)
    tickers_lista = [t.strip().upper() for t in tickers_input.strip().split("\n") if t.strip()]
    
    st.markdown("<div style='text-align: center; margin-top: 2rem; color: #94a3b8; font-size: 0.85rem;'>📊 Dados atualizados em tempo real<br>⚡ Cache: 15 minutos</div>", unsafe_allow_html=True)

# ===== CABEÇALHO PRINCIPAL =====
st.markdown("""
<div style="text-align: center; padding: 2rem 0; margin-bottom: 2rem; background: linear-gradient(90deg, #1e3a8a 0%, #0f172a 100%); border-radius: 16px; color: white;">
    <h1 style="font-size: 2.8rem; margin-bottom: 0.5rem;">📈 Análise Quantitativa B3</h1>
    <p style="font-size: 1.2rem; opacity: 0.9; max-width: 800px; margin: 0 auto;">
        Identifique oportunidades de investimento com base em valuation e qualidade fundamental
    </p>
</div>
""", unsafe_allow_html=True)

# ===== BOTÃO DE ANÁLISE =====
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    analisar = st.button("🚀 Executar Análise", use_container_width=True)

if analisar and tickers_lista:
    with st.spinner("🔍 Coletando dados e calculando indicadores..."):
        # Barra de progresso elegante
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        dados_coletados = []
        total = len(tickers_lista)
        
        for idx, ticker in enumerate(tickers_lista):
            progress = (idx + 1) / total
            progress_bar.progress(progress)
            status_text.markdown(f"<div style='text-align: center; font-weight: 500; color: #3b82f6;'>Analisando {ticker} ({idx+1}/{total})</div>", unsafe_allow_html=True)
            
            dados, erro = get_yahoo_data_cached(ticker)
            if dados:
                dados_coletados.append(dados)
            time.sleep(0.3)  # Rate limiting suave
        
        progress_bar.empty()
        status_text.empty()
    
    if dados_coletados:
        df = pd.DataFrame(dados_coletados)
        
        # Aplicar filtros
        df_filtrado = df[
            (df["DY %"] >= min_dy) &
            (df["ROE"] >= min_roe) &
            (df["P/L"] <= max_pl) &
            (df["P/VP"] <= max_pvp)
        ]
        
        if setor_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Setor"] == setor_selecionado]
        
        # ===== RESUMO EXECUTIVO =====
        st.markdown("### 📊 Resumo da Análise")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Ações Analisadas", len(df))
        with col2:
            st.metric("Oportunidades", len(df_filtrado), delta=f"{len(df_filtrado)/len(df)*100:.1f}%")
        with col3:
            if not df_filtrado.empty:
                st.metric("DY Médio", f"{df_filtrado['DY %'].mean():.2f}%")
        with col4:
            if not df_filtrado.empty:
                st.metric("ROE Médio", f"{df_filtrado['ROE'].mean():.2f}%")
        
        # ===== TABELA DE RESULTADOS =====
        if not df_filtrado.empty:
            st.markdown("### 🏆 Oportunidades Identificadas")
            
            # Estilizar tabela
            df_display = df_filtrado[[
                "Ação", "Preço", "DY %", "ROE", "P/L", "P/VP", 
                "LPA", "VPA", "Margem_Liq", "Liquidez_Corr", "Setor"
            ]].sort_values("DY %", ascending=False).reset_index(drop=True)
            df_display.index = df_display.index + 1
            
            # Formatação condicional
            def color_roe(val):
                color = '#10b981' if val >= 15 else '#f59e0b' if val >= 10 else '#ef4444'
                return f'color: {color}; font-weight: 600;'
            
            styled_df = df_display.style\
                .format({
                    "Preço": "R${:.2f}",
                    "DY %": "{:.2f}%",
                    "ROE": "{:.2f}%",
                    "P/L": "{:.1f}",
                    "P/VP": "{:.2f}",
                    "LPA": "R${:.2f}",
                    "VPA": "R${:.2f}",
                    "Margem_Liq": "{:.2f}%",
                    "Liquidez_Corr": "{:.2f}"
                })\
                .applymap(color_roe, subset=["ROE"])\
                .background_gradient(subset=["DY %"], cmap="Blues", vmin=4, vmax=15)\
                .background_gradient(subset=["P/VP"], cmap="Reds_r", vmin=0.3, vmax=1.5)
            
            st.dataframe(styled_df, use_container_width=True)
            
            # ===== VISUALIZAÇÕES =====
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # Gráfico de dispersão ROE x DY
                fig_scatter = px.scatter(
                    df_filtrado,
                    x="DY %",
                    y="ROE",
                    size="Preço",
                    color="Setor",
                    hover_name="Ação",
                    title="ROE vs DY - Oportunidades por Setor",
                    labels={"ROE": "ROE (%)", "DY %": "Dividend Yield (%)"},
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_scatter.update_traces(marker=dict(line=dict(width=1.5, color='white')))
                fig_scatter.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            with col_chart2:
                # Barras horizontais - Top 10 DY
                top_dy = df_filtrado.nlargest(10, "DY %")
                fig_bar = go.Figure(go.Bar(
                    x=top_dy["DY %"],
                    y=top_dy["Ação"],
                    orientation='h',
                    marker=dict(
                        color=top_dy["DY %"],
                        colorscale='Blues',
                        line=dict(color='white', width=1.5)
                    ),
                    text=top_dy["DY %"].round(2),
                    textposition='auto',
                ))
                fig_bar.update_layout(
                    title="Top 10 Ações por Dividend Yield",
                    xaxis_title="DY (%)",
                    yaxis=dict(autorange="reversed"),
                    plot_bgcolor='white',
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=400
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # ===== DOWNLOAD =====
            st.markdown("### 💾 Exportar Dados")
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar análise completa (CSV)",
                data=csv,
                file_name=f"analise_b3_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("⚠️ Nenhuma ação atende aos critérios selecionados. Tente ajustar os filtros.")
    else:
        st.error("❌ Nenhum dado foi coletado. Verifique os tickers informados.")

# ===== RODAPÉ =====
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1.5rem; color: #64748b; font-size: 0.9rem; border-top: 1px solid #e2e8f0;">
    <p>💡 Este aplicativo utiliza dados do Yahoo Finance e é destinado exclusivamente para fins educacionais e de análise pessoal.</p>
    <p>Não constitui recomendação de investimento. Sempre faça sua própria análise antes de investir.</p>
    <p style="margin-top: 0.5rem; font-weight: 600; color: #3b82f6;">Desenvolvido com Streamlit • Atualizado em {data}</p>
</div>
""".format(data=datetime.now().strftime("%d/%m/%Y às %H:%M")), unsafe_allow_html=True)
