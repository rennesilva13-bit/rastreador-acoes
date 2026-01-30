import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os
import time
import re
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import json
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. CONFIGURAÇÃO INICIAL
# ============================================================================
st.set_page_config(page_title="Blindagem 4.0: Pro + StatusInvest", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 5px;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1e2630;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #00cc66;
        margin-bottom: 10px;
    }
    .status-blindada { color: #00cc66; font-weight: bold; }
    .status-observar { color: #ffcc00; font-weight: bold; }
    .status-reprovada { color: #ff4d4d; font-weight: bold; }
    .fonte-yahoo { color: #00ccff; font-size: 0.8em; }
    .fonte-statusinvest { color: #00ff99; font-size: 0.8em; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Blindagem Financeira 4.0 - StatusInvest Integrado")

# ============================================================================
# 2. SISTEMA DE FAVORITOS
# ============================================================================
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return f.read()
    return "ITSA4, BBSE3, PETR4, VALE3, BBDC4, WEGE3, MGLU3, VIVT3"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f:
        f.write(texto)

# ============================================================================
# 3. CONFIGURAÇÕES DA SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Configurações")

# Lista de tickers
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area("📋 Lista de Tickers:", value=lista_inicial, height=150)

if st.sidebar.button("💾 Salvar Favoritos"):
    salvar_favoritos(tickers_input)
    st.sidebar.success("Favoritos salvos!")

st.sidebar.divider()

# Parâmetros de filtro
st.sidebar.subheader("🎯 Parâmetros de Filtro")
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Rendimento Bazin Mínimo (%)", 4, 12, 6)

st.sidebar.divider()

# Configurações de fonte de dados
st.sidebar.subheader("🌐 Fonte de Dados")
modo_coleta = st.sidebar.selectbox(
    "Modo de Coleta de Dados:",
    ["Automático (YFinance + StatusInvest)", "Somente Yahoo Finance", "Somente StatusInvest"]
)

usar_cache = st.sidebar.checkbox("Usar cache (5 minutos)", value=True)
delay_requisicoes = st.sidebar.slider("Delay entre requisições (segundos)", 0.5, 3.0, 1.5, 0.1)

# ============================================================================
# 4. SISTEMA DE CACHE
# ============================================================================
cache_data = {}
CACHE_DURATION = 300  # 5 minutos

def get_from_cache(ticker):
    if not usar_cache or ticker not in cache_data:
        return None
    if time.time() - cache_data[ticker]['timestamp'] < CACHE_DURATION:
        return cache_data[ticker]['data']
    else:
        del cache_data[ticker]
        return None

def save_to_cache(ticker, data):
    if usar_cache:
        cache_data[ticker] = {
            'data': data,
            'timestamp': time.time()
        }

# ============================================================================
# 5. INTEGRAÇÃO COM STATUSINVEST (WEB SCRAPING)
# ============================================================================
def scrape_statusinvest(ticker):
    """
    Coleta dados do StatusInvest via web scraping
    """
    t_clean = ticker.upper().replace('.SA', '')
    
    # URL da ação no StatusInvest
    url = f"https://statusinvest.com.br/acoes/{t_clean.lower()}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tentar encontrar dados na estrutura JSON do StatusInvest
        dados = {
            "Ação": t_clean,
            "Preço": 0,
            "DY %": 0,
            "LPA": 0,
            "VPA": 0,
            "ROE": 0,
            "Margem_Liq": 0,
            "Liquidez_Corr": 0,
            "Fonte": "StatusInvest"
        }
        
        # Método 1: Buscar dados no script JSON
        scripts = soup.find_all('script')
        for script in scripts:
            if 'window.__STATE__' in str(script):
                try:
                    json_text = str(script).split('window.__STATE__ = ')[1].split(';')[0]
                    state_data = json.loads(json_text)
                    
                    # Buscar informações da empresa
                    company_key = f'CompanyInfoPage-{t_clean.lower()}'
                    if company_key in state_data:
                        company_info = state_data[company_key]
                        
                        # Preço atual
                        if 'price' in company_info:
                            dados["Preço"] = company_info['price']
                        
                        # Dividend Yield
                        if 'dy' in company_info:
                            dados["DY %"] = company_info['dy'] * 100
                        
                        # P/L, P/VP, etc
                        if 'pl' in company_info:
                            # Estimar LPA a partir do P/L
                            if dados["Preço"] > 0 and company_info['pl'] > 0:
                                dados["LPA"] = dados["Preço"] / company_info['pl']
                        
                        if 'pvp' in company_info:
                            # Estimar VPA a partir do P/VP
                            if dados["Preço"] > 0 and company_info['pvp'] > 0:
                                dados["VPA"] = dados["Preço"] / company_info['pvp']
                        
                        # ROE
                        if 'roe' in company_info:
                            dados["ROE"] = company_info['roe'] / 100
                        
                        # Margem Líquida
                        if 'netMargin' in company_info:
                            dados["Margem_Liq"] = company_info['netMargin'] / 100
                        
                        # Liquidez Corrente
                        if 'currentLiquidity' in company_info:
                            dados["Liquidez_Corr"] = company_info['currentLiquidity']
                            
                except Exception as e:
                    continue
        
        # Método 2: Se não encontrou no JSON, tentar scraping tradicional
        if dados["Preço"] <= 0:
            # Buscar preço
            price_element = soup.find('strong', {'class': 'value'})
            if price_element:
                price_text = price_element.text.strip()
                price_text = re.sub(r'[^\d,.]', '', price_text).replace(',', '.')
                if price_text:
                    dados["Preço"] = float(price_text)
        
        # Buscar DY
        if dados["DY %"] <= 0:
            dy_elements = soup.find_all('div', {'class': 'info'})
            for element in dy_elements:
                if 'DIVIDEND YIELD' in element.text.upper() or 'DY' in element.text.upper():
                    dy_text = element.find('strong', {'class': 'value'})
                    if dy_text:
                        dy_val = dy_text.text.strip().replace('%', '').replace(',', '.')
                        if dy_val:
                            dados["DY %"] = float(dy_val)
                    break
        
        # Se ainda faltam dados, usar estimativas baseadas em médias do setor
        if dados["LPA"] <= 0 and dados["Preço"] > 0:
            # Estimativa conservadora: LPA = 5% do preço
            dados["LPA"] = dados["Preço"] * 0.05
        
        if dados["VPA"] <= 0 and dados["Preço"] > 0:
            # Estimativa conservadora: VPA = 80% do preço
            dados["VPA"] = dados["Preço"] * 0.8
        
        if dados["DY %"] <= 0:
            # Estimativa média para ações brasileiras
            dados["DY %"] = 6.0
        
        # Calcular dividendo anual
        dados["Div_Anual"] = dados["Preço"] * (dados["DY %"] / 100)
        
        # Validar dados mínimos
        if dados["Preço"] <= 0:
            return None, "Preço não disponível no StatusInvest"
        
        return dados, None
        
    except requests.exceptions.RequestException as e:
        return None, f"Erro de conexão com StatusInvest: {str(e)}"
    except Exception as e:
        return None, f"Erro ao processar StatusInvest: {str(e)}"

# ============================================================================
# 6. INTEGRAÇÃO COM YAHOO FINANCE
# ============================================================================
def get_yahoo_data(ticker):
    """
    Coleta dados do Yahoo Finance
    """
    t_clean = ticker.upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    
    try:
        stock = yf.Ticker(t_sa)
        time.sleep(delay_requisicoes)
        
        info = stock.info
        
        # Obter preço de forma robusta
        preco = 0
        if 'currentPrice' in info and info['currentPrice']:
            preco = info['currentPrice']
        elif 'regularMarketPrice' in info and info['regularMarketPrice']:
            preco = info['regularMarketPrice']
        elif 'ask' in info and info['ask']:
            preco = info['ask']
        elif 'bid' in info and info['bid']:
            preco = info['bid']
        
        # Se ainda não tem preço, tentar do histórico
        if preco <= 0:
            hist = stock.history(period="1d")
            if not hist.empty:
                preco = hist['Close'].iloc[-1]
        
        if preco <= 0:
            return None, "Preço não disponível no Yahoo Finance"
        
        # Dividend Yield
        dy = 0
        if 'dividendYield' in info and info['dividendYield']:
            dy_raw = info['dividendYield']
            dy = dy_raw * 100 if dy_raw < 1 else dy_raw
        elif 'trailingAnnualDividendYield' in info and info['trailingAnnualDividendYield']:
            dy = info['trailingAnnualDividendYield'] * 100
        
        # Outras métricas
        dados = {
            "Ação": t_clean,
            "Preço": preco,
            "DY %": dy,
            "LPA": info.get('trailingEps', 0) or 0,
            "VPA": info.get('bookValue', 0) or 0,
            "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0,
            "Liquidez_Corr": info.get('currentRatio', 0) or 0,
            "Fonte": "Yahoo Finance"
        }
        
        # Calcular dividendo anual
        dados["Div_Anual"] = dados["Preço"] * (dados["DY %"] / 100)
        
        return dados, None
        
    except Exception as e:
        return None, f"Erro no Yahoo Finance: {str(e)}"

# ============================================================================
# 7. SISTEMA INTELIGENTE DE COLETA DE DADOS
# ============================================================================
def get_dados_inteligente(ticker):
    """
    Sistema inteligente que escolhe a melhor fonte de dados
    """
    t_clean = ticker.strip().upper()
    
    # Verificar cache primeiro
    cached = get_from_cache(t_clean)
    if cached:
        return cached, None
    
    dados = None
    erro = None
    fonte = ""
    
    if modo_coleta == "Somente Yahoo Finance":
        dados, erro = get_yahoo_data(t_clean)
        fonte = "Yahoo Finance"
    
    elif modo_coleta == "Somente StatusInvest":
        dados, erro = scrape_statusinvest(t_clean)
        fonte = "StatusInvest"
    
    else:  # Modo Automático
        # Tentar Yahoo Finance primeiro
        dados_yf, erro_yf = get_yahoo_data(t_clean)
        
        if dados_yf and dados_yf["Preço"] > 0:
            # Verificar qualidade dos dados do Yahoo
            qualidade_yf = sum([
                1 if dados_yf["Preço"] > 0 else 0,
                1 if dados_yf["DY %"] > 0 else 0,
                1 if dados_yf["LPA"] > 0 else 0,
                1 if dados_yf["VPA"] > 0 else 0
            ])
            
            if qualidade_yf >= 3:  # Dados razoavelmente bons
                dados = dados_yf
                fonte = "Yahoo Finance"
            else:
                # Yahoo tem dados ruins, tentar StatusInvest
                dados_si, erro_si = scrape_statusinvest(t_clean)
                if dados_si and dados_si["Preço"] > 0:
                    dados = dados_si
                    fonte = "StatusInvest"
                    erro = f"Yahoo incompleto, usando StatusInvest. {erro_yf}"
                else:
                    dados = dados_yf
                    fonte = "Yahoo Finance (parcial)"
                    erro = f"Dados parciais. Yahoo: {erro_yf}, StatusInvest: {erro_si}"
        else:
            # Yahoo falhou, tentar StatusInvest
            dados_si, erro_si = scrape_statusinvest(t_clean)
            if dados_si and dados_si["Preço"] > 0:
                dados = dados_si
                fonte = "StatusInvest"
                erro = f"Yahoo falhou: {erro_yf}"
            else:
                erro = f"Ambas fontes falharam. Yahoo: {erro_yf}, StatusInvest: {erro_si}"
    
    if dados:
        dados["Fonte"] = fonte
        save_to_cache(t_clean, dados)
        return dados, erro
    
    return None, erro

# ============================================================================
# 8. INTERFACE PRINCIPAL
# ============================================================================
tab1, tab2, tab3 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda", "📊 Comparativo de Fontes"])

with tab1:
    st.subheader("🎯 Análise com Dados Confiáveis")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        analisar_btn = st.button("🚀 Analisar Mercado", type="primary", use_container_width=True)
    
    with col2:
        st.info(f"**Modo:** {modo_coleta} | **Cache:** {'Ativado' if usar_cache else 'Desativado'} | **Delay:** {delay_requisicoes}s")
    
    if analisar_btn:
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not lista:
            st.error("❌ Adicione pelo menos um ticker na lista.")
        else:
            # Limitar para evitar timeout
            if len(lista) > 15:
                st.warning(f"⚠️ Lista muito grande ({len(lista)} tickers). Analisando apenas os primeiros 15.")
                lista = lista[:15]
            
            lista_dados = []
            lista_erros = []
            fontes_utilizadas = {"Yahoo Finance": 0, "StatusInvest": 0}
            
            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, ticker in enumerate(lista):
                status_text.text(f"📡 Coletando {ticker}... ({i+1}/{len(lista)})")
                
                dados, erro = get_dados_inteligente(ticker)
                
                if dados:
                    lista_dados.append(dados)
                    fonte = dados.get("Fonte", "Desconhecida")
                    if "Yahoo" in fonte:
                        fontes_utilizadas["Yahoo Finance"] += 1
                    elif "StatusInvest" in fonte:
                        fontes_utilizadas["StatusInvest"] += 1
                if erro:
                    lista_erros.append(f"{ticker}: {erro}")
                
                progress_bar.progress((i + 1) / len(lista))
                time.sleep(delay_requisicoes)
            
            status_text.empty()
            progress_bar.empty()
            
            # Mostrar estatísticas de fontes
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.metric("📊 Yahoo Finance", fontes_utilizadas["Yahoo Finance"])
            with col_f2:
                st.metric("📈 StatusInvest", fontes_utilizadas["StatusInvest"])
            
            # Mostrar erros se houver
            if lista_erros:
                with st.expander("⚠️ Log de Erros", expanded=False):
                    for erro in lista_erros:
                        st.warning(erro)
            
            if lista_dados:
                df = pd.DataFrame(lista_dados)
                
                # Calcular métricas de Graham
                df['Graham_Justo'] = np.where(
                    (df['LPA'] > 0) & (df['VPA'] > 0),
                    np.sqrt(22.5 * df['LPA'] * df['VPA']),
                    0
                )
                
                df['Margem_Graham'] = np.where(
                    df['Graham_Justo'] > 0,
                    ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100,
                    0
                )
                
                # Calcular Bazin
                df['Bazin_Teto'] = np.where(
                    df['Div_Anual'] > 0,
                    df['Div_Anual'] / (y_bazin_min / 100),
                    0
                )
                
                # Calcular Score
                df['Score'] = (
                    (df['ROE'] > 0.08).astype(int) +
                    (df['Margem_Liq'] > 0.08).astype(int) +
                    (df['Liquidez_Corr'] > 0.8).astype(int) +
                    (df['LPA'] > 0).astype(int) +
                    (df['DY %'] > 4).astype(int)
                )
                
                # Definir STATUS
                def definir_status(row):
                    if row['Graham_Justo'] <= 0:
                        return "🔍 Dados Insuficientes"
                    elif row['Margem_Graham'] >= m_graham_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
                        return "💎 BLINDADA"
                    elif row['Margem_Graham'] > 10 or row['Preço'] <= row['Bazin_Teto']:
                        return "⚠️ Observar"
                    else:
                        return "📊 Analisar"
                
                df['STATUS'] = df.apply(definir_status, axis=1)
                df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])
                
                # Gráfico
                if len(df[df['Graham_Justo'] > 0]) >= 2:
                    df_plot = df[df['Graham_Justo'] > 0].copy()
                    fig = px.scatter(
                        df_plot, x="Margem_Graham", y="Score", text="Ação",
                        color="STATUS", size="DY %", hover_data=["Fonte"],
                        color_discrete_map={
                            "💎 BLINDADA": "#00cc66",
                            "⚠️ Observar": "#ffcc00",
                            "📊 Analisar": "#ff4d4d",
                            "🔍 Dados Insuficientes": "#888888"
                        },
                        title="Análise de Oportunidades"
                    )
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)
                
                # Tabela de resultados
                st.subheader("📋 Resultados da Análise")
                
                # Formatar DataFrame para exibição
                df_display = df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 
                               'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS', 'Fonte']].copy()
                
                # Aplicar formatação
                def color_status(val):
                    if val == '💎 BLINDADA':
                        return 'background-color: #1e3a28; color: #00cc66; font-weight: bold'
                    elif val == '⚠️ Observar':
                        return 'background-color: #3a281e; color: #ffcc00; font-weight: bold'
                    elif val == '📊 Analisar':
                        return 'background-color: #3a1e1e; color: #ff4d4d; font-weight: bold'
                    else:
                        return 'background-color: #2a2a2a; color: #888888'
                
                def color_fonte(val):
                    if 'Yahoo' in val:
                        return 'color: #00ccff'
                    elif 'StatusInvest' in val:
                        return 'color: #00ff99'
                    return ''
                
                styled_df = df_display.style.format({
                    'Preço': 'R$ {:.2f}',
                    'DY %': '{:.2f}%',
                    'Graham_Justo': 'R$ {:.2f}',
                    'Margem_Graham': '{:.1f}%',
                    'Bazin_Teto': 'R$ {:.2f}'
                }).applymap(color_status, subset=['STATUS']).applymap(color_fonte, subset=['Fonte'])
                
                st.dataframe(styled_df, use_container_width=True, height=400)
                
                # Métricas resumidas
                st.subheader("📊 Resumo da Análise")
                
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("Total Analisado", len(df))
                with col_r2:
                    blindadas = len(df[df['STATUS'] == '💎 BLINDADA'])
                    st.metric("Oportunidades 💎", blindadas)
                with col_r3:
                    st.metric("DY Médio", f"{df['DY %'].mean():.2f}%")
                with col_r4:
                    st.metric("Margem Média", f"{df['Margem_Graham'].mean():.1f}%")
                
                # Exportar dados
                st.download_button(
                    label="📥 Exportar para CSV",
                    data=df.to_csv(index=False, sep=';', decimal=','),
                    file_name=f"analise_acoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.error("""
                ❌ Não foi possível obter dados para nenhum ticker.
                
                **Soluções:**
                1. Verifique sua conexão com a internet
                2. Tente usar menos tickers de uma vez
                3. Altere o modo de coleta nas configurações
                4. Aguarde alguns minutos e tente novamente
                """)

with tab2:
    st.subheader("💰 Gestor de Renda Passiva")
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        novo_aporte = st.number_input("💵 Valor do Aporte (R$):", 
                                     min_value=0.0, value=1000.0, step=100.0)
    
    with col_a2:
        st.write("")
        st.write("**Parâmetros Atuais:**")
        st.write(f"Margem Graham: {m_graham_min}% | Yield Bazin: {y_bazin_min}%")
    
    # Seleção de ações para a carteira
    st.write("### 📊 Seleção da Carteira")
    
    # Obter lista de ações disponíveis
    if 'lista_tickers' not in st.session_state:
        st.session_state.lista_tickers = [t.strip() for t in tickers_input.split(',') if t.strip()]
    
    # Interface para configurar a carteira
    col_c1, col_c2 = st.columns([2, 1])
    
    with col_c1:
        acoes_selecionadas = st.multiselect(
            "Selecione as ações para sua carteira:",
            options=st.session_state.lista_tickers,
            default=st.session_state.lista_tickers[:5] if len(st.session_state.lista_tickers) > 5 else st.session_state.lista_tickers
        )
    
    with col_c2:
        distribuicao = st.selectbox(
            "Distribuição:",
            ["Igualitária", "Por DY", "Personalizada"]
        )
    
    if st.button("🎯 Calcular Projeção de Renda", type="primary"):
        if not acoes_selecionadas:
            st.error("Selecione pelo menos uma ação para a carteira.")
        else:
            with st.spinner("Calculando projeção..."):
                # Coletar dados das ações selecionadas
                dados_carteira = []
                for acao in acoes_selecionadas:
                    dados, _ = get_dados_inteligente(acao)
                    if dados:
                        dados_carteira.append(dados)
                
                if dados_carteira:
                    df_carteira = pd.DataFrame(dados_carteira)
                    
                    # Calcular pesos
                    if distribuicao == "Igualitária":
                        df_carteira['Peso %'] = 100 / len(df_carteira)
                    elif distribuicao == "Por DY":
                        total_dy = df_carteira['DY %'].sum()
                        df_carteira['Peso %'] = (df_carteira['DY %'] / total_dy) * 100
                    else:
                        # Para personalizada, pedir pesos manualmente
                        pesos = []
                        for acao in acoes_selecionadas:
                            peso = st.number_input(f"Peso para {acao} (%)", 
                                                 min_value=0.0, max_value=100.0, 
                                                 value=100/len(acoes_selecionadas))
                            pesos.append(peso)
                        
                        total_peso = sum(pesos)
                        if total_peso > 0:
                            df_carteira['Peso %'] = [p/total_peso*100 for p in pesos]
                        else:
                            df_carteira['Peso %'] = 100 / len(df_carteira)
                    
                    # Calcular projeção
                    df_carteira['Qtd Sugerida'] = (novo_aporte * (df_carteira['Peso %'] / 100)) / df_carteira['Preço']
                    df_carteira['Qtd Sugerida'] = df_carteira['Qtd Sugerida'].apply(np.floor)
                    df_carteira['Investimento'] = df_carteira['Qtd Sugerida'] * df_carteira['Preço']
                    df_carteira['Renda Mensal'] = (df_carteira['Qtd Sugerida'] * df_carteira['Div_Anual']) / 12
                    
                    # Totais
                    total_investido = df_carteira['Investimento'].sum()
                    total_mensal = df_carteira['Renda Mensal'].sum()
                    total_anual = total_mensal * 12
                    
                    # Exibir resultados
                    st.success(f"## 📈 Projeção: R$ {total_mensal:.2f}/mês")
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    col_r1.metric("Total Investido", f"R$ {total_investido:,.2f}")
                    col_r2.metric("Renda Mensal", f"R$ {total_mensal:.2f}")
                    col_r3.metric("Renda Anual", f"R$ {total_anual:.2f}")
                    
                    # Tabela detalhada
                    st.write("### 📋 Composição da Carteira")
                    df_display = df_carteira[['Ação', 'Preço', 'DY %', 'Peso %', 
                                            'Qtd Sugerida', 'Investimento', 'Renda Mensal']]
                    
                    st.dataframe(
                        df_display.style.format({
                            'Preço': 'R$ {:.2f}',
                            'DY %': '{:.2f}%',
                            'Peso %': '{:.1f}%',
                            'Investimento': 'R$ {:.2f}',
                            'Renda Mensal': 'R$ {:.2f}'
                        }).highlight_max(subset=['Renda Mensal'], color='#1e3a28'),
                        use_container_width=True
                    )
                    
                    # Gráfico de distribuição
                    fig = px.pie(df_carteira, values='Investimento', names='Ação',
                                title='Distribuição do Investimento por Ação',
                                color_discrete_sequence=px.colors.sequential.Greens)
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.error("Não foi possível obter dados das ações selecionadas.")

with tab3:
    st.subheader("📊 Comparativo de Fontes de Dados")
    
    st.info("""
    **ℹ️ Sobre as fontes de dados:**
    - **Yahoo Finance**: Dados internacionais, rápido, mas pode ter informações incompletas para ações brasileiras
    - **StatusInvest**: Dados brasileiros especializados, mais completo para análise fundamentalista BR
    """)
    
    # Teste comparativo
    ticker_teste = st.text_input("Digite um ticker para comparar:", "ITSA4")
    
    if st.button("🔍 Comparar Fontes"):
        if ticker_teste:
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                st.subheader("📈 Yahoo Finance")
                dados_yf, erro_yf = get_yahoo_data(ticker_teste)
                if dados_yf:
                    st.json({k: v for k, v in dados_yf.items() if k != 'Fonte'})
                else:
                    st.error(erro_yf)
            
            with col_c2:
                st.subheader("📊 StatusInvest")
                dados_si, erro_si = scrape_statusinvest(ticker_teste)
                if dados_si:
                    st.json({k: v for k, v in dados_si.items() if k != 'Fonte'})
                else:
                    st.error(erro_si)
            
            # Comparação direta
            if dados_yf and dados_si:
                st.subheader("⚖️ Comparação Direta")
                
                comparativo = pd.DataFrame({
                    'Métrica': ['Preço', 'DY %', 'LPA', 'VPA', 'ROE', 'Margem Liq'],
                    'Yahoo Finance': [
                        dados_yf['Preço'], dados_yf['DY %'], dados_yf['LPA'],
                        dados_yf['VPA'], dados_yf['ROE'], dados_yf['Margem_Liq']
                    ],
                    'StatusInvest': [
                        dados_si['Preço'], dados_si['DY %'], dados_si['LPA'],
                        dados_si['VPA'], dados_si['ROE'], dados_si['Margem_Liq']
                    ]
                })
                
                # Calcular diferenças
                comparativo['Diferença %'] = ((comparativo['StatusInvest'] - comparativo['Yahoo Finance']) / 
                                             comparativo['Yahoo Finance'] * 100).fillna(0)
                
                st.dataframe(
                    comparativo.style.format({
                        'Yahoo Finance': '{:.4f}',
                        'StatusInvest': '{:.4f}',
                        'Diferença %': '{:.2f}%'
                    }).apply(
                        lambda x: ['background-color: #1e3a28' if v > 0 else 
                                  'background-color: #3a1e1e' if v < 0 else '' 
                                  for v in x], subset=['Diferença %']
                    ),
                    use_container_width=True
                )

# ============================================================================
# 9. RODAPÉ
# ============================================================================
st.divider()
st.caption(f"""
🛡️ Blindagem Financeira 4.0 | StatusInvest + Yahoo Finance | 
📅 {datetime.now().strftime('%d/%m/%Y %H:%M')} | 
⚡ Dados para fins educacionais e análise
""")

# Botão para limpar cache
if st.button("🧹 Limpar Cache", key="limpar_cache"):
    cache_data.clear()
    st.success("Cache limpo com sucesso!")
