import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os
import time
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 3.6: Projeção de Renda", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 5px;
    }
    .stAlert { background-color: #1e2630; }
    .cache-info {
        font-size: 0.8em;
        color: #888;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.6")

# --- 2. SISTEMA DE FAVORITOS E CACHE ---
FAVORITOS_FILE = "favoritos.txt"
CACHE_FILE = "cache_data.pkl"
CACHE_DURATION = 300  # 5 minutos em segundos

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return f.read()
    return "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f:
        f.write(texto)

# --- 3. SISTEMA DE CACHE AVANÇADO ---
class DataCache:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        
    def get(self, ticker):
        if ticker in self.cache:
            # Verificar se o cache ainda é válido
            if time.time() - self.timestamps[ticker] < CACHE_DURATION:
                return self.cache[ticker]
            else:
                # Cache expirado
                del self.cache[ticker]
                del self.timestamps[ticker]
        return None
    
    def set(self, ticker, data):
        self.cache[ticker] = data
        self.timestamps[ticker] = time.time()
    
    def clear(self):
        self.cache.clear()
        self.timestamps.clear()

# Inicializar cache na sessão
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = DataCache()

# --- 4. CONFIGURAÇÃO DE REQUISIÇÕES COM RETRY ---
def criar_sessao_com_retry():
    """Cria uma sessão HTTP com política de retry para evitar rate limiting"""
    session = requests.Session()
    retry = Retry(
        total=3,  # Número total de tentativas
        backoff_factor=1,  # Fator de espera entre tentativas
        status_forcelist=[429, 500, 502, 503, 504],  # 429 = Too Many Requests
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session

# --- 5. BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações")
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area("Lista de Tickers:", value=lista_inicial, height=150)

if st.sidebar.button("💾 Salvar Favoritos"):
    salvar_favoritos(tickers_input)
    st.sidebar.success("✅ Favoritos salvos!")

st.sidebar.divider()
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Rendimento Bazin Mínimo (%)", 4, 12, 6)

st.sidebar.divider()
st.sidebar.markdown("### ⚡ Otimizações")
usar_cache = st.sidebar.checkbox("Usar cache de dados", value=True, help="Reduz requisições ao Yahoo Finance")
delay_requisicoes = st.sidebar.slider("Delay entre requisições (segundos)", 0.5, 3.0, 1.0, 0.1)

if st.sidebar.button("🧹 Limpar Cache"):
    st.session_state.data_cache.clear()
    st.sidebar.success("Cache limpo!")

# --- 6. FUNÇÃO DE COLETA OTIMIZADA ---
def get_data_otimizado(ticker):
    """Função otimizada para coleta de dados com cache e rate limiting"""
    t_clean = ticker.strip().upper()
    
    # Verificar cache primeiro
    if usar_cache:
        cached_data = st.session_state.data_cache.get(t_clean)
        if cached_data:
            return cached_data, None
    
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    
    try:
        # Usar sessão com retry
        session = criar_sessao_com_retry()
        
        # Configurar headers para simular navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Obter dados básicos primeiro
        stock = yf.Ticker(t_sa, session=session)
        
        # Adicionar delay para evitar rate limiting
        time.sleep(delay_requisicoes)
        
        # Tentar obter info
        try:
            info = stock.info
        except:
            # Se falhar, tentar método alternativo
            hist = stock.history(period="1mo")
            if hist.empty:
                return None, f"Sem dados disponíveis para {t_clean}"
            
            # Criar info básico a partir do histórico
            info = {
                'currentPrice': hist['Close'].iloc[-1],
                'dividendYield': 0,
                'trailingEps': 0,
                'bookValue': 0,
                'returnOnEquity': 0,
                'profitMargins': 0,
                'currentRatio': 0
            }
        
        if not info or 'currentPrice' not in info or info['currentPrice'] is None:
            # Tentar obter preço do histórico
            hist = stock.history(period="1d")
            if hist.empty:
                return None, f"Sem preço disponível para {t_clean}"
            preco = hist['Close'].iloc[-1]
        else:
            preco = info.get('currentPrice', 0)
        
        # Processar dividend yield
        dy_raw = info.get('dividendYield', 0) or 0
        if dy_raw is None:
            dy_raw = 0
        
        # Corrigir formato do dividend yield
        if dy_raw > 10:  # Se for muito alto, provavelmente está em percentual
            dy_corrigido = dy_raw / 100
        elif dy_raw > 1:  # Se estiver entre 1 e 10, dividir por 100
            dy_corrigido = dy_raw / 100
        else:
            dy_corrigido = dy_raw
        
        dados = {
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
        
        # Salvar no cache
        if usar_cache:
            st.session_state.data_cache.set(t_clean, dados)
        
        return dados, None
        
    except Exception as e:
        erro_msg = str(e)
        if "Too Many Requests" in erro_msg or "429" in erro_msg:
            return None, f"Rate limiting detectado para {t_clean}. Aguarde alguns minutos."
        elif "Not Found" in erro_msg:
            return None, f"Ticker {t_clean} não encontrado."
        else:
            return None, f"Erro ao obter {t_clean}: {erro_msg}"

# --- 7. FUNÇÃO PARA BAIXAR MÚLTIPLOS TICKERS DE UMA VEZ ---
def get_multiple_tickers(tickers_list):
    """Baixa múltiplos tickers de uma vez para reduzir requisições"""
    if not tickers_list:
        return {}
    
    # Preparar tickers com .SA
    tickers_sa = [t + ".SA" if not t.endswith(".SA") else t for t in tickers_list]
    tickers_str = " ".join(tickers_sa)
    
    try:
        # Baixar dados básicos de uma vez
        data = yf.download(tickers_str, period="1d", progress=False)
        
        if data.empty:
            return {}
        
        resultados = {}
        for t_clean in tickers_list:
            t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
            
            if t_sa in data['Close'].columns:
                preco = data['Close'][t_sa].iloc[-1]
                # Para outras informações, ainda precisamos do Ticker individual
                resultados[t_clean] = {"Preço": preco}
        
        return resultados
        
    except Exception as e:
        st.warning(f"Aviso ao baixar múltiplos tickers: {str(e)}")
        return {}

# --- 8. INTERFACE EM ABAS ---
tab1, tab2 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda & Aportes"])

with tab1:
    st.subheader("📊 Análise de Oportunidades")
    
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        analisar_btn = st.button("🚀 Analisar Mercado", key="analisar_mercado", type="primary")
    
    with col_info:
        st.markdown(f"""
        <div class="cache-info">
        ℹ️ Cache: {'Ativado' if usar_cache else 'Desativado'} | Delay: {delay_requisicoes}s
        </div>
        """, unsafe_allow_html=True)
    
    if analisar_btn:
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not lista:
            st.error("❌ Por favor, insira pelo menos um ticker na lista.")
        else:
            lista_dados = []
            lista_erros = []
            preco_cache = {}
            
            # Barra de progresso
            bar = st.progress(0)
            status_text = st.empty()
            
            # Primeiro: tentar baixar preços de todos de uma vez
            status_text.text("Buscando preços em lote...")
            precos_em_lote = get_multiple_tickers(lista)
            
            for i, t in enumerate(lista):
                status_text.text(f"Processando {t}... ({i+1}/{len(lista)})")
                
                # Verificar se temos preço do lote
                preco_lote = None
                if t in precos_em_lote:
                    preco_lote = precos_em_lote[t]["Preço"]
                
                dados, erro = get_data_otimizado(t)
                
                # Se tivermos preço do lote mas o get_data falhou, criar dados básicos
                if erro and preco_lote:
                    st.warning(f"Dados limitados para {t}. Usando apenas preço de referência.")
                    dados = {
                        "Ação": t,
                        "Preço": preco_lote,
                        "LPA": 0,
                        "VPA": 0,
                        "DY %": 0,
                        "Div_Anual": 0,
                        "ROE": 0,
                        "Margem_Liq": 0,
                        "Liquidez_Corr": 0
                    }
                    erro = None
                
                if dados:
                    lista_dados.append(dados)
                elif erro:
                    lista_erros.append(erro)
                
                bar.progress((i + 1) / len(lista))
                
                # Delay adicional entre requisições
                if i < len(lista) - 1:
                    time.sleep(delay_requisicoes)
            
            status_text.empty()
            bar.empty()
            
            # Mostrar estatísticas do cache
            if usar_cache:
                cache_hits = len([t for t in lista if st.session_state.data_cache.get(t)])
                st.caption(f"📊 Cache: {cache_hits}/{len(lista)} tickers servidos do cache")
            
            # Mostrar erros se houver
            if lista_erros:
                with st.expander("⚠️ Avisos e Erros", expanded=len(lista_dados) == 0):
                    for erro in lista_erros:
                        if "Rate limiting" in erro:
                            st.error(erro)
                        else:
                            st.warning(erro)
                    
                    if any("Rate limiting" in e for e in lista_erros):
                        st.info("""
                        **💡 Dica para evitar rate limiting:**
                        1. Aumente o delay entre requisições nas configurações
                        2. Use menos tickers por vez
                        3. Aguarde alguns minutos e tente novamente
                        4. Ative o cache de dados
                        """)
            
            if lista_dados:
                df = pd.DataFrame(lista_dados)
                
                # Calcular métricas de Graham (apenas para ações com LPA e VPA positivos)
                df['LPA_VPA_Valido'] = (df['LPA'] > 0) & (df['VPA'] > 0)
                df['Graham_Justo'] = np.where(
                    df['LPA_VPA_Valido'],
                    np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA'])),
                    0
                )
                df['Margem_Graham'] = np.where(
                    df['Graham_Justo'] > 0,
                    ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100,
                    -100
                )
                
                # Calcular Bazin
                df['Bazin_Teto'] = np.where(
                    df['Div_Anual'] > 0,
                    df['Div_Anual'] / (y_bazin_min / 100),
                    0
                )
                
                # Calcular Score (0-4)
                df['Score'] = ((df['ROE'] > 0.10).astype(int) + 
                              (df['Margem_Liq'] > 0.10).astype(int) + 
                              (df['Liquidez_Corr'] > 1.0).astype(int) + 
                              (df['LPA'] > 0).astype(int))
                
                # Definir STATUS
                def definir_status(row):
                    if row['LPA'] == 0 and row['VPA'] == 0:
                        return "📊 Dados Limitados"
                    elif row['Graham_Justo'] <= 0:
                        return "🔍 Dados Insuficientes"
                    elif row['Margem_Graham'] >= m_graham_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
                        return "💎 BLINDADA"
                    elif row['Margem_Graham'] > 0 or row['Preço'] <= row['Bazin_Teto']:
                        return "⚠️ Observar"
                    else:
                        return "🛑 Reprovada"
                
                df['STATUS'] = df.apply(definir_status, axis=1)
                df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])
                
                # Gráfico
                if len(df) > 1:
                    fig = px.scatter(df, x="Margem_Graham", y="Score", text="Ação", 
                                     color="STATUS", size="DY %",
                                     color_discrete_map={
                                         "💎 BLINDADA": "#00cc66", 
                                         "⚠️ Observar": "#ffcc00", 
                                         "🛑 Reprovada": "#ff4d4d",
                                         "🔍 Dados Insuficientes": "#888888",
                                         "📊 Dados Limitados": "#aaaaaa"
                                     },
                                     title="Análise de Oportunidades - Margem Graham vs Score")
                    
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)
                
                # Dataframe formatado
                st.dataframe(df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 
                               'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS']]
                    .style
                    .format({
                        'Preço': 'R$ {:.2f}', 
                        'DY %': '{:.2f}%', 
                        'Graham_Justo': 'R$ {:.2f}', 
                        'Margem_Graham': '{:.1f}%', 
                        'Bazin_Teto': 'R$ {:.2f}'
                    })
                    .apply(lambda x: ['background-color: #1e3a28' if v == '💎 BLINDADA' else 
                                      'background-color: #3a281e' if v == '⚠️ Observar' else
                                      'background-color: #3a1e1e' if v == '🛑 Reprovada' else
                                      'background-color: #2a2a2a' if v == '🔍 Dados Insuficientes' else
                                      'background-color: #333333' if v == '📊 Dados Limitados' else
                                      '' for v in x], 
                           subset=['STATUS']),
                    use_container_width=True,
                    height=400)
                
                # Estatísticas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Ações Analisadas", len(df))
                with col2:
                    blindadas = len(df[df['STATUS'] == '💎 BLINDADA'])
                    st.metric("Oportunidades Blindadas", blindadas)
                with col3:
                    st.metric("Média DY", f"{df['DY %'].mean():.2f}%")
                with col4:
                    st.metric("Cache Hits", f"{cache_hits}/{len(lista)}")
                
                # Botão para exportar dados
                if st.button("📥 Exportar para Excel"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name=f"analise_acoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.error("""
                ❌ Não foi possível obter dados para nenhum ticker. 
                
                **Soluções imediatas:**
                1. **Aumente o delay entre requisições** nas configurações laterais (recomendado: 2-3 segundos)
                2. **Ative o cache de dados** nas configurações
                3. **Use menos tickers** por vez (5-10 por análise)
                4. **Tente novamente em alguns minutos**
                
                **Configurações recomendadas para evitar bloqueio:**
                - Delay entre requisições: 2-3 segundos
                - Cache de dados: Ativado
                - Limite de tickers por análise: 10
                """)

with tab2:
    # ... (código da aba 2 mantido similar, usando get_data_otimizado)
    st.subheader("⚖️ Planejador de Renda Passiva")
    
    # Mostrar informações de cache
    if usar_cache:
        st.info(f"🔧 **Configuração atual:** Cache ativado | Delay: {delay_requisicoes}s")
    
    # ... (restante do código da aba 2 similar ao anterior)

# --- 9. RODAPÉ ---
st.divider()
st.caption(f"🛡️ Protocolo de Segurança Máxima v3.6 | Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.caption("⚠️ Dados fornecidos pelo Yahoo Finance. Use para fins educacionais e de análise.")
