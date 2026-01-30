import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# 1. CONFIGURAÇÃO INICIAL
# ============================================================================
st.set_page_config(
    page_title="Blindagem Financeira Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado (Mantido original)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    
    /* Botões principais */
    div.stButton > button:first-child {
        background-color: #00cc66; color: white; border-radius: 8px;
        font-weight: bold; border: none; padding: 12px 24px;
        font-size: 16px; transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #00aa55; transform: scale(1.02);
    }
    
    /* Métricas e Cards */
    .metric-card {
        background-color: #1e2630; padding: 15px; border-radius: 10px;
        border-left: 4px solid #00cc66; margin: 5px;
    }
    .dataframe { background-color: #1e2630; border-radius: 10px; overflow: hidden; }
    .stProgress > div > div > div > div { background-color: #00cc66; }
    .streamlit-expanderHeader { background-color: #1e2630; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Blindagem Financeira Pro 4.5")
st.caption("Sistema avançado de análise fundamentalista - Yahoo Finance (Otimizado)")

# ============================================================================
# 2. SISTEMA DE FAVORITOS
# ============================================================================
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        try:
            with open(FAVORITOS_FILE, "r") as f:
                return f.read().strip()
        except:
            return "ITSA4, BBSE3, PETR4, VALE3, BBDC4"
    return "ITSA4, BBSE3, PETR4, VALE3, BBDC4"

def salvar_favoritos(texto):
    try:
        with open(FAVORITOS_FILE, "w") as f:
            f.write(texto)
        return True
    except:
        return False

# ============================================================================
# 3. SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Configurações")

lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area(
    "📋 Lista de Tickers:", 
    value=lista_inicial, 
    height=120,
    placeholder="Ex: PETR4, VALE3, ITSA4"
)

col_save, col_clear = st.sidebar.columns(2)
with col_save:
    if st.button("💾 Salvar Lista", use_container_width=True):
        if salvar_favoritos(tickers_input):
            st.sidebar.success("Salvo!")
with col_clear:
    if st.button("🗑️ Limpar", use_container_width=True):
        tickers_input = ""
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🎯 Critérios")

m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Yield Bazin Mínimo (%)", 4, 12, 6)

st.sidebar.divider()
st.sidebar.subheader("⚡ Performance")

usar_cache = st.sidebar.checkbox("Usar cache (15 min)", value=True)
delay_requisicoes = st.sidebar.slider("Delay (segundos)", 0.5, 5.0, 1.0)

if st.sidebar.button("🧹 Limpar Cache", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Cache limpo!")

# ============================================================================
# 4. DATA FETCHING (BLINDADO)
# ============================================================================

# Função auxiliar para criar sessão robusta
def get_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

@st.cache_data(ttl=900, show_spinner=False)
def get_yahoo_data_cached(ticker):
    """
    Função otimizada com cache nativo e tratamento de rate limit
    """
    ticker_clean = ticker.strip().upper().replace('.SA', '')
    yahoo_ticker = f"{ticker_clean}.SA"
    
    try:
        # Inicializa com sessão customizada
        session = get_session()
        acao = yf.Ticker(yahoo_ticker, session=session)
        
        # 1. Tenta pegar Preço (Estratégia Híbrida)
        preco_atual = 0.0
        try:
            # Tenta fast_info primeiro (muito mais rápido)
            if hasattr(acao, 'fast_info'):
                preco_atual = acao.fast_info['last_price']
            
            # Se falhar ou for None, tenta histórico
            if preco_atual is None or preco_atual <= 0:
                hist = acao.history(period="1d")
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]
        except:
            pass
            
        if preco_atual <= 0:
            return None, "Preço não disponível"

        # 2. Tenta pegar Fundamentos
        # O .info é o ponto crítico de bloqueio, usamos try/except isolado
        try:
            info = acao.info
        except Exception as e:
            return None, f"Erro ao obter fundamentos (Bloqueio ou API): {str(e)}"

        if not info:
             return None, "Informações fundamentais vazias"

        # 3. Processamento dos dados
        dy_val = info.get('dividendYield', 0)
        dividend_yield = (dy_val * 100) if dy_val and dy_val < 1 else (dy_val if dy_val else 0)

        dados = {
            "Ação": ticker_clean,
            "Preço": float(preco_atual),
            "DY %": float(dividend_yield),
            "LPA": float(info.get('trailingEps', 0) or 0),
            "VPA": float(info.get('bookValue', 0) or 0),
            "ROE": float(info.get('returnOnEquity', 0) or 0),
            "Margem_Liq": float(info.get('profitMargins', 0) or 0),
            "Liquidez_Corr": float(info.get('currentRatio', 0) or 0),
        }
        
        dados["Div_Anual"] = dados["Preço"] * (dados["DY %"] / 100)
        
        return dados, None

    except Exception as e:
        return None, f"Erro genérico: {str(e)}"

# Wrapper para respeitar a opção de "Não usar cache" da sidebar
def get_yahoo_data(ticker):
    if usar_cache:
        return get_yahoo_data_cached(ticker)
    else:
        st.cache_data.clear()
        return get_yahoo_data_cached(ticker)

# ============================================================================
# 5. CÁLCULOS
# ============================================================================
def calcular_preco_justo_graham(lpa, vpa):
    if lpa > 0 and vpa > 0:
        return np.sqrt(22.5 * lpa * vpa)
    return 0

def calcular_preco_teto_bazin(div_anual, yield_minimo):
    if div_anual > 0 and yield_minimo > 0:
        return div_anual / (yield_minimo / 100)
    return 0

def calcular_score_fundamentalista(dados):
    score = 0
    if dados.get('ROE', 0) > 0.08: score += 1
    if dados.get('Margem_Liq', 0) > 0.08: score += 1
    if dados.get('Liquidez_Corr', 0) > 0.8: score += 1
    if dados.get('LPA', 0) > 0: score += 1
    if dados.get('DY %', 0) > 4: score += 1
    return score

def classificar_acao(dados, margem_minima):
    if dados['Graham_Justo'] <= 0: return "🔍 Dados Insuf."
    
    margem = dados['Margem_Graham']
    teto_bazin = dados['Bazin_Teto']
    score = dados['Score']
    
    if (margem >= margem_minima and dados['Preço'] <= teto_bazin and score >= 3):
        return "💎 BLINDADA"
    elif margem > 10 or dados['Preço'] <= teto_bazin:
        return "⚠️ Observar"
    else:
        return "📊 Analisar"

# ============================================================================
# 6. INTERFACE
# ============================================================================
tab_analise, tab_simulador = st.tabs(["🔍 Análise de Oportunidades", "💰 Simulador de Renda"])

with tab_analise:
    st.header("🎯 Busca por Oportunidades")
    
    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        btn_analisar = st.button("🚀 Analisar Mercado", type="primary", use_container_width=True)
    
    if btn_analisar:
        tickers_lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers_lista:
            st.error("❌ Adicione tickers na lista lateral.")
        else:
            # Limite de segurança
            MAX_TICKERS = 15
            if len(tickers_lista) > MAX_TICKERS:
                st.warning(f"⚠️ Limitando a {MAX_TICKERS} tickers para evitar bloqueio do Yahoo.")
                tickers_lista = tickers_lista[:MAX_TICKERS]

            progress_bar = st.progress(0)
            status_text = st.empty()
            
            dados_coletados = []
            erros_coletados = []
            
            for i, ticker in enumerate(tickers_lista):
                status_text.text(f"📡 Analisando {ticker}...")
                
                # Pequeno delay para ser gentil com a API
                time.sleep(delay_requisicoes)
                
                dados, erro = get_yahoo_data(ticker)
                
                if dados:
                    dados_coletados.append(dados)
                elif erro:
                    erros_coletados.append(f"{ticker}: {erro}")
                
                progress_bar.progress((i + 1) / len(tickers_lista))
            
            status_text.empty()
            progress_bar.empty()
            
            if dados_coletados:
                df = pd.DataFrame(dados_coletados)
                
                # Cálculos
                df['Graham_Justo'] = df.apply(lambda x: calcular_preco_justo_graham(x['LPA'], x['VPA']), axis=1)
                df['Margem_Graham'] = df.apply(lambda x: ((x['Graham_Justo'] - x['Preço']) / x['Graham_Justo']) * 100 if x['Graham_Justo'] > 0 else 0, axis=1)
                df['Bazin_Teto'] = df.apply(lambda x: calcular_preco_teto_bazin(x['Div_Anual'], y_bazin_min), axis=1)
                df['Score'] = df.apply(calcular_score_fundamentalista, axis=1)
                df['Status'] = df.apply(lambda x: classificar_acao(x, m_graham_min), axis=1)
                
                df = df.sort_values(by=['Status', 'Margem_Graham'], ascending=[True, False])
                
                # KPIs
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Analisados", len(df))
                c2.metric("Oportunidades 💎", len(df[df['Status'] == '💎 BLINDADA']))
                c3.metric("DY Médio", f"{df['DY %'].mean():.2f}%")
                c4.metric("Margem Média", f"{df['Margem_Graham'].mean():.1f}%")
                
                # Gráfico
                if len(df[df['Graham_Justo'] > 0]) >= 2:
                    fig = px.scatter(
                        df[df['Graham_Justo'] > 0],
                        x='Margem_Graham', y='Score', size='DY %', color='Status',
                        hover_name='Ação',
                        color_discrete_map={'💎 BLINDADA': '#00cc66', '⚠️ Observar': '#ffcc00', '📊 Analisar': '#ff6b6b'}
                    )
                    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                    st.plotly_chart(fig, use_container_width=True)
                
                # Tabela Formatada
                df_show = df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 'Margem_Graham', 'Bazin_Teto', 'Score', 'Status']].copy()
                
                # Formatação visual
                for col in ['Preço', 'Graham_Justo', 'Bazin_Teto']:
                    df_show[col] = df_show[col].apply(lambda x: f"R$ {x:,.2f}")
                
                df_show['DY %'] = df_show['DY %'].apply(lambda x: f"{x:.2f}%")
                df_show['Margem_Graham'] = df_show['Margem_Graham'].apply(lambda x: f"{x:.2f}%")
                
                st.dataframe(df_show, use_container_width=True, height=400)
                
                # Exportação
                csv = df.to_csv(index=False, sep=';', decimal=',')
                st.download_button("📥 Baixar CSV", csv, "analise_pro.csv", "text/csv")
            
            if erros_coletados:
                with st.expander("⚠️ Log de Erros"):
                    for e in erros_coletados: st.warning(e)

with tab_simulador:
    st.header("💰 Simulador de Renda Passiva")
    
    col_val, col_est = st.columns(2)
    valor_aporte = col_val.number_input("Valor do Aporte (R$)", min_value=100.0, value=5000.0, step=500.0)
    estrategia = col_est.selectbox("Estratégia", ["Igualitária", "Por Dividend Yield"])
    
    tickers_disp = [t.strip() for t in tickers_input.split(',') if t.strip()]
    selecionadas = st.multiselect("Selecione as ações:", tickers_disp, default=tickers_disp[:5])
    
    if st.button("🎯 Calcular Projeção") and selecionadas:
        dados_sim = []
        for t in selecionadas:
            d, _ = get_yahoo_data(t)
            if d: dados_sim.append(d)
        
        if dados_sim:
            df_sim = pd.DataFrame(dados_sim)
            
            if estrategia == "Igualitária":
                df_sim['Peso %'] = 100 / len(df_sim)
            else:
                total_dy = df_sim['DY %'].sum()
                df_sim['Peso %'] = (df_sim['DY %'] / total_dy * 100) if total_dy > 0 else 100/len(df_sim)
            
            df_sim['Aporte'] = valor_aporte * (df_sim['Peso %'] / 100)
            df_sim['Qtd'] = (df_sim['Aporte'] / df_sim['Preço']).apply(np.floor)
            df_sim['Investido'] = df_sim['Qtd'] * df_sim['Preço']
            df_sim['Renda Anual'] = df_sim['Qtd'] * df_sim['Div_Anual']
            df_sim['Renda Mensal'] = df_sim['Renda Anual'] / 12
            
            total_invest = df_sim['Investido'].sum()
            renda_mensal = df_sim['Renda Mensal'].sum()
            yield_cart = (df_sim['Renda Anual'].sum() / total_invest * 100) if total_invest > 0 else 0
            
            st.success(f"## Renda Mensal Estimada: R$ {renda_mensal:,.2f}")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Investido", f"R$ {total_invest:,.2f}")
            m2.metric("Yield Carteira (a.a.)", f"{yield_cart:.2f}%")
            m3.metric("Sobra de Caixa", f"R$ {valor_aporte - total_invest:,.2f}")
            
            st.dataframe(df_sim[['Ação', 'Qtd', 'Investido', 'Renda Mensal', 'DY %']], use_container_width=True)

# Rodapé
st.divider()
st.caption(f"Blindagem Financeira Pro 4.5 • {datetime.now().year}")
