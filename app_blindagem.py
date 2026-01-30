import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
import time
import ta  # Biblioteca para análise técnica

# ============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="B3 Screener Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# CSS personalizado
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        padding: 0px 20px;
    }
    
    /* Títulos */
    h1, h2, h3, h4 {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards de métricas */
    .metric-card {
        background: linear-gradient(135deg, #1e2630 0%, #2a3340 100%);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #00cc66;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        margin: 8px 0;
    }
    
    /* Badges */
    .badge-buy {
        background-color: rgba(0, 204, 102, 0.15);
        color: #00ff88;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        border: 1px solid #00cc66;
        font-size: 12px;
    }
    
    .badge-sell {
        background-color: rgba(255, 75, 75, 0.15);
        color: #ff6b6b;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        border: 1px solid #ff4d4d;
        font-size: 12px;
    }
    
    .badge-neutral {
        background-color: rgba(255, 204, 0, 0.15);
        color: #ffcc00;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        border: 1px solid #ffcc00;
        font-size: 12px;
    }
    
    /* Botões */
    .stButton button {
        background: linear-gradient(135deg, #00cc66 0%, #00aa55 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 204, 102, 0.3);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #1e2630;
        padding: 8px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #2a3340;
        border-radius: 8px;
        padding: 12px 24px;
        color: #cccccc;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #00cc66;
        color: white;
    }
    
    /* Dataframes */
    .dataframe {
        background-color: #1e2630;
        border-radius: 10px;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #2a3340;
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 2. TÍTULO E DESCRIÇÃO
# ============================================================================
col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("📊 B3 Screener Pro")
    st.markdown("""
    <div style='color: #888; margin-bottom: 30px;'>
    Sistema avançado de filtragem e análise de ações da B3 com mais de 20 indicadores fundamentais e técnicos
    </div>
    """, unsafe_allow_html=True)
with col_logo:
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: 48px;'>🚀</div>
        <div style='color: #00cc66; font-weight: bold;'>v1.0</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 3. LISTA DE AÇÕES DISPONÍVEIS
# ============================================================================
# Lista completa de ações brasileiras (pode ser expandida)
TICKERS_B3 = {
    "PETR4": "Petrobras PN",
    "VALE3": "Vale ON",
    "ITUB4": "Itaú Unibanco PN",
    "BBDC4": "Bradesco PN",
    "BBAS3": "Banco do Brasil ON",
    "ITSA4": "Itaúsa PN",
    "WEGE3": "WEG ON",
    "ABEV3": "Ambev ON",
    "MGLU3": "Magazine Luiza ON",
    "B3SA3": "B3 ON",
    "RENT3": "Localiza ON",
    "GGBR4": "Gerdau PN",
    "ELET3": "Eletrobras ON",
    "SUZB3": "Suzano ON",
    "RADL3": "Raia Drogasil ON",
    "BPAC11": "BTG Pactual",
    "LREN3": "Lojas Renner ON",
    "HAPV3": "Hapvida ON",
    "VBBR3": "Vibra ON",
    "TOTS3": "Totvs ON",
    "BBSE3": "BB Seguridade ON",
    "EQTL3": "Equatorial ON",
    "CSAN3": "Cosan ON",
    "UGPA3": "Ultrapar ON",
    "SBSP3": "Sabesp ON",
    "RAIL3": "Rumo ON",
    "PRIO3": "PetroRio ON",
    "KLBN11": "Klabin",
    "CMIG4": "CEMIG PN",
    "BRFS3": "BRF ON",
    "TAEE11": "Taesa",
    "HYPE3": "Hypera ON",
    "CYRE3": "Cyrela ON",
    "BRKM5": "Braskem PN",
    "GOAU4": "Gerdau PN",
    "MULT3": "Multiplan ON",
    "EGIE3": "ENGIE Brasil ON",
    "CSNA3": "CSN ON",
    "EMBR3": "Embraer ON",
    "ASAI3": "Assaí ON",
    "MRFG3": "Marfrig ON",
    "CRFB3": "Carrefour ON",
    "AMER3": "Americanas ON",
    "VIVT3": "Telefônica Brasil ON",
    "TIMS3": "TIM ON",
    "MRVE3": "MRV ON",
    "YDUQ3": "YDUQS ON",
    "PCAR3": "GPA ON",
    "GOLL4": "Gol PN",
    "AZUL4": "Azul PN",
    "CVCB3": "CVC ON",
    "NTCO3": "Natura ON",
    "QUAL3": "Qualicorp ON",
    "LWSA3": "Locaweb ON",
    "DXCO3": "Dexco ON",
    "EZTC3": "EZTEC ON",
    "ARZZ3": "Arezzo ON",
    "MOVI3": "Movida ON",
    "BRML3": "BR Malls ON",
    "ENEV3": "Eneva ON",
    "CPLE6": "Copel PNB",
    "ELET6": "Eletrobras PNB",
    "SANB11": "Santander",
    "BBDC3": "Bradesco ON",
    "PETR3": "Petrobras ON",
    "VALE5": "Vale PNA",
    "ITUB3": "Itaú Unibanco ON"
}

# ============================================================================
# 4. SIDEBAR - FILTROS E CONFIGURAÇÕES
# ============================================================================
st.sidebar.header("⚙️ Configurações do Screener")

# Seletor de tickers
st.sidebar.subheader("📋 Seleção de Ações")
ticker_selection = st.sidebar.multiselect(
    "Selecione as ações para análise:",
    options=list(TICKERS_B3.keys()),
    default=["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3"],
    format_func=lambda x: f"{x} - {TICKERS_B3[x]}",
    help="Escolha até 15 ações para análise simultânea"
)

# Limitar a 15 tickers para performance
if len(ticker_selection) > 15:
    st.sidebar.warning(f"⚠️ Limitando a 15 ações para melhor performance")
    ticker_selection = ticker_selection[:15]

st.sidebar.divider()

# FILTROS FUNDAMENTAIS
st.sidebar.subheader("📊 Filtros Fundamentais")

col_f1, col_f2 = st.sidebar.columns(2)
with col_f1:
    pl_min = st.number_input("P/L Mín:", value=0.0, step=1.0)
    pl_max = st.number_input("P/L Máx:", value=50.0, step=1.0)
    roe_min = st.number_input("ROE Mín (%):", value=0.0, step=1.0)
    margem_min = st.number_input("Margem Mín (%):", value=0.0, step=1.0)

with col_f2:
    pvp_min = st.number_input("P/VP Mín:", value=0.0, step=0.1)
    pvp_max = st.number_input("P/VP Máx:", value=5.0, step=0.1)
    dy_min = st.number_input("DY Mín (%):", value=0.0, step=0.5)
    div_pl_max = st.number_input("Dív/PL Máx:", value=5.0, step=0.5)

# FILTROS TÉCNICOS
st.sidebar.subheader("📈 Filtros Técnicos")

col_t1, col_t2 = st.sidebar.columns(2)
with col_t1:
    rsi_min = st.slider("RSI Mín:", 0, 100, 30)
    rsi_max = st.slider("RSI Máx:", 0, 100, 70)
    volume_min = st.number_input("Volume Mín (M):", value=1.0, step=1.0)

with col_t2:
    acima_media_20 = st.checkbox("Acima Média 20d")
    abaixo_media_50 = st.checkbox("Abaixo Média 50d")
    tendencia_alta = st.checkbox("Tendência de Alta")

st.sidebar.divider()

# CONFIGURAÇÕES AVANÇADAS
st.sidebar.subheader("⚡ Configurações Avançadas")

periodo_analise = st.sidebar.selectbox(
    "Período de Análise:",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"],
    index=2
)

intervalo_analise = st.sidebar.selectbox(
    "Intervalo:",
    ["1d", "1h", "30m", "15m", "5m", "1m"],
    index=0
)

usar_cache = st.sidebar.checkbox("Usar Cache", value=True)
delay_requisicoes = st.sidebar.slider("Delay (segundos):", 0.5, 5.0, 1.5, 0.5)

# Botão para executar análise
st.sidebar.divider()
btn_analisar = st.sidebar.button("🚀 Executar Screener", type="primary", use_container_width=True)

# ============================================================================
# 5. FUNÇÕES DE ANÁLISE
# ============================================================================
class B3Screener:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 600  # 10 minutos
        
    def get_cached_data(self, ticker):
        """Recupera dados do cache"""
        if not usar_cache or ticker not in self.cache:
            return None
        
        cache_time, data = self.cache[ticker]
        if time.time() - cache_time < self.cache_duration:
            return data
        else:
            del self.cache[ticker]
            return None
    
    def set_cached_data(self, ticker, data):
        """Armazena dados no cache"""
        if usar_cache:
            self.cache[ticker] = (time.time(), data)
    
    def get_fundamental_data(self, ticker):
        """Obtém dados fundamentais do Yahoo Finance"""
        cached = self.get_cached_data(f"fund_{ticker}")
        if cached:
            return cached
        
        try:
            stock = yf.Ticker(f"{ticker}.SA")
            time.sleep(delay_requisicoes)
            
            info = stock.info
            
            # Dados fundamentais
            data = {
                "Ticker": ticker,
                "Empresa": TICKERS_B3.get(ticker, "N/A"),
                "Preço": info.get('currentPrice', 0),
                "Variação %": info.get('regularMarketChangePercent', 0),
                "DY %": (info.get('dividendYield', 0) or 0) * 100,
                "P/L": info.get('trailingPE', 0),
                "P/VP": info.get('priceToBook', 0),
                "ROE %": (info.get('returnOnEquity', 0) or 0) * 100,
                "Margem %": (info.get('profitMargins', 0) or 0) * 100,
                "Dív/PL": info.get('debtToEquity', 0),
                "EV/EBITDA": info.get('enterpriseToEbitda', 0),
                "Cresc. Receita %": info.get('revenueGrowth', 0) * 100,
                "Beta": info.get('beta', 0),
                "Volume Médio": info.get('averageVolume', 0) / 1_000_000,  # Em milhões
                "Market Cap (B)": (info.get('marketCap', 0) or 0) / 1_000_000_000,  # Em bilhões
                "LPA": info.get('trailingEps', 0),
                "VPA": info.get('bookValue', 0),
            }
            
            self.set_cached_data(f"fund_{ticker}", data)
            return data
            
        except Exception as e:
            print(f"Erro ao buscar {ticker}: {str(e)}")
            return None
    
    def get_technical_data(self, ticker, period="1mo", interval="1d"):
        """Obtém dados técnicos e calcula indicadores"""
        cache_key = f"tech_{ticker}_{period}_{interval}"
        cached = self.get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            stock = yf.Ticker(f"{ticker}.SA")
            time.sleep(delay_requisicoes)
            
            # Buscar dados históricos
            hist = stock.history(period=period, interval=interval)
            
            if hist.empty or len(hist) < 20:
                return None
            
            # Calcular indicadores técnicos
            hist['RSI'] = ta.momentum.RSIIndicator(hist['Close'], window=14).rsi()
            hist['MACD'] = ta.trend.MACD(hist['Close']).macd()
            hist['MACD_Signal'] = ta.trend.MACD(hist['Close']).macd_signal()
            hist['BB_Upper'] = ta.volatility.BollingerBands(hist['Close']).bollinger_hband()
            hist['BB_Lower'] = ta.volatility.BollingerBands(hist['Close']).bollinger_lband()
            
            # Médias móveis
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA50'] = hist['Close'].rolling(window=50).mean()
            hist['MA200'] = hist['Close'].rolling(window=200).mean()
            
            # Volume
            hist['Volume_SMA'] = hist['Volume'].rolling(window=20).mean()
            
            # Últimos valores
            last_close = hist['Close'].iloc[-1]
            last_rsi = hist['RSI'].iloc[-1] if not pd.isna(hist['RSI'].iloc[-1]) else 50
            last_volume = hist['Volume'].iloc[-1] / 1_000_000  # Em milhões
            
            # Sinais técnicos
            sinal_rsi = "COMPRAR" if last_rsi < 30 else "VENDER" if last_rsi > 70 else "NEUTRO"
            acima_ma20 = last_close > hist['MA20'].iloc[-1]
            acima_ma50 = last_close > hist['MA50'].iloc[-1]
            
            # Tendência
            if len(hist) >= 20:
                recent_trend = hist['Close'].iloc[-5:].mean() > hist['Close'].iloc[-20:-15].mean()
            else:
                recent_trend = False
            
            tech_data = {
                "Ticker": ticker,
                "Último Preço": last_close,
                "RSI": last_rsi,
                "Sinal RSI": sinal_rsi,
                "Volume (M)": last_volume,
                "Acima MA20": acima_ma20,
                "Acima MA50": acima_ma50,
                "Tendência": "ALTA" if recent_trend else "BAIXA",
                "Volatilidade %": hist['Close'].pct_change().std() * 100,
                "Máxima 52s": hist['Close'].max(),
                "Mínima 52s": hist['Close'].min(),
                "Dist. Mínima %": ((last_close - hist['Close'].min()) / hist['Close'].min()) * 100,
                "Dist. Máxima %": ((hist['Close'].max() - last_close) / last_close) * 100,
                "Histórico": hist
            }
            
            self.set_cached_data(cache_key, tech_data)
            return tech_data
            
        except Exception as e:
            print(f"Erro técnico {ticker}: {str(e)}")
            return None
    
    def calculate_composite_score(self, fund_data, tech_data):
        """Calcula score composto baseado em múltiplos fatores"""
        if not fund_data or not tech_data:
            return 0
        
        score = 50  # Score base
        
        # Fatores fundamentais (peso 60%)
        factors_fund = {
            "ROE": min(fund_data.get("ROE %", 0) / 20, 10),  # ROE ideal ~20%
            "DY": min(fund_data.get("DY %", 0) / 10, 10),    # DY ideal ~10%
            "P/L": max(0, 10 - abs(fund_data.get("P/L", 20) - 15) / 3),  # P/L ideal ~15
            "P/VP": max(0, 10 - abs(fund_data.get("P/VP", 1.5) - 1) / 0.2),  # P/VP ideal ~1
            "Margem": min(fund_data.get("Margem %", 0) / 15, 10),  # Margem ideal ~15%
        }
        
        # Fatores técnicos (peso 40%)
        factors_tech = {
            "RSI": 10 if 30 <= tech_data.get("RSI", 50) <= 70 else 5,
            "Tendência": 10 if tech_data.get("Tendência") == "ALTA" else 5,
            "Volume": min(tech_data.get("Volume (M)", 0) / 10, 10),
            "Posição Médias": 10 if tech_data.get("Acima MA20") and tech_data.get("Acima MA50") else 5,
        }
        
        # Calcular score ponderado
        fund_score = sum(factors_fund.values()) / len(factors_fund) * 0.6
        tech_score = sum(factors_tech.values()) / len(factors_tech) * 0.4
        
        score = fund_score * 60 + tech_score * 40
        
        return min(100, max(0, score))
    
    def apply_filters(self, df_fund, df_tech):
        """Aplica filtros selecionados pelo usuário"""
        if df_fund.empty or df_tech.empty:
            return pd.DataFrame()
        
        # Merge dos dados
        df_merged = pd.merge(df_fund, df_tech, on="Ticker", suffixes=('', '_tech'))
        
        # Aplicar filtros fundamentais
        mask = (
            (df_merged['P/L'].between(pl_min, pl_max)) &
            (df_merged['P/VP'].between(pvp_min, pvp_max)) &
            (df_merged['ROE %'] >= roe_min) &
            (df_merged['Margem %'] >= margem_min) &
            (df_merged['DY %'] >= dy_min) &
            (df_merged['Dív/PL'] <= div_pl_max)
        )
        
        # Aplicar filtros técnicos
        if rsi_min > 0 or rsi_max < 100:
            mask = mask & (df_merged['RSI'].between(rsi_min, rsi_max))
        
        if volume_min > 0:
            mask = mask & (df_merged['Volume (M)'] >= volume_min)
        
        if acima_media_20:
            mask = mask & (df_merged['Acima MA20'] == True)
        
        if abaixo_media_50:
            mask = mask & (df_merged['Acima MA50'] == False)
        
        if tendencia_alta:
            mask = mask & (df_merged['Tendência'] == "ALTA")
        
        return df_merged[mask].copy()

# ============================================================================
# 6. INTERFACE PRINCIPAL
# ============================================================================
# Inicializar screener
screener = B3Screener()

# Abas principais
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", 
    "🔍 Resultados Filtrados", 
    "📈 Análise Técnica", 
    "🎯 Ranking Completo"
])

# Executar análise quando o botão for clicado
if btn_analisar and ticker_selection:
    with st.spinner("🔄 Coletando e analisando dados..."):
        
        # Coletar dados fundamentais
        fund_data_list = []
        tech_data_list = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ticker in enumerate(ticker_selection):
            status_text.text(f"Analisando {ticker}... ({i+1}/{len(ticker_selection)})")
            
            # Dados fundamentais
            fund_data = screener.get_fundamental_data(ticker)
            if fund_data:
                fund_data_list.append(fund_data)
            
            # Dados técnicos
            tech_data = screener.get_technical_data(ticker, periodo_analise, intervalo_analise)
            if tech_data:
                tech_data_list.append(tech_data)
            
            progress_bar.progress((i + 1) / len(ticker_selection))
        
        status_text.empty()
        progress_bar.empty()
        
        if fund_data_list and tech_data_list:
            df_fund = pd.DataFrame(fund_data_list)
            df_tech = pd.DataFrame(tech_data_list)
            
            # Calcular score composto
            scores = []
            for idx, row_fund in df_fund.iterrows():
                ticker = row_fund['Ticker']
                tech_row = df_tech[df_tech['Ticker'] == ticker]
                if not tech_row.empty:
                    score = screener.calculate_composite_score(
                        row_fund.to_dict(), 
                        tech_row.iloc[0].to_dict()
                    )
                else:
                    score = 0
                scores.append(score)
            
            df_fund['Score'] = scores
            
            # Aplicar filtros
            df_filtered = screener.apply_filters(df_fund, df_tech)
            
            # Salvar dados na sessão
            st.session_state.df_fund = df_fund
            st.session_state.df_tech = df_tech
            st.session_state.df_filtered = df_filtered
            
            st.success(f"✅ Análise concluída! {len(df_filtered)} ações passaram nos filtros.")

# ============================================================================
# 7. ABA 1 - DASHBOARD
# ============================================================================
with tab1:
    st.header("📊 Dashboard de Mercado")
    
    if 'df_fund' in st.session_state:
        df_fund = st.session_state.df_fund
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_pl = df_fund['P/L'].mean()
            st.metric("P/L Médio", f"{avg_pl:.1f}", 
                     delta="Baixo" if avg_pl < 15 else "Alto")
        
        with col2:
            avg_dy = df_fund['DY %'].mean()
            st.metric("DY Médio", f"{avg_dy:.1f}%", 
                     delta="Alto" if avg_dy > 6 else "Baixo")
        
        with col3:
            avg_roe = df_fund['ROE %'].mean()
            st.metric("ROE Médio", f"{avg_roe:.1f}%", 
                     delta="Bom" if avg_roe > 15 else "Ruim")
        
        with col4:
            total_mkt_cap = df_fund['Market Cap (B)'].sum()
            st.metric("Market Cap Total", f"R$ {total_mkt_cap:.1f}B")
        
        # Gráficos
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Gráfico de P/L vs P/VP
            fig1 = px.scatter(
                df_fund,
                x='P/L',
                y='P/VP',
                size='Market Cap (B)',
                color='Score',
                hover_name='Ticker',
                title='P/L vs P/VP (Tamanho = Market Cap)',
                color_continuous_scale='RdYlGn'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_chart2:
            # Gráfico de ROE vs DY
            fig2 = px.scatter(
                df_fund,
                x='ROE %',
                y='DY %',
                size='Preço',
                color='Score',
                hover_name='Ticker',
                title='ROE vs Dividend Yield (Tamanho = Preço)',
                color_continuous_scale='RdYlGn'
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Heatmap de correlações
        st.subheader("🔥 Heatmap de Correlações")
        
        # Selecionar colunas numéricas para correlação
        numeric_cols = ['Preço', 'DY %', 'P/L', 'P/VP', 'ROE %', 'Margem %', 
                       'Dív/PL', 'EV/EBITDA', 'Score']
        
        df_corr = df_fund[numeric_cols].corr()
        
        fig_corr = px.imshow(
            df_corr,
            text_auto='.2f',
            aspect="auto",
            color_continuous_scale='RdBu',
            title='Correlação entre Indicadores'
        )
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, use_container_width=True)
        
    else:
        st.info("👈 Execute o screener primeiro para ver o dashboard.")

# ============================================================================
# 8. ABA 2 - RESULTADOS FILTRADOS
# ============================================================================
with tab2:
    st.header("🔍 Resultados dos Filtros Aplicados")
    
    if 'df_filtered' in st.session_state and not st.session_state.df_filtered.empty:
        df_filtered = st.session_state.df_filtered
        
        # Métricas dos resultados filtrados
        st.subheader(f"📋 {len(df_filtered)} Ações Encontradas")
        
        # Ordenar opções
        sort_options = {
            "Score": "Score",
            "DY %": "DY %", 
            "P/VP": "P/VP",
            "ROE %": "ROE %",
            "P/L": "P/L"
        }
        
        sort_by = st.selectbox("Ordenar por:", list(sort_options.keys()), key="sort_filtered")
        ascending = st.checkbox("Ordem Crescente", key="asc_filtered")
        
        df_sorted = df_filtered.sort_values(
            by=sort_options[sort_by], 
            ascending=ascending
        )
        
        # Formatar dataframe para exibição
        display_cols = [
            'Ticker', 'Empresa', 'Preço', 'Variação %', 'DY %', 
            'P/L', 'P/VP', 'ROE %', 'Margem %', 'Score'
        ]
        
        df_display = df_sorted[display_cols].copy()
        
        # Adicionar formatação condicional
        def color_score(val):
            if val >= 80:
                return 'background-color: #1e3a28; color: #00ff88'
            elif val >= 60:
                return 'background-color: #3a281e; color: #ffcc00'
            else:
                return 'background-color: #3a1e1e; color: #ff6b6b'
        
        def color_dy(val):
            if val >= 8:
                return 'background-color: #1e3a28; color: #00ff88'
            elif val >= 5:
                return 'background-color: #3a281e; color: #ffcc00'
            else:
                return ''
        
        # Aplicar estilo
        styled_df = df_display.style.map(color_score, subset=['Score'])\
                                   .map(color_dy, subset=['DY %'])\
                                   .format({
                                       'Preço': 'R$ {:,.2f}',
                                       'Variação %': '{:+.2f}%',
                                       'DY %': '{:.2f}%',
                                       'P/L': '{:.1f}',
                                       'P/VP': '{:.2f}',
                                       'ROE %': '{:.1f}%',
                                       'Margem %': '{:.1f}%',
                                       'Score': '{:.0f}'
                                   })
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Botões de ação
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            # Exportar para CSV
            csv = df_filtered.to_csv(index=False, sep=';', decimal=',')
            st.download_button(
                label="📥 Exportar CSV",
                data=csv,
                file_name=f"screener_resultados_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp2:
            # Exportar para Excel
            @st.cache_data
            def convert_to_excel(df):
                return df.to_excel(index=False)
            
            excel_data = convert_to_excel(df_filtered)
            st.download_button(
                label="📊 Exportar Excel",
                data=excel_data,
                file_name=f"screener_resultados_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_exp3:
            if st.button("🔄 Nova Análise", use_container_width=True):
                st.rerun()
        
        # Detalhes por ação selecionada
        st.subheader("📈 Detalhes da Ação Selecionada")
        
        selected_ticker = st.selectbox(
            "Selecione uma ação para detalhes:",
            df_filtered['Ticker'].tolist(),
            key="select_detail"
        )
        
        if selected_ticker:
            # Buscar dados técnicos detalhados
            tech_data = None
            if 'df_tech' in st.session_state:
                tech_row = st.session_state.df_tech[st.session_state.df_tech['Ticker'] == selected_ticker]
                if not tech_row.empty:
                    tech_data = tech_row.iloc[0]
            
            if tech_data and 'Histórico' in tech_data:
                hist = tech_data['Histórico']
                
                # Gráfico de preços com indicadores
                fig_price = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=('Preço e Médias Móveis', 'Volume'),
                    row_heights=[0.7, 0.3]
                )
                
                # Adicionar preço e médias
                fig_price.add_trace(
                    go.Scatter(x=hist.index, y=hist['Close'], name='Preço', line=dict(color='#00cc66')),
                    row=1, col=1
                )
                
                if 'MA20' in hist.columns:
                    fig_price.add_trace(
                        go.Scatter(x=hist.index, y=hist['MA20'], name='MA20', line=dict(color='#ffcc00', dash='dash')),
                        row=1, col=1
                    )
                
                if 'MA50' in hist.columns:
                    fig_price.add_trace(
                        go.Scatter(x=hist.index, y=hist['MA50'], name='MA50', line=dict(color='#ff6b6b', dash='dash')),
                        row=1, col=1
                    )
                
                # Adicionar volume
                colors = ['red' if row['Open'] > row['Close'] else 'green' for _, row in hist.iterrows()]
                fig_price.add_trace(
                    go.Bar(x=hist.index, y=hist['Volume'], name='Volume', marker_color=colors),
                    row=2, col=1
                )
                
                fig_price.update_layout(height=600, showlegend=True, title=f"{selected_ticker} - Análise Técnica")
                st.plotly_chart(fig_price, use_container_width=True)
                
                # Indicadores técnicos
                col_tech1, col_tech2, col_tech3, col_tech4 = st.columns(4)
                
                with col_tech1:
                    rsi_value = tech_data.get('RSI', 50)
                    rsi_color = "#00ff88" if rsi_value < 30 else "#ff6b6b" if rsi_value > 70 else "#ffcc00"
                    st.metric("RSI", f"{rsi_value:.1f}", delta=tech_data.get('Sinal RSI', 'NEUTRO'))
                
                with col_tech2:
                    st.metric("Tendência", tech_data.get('Tendência', 'NEUTRA'))
                
                with col_tech3:
                    st.metric("Volume Médio", f"{tech_data.get('Volume (M)', 0):.1f}M")
                
                with col_tech4:
                    st.metric("Volatilidade", f"{tech_data.get('Volatilidade %', 0):.1f}%")
    
    elif 'df_filtered' in st.session_state and st.session_state.df_filtered.empty:
        st.warning("⚠️ Nenhuma ação passou nos filtros aplicados. Tente ajustar os critérios.")
    else:
        st.info("👈 Execute o screener primeiro para ver os resultados filtrados.")

# ============================================================================
# 9. ABA 3 - ANÁLISE TÉCNICA AVANÇADA
# ============================================================================
with tab3:
    st.header("📈 Análise Técnica Avançada")
    
    if 'df_tech' in st.session_state:
        # Seletor de ação para análise técnica
        selected_ticker_tech = st.selectbox(
            "Selecione uma ação para análise técnica avançada:",
            st.session_state.df_tech['Ticker'].tolist(),
            key="select_tech"
        )
        
        if selected_ticker_tech:
            tech_row = st.session_state.df_tech[st.session_state.df_tech['Ticker'] == selected_ticker_tech]
            
            if not tech_row.empty:
                tech_data = tech_row.iloc[0]
                hist = tech_data.get('Histórico')
                
                if hist is not None and not hist.empty:
                    # Configurações da análise técnica
                    st.subheader(f"🔧 Configurações para {selected_ticker_tech}")
                    
                    col_config1, col_config2 = st.columns(2)
                    
                    with col_config1:
                        show_rsi = st.checkbox("Mostrar RSI", value=True)
                        show_macd = st.checkbox("Mostrar MACD", value=True)
                        show_bb = st.checkbox("Mostrar Bollinger Bands", value=True)
                    
                    with col_config2:
                        show_volume = st.checkbox("Mostrar Volume", value=True)
                        show_patterns = st.checkbox("Detectar Padrões", value=True)
                    
                    # Gráfico principal
                    fig_tech = make_subplots(
                        rows=3 if show_rsi or show_macd else 2, 
                        cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        row_heights=[0.5, 0.25, 0.25] if show_rsi and show_macd else [0.6, 0.4]
                    )
                    
                    # Preços
                    fig_tech.add_trace(
                        go.Candlestick(
                            x=hist.index,
                            open=hist['Open'],
                            high=hist['High'],
                            low=hist['Low'],
                            close=hist['Close'],
                            name='Candles',
                            increasing_line_color='#00cc66',
                            decreasing_line_color='#ff6b6b'
                        ),
                        row=1, col=1
                    )
                    
                    # Bollinger Bands
                    if show_bb and 'BB_Upper' in hist.columns:
                        fig_tech.add_trace(
                            go.Scatter(x=hist.index, y=hist['BB_Upper'], 
                                     name='BB Superior', line=dict(color='#888888', dash='dash')),
                            row=1, col=1
                        )
                        fig_tech.add_trace(
                            go.Scatter(x=hist.index, y=hist['BB_Lower'], 
                                     name='BB Inferior', line=dict(color='#888888', dash='dash'),
                                     fill='tonexty', fillcolor='rgba(136, 136, 136, 0.1)'),
                            row=1, col=1
                        )
                    
                    # Volume
                    if show_volume:
                        colors = ['red' if row['Open'] > row['Close'] else 'green' for _, row in hist.iterrows()]
                        fig_tech.add_trace(
                            go.Bar(x=hist.index, y=hist['Volume'], name='Volume', 
                                  marker_color=colors, opacity=0.7),
                            row=2 if show_rsi or show_macd else 1, col=1
                        )
                    
                    # RSI
                    if show_rsi and 'RSI' in hist.columns:
                        row_num = 3 if show_macd else 2
                        fig_tech.add_trace(
                            go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', 
                                      line=dict(color='#ffcc00')),
                            row=row_num, col=1
                        )
                        # Linhas de sobrecompra/sobrevenda
                        fig_tech.add_hline(y=70, line_dash="dash", line_color="red", 
                                          row=row_num, col=1)
                        fig_tech.add_hline(y=30, line_dash="dash", line_color="green", 
                                          row=row_num, col=1)
                        fig_tech.add_hline(y=50, line_dash="dot", line_color="gray", 
                                          row=row_num, col=1)
                    
                    # MACD
                    if show_macd and 'MACD' in hist.columns:
                        fig_tech.add_trace(
                            go.Scatter(x=hist.index, y=hist['MACD'], name='MACD', 
                                      line=dict(color='#00ccff')),
                            row=3, col=1
                        )
                        fig_tech.add_trace(
                            go.Scatter(x=hist.index, y=hist['MACD_Signal'], name='Signal', 
                                      line=dict(color='#ff6b6b')),
                            row=3, col=1
                        )
                    
                    fig_tech.update_layout(
                        height=800,
                        title=f"{selected_ticker_tech} - Análise Técnica Completa",
                        xaxis_rangeslider_visible=False,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_tech, use_container_width=True)
                    
                    # Análise de padrões
                    if show_patterns:
                        st.subheader("🎯 Detecção de Padrões Gráficos")
                        
                        # Implementação simples de detecção de padrões
                        col_pattern1, col_pattern2, col_pattern3 = st.columns(3)
                        
                        with col_pattern1:
                            # Verificar tendência
                            if len(hist) >= 50:
                                ma_short = hist['Close'].rolling(window=20).mean()
                                ma_long = hist['Close'].rolling(window=50).mean()
                                
                                last_ma_short = ma_short.iloc[-1]
                                last_ma_long = ma_long.iloc[-1]
                                
                                if last_ma_short > last_ma_long:
                                    st.markdown('<div class="badge-buy">TENDÊNCIA DE ALTA</div>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<div class="badge-sell">TENDÊNCIA DE BAIXA</div>', unsafe_allow_html=True)
                        
                        with col_pattern2:
                            # Verificar suporte/resistência
                            recent_high = hist['High'].tail(20).max()
                            recent_low = hist['Low'].tail(20).min()
                            current = hist['Close'].iloc[-1]
                            
                            dist_to_high = ((recent_high - current) / current) * 100
                            dist_to_low = ((current - recent_low) / current) * 100
                            
                            if dist_to_high < 5:
                                st.markdown('<div class="badge-sell">PRÓXIMO DA RESISTÊNCIA</div>', unsafe_allow_html=True)
                            elif dist_to_low < 5:
                                st.markdown('<div class="badge-buy">PRÓXIMO DO SUPORTE</div>', unsafe_allow_html=True)
                        
                        with col_pattern3:
                            # Volume analysis
                            avg_volume = hist['Volume'].mean()
                            last_volume = hist['Volume'].iloc[-1]
                            
                            if last_volume > avg_volume * 1.5:
                                st.markdown('<div class="badge-buy">ALTO VOLUME</div>', unsafe_allow_html=True)
    else:
        st.info("👈 Execute o screener primeiro para ver a análise técnica.")

# ============================================================================
# 10. ABA 4 - RANKING COMPLETO
# ============================================================================
with tab4:
    st.header("🎯 Ranking Completo de Ações")
    
    if 'df_fund' in st.session_state and 'df_tech' in st.session_state:
        df_fund = st.session_state.df_fund
        df_tech = st.session_state.df_tech
        
        # Merge para ranking completo
        df_ranking = pd.merge(df_fund, df_tech[['Ticker', 'RSI', 'Sinal RSI', 'Tendência']], 
                             on='Ticker', how='left')
        
        # Opções de ranking
        st.subheader("📊 Configurar Ranking")
        
        rank_by = st.selectbox(
            "Rankear por:",
            ['Score', 'DY %', 'ROE %', 'P/VP', 'P/L', 'Margem %'],
            key="rank_by"
        )
        
        ascending = st.checkbox("Ordem Crescente", key="asc_rank")
        
        # Ordenar
        df_ranked = df_ranking.sort_values(by=rank_by, ascending=ascending)
        
        # Adicionar posição
        df_ranked.insert(0, 'Posição', range(1, len(df_ranked) + 1))
        
        # Selecionar colunas para exibição
        rank_cols = ['Posição', 'Ticker', 'Empresa', 'Preço', rank_by, 
                    'DY %', 'P/VP', 'ROE %', 'Score', 'Sinal RSI', 'Tendência']
        
        df_display_rank = df_ranked[rank_cols].copy()
        
        # Formatar
        def highlight_top3(val):
            if isinstance(val, (int, float)) and val <= 3:
                return 'background-color: #1e3a28; color: #00ff88; font-weight: bold'
            return ''
        
        styled_rank = df_display_rank.style.applymap(highlight_top3, subset=['Posição'])\
                                          .format({
                                              'Preço': 'R$ {:,.2f}',
                                              'DY %': '{:.2f}%',
                                              'ROE %': '{:.1f}%',
                                              'P/VP': '{:.2f}',
                                              'P/L': '{:.1f}',
                                              'Margem %': '{:.1f}%',
                                              'Score': '{:.0f}'
                                          })
        
        st.dataframe(styled_rank, use_container_width=True, height=500)
        
        # Análise por setor (simplificada)
        st.subheader("📈 Análise por Categoria")
        
        # Definir categorias simples baseadas no score
        def categorize_score(score):
            if score >= 80:
                return '⭐ Excelente'
            elif score >= 70:
                return '👍 Bom'
            elif score >= 60:
                return '⚖️ Regular'
            else:
                return '⚠️ Cuidado'
        
        df_ranking['Categoria'] = df_ranking['Score'].apply(categorize_score)
        
        # Gráfico de distribuição
        category_counts = df_ranking['Categoria'].value_counts()
        
        fig_pie = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title='Distribuição por Categoria de Score',
            color_discrete_sequence=['#00cc66', '#ffcc00', '#ff6b6b', '#888888']
        )
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_chart2:
            # Top 5 por DY
            top_dy = df_ranking.nlargest(5, 'DY %')[['Ticker', 'DY %', 'Preço']]
            st.write("**🏆 Top 5 Dividend Yield:**")
            st.dataframe(top_dy.style.format({
                'DY %': '{:.2f}%',
                'Preço': 'R$ {:,.2f}'
            }), use_container_width=True)
        
        # Exportar ranking completo
        st.download_button(
            label="📊 Exportar Ranking Completo",
            data=df_ranking.to_csv(index=False, sep=';', decimal=','),
            file_name=f"ranking_completo_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    else:
        st.info("👈 Execute o screener primeiro para ver o ranking completo.")

# ============================================================================
# 11. RODAPÉ E INFORMAÇÕES
# ============================================================================
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"**B3 Screener Pro v1.0** • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

with footer_col2:
    if 'df_fund' in st.session_state:
        num_acoes = len(st.session_state.df_fund)
        st.caption(f"**{num_acoes} ações analisadas**")

with footer_col3:
    st.caption("Dados: Yahoo Finance • Análise para fins educacionais")

# Informações de ajuda
with st.expander("❓ Como usar este Screener", expanded=False):
    st.markdown("""
    ### 🎯 **Guia Rápido:**
    
    1. **Selecione as ações** que deseja analisar na sidebar
    2. **Configure os filtros** fundamentais e técnicos
    3. **Clique em 'Executar Screener'** para iniciar a análise
    4. **Explore as abas** para diferentes visualizações
    
    ### 📊 **Indicadores Fundamentais:**
    
    - **P/L (Price to Earnings):** Preço dividido pelo lucro por ação
    - **P/VP (Price to Book):** Preço dividido pelo valor patrimonial
    - **ROE (Return on Equity):** Retorno sobre o patrimônio líquido
    - **DY (Dividend Yield):** Dividendos pagos divididos pelo preço
    - **Dív/PL:** Dívida líquida dividida pelo patrimônio líquido
    
    ### 📈 **Indicadores Técnicos:**
    
    - **RSI (Relative Strength Index):** Indicador de momentum (30-70)
    - **Médias Móveis:** Tendências de curto e longo prazo
    - **Volume:** Liquidez e interesse no ativo
    - **MACD:** Convergência/divergência de médias móveis
    
    ### ⚡ **Dicas:**
    
    - Comece com **5-10 ações** para testes rápidos
    - Use **delay de 1.5-3 segundos** para evitar bloqueios
    - **Exporte os resultados** para análise detalhada
    - Combine **filtros fundamentais e técnicos** para melhores resultados
    
    ### ⚠️ **Aviso Importante:**
    
    Esta ferramenta fornece análises automatizadas baseadas em dados históricos.
    Não constitui recomendação de investimento. Sempre faça sua própria pesquisa
    e consulte um profissional qualificado antes de investir.
    """)
