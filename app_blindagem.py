import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. CONFIGURAÇÃO INICIAL
# ============================================================================
st.set_page_config(page_title="Blindagem Financeira Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
    }
    div.stButton > button:first-child:hover {
        background-color: #00aa55;
        transform: scale(1.05);
        transition: all 0.3s ease;
    }
    .metric-card {
        background-color: #1e2630;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #00cc66;
        margin-bottom: 15px;
    }
    .status-blindada {
        background-color: rgba(0, 204, 102, 0.2);
        color: #00ff88;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        border: 1px solid #00cc66;
    }
    .status-observar {
        background-color: rgba(255, 204, 0, 0.2);
        color: #ffcc00;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        border: 1px solid #ffcc00;
    }
    .status-analisar {
        background-color: rgba(255, 107, 107, 0.2);
        color: #ff6b6b;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        border: 1px solid #ff6b6b;
    }
    .ticker-badge {
        background-color: #1e3a28;
        color: #00ff88;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        margin: 2px;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Blindagem Financeira Pro 4.2")
st.caption("Análise fundamentalista avançada para ações brasileiras")

# ============================================================================
# 2. SISTEMA DE FAVORITOS
# ============================================================================
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return f.read()
    return "ITSA4, BBSE3, PETR4, VALE3, BBDC4, WEGE3"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f:
        f.write(texto)

# ============================================================================
# 3. CONFIGURAÇÕES DA SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Configurações")

# Lista de tickers
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area("📋 Lista de Tickers (separados por vírgula):", 
                                     value=lista_inicial, 
                                     height=120,
                                     help="Exemplo: ITSA4, PETR4, VALE3, BBSE3")

col_save, col_clear = st.sidebar.columns(2)
with col_save:
    if st.button("💾 Salvar", use_container_width=True):
        salvar_favoritos(tickers_input)
        st.sidebar.success("Lista salva!")
with col_clear:
    if st.button("🧹 Limpar", use_container_width=True):
        tickers_input = ""
        st.rerun()

st.sidebar.divider()

# Parâmetros de filtro
st.sidebar.subheader("🎯 Critérios de Análise")
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20, 
                                 help="Margem de segurança mínima usando fórmula de Graham")
y_bazin_min = st.sidebar.slider("Yield Bazin Mínimo (%)", 4, 12, 6,
                                help="Dividend yield mínimo para cálculo do preço teto Bazin")

st.sidebar.divider()

# Configurações avançadas
st.sidebar.subheader("⚡ Performance")
usar_cache = st.sidebar.checkbox("Usar cache inteligente", value=True,
                                 help="Armazena dados por 10 minutos para evitar requisições repetidas")
delay_requisicoes = st.sidebar.slider("Intervalo entre requisições (segundos)", 1.0, 10.0, 3.0, 0.5,
                                      help="Aumente este valor se estiver recebendo erros de rate limiting")

# ============================================================================
# 4. SISTEMA DE CACHE AVANÇADO
# ============================================================================
cache_data = {}
CACHE_DURATION = 600  # 10 minutos

def get_from_cache(ticker):
    """Recupera dados do cache se estiverem válidos"""
    if not usar_cache or ticker not in cache_data:
        return None
    
    cache_entry = cache_data[ticker]
    if time.time() - cache_entry['timestamp'] < CACHE_DURATION:
        return cache_entry['data']
    else:
        # Cache expirado
        del cache_data[ticker]
        return None

def save_to_cache(ticker, data):
    """Salva dados no cache"""
    if usar_cache:
        cache_data[ticker] = {
            'data': data,
            'timestamp': time.time(),
            'source': 'yfinance'
        }

# ============================================================================
# 5. COLETA DE DADOS ROBUSTA DO YAHOO FINANCE
# ============================================================================
def get_yahoo_data(ticker):
    """
    Coleta dados do Yahoo Finance com múltiplas camadas de fallback
    """
    t_clean = ticker.strip().upper().replace('.SA', '')
    
    # Verificar cache primeiro
    cached = get_from_cache(t_clean)
    if cached:
        return cached, None
    
    try:
        # Tentativa 1: Usar Ticker com timeout
        stock = yf.Ticker(t_clean + ".SA")
        
        # Adicionar delay configurável
        time.sleep(delay_requisicoes)
        
        # Obter informações - tentar múltiplas fontes
        info = stock.info
        
        # Estratégia para obter preço
        preco = 0
        price_sources = [
            ('currentPrice', info.get('currentPrice')),
            ('regularMarketPrice', info.get('regularMarketPrice')),
            ('ask', info.get('ask')),
            ('bid', info.get('bid')),
            ('previousClose', info.get('previousClose'))
        ]
        
        for source_name, source_value in price_sources:
            if source_value and source_value > 0:
                preco = source_value
                break
        
        # Se ainda não tem preço, tentar histórico
        if preco <= 0:
            try:
                hist = stock.history(period="1d", timeout=10)
                if not hist.empty and 'Close' in hist.columns:
                    preco = hist['Close'].iloc[-1]
            except:
                pass
        
        # Validar preço
        if preco <= 0:
            return None, "Preço não disponível"
        
        # Obter Dividend Yield
        dy = 0
        dy_sources = [
            ('dividendYield', info.get('dividendYield')),
            ('trailingAnnualDividendYield', info.get('trailingAnnualDividendYield')),
            ('forwardAnnualDividendYield', info.get('forwardAnnualDividendYield'))
        ]
        
        for source_name, source_value in dy_sources:
            if source_value:
                dy_val = source_value
                # Converter para percentual se necessário
                if dy_val < 1:
                    dy = dy_val * 100
                else:
                    dy = dy_val
                break
        
        # Outras métricas fundamentais
        dados = {
            "Ação": t_clean,
            "Preço": preco,
            "DY %": dy,
            "LPA": info.get('trailingEps', 0) or 0,
            "VPA": info.get('bookValue', 0) or 0,
            "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0,
            "Liquidez_Corr": info.get('currentRatio', 0) or 0,
            "Fonte": "Yahoo Finance",
            "Div_Anual": preco * (dy / 100) if dy > 0 else 0
        }
        
        # Salvar no cache
        save_to_cache(t_clean, dados)
        
        return dados, None
        
    except Exception as e:
        erro_msg = str(e).lower()
        
        # Mapear erros comuns para mensagens amigáveis
        if "rate" in erro_msg or "429" in erro_msg:
            return None, f"Rate limit atingido para {t_clean}. Aumente o intervalo nas configurações."
        elif "not found" in erro_msg:
            return None, f"Ação {t_clean} não encontrada no Yahoo Finance."
        elif "timeout" in erro_msg:
            return None, f"Timeout ao buscar {t_clean}. Verifique sua conexão."
        else:
            return None, f"Erro ao buscar {t_clean}: {str(e)}"

# ============================================================================
# 6. FUNÇÕES DE ANÁLISE
# ============================================================================
def calcular_graham(lpa, vpa):
    """Calcula preço justo pela fórmula de Graham"""
    if lpa > 0 and vpa > 0:
        return np.sqrt(22.5 * lpa * vpa)
    return 0

def calcular_bazin(div_anual, y_min):
    """Calcula preço teto pela fórmula de Bazin"""
    if div_anual > 0 and y_min > 0:
        return div_anual / (y_min / 100)
    return 0

def calcular_score(row):
    """Calcula score de qualidade (0-5)"""
    score = 0
    score += 1 if row['ROE'] > 0.08 else 0      # ROE > 8%
    score += 1 if row['Margem_Liq'] > 0.08 else 0  # Margem > 8%
    score += 1 if row['Liquidez_Corr'] > 0.8 else 0  # Liquidez > 0.8
    score += 1 if row['LPA'] > 0 else 0          # LPA positivo
    score += 1 if row['DY %'] > 4 else 0         # DY > 4%
    return score

def definir_status(row, margem_min):
    """Define status da ação baseado nos critérios"""
    if row['Graham_Justo'] <= 0:
        return "🔍 Dados Insuficientes"
    elif row['Margem_Graham'] >= margem_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
        return "💎 BLINDADA"
    elif row['Margem_Graham'] > 10 or row['Preço'] <= row['Bazin_Teto']:
        return "⚠️ Observar"
    else:
        return "📊 Analisar"

# ============================================================================
# 7. INTERFACE PRINCIPAL
# ============================================================================
tab1, tab2 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda"])

with tab1:
    st.header("🎯 Análise Fundamentalista Avançada")
    
    # Painel de controle
    col_control, col_stats = st.columns([1, 2])
    
    with col_control:
        if st.button("🚀 Analisar Mercado", type="primary", use_container_width=True):
            st.session_state.analisar = True
        else:
            if 'analisar' not in st.session_state:
                st.session_state.analisar = False
    
    with col_stats:
        if st.session_state.get('analisar', False):
            tickers = [t.strip() for t in tickers_input.split(',') if t.strip()]
            if tickers:
                st.markdown(f"<div class='ticker-badge'>📊 {len(tickers)} tickers</div>", unsafe_allow_html=True)
    
    if st.session_state.get('analisar', False):
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not lista:
            st.error("❌ Adicione pelo menos um ticker para análise.")
            st.session_state.analisar = False
        else:
            # Limitar número de tickers para evitar rate limiting
            max_tickers = min(len(lista), 12)
            if len(lista) > max_tickers:
                st.warning(f"⚠️ Analisando os primeiros {max_tickers} tickers para otimizar performance.")
                lista = lista[:max_tickers]
            
            # Inicializar containers
            progress_container = st.empty()
            results_container = st.empty()
            error_container = st.empty()
            
            # Coletar dados
            with progress_container.container():
                st.subheader("📡 Coletando dados...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                lista_dados = []
                lista_erros = []
                
                for i, ticker in enumerate(lista):
                    status_text.text(f"Buscando {ticker}... ({i+1}/{len(lista)})")
                    
                    dados, erro = get_yahoo_data(ticker)
                    
                    if dados:
                        lista_dados.append(dados)
                    elif erro:
                        lista_erros.append(f"**{ticker}:** {erro}")
                    
                    progress_bar.progress((i + 1) / len(lista))
            
            # Limpar containers de progresso
            progress_container.empty()
            status_text.empty()
            
            # Processar resultados
            if lista_dados:
                df = pd.DataFrame(lista_dados)
                
                # Calcular métricas
                df['Graham_Justo'] = df.apply(lambda x: calcular_graham(x['LPA'], x['VPA']), axis=1)
                df['Margem_Graham'] = df.apply(
                    lambda x: ((x['Graham_Justo'] - x['Preço']) / x['Graham_Justo']) * 100 
                    if x['Graham_Justo'] > 0 else 0, 
                    axis=1
                )
                df['Bazin_Teto'] = df.apply(lambda x: calcular_bazin(x['Div_Anual'], y_bazin_min), axis=1)
                df['Score'] = df.apply(calcular_score, axis=1)
                df['STATUS'] = df.apply(lambda x: definir_status(x, m_graham_min), axis=1)
                
                # Ordenar resultados
                df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])
                
                with results_container.container():
                    # Métricas resumidas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("📈 Ações Analisadas", len(df))
                    with col2:
                        blindadas = len(df[df['STATUS'] == '💎 BLINDADA'])
                        st.metric("💎 Blindadas", blindadas)
                    with col3:
                        st.metric("📊 DY Médio", f"{df['DY %'].mean():.2f}%")
                    with col4:
                        st.metric("🎯 Margem Média", f"{df['Margem_Graham'].mean():.1f}%")
                    
                    st.divider()
                    
                    # Gráfico de dispersão
                    if len(df[df['Graham_Justo'] > 0]) >= 3:
                        df_plot = df[df['Graham_Justo'] > 0].copy()
                        
                        fig = px.scatter(
                            df_plot,
                            x='Margem_Graham',
                            y='Score',
                            size='DY %',
                            color='STATUS',
                            text='Ação',
                            hover_data=['Preço', 'Fonte'],
                            title='📊 Mapa de Oportunidades - Margem Graham vs Score',
                            color_discrete_map={
                                '💎 BLINDADA': '#00cc66',
                                '⚠️ Observar': '#ffcc00',
                                '📊 Analisar': '#ff6b6b',
                                '🔍 Dados Insuficientes': '#888888'
                            },
                            size_max=20
                        )
                        
                        fig.update_traces(
                            textposition='top center',
                            marker=dict(line=dict(width=1, color='white')),
                            textfont=dict(size=12, color='white')
                        )
                        
                        fig.update_layout(
                            xaxis_title="Margem Graham (%) ← Mais barata | Mais cara →",
                            yaxis_title="Score (0-5) ← Menor qualidade | Maior qualidade →",
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            hoverlabel=dict(
                                bgcolor="#1e2630",
                                font_size=14,
                                font_color="white"
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabela de resultados
                    st.subheader("📋 Resultados Detalhados")
                    
                    # Formatar DataFrame
                    display_cols = ['Ação', 'Preço', 'DY %', 'Graham_Justo', 
                                  'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS']
                    
                    if 'Fonte' in df.columns:
                        display_cols.append('Fonte')
                    
                    df_display = df[display_cols].copy()
                    
                    # Função para formatar status com HTML
                    def format_status(val):
                        if val == '💎 BLINDADA':
                            return '<span class="status-blindada">💎 BLINDADA</span>'
                        elif val == '⚠️ Observar':
                            return '<span class="status-observar">⚠️ Observar</span>'
                        elif val == '📊 Analisar':
                            return '<span class="status-analisar">📊 Analisar</span>'
                        else:
                            return val
                    
                    # Aplicar formatação
                    styled_df = df_display.copy()
                    styled_df['STATUS'] = styled_df['STATUS'].apply(format_status)
                    
                    # Mostrar tabela
                    st.markdown(styled_df.to_html(escape=False, index=False, 
                                                 formatters={
                                                     'Preço': 'R$ {:,.2f}'.format,
                                                     'DY %': '{:.2f}%'.format,
                                                     'Graham_Justo': 'R$ {:,.2f}'.format,
                                                     'Margem_Graham': '{:.1f}%'.format,
                                                     'Bazin_Teto': 'R$ {:,.2f}'.format
                                                 }), unsafe_allow_html=True)
                    
                    # Botões de ação
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        csv = df.to_csv(index=False, sep=';', decimal=',')
                        st.download_button(
                            label="📥 Exportar CSV",
                            data=csv,
                            file_name=f"blindagem_analise_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col_btn2:
                        if st.button("🔄 Nova Análise", use_container_width=True):
                            st.session_state.analisar = False
                            st.rerun()
                    
                    with col_btn3:
                        if st.button("🧹 Limpar Cache", use_container_width=True):
                            cache_data.clear()
                            st.success("Cache limpo com sucesso!")
                            st.rerun()
            
            # Mostrar erros se houver
            if lista_erros:
                with error_container.container():
                    with st.expander("⚠️ Detalhes dos Erros", expanded=False):
                        for erro in lista_erros:
                            st.warning(erro)
                        
                        st.info("""
                        **💡 Soluções para erros de conexão:**
                        
                        1. **Aumente o intervalo** entre requisições nas configurações (recomendado: 3-5 segundos)
                        2. **Reduza o número** de tickers por análise (máximo 10-12)
                        3. **Verifique sua conexão** com a internet
                        4. **Tente novamente** em alguns minutos
                        5. **Use tickers líquidos** (ex: PETR4, VALE3, ITSA4, BBSE3)
                        """)
            
            if not lista_dados and lista_erros:
                st.error("""
                ❌ Não foi possível obter dados para nenhum ticker.
                
                **Ações recomendadas:**
                1. Verifique se os tickers estão corretos (formato: PETR4, VALE3, etc.)
                2. Aumente o intervalo para 5-10 segundos nas configurações
                3. Tente novamente em alguns minutos
                4. Verifique sua conexão com a internet
                """)

with tab2:
    st.header("💰 Simulador de Renda Passiva")
    
    st.info("""
    **ℹ️ Como funciona:**
    Esta ferramenta simula quanto sua carteira pode render em dividendos com base
    nos preços atuais e dividend yields das ações selecionadas.
    """)
    
    # Input principal
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        aporte = st.number_input(
            "💵 Valor do Aporte (R$):",
            min_value=100.0,
            value=5000.0,
            step=500.0,
            help="Valor que você pretende investir"
        )
    
    with col_input2:
        estrategia = st.selectbox(
            "🎯 Estratégia de Alocação:",
            ["Igualitária", "Por Dividend Yield", "Por Margem de Segurança", "Personalizada"],
            help="Como distribuir o valor entre as ações"
        )
    
    # Carregar tickers disponíveis
    tickers_disponiveis = [t.strip() for t in tickers_input.split(',') if t.strip()]
    
    if not tickers_disponiveis:
        st.warning("Adicione tickers nas configurações para usar o simulador.")
    else:
        # Seleção de ações
        st.subheader("📋 Seleção da Carteira")
        
        acoes_selecionadas = st.multiselect(
            "Selecione as ações para sua carteira:",
            options=tickers_disponiveis,
            default=tickers_disponiveis[:4] if len(tickers_disponiveis) > 4 else tickers_disponiveis,
            help="Escolha até 8 ações para otimizar performance"
        )
        
        if len(acoes_selecionadas) > 8:
            st.warning("⚠️ Limitando a 8 ações para melhor performance.")
            acoes_selecionadas = acoes_selecionadas[:8]
        
        if acoes_selecionadas and st.button("🎯 Calcular Projeção", type="primary"):
            with st.spinner("Calculando projeção de renda..."):
                # Coletar dados das ações selecionadas
                dados_carteira = []
                for ticker in acoes_selecionadas:
                    dados, erro = get_yahoo_data(ticker)
                    if dados:
                        dados_carteira.append(dados)
                
                if dados_carteira:
                    df_carteira = pd.DataFrame(dados_carteira)
                    
                    # Calcular métricas de análise
                    df_carteira['Graham_Justo'] = df_carteira.apply(
                        lambda x: calcular_graham(x['LPA'], x['VPA']), axis=1
                    )
                    df_carteira['Margem_Graham'] = df_carteira.apply(
                        lambda x: ((x['Graham_Justo'] - x['Preço']) / x['Graham_Justo']) * 100 
                        if x['Graham_Justo'] > 0 else 0, 
                        axis=1
                    )
                    
                    # Calcular pesos conforme estratégia
                    if estrategia == "Igualitária":
                        df_carteira['Peso %'] = 100 / len(df_carteira)
                    
                    elif estrategia == "Por Dividend Yield":
                        total_dy = df_carteira['DY %'].sum()
                        if total_dy > 0:
                            df_carteira['Peso %'] = (df_carteira['DY %'] / total_dy) * 100
                        else:
                            df_carteira['Peso %'] = 100 / len(df_carteira)
                    
                    elif estrategia == "Por Margem de Segurança":
                        # Ponderar por margem de Graham (ações com maior margem recebem mais peso)
                        margens = df_carteira['Margem_Graham'].clip(lower=0)  # Remove valores negativos
                        total_margem = margens.sum()
                        if total_margem > 0:
                            df_carteira['Peso %'] = (margens / total_margem) * 100
                        else:
                            df_carteira['Peso %'] = 100 / len(df_carteira)
                    
                    else:  # Personalizada
                        pesos = []
                        for acao in acoes_selecionadas:
                            peso = st.number_input(
                                f"Peso para {acao} (%)",
                                min_value=0.0,
                                max_value=100.0,
                                value=100/len(acoes_selecionadas),
                                key=f"peso_{acao}"
                            )
                            pesos.append(peso)
                        
                        total_pesos = sum(pesos)
                        if total_pesos > 0:
                            df_carteira['Peso %'] = [p/total_pesos*100 for p in pesos]
                        else:
                            df_carteira['Peso %'] = 100 / len(df_carteira)
                    
                    # Calcular alocação
                    df_carteira['Valor Alocado'] = aporte * (df_carteira['Peso %'] / 100)
                    df_carteira['Qtd Sugerida'] = (df_carteira['Valor Alocado'] / df_carteira['Preço']).apply(np.floor)
                    df_carteira['Qtd Sugerida'] = df_carteira['Qtd Sugerida'].clip(lower=0)  # Remove negativos
                    df_carteira['Investimento Real'] = df_carteira['Qtd Sugerida'] * df_carteira['Preço']
                    df_carteira['Renda Mensal'] = (df_carteira['Qtd Sugerida'] * df_carteira['Div_Anual']) / 12
                    
                    # Totais
                    total_investido = df_carteira['Investimento Real'].sum()
                    renda_mensal = df_carteira['Renda Mensal'].sum()
                    renda_anual = renda_mensal * 12
                    
                    # Ajuste para valor realmente investido
                    if total_investido > 0:
                        yield_carteira = (renda_anual / total_investido) * 100
                    else:
                        yield_carteira = 0
                    
                    # Exibir resultados
                    st.success(f"## 📈 Projeção de Renda: **R$ {renda_mensal:,.2f} por mês**")
                    
                    # Métricas
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    
                    with col_m1:
                        st.metric("💰 Total Investido", f"R$ {total_investido:,.2f}")
                    
                    with col_m2:
                        st.metric("📅 Renda Mensal", f"R$ {renda_mensal:,.2f}")
                    
                    with col_m3:
                        st.metric("📊 Renda Anual", f"R$ {renda_anual:,.2f}")
                    
                    with col_m4:
                        st.metric("🎯 Yield da Carteira", f"{yield_carteira:.2f}%")
                    
                    st.divider()
                    
                    # Tabela de alocação
                    st.subheader("📋 Composição da Carteira")
                    
                    df_display = df_carteira[[
                        'Ação', 'Preço', 'DY %', 'Margem_Graham', 
                        'Peso %', 'Qtd Sugerida', 'Investimento Real', 'Renda Mensal'
                    ]].copy()
                    
                    # Formatação da tabela
                    st.dataframe(
                        df_display.style.format({
                            'Preço': 'R$ {:,.2f}',
                            'DY %': '{:.2f}%',
                            'Margem_Graham': '{:.1f}%',
                            'Peso %': '{:.1f}%',
                            'Investimento Real': 'R$ {:,.2f}',
                            'Renda Mensal': 'R$ {:,.2f}'
                        }).highlight_max(subset=['Renda Mensal'], color='#1e3a28')
                        .highlight_min(subset=['Margem_Graham'], color='#3a1e1e'),
                        use_container_width=True
                    )
                    
                    # Gráfico de distribuição
                    col_chart1, col_chart2 = st.columns(2)
                    
                    with col_chart1:
                        fig1 = px.pie(
                            df_carteira,
                            values='Investimento Real',
                            names='Ação',
                            title='💰 Distribuição do Investimento',
                            color_discrete_sequence=px.colors.sequential.Greens,
                            hole=0.3
                        )
                        fig1.update_traces(
                            textposition='inside',
                            textinfo='percent+label',
                            hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>(%{percent})'
                        )
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col_chart2:
                        fig2 = px.bar(
                            df_carteira.sort_values('Renda Mensal', ascending=False),
                            x='Ação',
                            y='Renda Mensal',
                            title='📅 Renda Mensal por Ação',
                            color='DY %',
                            color_continuous_scale='greens'
                        )
                        fig2.update_layout(
                            yaxis_title="Renda Mensal (R$)",
                            xaxis_title="",
                            plot_bgcolor='rgba(0,0,0,0)'
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # Resumo final
                    st.info(f"""
                    **📊 Resumo da Simulação:**
                    
                    • **Aporte inicial:** R$ {aporte:,.2f}
                    • **Total efetivamente investido:** R$ {total_investido:,.2f}
                    • **Sobra para caixa:** R$ {aporte - total_investido:,.2f}
                    • **Renda mensal estimada:** R$ {renda_mensal:,.2f}
                    • **Renda anual estimada:** R$ {renda_anual:,.2f}
                    • **Yield sobre investido:** {yield_carteira:.2f}% a.a.
                    
                    **💡 Dica:** Esta é uma projeção baseada em dados atuais. 
                    Dividendos podem variar e os preços das ações flutuam.
                    """)
                
                else:
                    st.error("Não foi possível obter dados das ações selecionadas. Tente novamente.")

# ============================================================================
# 8. RODAPÉ E INFORMAÇÕES
# ============================================================================
st.divider()

footer_col1, footer_col2 = st.columns([3, 1])

with footer_col1:
    st.caption(f"""
    🛡️ **Blindagem Financeira Pro 4.2** | Yahoo Finance | 
    📅 {datetime.now().strftime('%d/%m/%Y %H:%M')} | 
    ⚡ Dados para análise e educação financeira
    
    **Tickers na lista:** {len([t for t in tickers_input.split(',') if t.strip()])} | 
    **Cache:** {'Ativo' if usar_cache else 'Inativo'} | 
    **Intervalo:** {delay_requisicoes}s
    """)

with footer_col2:
    if st.button("🔄 Reiniciar", type="secondary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Informações de ajuda
with st.expander("❓ Ajuda e Dicas", expanded=False):
    st.markdown("""
    ### 🎯 **Como usar esta ferramenta:**
    
    1. **Adicione tickers** na caixa de texto (ex: ITSA4, PETR4, VALE3)
    2. **Configure os critérios** de análise (Graham e Bazin)
    3. **Clique em "Analisar Mercado"** para ver oportunidades
    4. **Use o simulador de renda** para planejar investimentos
    
    ### ⚡ **Para evitar erros de conexão:**
    
    - **Use intervalos maiores** (3-5 segundos) nas configurações
    - **Limite a 10-12 tickers** por análise
    - **Use tickers líquidos** (alta negociação)
    - **Ative o cache** para evitar requisições repetidas
    
    ### 📊 **Interpretação dos resultados:**
    
    - **💎 BLINDADA:** Atende todos os critérios rigorosos
    - **⚠️ Observar:** Atende parcialmente, merece análise
    - **📊 Analisar:** Precisa de estudo mais aprofundado
    - **🔍 Dados Insuficientes:** Informações incompletas
    
    ### 🔧 **Configurações recomendadas:**
    
    - **Margem Graham:** 20-25% (conservador)
    - **Yield Bazin:** 6-7% (realista)
    - **Intervalo:** 3 segundos para até 10 tickers
    - **Cache:** Sempre ativado
    """)
