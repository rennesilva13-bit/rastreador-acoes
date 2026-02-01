import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime
import re
import time
import json

# --- TENTAR IMPORTAR DEPENDÊNCIAS DE IA ---
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    import feedparser
    analyzer = SentimentIntensityAnalyzer()
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

# --- CONFIGURAÇÃO DAS CHAVES API ---
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
FINANCIAL_DATASETS_API_KEY = st.secrets.get("FINANCIAL_DATASETS_API_KEY", None)

if OPENAI_API_KEY and OPENAI_AVAILABLE:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="🧠 Dashboard IA Valuation B3",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PALETA DE CORES MODERNA ---
COLORS = {
    'primary': '#636EFA',
    'secondary': '#EF553B',
    'success': '#00CC96',
    'warning': '#FFA15A',
    'danger': '#FF6692',
    'info': '#AB63FA',
    'ai': '#8A2BE2',
    'background': '#0E1117',
    'card_bg': '#262730',
    'text': '#FAFAFA',
    'text_secondary': '#8B9AA3'
}

# --- ESTILO CSS MODERNO ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {{
        font-family: 'Inter', sans-serif;
    }}
    
    .stApp {{
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: {COLORS['text']};
    }}
    
    div[data-testid="stMetricValue"] {{
        background: linear-gradient(135deg, {COLORS['card_bg']} 0%, #334155 100%);
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    
    .stButton button {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, #8884d8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(99, 110, 250, 0.3);
    }}
    
    .stButton button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 110, 250, 0.4);
    }}
    
    div[data-baseweb="select"], div[data-baseweb="input"] {{
        background: {COLORS['card_bg']};
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    
    .stSlider > div > div > div {{
        background: {COLORS['primary']};
    }}
    
    button[data-baseweb="tab"] {{
        background: transparent;
        border: none;
        color: {COLORS['text_secondary']};
        font-weight: 500;
        padding: 0.8rem 1.5rem;
        border-radius: 8px 8px 0 0;
        transition: all 0.3s ease;
    }}
    
    button[data-baseweb="tab"]:hover {{
        color: {COLORS['primary']};
        background: rgba(99, 110, 250, 0.1);
    }}
    
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {COLORS['primary']};
        background: rgba(99, 110, 250, 0.15);
        border-bottom: 3px solid {COLORS['primary']};
    }}
    
    .streamlit-expanderHeader {{
        background: {COLORS['card_bg']};
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    
    .ai-insight {{
        background: linear-gradient(135deg, rgba(138, 43, 226, 0.1), rgba(102, 51, 153, 0.15));
        border-left: 4px solid {COLORS['ai']};
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1.5rem 0;
    }}
    
    .ai-badge {{
        display: inline-block;
        background: rgba(138, 43, 226, 0.2);
        color: {COLORS['ai']};
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-left: 0.5rem;
    }}
    
    .stSpinner > div {{
        border-color: {COLORS['primary']} {COLORS['primary']} {COLORS['primary']} transparent !important;
    }}
    
    h1 {{
        background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['ai']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}
    
    hr {{
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        margin: 2rem 0;
    }}
    
    .shield-badge {{
        display: inline-block;
        background: rgba(0, 204, 150, 0.2);
        color: #00CC96;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-left: 0.5rem;
    }}
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE SUPORTE ---
def clean_text(text):
    """Remove URLs e caracteres especiais."""
    if not text:
        return ""
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# --- 🔒 FUNÇÃO BLINDADA DO YAHOO FINANCE (INTEGRADA) ---
@st.cache_data(ttl=900, show_spinner=False)
def get_yahoo_data_cached(ticker):
    """
    Função otimizada: Deixa o yfinance gerenciar a sessão (correção do erro curl_cffi)
    """
    ticker_clean = ticker.strip().upper().replace('.SA', '')
    yahoo_ticker = f"{ticker_clean}.SA"
    
    try:
        # CORREÇÃO PRINCIPAL: Não passamos mais 'session=session'
        # O yfinance agora usa internamente uma sessão blindada
        acao = yf.Ticker(yahoo_ticker)
        
        # 1. Tenta pegar Preço (Estratégia Híbrida)
        preco_atual = 0.0
        try:
            # Tenta fast_info primeiro (muito mais rápido)
            if hasattr(acao, 'fast_info'):
                # Verifica se o valor é válido antes de aceitar
                last_price = acao.fast_info.get('last_price')
                if last_price and last_price > 0:
                    preco_atual = last_price
            
            # Se falhar ou for None, tenta histórico
            if preco_atual <= 0:
                hist = acao.history(period="1d")
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]
        except:
            pass
            
        if preco_atual <= 0:
            return None, "Preço não disponível"

        # 2. Tenta pegar Fundamentos
        try:
            info = acao.info
        except Exception as e:
            return None, f"Erro ao obter fundamentos: {str(e)}"

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

@st.cache_data(ttl=3600)
def carregar_dados_fundamentus():
    url = 'https://www.fundamentus.com.br/resultado.php'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        try:
            df = pd.read_html(r.content, thousands='.', decimal=',', flavor='lxml')[0]
        except Exception:
            df = pd.read_html(r.content, thousands='.', decimal=',', flavor='html5lib')[0]
    except Exception as e:
        st.error(f"Erro ao acessar Fundamentus: {e}")
        return pd.DataFrame()

    cols_pct = ['Div.Yield', 'Mrg Ebit', 'Mrg. Líq.', 'ROIC', 'ROE', 'Cresc. Rec.5a']
    for col in cols_pct:
        df[col] = df[col].astype(str).str.replace('.', '', regex=False)
        df[col] = df[col].str.replace(',', '.', regex=False).str.replace('%', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce') / 100

    df.columns = [
        'Papel', 'Cotacao', 'PL', 'PVP', 'PSR', 'DivYield', 'P_Ativo', 'P_CapGiro',
        'P_EBIT', 'P_AtivoCircLiq', 'EV_EBIT', 'EV_EBITDA', 'MrgEbit', 'MrgLiq',
        'LiqCorr', 'ROIC', 'ROE', 'Liq2meses', 'PatrimLiq', 'DivBruta_Patrim', 'Cresc5a'
    ]
    
    return df

def calcular_graham(df):
    def formula(row):
        if pd.notna(row['PL']) and pd.notna(row['PVP']) and row['PL'] > 0 and row['PVP'] > 0:
            lpa = row['Cotacao'] / row['PL']
            vpa = row['Cotacao'] / row['PVP']
            return np.sqrt(22.5 * lpa * vpa)
        return np.nan
    
    df['Preco_Graham'] = df.apply(formula, axis=1)
    df['Upside_Graham'] = ((df['Preco_Graham'] - df['Cotacao']) / df['Cotacao']) * 100
    return df

def get_news_sentiment(ticker):
    """Busca notícias para um ticker e retorna o sentimento médio."""
    if not SENTIMENT_AVAILABLE:
        return None, [], []
    
    rss_urls = [
        f'https://www.infomoney.com.br/feed/?s={ticker}',
        f'https://www.infomoney.com.br/feed/?s={ticker[:4]}',
        f'https://www.infomoney.com.br/feed/?s={ticker[:3]}',
    ]
    
    all_scores = []
    all_titles = []

    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                continue

            for entry in feed.entries[:5]:
                title = clean_text(entry.title)
                summary = clean_text(entry.summary)
                text_to_analyze = f"{title} {summary}".lower()
                scores = analyzer.polarity_scores(text_to_analyze)
                all_scores.append(scores)
                all_titles.append(title)

        except Exception:
            continue

    if not all_scores:
        return None, [], []

    avg_compound = np.mean([s['compound'] for s in all_scores])
    avg_pos = np.mean([s['pos'] for s in all_scores])
    avg_neu = np.mean([s['neu'] for s in all_scores])
    avg_neg = np.mean([s['neg'] for s in all_scores])

    summary_stats = {
        'avg_compound': avg_compound,
        'avg_positive': avg_pos,
        'avg_neutral': avg_neu,
        'avg_negative': avg_neg
    }

    last_news = [(t, s) for t, s in zip(all_titles[-5:], all_scores[-5:])]

    return summary_stats, last_news, all_scores

@st.cache_data(ttl=3600)
def obter_dados_financial_datasets(ticker):
    """Busca dados enriquecidos da Financial Datasets API"""
    if not FINANCIAL_DATASETS_API_KEY:
        return None
    
    try:
        ticker_base = ticker.replace('3', '').replace('4', '').replace('11', '').replace('SA', '')
        
        url = f"https://api.financialdatasets.ai/financials/stocks/{ticker_base}"
        headers = {
            "Authorization": f"Bearer {FINANCIAL_DATASETS_API_KEY}",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

def analisar_sentimento_com_gpt(ticker, noticias, empresa_info=""):
    """Usa GPT para análise de sentimento avançada"""
    if not client or not noticias:
        return None
    
    contexto_noticias = "\n".join([
        f"- {n['title']}" + (f" ({n['summary'][:100]}...)" if n.get('summary') else "")
        for n in noticias[:5]
    ])
    
    prompt = f"""
Você é um analista financeiro especialista em mercado brasileiro B3.
Analise o sentimento das notícias abaixo sobre a empresa {ticker} {f'({empresa_info})' if empresa_info else ''}.

Notícias recentes:
{contexto_noticias}

Forneça sua análise no seguinte formato JSON EXATO:

{{
  "sentimento_geral": "positivo|neutro|negativo",
  "score": -1.0 a 1.0,
  "confianca": 0.0 a 1.0,
  "resumo": "Resumo conciso em português do sentimento geral",
  "fatores_positivos": ["lista", "de", "fatores"],
  "fatores_negativos": ["lista", "de", "fatores"],
  "recomendacao_curto_prazo": "comprar|manter|vender"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um analista financeiro preciso e objetivo."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        if content.startswith("```json"):
            content = content[7:].strip()
        if content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()
        
        return json.loads(content)
        
    except Exception:
        return None

def gerar_insight_com_gpt(ticker, dados_basicos, dados_enriquecidos=None):
    """Gera insights de investimento usando GPT"""
    if not client:
        return None
    
    cotacao = dados_basicos.get('Cotacao', 'N/A')
    pl = dados_basicos.get('PL', 'N/A')
    pvp = dados_basicos.get('PVP', 'N/A')
    dy = dados_basicos.get('DivYield', 0) * 100 if pd.notna(dados_basicos.get('DivYield')) else 0
    roe = dados_basicos.get('ROE', 0) * 100 if pd.notna(dados_basicos.get('ROE')) else 0
    
    contexto_enriquecido = ""
    if dados_enriquecidos:
        try:
            financials = dados_enriquecidos.get('financials', {})
            income_statement = financials.get('income_statement', [{}])[0] if financials.get('income_statement') else {}
            
            revenue = income_statement.get('total_revenue', 'N/A')
            net_income = income_statement.get('net_income', 'N/A')
            
            contexto_enriquecido = f"""
Dados enriquecidos:
- Receita Trailing Twelve Months: {revenue}
- Lucro Líquido TTM: {net_income}
"""
        except Exception:
            pass
    
    prompt = f"""
Você é um analista de investimentos especialista em value investing e análise fundamentalista.
Analise a empresa {ticker} com base nos seguintes dados:

Dados Fundamentus:
- Cotação atual: R$ {cotacao:.2f}
- P/L: {pl:.2f}
- P/VP: {pvp:.2f}
- Dividend Yield: {dy:.2f}%
- ROE: {roe:.2f}%

{contexto_enriquecido}

Forneça uma análise concisa e acionável em português brasileiro com:
1. Pontos fortes e fracos da empresa
2. Avaliação de valuation (subvalorizada/justa/sobrevalorizada)
3. Potencial de dividendos
4. Riscos relevantes
5. Recomendação final (comprar/manter/vender) com justificativa

Mantenha a análise objetiva, baseada em dados, e evite exageros.
Limite a 150 palavras.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um analista de investimentos preciso, objetivo e ético."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception:
        return None

# --- COMPONENTES REUTILIZÁVEIS ---
def metric_card(title, value, delta=None, icon="📊", help_text=None):
    st.markdown(f"""
        <div style='padding: 1rem; background: {COLORS['card_bg']}; border-radius: 12px; border-left: 4px solid {COLORS['primary']}; margin-bottom: 1rem;'>
            <div style='display: flex; align-items: center; margin-bottom: 0.5rem;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>{icon}</span>
                <span style='color: {COLORS['text_secondary']}; font-size: 0.9rem; font-weight: 500;'>{title}</span>
            </div>
            <div style='font-size: 1.8rem; font-weight: 700; color: {COLORS['text']};'>{value}</div>
            {f"<div style='color: {'#00CC96' if delta and (str(delta).startswith('+') or float(str(delta).replace('%','')) > 0) else '#FF6692'}; font-size: 0.9rem; margin-top: 0.3rem;'>{delta}</div>" if delta else ""}
            {f"<div style='color: {COLORS['text_secondary']}; font-size: 0.8rem; margin-top: 0.3rem;'>{help_text}</div>" if help_text else ""}
        </div>
    """, unsafe_allow_html=True)

def section_header(title, subtitle=None, icon="📈"):
    st.markdown(f"""
        <div style='margin: 2rem 0 1.5rem 0;'>
            <div style='display: flex; align-items: center; margin-bottom: 0.5rem;'>
                <span style='font-size: 1.8rem; margin-right: 0.8rem;'>{icon}</span>
                <h2 style='margin: 0; color: {COLORS['text']};'>{title}</h2>
            </div>
            {f"<p style='color: {COLORS['text_secondary']}; margin: 0.5rem 0 0 2.8rem; font-size: 1rem;'>{subtitle}</p>" if subtitle else ""}
        </div>
    """, unsafe_allow_html=True)

def info_box(message, type='info'):
    icons = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌', 'ai': '🧠', 'shield': '🔒'}
    colors = {
        'info': COLORS['info'], 'success': COLORS['success'], 
        'warning': COLORS['warning'], 'error': COLORS['danger'], 
        'ai': COLORS['ai'], 'shield': COLORS['success']
    }
    icon = icons.get(type, 'ℹ️')
    color = colors.get(type, COLORS['info'])
    
    st.markdown(f"""
        <div style='background: rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, 0.1); 
                    border-left: 4px solid {color}; 
                    padding: 1rem; 
                    border-radius: 8px; 
                    margin: 1rem 0;'>
            <div style='display: flex; align-items: start;'>
                <span style='font-size: 1.2rem; margin-right: 0.8rem;'>{icon}</span>
                <div style='color: {COLORS['text']};'>{message}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def ai_insight_box(insight_text):
    """Exibe insight gerado por IA com estilo especial"""
    if not insight_text:
        return
    
    st.markdown(f"""
        <div class="ai-insight">
            <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                <span style='font-size: 1.5rem; margin-right: 0.8rem;'>🧠</span>
                <h3 style='color: {COLORS['ai']}; margin: 0;'>Insight Gerado por IA</h3>
                <span class="ai-badge">GPT-4o mini</span>
            </div>
            <div style='color: {COLORS['text']}; line-height: 1.6;'>{insight_text}</div>
        </div>
    """, unsafe_allow_html=True)

def shield_info_box():
    """Exibe informação sobre a blindagem"""
    st.markdown(f"""
        <div style='background: rgba(0, 204, 150, 0.1); border-left: 4px solid #00CC96; padding: 1rem; border-radius: 8px; margin: 1rem 0;'>
            <div style='display: flex; align-items: start;'>
                <span style='font-size: 1.2rem; margin-right: 0.8rem;'>🔒</span>
                <div style='color: {COLORS['text']};'>
                    <strong>Blindagem Ativada:</strong> Dados do Yahoo Finance otimizados com fallback automático e cache de 15 minutos para maior confiabilidade.
                    <span class="shield-badge">v2.0</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO ---
st.markdown("""
    <div style='text-align: center; padding: 2rem 0; margin-bottom: 2rem;'>
        <h1>🧠 Dashboard IA Valuation B3</h1>
        <p style='color: #8B9AA3; font-size: 1.1rem; margin-top: 0.5rem;'>
            Análise Quantitativa com Inteligência Artificial + Blindagem Anti-Falhas
        </p>
    </div>
""", unsafe_allow_html=True)

# Verifica disponibilidade das APIs
col_api1, col_api2, col_api3 = st.columns(3)
with col_api1:
    if OPENAI_API_KEY and client:
        st.success("✅ OpenAI API")
    else:
        st.warning("⚠️ OpenAI API")
with col_api2:
    if FINANCIAL_DATASETS_API_KEY:
        st.success("✅ Financial Datasets")
    else:
        st.info("ℹ️ Financial Datasets")
with col_api3:
    st.success("✅ Blindagem YFinance v2.0")

st.markdown("---")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "🔍 Screener IA",
    "📈 Análise Histórica",
    "❄️ Simulador Bola de Neve",
    "💬 Sentimento com GPT",
    "🤖 Insights Personalizados"
])

with st.spinner('🔄 Conectando ao mercado...'):
    df_raw = carregar_dados_fundamentus()
    
if df_raw.empty:
    st.error("❌ Não foi possível carregar os dados do Fundamentus.")
    st.stop()

df_graham = calcular_graham(df_raw)
lista_tickers = sorted(df_raw['Papel'].unique())

# --- ABA 1: SCREENER COM BLINDAGEM ---
with aba1:
    section_header("Screener Inteligente com Blindagem", "Filtros avançados + dados blindados do Yahoo Finance", "🎯")
    
    shield_info_box()
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        min_liq = st.number_input("💧 Liquidez Diária (R$)", value=1000000, step=500000, format="%d")
    with col_f2:
        min_roe = st.slider("📈 ROE Mínimo (%)", 0, 40, 15) / 100
    with col_f3:
        max_pvp = st.slider("💰 P/VP Máximo", 0.3, 3.0, 1.2)
    with col_f4:
        min_dy = st.slider("💵 DY Mínimo (%)", 0.0, 15.0, 4.0) / 100

    mask = (
        (df_graham['Liq2meses'] >= min_liq) &
        (df_graham['PL'] > 0) &
        (df_graham['ROE'] >= min_roe) &
        (df_graham['PVP'] <= max_pvp) &
        (df_graham['DivYield'] >= min_dy)
    )
    
    df_filtrado = df_graham[mask].copy()

    if not df_filtrado.empty:
        section_header("Resultados da Busca", f"{len(df_filtrado)} oportunidades encontradas", "💎")
        
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        
        with col_kpi1:
            metric_card("Total de Ativos", f"{len(df_filtrado)}", icon="🎯")
        
        valid_upside_df = df_filtrado[df_filtrado['Upside_Graham'].notna()]
        
        if not valid_upside_df.empty:
            top_asset = valid_upside_df.sort_values('Upside_Graham', ascending=False).iloc[0]
            with col_kpi2:
                metric_card("Melhor Oportunidade", top_asset['Papel'], 
                           f"+{top_asset['Upside_Graham']:.1f}%", icon="🚀")
            
            avg_upside = valid_upside_df['Upside_Graham'].mean()
            with col_kpi3:
                metric_card("Desconto Médio", f"{avg_upside:.1f}%", icon="📊")
            
            avg_roe = valid_upside_df['ROE'].mean() * 100
            with col_kpi4:
                metric_card("ROE Médio", f"{avg_roe:.1f}%", icon="📈")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gráfico de dispersão
        fig = px.scatter(
            df_filtrado,
            x='Cotacao',
            y='Preco_Graham',
            color='DivYield',
            size='ROE',
            hover_name='Papel',
            hover_data=['ROE', 'PVP', 'Liq2meses', 'DivYield'],
            title="🗺️ Mapa de Valor - Visualização de Oportunidades",
            labels={
                'Cotacao': 'Preço Atual (R$)',
                'Preco_Graham': 'Preço Justo Graham (R$)',
                'DivYield': 'Dividend Yield'
            },
            color_continuous_scale='RdYlGn',
            template='plotly_dark'
        )

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            hoverlabel=dict(bgcolor=COLORS['card_bg']),
            coloraxis_colorbar=dict(title="DY", thickness=15, len=0.8)
        )

        if not df_filtrado.empty and df_filtrado['Preco_Graham'].notna().any():
            max_val = max(df_filtrado['Preco_Graham'].max(), df_filtrado['Cotacao'].max())
            if pd.notna(max_val) and np.isfinite(max_val) and max_val > 0:
                fig.add_shape(
                    type="line", 
                    line=dict(dash='dash', color=COLORS['warning'], width=2),
                    x0=0, y0=0, x1=max_val, y1=max_val,
                    opacity=0.7
                )
                fig.add_annotation(
                    x=max_val * 0.6, y=max_val * 0.75,
                    text="Linha de Referência: Preço = Valor",
                    showarrow=False,
                    font=dict(size=11, color=COLORS['text_secondary'])
                )

        st.plotly_chart(fig, use_container_width=True)

        # Tabela de resultados
        section_header("📋 Empresas Filtradas", "Ordenadas por potencial de valorização", "📊")
        
        df_display = df_filtrado[['Papel', 'Cotacao', 'Preco_Graham', 'Upside_Graham', 'ROE', 'DivYield', 'PVP', 'Liq2meses', 'PL']].copy()
        df_display = df_display.sort_values('Upside_Graham', ascending=False)
        
        # Formatação manual
        df_display_formatted = df_display.copy()
        df_display_formatted['Cotacao'] = df_display_formatted['Cotacao'].apply(lambda x: f"R$ {x:.2f}")
        df_display_formatted['Preco_Graham'] = df_display_formatted['Preco_Graham'].apply(lambda x: f"R$ {x:.2f}" if pd.notna(x) else "N/A")
        df_display_formatted['Upside_Graham'] = df_display_formatted['Upside_Graham'].apply(lambda x: f"+{x:.1f}%" if pd.notna(x) and x > 0 else f"{x:.1f}%" if pd.notna(x) else "N/A")
        df_display_formatted['ROE'] = df_display_formatted['ROE'].apply(lambda x: f"{x:.1%}")
        df_display_formatted['DivYield'] = df_display_formatted['DivYield'].apply(lambda x: f"{x:.1%}")
        df_display_formatted['PVP'] = df_display_formatted['PVP'].apply(lambda x: f"{x:.2f}")
        df_display_formatted['Liq2meses'] = df_display_formatted['Liq2meses'].apply(lambda x: f"R$ {x:,.0f}")
        df_display_formatted['PL'] = df_display_formatted['PL'].apply(lambda x: f"{x:.1f}")

        st.dataframe(
            df_display_formatted,
            use_container_width=True,
            height=400
        )
        
        # Botão de download
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar Resultados para CSV",
            data=csv,
            file_name=f'screener_resultados_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
            use_container_width=True
        )
        
        # Destaque para top 3 com dados blindados
        if len(valid_upside_df) >= 3:
            st.markdown("<br>", unsafe_allow_html=True)
            section_header("🏆 Top 3 Oportunidades com Dados Blindados", "Dados do Yahoo Finance com fallback automático", "🔒")
            
            top3 = valid_upside_df.head(3)
            for idx, row in top3.iterrows():
                ticker = row['Papel']
                with st.expander(f"🚀 {ticker} - Upside: +{row['Upside_Graham']:.1f}%"):
                    col_t1, col_t2 = st.columns([1, 2])
                    
                    with col_t1:
                        # Usa dados blindados do Yahoo Finance
                        with st.spinner(f"Buscando dados atualizados..."):
                            dados_yahoo, erro = get_yahoo_data_cached(ticker)
                        
                        if dados_yahoo:
                            metric_card("Preço (Yahoo)", f"R$ {dados_yahoo['Preço']:.2f}", icon="💵")
                            metric_card("DY (Yahoo)", f"{dados_yahoo['DY %']:.2f}%", icon="💵")
                            metric_card("ROE (Yahoo)", f"{dados_yahoo['ROE']*100:.1f}%", icon="📈")
                            metric_card("LPA", f"R$ {dados_yahoo['LPA']:.2f}", icon="📊")
                        else:
                            metric_card("Preço", f"R$ {row['Cotacao']:.2f}", icon="💵")
                            metric_card("P/VP", f"{row['PVP']:.2f}", icon="📊")
                            metric_card("ROE", f"{row['ROE']*100:.1f}%", icon="📈")
                            metric_card("DY", f"{row['DivYield']*100:.2f}%", icon="💵")
                    
                    with col_t2:
                        if client:
                            with st.spinner(f"Gerando insight com IA..."):
                                dados_enriquecidos = obter_dados_financial_datasets(ticker) if FINANCIAL_DATASETS_API_KEY else None
                                insight = gerar_insight_com_gpt(ticker, row.to_dict(), dados_enriquecidos)
                                if insight:
                                    ai_insight_box(insight)
                                else:
                                    st.info("💡 Insight não disponível no momento.")
                        else:
                            st.info("ℹ️ Configure OpenAI API para insights com IA")
        
    else:
        info_box("Nenhum ativo passou nos filtros. Tente ajustar os parâmetros para encontrar oportunidades.", "warning")

# --- ABA 2: ANÁLISE HISTÓRICA COM BLINDAGEM ---
with aba2:
    col_graph, col_calc = st.columns([2, 1])
    
    with col_graph:
        section_header("Histórico de Cotações com Blindagem", "Dados do Yahoo Finance com estratégia híbrida", "📉")
        
        shield_info_box()
        
        ticker_sel = st.selectbox(
            "🎯 Selecione o Ativo",
            lista_tickers,
            index=lista_tickers.index('BBAS3') if 'BBAS3' in lista_tickers else 0,
            key='ticker_aba2'
        )
        
        periodo = st.selectbox(
            "📅 Período",
            ["1y", "3y", "5y", "10y", "max"],
            index=2,
            key='periodo_aba2'
        )
        
        if st.button("📊 Carregar Análise", use_container_width=True):
            with st.spinner(f"Baixando dados históricos de {ticker_sel} com blindagem..."):
                try:
                    # Usa a função blindada
                    dados_yahoo, erro_yahoo = get_yahoo_data_cached(ticker_sel)
                    
                    if dados_yahoo:
                        info_box(f"✅ Dados obtidos com sucesso via blindagem (Preço: R$ {dados_yahoo['Preço']:.2f})", "shield")
                    
                    # Continua usando yfinance para histórico
                    acao = yf.Ticker(f"{ticker_sel}.SA")
                    hist = acao.history(period=periodo)
                    
                    if hist.empty:
                        st.error(f"❌ Não foi possível obter dados históricos para {ticker_sel}.")
                    else:
                        graham_value = df_graham[df_graham['Papel'] == ticker_sel]['Preco_Graham'].values
                        
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=hist.index, 
                            y=hist['Close'], 
                            mode='lines', 
                            name='Cotação',
                            line=dict(color=COLORS['primary'], width=3),
                            fill='tozeroy',
                            fillcolor=f'rgba({int(COLORS["primary"][1:3],16)}, {int(COLORS["primary"][3:5],16)}, {int(COLORS["primary"][5:7],16)}, 0.1)'
                        ))
                        
                        if len(graham_value) > 0 and pd.notna(graham_value[0]):
                            graham = graham_value[0]
                            fig.add_hline(
                                y=graham, 
                                line_dash="dash", 
                                line_color=COLORS['success'], 
                                line_width=3,
                                annotation_text=f"Preço Justo: R${graham:.2f}",
                                annotation_position="top right",
                                annotation_font=dict(size=12, color=COLORS['success'])
                            )
                        
                        fig.update_layout(
                            title=f"Histórico de {ticker_sel} - {periodo.upper()}",
                            xaxis_title="Data",
                            yaxis_title="Preço (R$)",
                            hovermode="x unified",
                            template="plotly_dark",
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color=COLORS['text']),
                            hoverlabel=dict(bgcolor=COLORS['card_bg'])
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        
                        preco_atual = hist['Close'].iloc[-1]
                        preco_max = hist['Close'].max()
                        preco_min = hist['Close'].min()
                        variacao = ((preco_atual / hist['Close'].iloc[0]) - 1) * 100
                        
                        with col_stat1:
                            metric_card("Preço Atual", f"R$ {preco_atual:.2f}", icon="💵")
                        with col_stat2:
                            metric_card("Máximo", f"R$ {preco_max:.2f}", icon="📈")
                        with col_stat3:
                            metric_card("Mínimo", f"R$ {preco_min:.2f}", icon="📉")
                        with col_stat4:
                            cor_var = COLORS['success'] if variacao > 0 else COLORS['danger']
                            metric_card("Variação", f"{variacao:+.1f}%", icon="📊")

                except Exception as e:
                    st.error(f"Erro ao baixar dados históricos: {e}")

    with col_calc:
        section_header("Calculadora de Renda Passiva", "Planeje sua independência financeira", "💰")
        
        ticker_sel_calc = st.selectbox(
            "🎯 Ativo para Cálculo",
            lista_tickers,
            index=lista_tickers.index('BBAS3') if 'BBAS3' in lista_tickers else 0,
            key='ticker_calc'
        )
        
        meta = st.number_input("💵 Renda Mensal Desejada (R$)", value=2000.0, step=100.0, min_value=0.0)
        imposto = st.checkbox("⚖️ Considerar Imposto de Renda (15%)", value=True)
        
        dados = df_graham[df_graham['Papel'] == ticker_sel_calc]
        
        if not dados.empty:
            dados = dados.iloc[0]
            dy = dados['DivYield']
            
            if pd.notna(dy) and dy > 0:
                dy_efetivo = dy * 0.85 if imposto else dy
                renda_anual_necessaria = meta * 12
                valor_necessario = renda_anual_necessaria / dy_efetivo
                qtd_acoes = int(valor_necessario / dados['Cotacao'])
                total_investido = qtd_acoes * dados['Cotacao']
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col_inv1, col_inv2 = st.columns(2)
                with col_inv1:
                    metric_card("Valor Necessário", f"R$ {valor_necessario:,.2f}", icon="🎯")
                with col_inv2:
                    metric_card("Total Investido", f"R$ {total_investido:,.2f}", icon="💰")
                
                col_inv3, col_inv4 = st.columns(2)
                with col_inv3:
                    metric_card("Ações Necessárias", f"{qtd_acoes:,}", icon="📊")
                with col_inv4:
                    metric_card("Preço Unitário", f"R$ {dados['Cotacao']:.2f}", icon="💵")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col_prog1, col_prog2 = st.columns(2)
                with col_prog1:
                    st.markdown(f"**Dividendos Líquidos**")
                    st.progress(min(dy_efetivo * 100 / 10, 1.0))
                    st.caption(f"DY: {dy_efetivo:.2%} {'(após IR)' if imposto else ''}")
                
                with col_prog2:
                    st.markdown(f"**Capital Investido**")
                    st.progress(1.0)
                    st.caption(f"Total: R$ {total_investido:,.2f}")
                
                payback_anos = total_investido / renda_anual_necessaria
                info_box(
                    f"⏱️ **Payback:** {payback_anos:.1f} anos para recuperar o investimento via dividendos.<br>"
                    f"📊 **DY Bruto:** {dy:.2%} | **DY Líquido:** {dy_efetivo:.2%}",
                    "success"
                )
                
            else:
                info_box(f"A empresa {ticker_sel_calc} não paga dividendos ou DY não disponível.", "warning")
        else:
            st.error(f"❌ Dados não encontrados para {ticker_sel_calc}.")

# --- ABA 3: SIMULADOR ---
with aba3:
    section_header("Simulador Bola de Neve", "Veja o poder dos juros compostos em ação", "❄️")
    
    col_sim1, col_sim2 = st.columns([1, 2])
    
    with col_sim1:
        st.markdown("#### ⚙️ Parâmetros da Simulação")
        
        ticker_sim = st.selectbox(
            "🎯 Ativo Base",
            lista_tickers,
            index=lista_tickers.index('TAEE11') if 'TAEE11' in lista_tickers else 0,
            key='ticker_aba3'
        )

        dados_sim = df_graham[df_graham['Papel'] == ticker_sim]
        
        if dados_sim.empty:
            st.error(f"❌ Dados não encontrados para {ticker_sim}.")
            st.stop()
        
        dados_sim = dados_sim.iloc[0]
        dy_real = dados_sim['DivYield'] * 100 if pd.notna(dados_sim['DivYield']) else 0.0

        aporte = st.number_input("💵 Aporte Mensal (R$)", value=1000.0, step=100.0, min_value=0.0)
        aporte_aumento = st.slider("📈 Aumento Anual do Aporte (%)", 0, 20, 5)
        anos = st.slider("🕐 Tempo (Anos)", 1, 30, 15)
        taxa_valorizacao = st.slider("💹 Valorização Anual (%)", 0, 20, 8)
        taxa_dy = st.slider(
            "💵 Dividend Yield (%)",
            0.0, 20.0, 
            float(dy_real),
            help="DY atual do ativo selecionado"
        )
        
        reinvestir = st.checkbox("🔄 Reinvestir Dividendos", value=True)

    with col_sim2:
        with st.spinner("Calculando projeção..."):
            meses = anos * 12
            saldo = 0
            total_investido = 0
            lista_meses = []
            lista_investido = []
            lista_patrimonio = []
            lista_dividendos = []

            taxa_val_mensal = (1 + taxa_valorizacao/100)**(1/12) - 1
            taxa_dy_mensal = (1 + taxa_dy/100)**(1/12) - 1

            aporte_atual = aporte
            
            for m in range(1, meses + 1):
                if (m - 1) % 12 == 0 and m > 1:
                    aporte_atual *= (1 + aporte_aumento / 100)
                
                total_investido += aporte_atual
                saldo += aporte_atual

                saldo = saldo * (1 + taxa_val_mensal)

                dividendos = saldo * taxa_dy_mensal
                lista_dividendos.append(dividendos)
                
                if reinvestir:
                    saldo += dividendos

                lista_meses.append(m)
                lista_investido.append(total_investido)
                lista_patrimonio.append(saldo)

        lucro_bruto = saldo - total_investido
        perc_lucro = ((saldo/total_investido)-1)*100 if total_investido > 0 else 0
        dividendos_totais = sum(lista_dividendos)

        section_header("Resultados da Simulação", f"Projeção para {anos} anos", "📊")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            metric_card("Total Investido", f"R$ {total_investido:,.0f}", icon="💰")
        with col_res2:
            metric_card("Patrimônio Final", f"R$ {saldo:,.0f}", icon="🎯", 
                       delta=f"+{perc_lucro:.1f}%")
        with col_res3:
            metric_card("Lucro Gerado", f"R$ {lucro_bruto:,.0f}", icon="📈",
                       delta=f"{lucro_bruto/total_investido*100:.1f}%")

        col_res4, col_res5, col_res6 = st.columns(3)
        with col_res4:
            metric_card("Dividendos", f"R$ {dividendos_totais:,.0f}", icon="💵")
        with col_res5:
            metric_card("Aporte Final", f"R$ {aporte_atual:,.0f}/mês", icon="📊")
        with col_res6:
            rent_anual = ((saldo/total_investido)**(1/anos)-1)*100
            metric_card("Rentabilidade", f"{rent_anual:.1f}%/ano", icon="💹")

        fig_sim = go.Figure()
        fig_sim.add_trace(go.Scatter(
            x=lista_meses, 
            y=lista_patrimonio, 
            fill='tozeroy', 
            mode='lines',
            name='Patrimônio Acumulado',
            line=dict(color=COLORS['success'], width=3),
            fillcolor=f'rgba({int(COLORS["success"][1:3],16)}, {int(COLORS["success"][3:5],16)}, {int(COLORS["success"][5:7],16)}, 0.2)'
        ))
        fig_sim.add_trace(go.Scatter(
            x=lista_meses, 
            y=lista_investido, 
            fill='tozeroy', 
            mode='lines',
            name='Dinheiro Investido',
            line=dict(color=COLORS['primary'], width=3),
            fillcolor=f'rgba({int(COLORS["primary"][1:3],16)}, {int(COLORS["primary"][3:5],16)}, {int(COLORS["primary"][5:7],16)}, 0.2)'
        ))

        fig_sim.update_layout(
            title="📈 A Boca de Jacaré - Efeito Bola de Neve",
            xaxis_title="Meses",
            yaxis_title="R$ Acumulado",
            hovermode="x unified",
            template="plotly_dark",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            hoverlabel=dict(bgcolor=COLORS['card_bg']),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_sim, use_container_width=True)

        info_box(
            f"💡 **Interpretação:** Você investirá R$ {total_investido:,.0f} ao longo de {anos} anos. "
            f"Graças aos juros compostos (valorização de {taxa_valorizacao}% + dividendos de {taxa_dy:.1f}%), "
            f"seu patrimônio crescerá para R$ {saldo:,.0f}, gerando um lucro de R$ {lucro_bruto:,.0f}. "
            f"{'🔄 Com reinvestimento de dividendos.' if reinvestir else '❌ Sem reinvestimento.'}",
            "success"
        )

# --- ABA 4: ANÁLISE DE SENTIMENTO COM GPT ---
with aba4:
    section_header("Análise de Sentimento com IA", "Análise avançada usando GPT-4o mini", "🧠")
    
    col_sent1, col_sent2 = st.columns([2, 1])
    
    with col_sent1:
        ticker_sentiment = st.selectbox(
            "🎯 Selecione o Ativo",
            lista_tickers,
            key='ticker_sentiment_gpt'
        )
    
    with col_sent2:
        num_noticias = st.slider("📄 Número de Notícias", 3, 10, 5)
    
    analisar = st.button("🔍 Analisar com IA", use_container_width=True, type="primary")
    
    if analisar:
        if not client:
            st.error("❌ OpenAI API não configurada. Configure sua chave API para usar esta funcionalidade.")
        else:
            with st.spinner(f"Buscando e analisando notícias sobre {ticker_sentiment} com IA..."):
                noticias = []
                for url_base in [f'https://www.infomoney.com.br/feed/?s={ticker_sentiment}', 
                               f'https://www.infomoney.com.br/feed/?s={ticker_sentiment[:4]}']:
                    try:
                        feed = feedparser.parse(url_base)
                        if not feed.bozo:
                            for entry in feed.entries[:num_noticias]:
                                noticias.append({
                                    'title': clean_text(entry.title),
                                    'summary': clean_text(entry.summary) if hasattr(entry, 'summary') else "",
                                    'link': entry.link if hasattr(entry, 'link') else "",
                                    'source': 'InfoMoney'
                                })
                    except:
                        continue
                
                if not noticias:
                    info_box(f"⚠️ Não encontramos notícias recentes para {ticker_sentiment}.", "warning")
                else:
                    analise_gpt = analisar_sentimento_com_gpt(ticker_sentiment, noticias)
                    
                    if analise_gpt:
                        section_header(f"Resultados para {ticker_sentiment}", "Análise avançada com GPT-4o mini", "📊")
                        
                        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                        
                        sentimento = analise_gpt.get('sentimento_geral', 'neutro')
                        score = analise_gpt.get('score', 0)
                        confianca = analise_gpt.get('confianca', 0)
                        
                        with col_s1:
                            if sentimento == 'positivo':
                                metric_card("Sentimento", "Positivo", f"+{score:.2f}", icon="🟢")
                            elif sentimento == 'negativo':
                                metric_card("Sentimento", "Negativo", f"{score:.2f}", icon="🔴")
                            else:
                                metric_card("Sentimento", "Neutro", f"{score:.2f}", icon="🟡")
                        
                        with col_s2:
                            metric_card("Confiança", f"{confianca*100:.0f}%", icon="🎯")
                        
                        with col_s3:
                            recomendacao = analise_gpt.get('recomendacao_curto_prazo', 'manter').upper()
                            metric_card("Recomendação", recomendacao, icon="💡")
                        
                        with col_s4:
                            metric_card("Notícias", f"{len(noticias)}", icon="📰")
                        
                        resumo = analise_gpt.get('resumo', 'Resumo não disponível')
                        ai_insight_box(resumo)
                        
                        col_f1, col_f2 = st.columns(2)
                        
                        with col_f1:
                            st.markdown("#### ✅ Fatores Positivos")
                            fatores_pos = analise_gpt.get('fatores_positivos', [])
                            if fatores_pos:
                                for fator in fatores_pos:
                                    st.markdown(f"- {fator}")
                            else:
                                st.info("Nenhum fator positivo identificado")
                        
                        with col_f2:
                            st.markdown("#### ❌ Fatores Negativos")
                            fatores_neg = analise_gpt.get('fatores_negativos', [])
                            if fatores_neg:
                                for fator in fatores_neg:
                                    st.markdown(f"- {fator}")
                            else:
                                st.info("Nenhum fator negativo identificado")
                        
                        st.markdown("#### 📰 Notícias Analisadas")
                        for noticia in noticias[:num_noticias]:
                            with st.expander(f"📰 {noticia['title'][:90]}..."):
                                st.markdown(f"**Fonte:** {noticia.get('source', 'Desconhecida')}")
                                if noticia.get('summary'):
                                    st.markdown(f"**Resumo:** {noticia['summary'][:200]}...")
                                if noticia.get('link'):
                                    st.markdown(f"[Ler notícia completa]({noticia['link']})")
                    else:
                        info_box("⚠️ Não foi possível realizar a análise com IA.", "error")

# --- ABA 5: INSIGHTS PERSONALIZADOS ---
with aba5:
    section_header("🤖 Insights Personalizados com GPT", "Análise fundamentalista profunda gerada por IA", "✨")
    
    col_ins1, col_ins2 = st.columns([1, 2])
    
    with col_ins1:
        ticker_insight = st.selectbox(
            "🎯 Selecione o Ativo para Análise Profunda",
            lista_tickers,
            index=lista_tickers.index('PETR4') if 'PETR4' in lista_tickers else 0,
            key='ticker_insight'
        )
        
        incluir_dados_enriquecidos = st.checkbox("📊 Incluir dados Financial Datasets", value=bool(FINANCIAL_DATASETS_API_KEY))
        profundidade = st.select_slider(
            "🔍 Profundidade da Análise",
            options=["Rápida", "Padrão", "Profunda"],
            value="Padrão"
        )
    
    with col_ins2:
        st.markdown("""
        #### ℹ️ O que esta análise inclui:
        - Avaliação de valuation (P/L, P/VP, Graham)
        - Qualidade dos dividendos e sustentabilidade
        - Forças e fraquezas competitivas
        - Riscos setoriais e macroeconômicos
        - Recomendação com justificativa objetiva
        
        *Análise gerada por GPT-4o mini com base em dados atualizados*
        """)
    
    gerar_insight = st.button("🚀 Gerar Insight Personalizado", use_container_width=True, type="primary")
    
    if gerar_insight:
        if not client:
            st.error("❌ OpenAI API não configurada.")
        else:
            dados_basicos = df_graham[df_graham['Papel'] == ticker_insight]
            
            if dados_basicos.empty:
                st.error(f"❌ Dados não encontrados para {ticker_insight}.")
            else:
                dados_basicos = dados_basicos.iloc[0].to_dict()
                
                with st.spinner(f"Gerando análise profunda para {ticker_insight} com IA..."):
                    dados_enriquecidos = None
                    if incluir_dados_enriquecidos and FINANCIAL_DATASETS_API_KEY:
                        with st.spinner("Buscando dados enriquecidos..."):
                            dados_enriquecidos = obter_dados_financial_datasets(ticker_insight)
                    
                    insight = gerar_insight_com_gpt(ticker_insight, dados_basicos, dados_enriquecidos)
                    
                    if insight:
                        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                        with col_m1:
                            metric_card("Cotação", f"R$ {dados_basicos['Cotacao']:.2f}", icon="💵")
                        with col_m2:
                            metric_card("P/L", f"{dados_basicos['PL']:.1f}", icon="📊")
                        with col_m3:
                            metric_card("P/VP", f"{dados_basicos['PVP']:.2f}", icon="📈")
                        with col_m4:
                            dy_valor = dados_basicos['DivYield'] * 100 if pd.notna(dados_basicos['DivYield']) else 0
                            metric_card("DY", f"{dy_valor:.2f}%", icon="💵")
                        
                        ai_insight_box(insight)
                        
                        if dados_enriquecidos and incluir_dados_enriquecidos:
                            st.markdown("#### 📊 Dados Enriquecidos (Financial Datasets)")
                            with st.expander("Ver detalhes financeiros"):
                                st.json(dados_enriquecidos)
                    else:
                        info_box("⚠️ Não foi possível gerar o insight no momento.", "error")

# --- RODAPÉ ---
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; padding: 2rem; color: {COLORS['text_secondary']}; font-size: 0.9rem;'>
        <p>✅ Dashboard atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | 
        Fonte: Fundamentus {'| Financial Datasets API' if FINANCIAL_DATASETS_API_KEY else ''} | 
        IA: OpenAI GPT-4o mini {'✅' if client else '❌'} | 
        Blindagem: YFinance v2.0 🔒</p>
        <p style='margin-top: 0.5rem; font-size: 0.8rem;'>
            <span style='background: rgba(99, 110, 250, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; margin: 0 0.3rem;'>Python</span>
            <span style='background: rgba(99, 110, 250, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; margin: 0 0.3rem;'>Pandas</span>
            <span style='background: rgba(138, 43, 226, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; margin: 0 0.3rem;'>OpenAI</span>
            <span style='background: rgba(0, 204, 150, 0.2); padding: 0.3rem 0.8rem; border-radius: 20px; margin: 0 0.3rem;'>Blindagem</span>
        </p>
        <p style='margin-top: 1rem; font-size: 0.85rem; color: #64748b;'>
            ⚠️ As análises geradas por IA são para fins informativos e não constituem recomendação de investimento.
        </p>
    </div>
""", unsafe_allow_html=True)
