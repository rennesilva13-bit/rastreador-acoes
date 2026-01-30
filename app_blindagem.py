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
st.set_page_config(
    page_title="Blindagem Financeira Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    
    /* Botões principais */
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #00aa55;
        transform: scale(1.02);
    }
    
    /* Métricas */
    .metric-card {
        background-color: #1e2630;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #00cc66;
        margin: 5px;
    }
    
    /* Badges de status */
    .badge-blindada {
        background-color: rgba(0, 204, 102, 0.2);
        color: #00ff88;
        padding: 4px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 14px;
        border: 1px solid #00cc66;
        display: inline-block;
    }
    
    .badge-observar {
        background-color: rgba(255, 204, 0, 0.2);
        color: #ffcc00;
        padding: 4px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 14px;
        border: 1px solid #ffcc00;
        display: inline-block;
    }
    
    .badge-analisar {
        background-color: rgba(255, 107, 107, 0.2);
        color: #ff6b6b;
        padding: 4px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 14px;
        border: 1px solid #ff6b6b;
        display: inline-block;
    }
    
    /* Tabelas */
    .dataframe {
        background-color: #1e2630;
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Progresso */
    .stProgress > div > div > div > div {
        background-color: #00cc66;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1e2630;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.title("🛡️ Blindagem Financeira Pro 4.3")
st.caption("Sistema avançado de análise fundamentalista - Yahoo Finance")

# ============================================================================
# 2. SISTEMA DE FAVORITOS
# ============================================================================
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    """Carrega a lista de tickers favoritos do arquivo"""
    if os.path.exists(FAVORITOS_FILE):
        try:
            with open(FAVORITOS_FILE, "r") as f:
                return f.read().strip()
        except:
            return "ITSA4, BBSE3, PETR4, VALE3, BBDC4"
    return "ITSA4, BBSE3, PETR4, VALE3, BBDC4"

def salvar_favoritos(texto):
    """Salva a lista de tickers favoritos no arquivo"""
    try:
        with open(FAVORITOS_FILE, "w") as f:
            f.write(texto)
        return True
    except:
        return False

# ============================================================================
# 3. CONFIGURAÇÕES DA SIDEBAR
# ============================================================================
st.sidebar.header("⚙️ Configurações")

# Lista de tickers
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area(
    "📋 Lista de Tickers:", 
    value=lista_inicial, 
    height=120,
    placeholder="Digite os tickers separados por vírgula\nEx: PETR4, VALE3, ITSA4, BBSE3",
    help="Ações brasileiras no formato: PETR4, VALE3, ITSA4"
)

# Botões de ação para tickers
col_save, col_clear = st.sidebar.columns(2)
with col_save:
    if st.button("💾 Salvar Lista", use_container_width=True):
        if salvar_favoritos(tickers_input):
            st.sidebar.success("Lista salva!")
        else:
            st.sidebar.error("Erro ao salvar lista")
with col_clear:
    if st.button("🗑️ Limpar", use_container_width=True):
        tickers_input = ""
        st.rerun()

st.sidebar.divider()

# Parâmetros de análise
st.sidebar.subheader("🎯 Critérios de Análise")

m_graham_min = st.sidebar.slider(
    "Margem Graham Mínima (%)", 
    0, 50, 20,
    help="Margem de segurança mínima segundo a fórmula de Graham"
)

y_bazin_min = st.sidebar.slider(
    "Yield Bazin Mínimo (%)", 
    4, 12, 6,
    help="Rendimento mínimo exigido para cálculo do preço teto Bazin"
)

st.sidebar.divider()

# Configurações de performance
st.sidebar.subheader("⚡ Performance")

usar_cache = st.sidebar.checkbox(
    "Usar cache (10 minutos)", 
    value=True,
    help="Armazena dados para evitar requisições repetidas"
)

delay_requisicoes = st.sidebar.slider(
    "Delay entre requisições (segundos)", 
    1.0, 10.0, 3.0, 0.5,
    help="Aumente se estiver recebendo erros de rate limiting"
)

# Botão para limpar cache
if st.sidebar.button("🧹 Limpar Cache", use_container_width=True):
    st.session_state.clear()
    st.sidebar.success("Cache limpo!")

# ============================================================================
# 4. SISTEMA DE CACHE SIMPLIFICADO
# ============================================================================
class SimpleCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, ticker):
        if not usar_cache:
            return None
        if ticker in self.cache:
            entry = self.cache[ticker]
            # Verificar se o cache ainda é válido (10 minutos)
            if time.time() - entry['time'] < 600:
                return entry['data']
            else:
                del self.cache[ticker]
        return None
    
    def set(self, ticker, data):
        if usar_cache:
            self.cache[ticker] = {
                'data': data,
                'time': time.time()
            }

# Inicializar cache na sessão
if 'cache' not in st.session_state:
    st.session_state.cache = SimpleCache()

# ============================================================================
# 5. FUNÇÃO DE COLETA DE DADOS DO YAHOO FINANCE
# ============================================================================
def get_yahoo_data(ticker):
    """
    Coleta dados do Yahoo Finance de forma robusta e com tratamento de erros
    """
    ticker_clean = ticker.strip().upper().replace('.SA', '')
    
    # Verificar cache primeiro
    cached_data = st.session_state.cache.get(ticker_clean)
    if cached_data:
        return cached_data, None
    
    try:
        # Formatar ticker para Yahoo Finance (.SA para ações brasileiras)
        yahoo_ticker = f"{ticker_clean}.SA"
        
        # Adicionar delay para evitar rate limiting
        time.sleep(delay_requisicoes)
        
        # Baixar dados
        acao = yf.Ticker(yahoo_ticker)
        
        # Tentar obter informações
        info = acao.info
        
        # Estratégia para obter o preço atual
        preco_atual = 0
        
        # Tentar múltiplas fontes de preço
        price_fields = ['currentPrice', 'regularMarketPrice', 'ask', 'bid', 'previousClose']
        for field in price_fields:
            if field in info and info[field] is not None:
                preco_atual = info[field]
                if preco_atual > 0:
                    break
        
        # Se ainda não tem preço, tentar histórico
        if preco_atual <= 0:
            try:
                hist = acao.history(period="1d")
                if not hist.empty and len(hist) > 0:
                    preco_atual = hist['Close'].iloc[-1]
            except:
                pass
        
        # Se ainda não tem preço, retornar erro
        if preco_atual <= 0:
            return None, "Preço não disponível"
        
        # Obter Dividend Yield
        dividend_yield = 0
        if 'dividendYield' in info and info['dividendYield'] is not None:
            dy_val = info['dividendYield']
            # Converter para percentual (Yahoo retorna decimal)
            dividend_yield = dy_val * 100 if dy_val < 1 else dy_val
        
        # Outras métricas fundamentais
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
        
        # Calcular dividendos anuais
        dados["Div_Anual"] = dados["Preço"] * (dados["DY %"] / 100)
        
        # Salvar no cache
        st.session_state.cache.set(ticker_clean, dados)
        
        return dados, None
        
    except Exception as e:
        error_msg = str(e)
        
        # Mensagens de erro amigáveis
        if "rate" in error_msg.lower() or "429" in error_msg:
            return None, "Rate limit atingido. Aumente o delay nas configurações."
        elif "not found" in error_msg.lower():
            return None, f"Ticker {ticker_clean} não encontrado."
        else:
            return None, f"Erro ao buscar {ticker_clean}: {error_msg[:100]}"

# ============================================================================
# 6. FUNÇÕES DE ANÁLISE FUNDAMENTALISTA
# ============================================================================
def calcular_preco_justo_graham(lpa, vpa):
    """Calcula preço justo usando a fórmula de Graham"""
    if lpa > 0 and vpa > 0:
        return np.sqrt(22.5 * lpa * vpa)
    return 0

def calcular_preco_teto_bazin(div_anual, yield_minimo):
    """Calcula preço teto usando a fórmula de Bazin"""
    if div_anual > 0 and yield_minimo > 0:
        return div_anual / (yield_minimo / 100)
    return 0

def calcular_score_fundamentalista(dados):
    """Calcula score de qualidade fundamentalista (0-5 pontos)"""
    score = 0
    
    # ROE > 8%
    if dados.get('ROE', 0) > 0.08:
        score += 1
    
    # Margem Líquida > 8%
    if dados.get('Margem_Liq', 0) > 0.08:
        score += 1
    
    # Liquidez Corrente > 0.8
    if dados.get('Liquidez_Corr', 0) > 0.8:
        score += 1
    
    # LPA positivo
    if dados.get('LPA', 0) > 0:
        score += 1
    
    # DY > 4%
    if dados.get('DY %', 0) > 4:
        score += 1
    
    return score

def classificar_acao(dados, margem_minima):
    """Classifica a ação com base nos critérios"""
    if dados['Graham_Justo'] <= 0:
        return "🔍 Dados Insuf."
    
    margem_graham = dados['Margem_Graham']
    preco_teto_bazin = dados['Bazin_Teto']
    score = dados['Score']
    
    # Critério para ação BLINDADA
    if (margem_graham >= margem_minima and 
        dados['Preço'] <= preco_teto_bazin and 
        score >= 3):
        return "💎 BLINDADA"
    
    # Critério para ação em OBSERVAÇÃO
    elif margem_graham > 10 or dados['Preço'] <= preco_teto_bazin:
        return "⚠️ Observar"
    
    # Demais casos
    else:
        return "📊 Analisar"

# ============================================================================
# 7. INTERFACE PRINCIPAL - ABA DE ANÁLISE
# ============================================================================
tab_analise, tab_simulador = st.tabs(["🔍 Análise de Oportunidades", "💰 Simulador de Renda"])

with tab_analise:
    st.header("🎯 Busca por Oportunidades de Investimento")
    
    # Painel de controle
    col_btn, col_info = st.columns([1, 2])
    
    with col_btn:
        btn_analisar = st.button(
            "🚀 Analisar Mercado", 
            type="primary", 
            use_container_width=True,
            key="btn_analise"
        )
    
    with col_info:
        if btn_analisar:
            num_tickers = len([t for t in tickers_input.split(',') if t.strip()])
            st.info(f"🔍 Analisando {num_tickers} ticker(s)...")
    
    # Executar análise quando o botão for clicado
    if btn_analisar:
        tickers_lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not tickers_lista:
            st.error("❌ Adicione pelo menos um ticker na lista de configurações.")
        else:
            # Limitar número de tickers para evitar timeout
            max_tickers = min(len(tickers_lista), 10)
            if len(tickers_lista) > max_tickers:
                st.warning(f"⚠️ Analisando os primeiros {max_tickers} tickers para otimizar performance.")
                tickers_lista = tickers_lista[:max_tickers]
            
            # Container para progresso
            progress_container = st.empty()
            
            with progress_container.container():
                st.subheader("📡 Coletando dados...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                dados_coletados = []
                erros_coletados = []
                
                # Coletar dados para cada ticker
                for i, ticker in enumerate(tickers_lista):
                    status_text.text(f"Buscando {ticker}... ({i+1}/{len(tickers_lista)})")
                    
                    dados, erro = get_yahoo_data(ticker)
                    
                    if dados:
                        dados_coletados.append(dados)
                    elif erro:
                        erros_coletados.append(f"{ticker}: {erro}")
                    
                    # Atualizar barra de progresso
                    progress_bar.progress((i + 1) / len(tickers_lista))
            
            # Limpar container de progresso
            progress_container.empty()
            
            # Processar dados coletados
            if dados_coletados:
                df = pd.DataFrame(dados_coletados)
                
                # Calcular métricas de análise
                df['Graham_Justo'] = df.apply(
                    lambda x: calcular_preco_justo_graham(x['LPA'], x['VPA']), 
                    axis=1
                )
                
                df['Margem_Graham'] = df.apply(
                    lambda x: ((x['Graham_Justo'] - x['Preço']) / x['Graham_Justo']) * 100 
                    if x['Graham_Justo'] > 0 else 0, 
                    axis=1
                )
                
                df['Bazin_Teto'] = df.apply(
                    lambda x: calcular_preco_teto_bazin(x['Div_Anual'], y_bazin_min), 
                    axis=1
                )
                
                df['Score'] = df.apply(calcular_score_fundamentalista, axis=1)
                
                df['Status'] = df.apply(
                    lambda x: classificar_acao(x, m_graham_min), 
                    axis=1
                )
                
                # Ordenar resultados
                df = df.sort_values(
                    by=['Status', 'Margem_Graham'], 
                    ascending=[True, False]
                )
                
                # Exibir métricas resumidas
                st.subheader("📊 Resultados da Análise")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Analisado", len(df))
                
                with col2:
                    blindadas = len(df[df['Status'] == '💎 BLINDADA'])
                    st.metric("Oportunidades 💎", blindadas)
                
                with col3:
                    st.metric("DY Médio", f"{df['DY %'].mean():.2f}%")
                
                with col4:
                    st.metric("Margem Média", f"{df['Margem_Graham'].mean():.1f}%")
                
                # Gráfico de dispersão
                if len(df) >= 3:
                    st.subheader("📈 Mapa de Oportunidades")
                    
                    # Filtrar apenas ações com dados suficientes
                    df_grafico = df[df['Graham_Justo'] > 0].copy()
                    
                    if len(df_grafico) >= 2:
                        fig = px.scatter(
                            df_grafico,
                            x='Margem_Graham',
                            y='Score',
                            size='DY %',
                            color='Status',
                            hover_name='Ação',
                            hover_data=['Preço', 'DY %'],
                            title='Margem Graham vs Score Fundamentalista',
                            color_discrete_map={
                                '💎 BLINDADA': '#00cc66',
                                '⚠️ Observar': '#ffcc00',
                                '📊 Analisar': '#ff6b6b',
                                '🔍 Dados Insuf.': '#888888'
                            }
                        )
                        
                        fig.update_layout(
                            xaxis_title="Margem Graham (%)",
                            yaxis_title="Score (0-5)",
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white')
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                
                # Tabela de resultados
                st.subheader("📋 Detalhes por Ação")
                
                # Selecionar e ordenar colunas
                colunas_exibicao = [
                    'Ação', 'Preço', 'DY %', 'Graham_Justo', 
                    'Margem_Graham', 'Bazin_Teto', 'Score', 'Status'
                ]
                
                df_exibicao = df[colunas_exibicao].copy()
                
                # Formatar valores
                def formatar_valor(valor, formato):
                    if pd.isna(valor):
                        return "-"
                    if formato == "moeda":
                        return f"R$ {valor:,.2f}"
                    elif formato == "percentual":
                        return f"{valor:.2f}%"
                    elif formato == "decimal":
                        return f"{valor:.2f}"
                    return str(valor)
                
                # Aplicar formatação
                df_exibicao['Preço'] = df_exibicao['Preço'].apply(lambda x: formatar_valor(x, "moeda"))
                df_exibicao['DY %'] = df_exibicao['DY %'].apply(lambda x: formatar_valor(x, "percentual"))
                df_exibicao['Graham_Justo'] = df_exibicao['Graham_Justo'].apply(lambda x: formatar_valor(x, "moeda"))
                df_exibicao['Margem_Graham'] = df_exibicao['Margem_Graham'].apply(lambda x: formatar_valor(x, "percentual"))
                df_exibicao['Bazin_Teto'] = df_exibicao['Bazin_Teto'].apply(lambda x: formatar_valor(x, "moeda"))
                df_exibicao['Score'] = df_exibicao['Score'].apply(lambda x: formatar_valor(x, "decimal"))
                
                # Exibir tabela
                st.dataframe(
                    df_exibicao,
                    use_container_width=True,
                    height=400
                )
                
                # Botões de ação
                col_export, col_nova = st.columns(2)
                
                with col_export:
                    # Converter para CSV
                    csv = df.to_csv(index=False, sep=';', decimal=',')
                    st.download_button(
                        label="📥 Exportar CSV",
                        data=csv,
                        file_name=f"analise_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_nova:
                    if st.button("🔄 Nova Análise", use_container_width=True):
                        st.rerun()
            
            # Mostrar erros se houver
            if erros_coletados:
                with st.expander("⚠️ Log de Erros", expanded=False):
                    for erro in erros_coletados:
                        st.warning(erro)
                    
                    st.info("""
                    **💡 Dicas para evitar erros:**
                    1. Verifique se os tickers estão corretos (ex: PETR4, VALE3)
                    2. Aumente o delay entre requisições nas configurações
                    3. Use menos tickers por análise (recomendado: 5-8)
                    4. Verifique sua conexão com a internet
                    """)
            
            # Se nenhum dado foi coletado
            if not dados_coletados and erros_coletados:
                st.error("""
                ❌ Não foi possível obter dados para nenhum ticker.
                
                **Possíveis soluções:**
                1. Aumente o delay para 5-10 segundos nas configurações
                2. Verifique os tickers (use formato: ITSA4, PETR4, VALE3)
                3. Tente novamente em alguns minutos
                4. Use apenas tickers de alta liquidez
                """)

with tab_simulador:
    st.header("💰 Simulador de Renda Passiva")
    
    st.info("""
    **ℹ️ Simule quanto sua carteira pode render em dividendos com base nos preços atuais.**
    Os cálculos são baseados nos dividend yields atuais das ações selecionadas.
    """)
    
    # Inputs do simulador
    col_valor, col_estrategia = st.columns(2)
    
    with col_valor:
        valor_aporte = st.number_input(
            "💵 Valor do Aporte (R$):",
            min_value=100.0,
            value=5000.0,
            step=500.0,
            help="Valor total que você pretende investir"
        )
    
    with col_estrategia:
        estrategia_alocacao = st.selectbox(
            "📊 Estratégia de Alocação:",
            ["Igualitária", "Por Dividend Yield", "Personalizada"],
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
            "Escolha as ações para sua carteira:",
            options=tickers_disponiveis,
            default=tickers_disponiveis[:min(5, len(tickers_disponiveis))],
            max_selections=8,
            help="Selecione até 8 ações"
        )
        
        if acoes_selecionadas:
            # Botão para calcular
            if st.button("🎯 Calcular Projeção", type="primary"):
                with st.spinner("Calculando projeção de renda..."):
                    # Coletar dados das ações selecionadas
                    dados_simulacao = []
                    for ticker in acoes_selecionadas:
                        dados, _ = get_yahoo_data(ticker)
                        if dados:
                            dados_simulacao.append(dados)
                    
                    if dados_simulacao:
                        df_simulacao = pd.DataFrame(dados_simulacao)
                        
                        # Calcular pesos conforme estratégia
                        if estrategia_alocacao == "Igualitária":
                            df_simulacao['Peso %'] = 100 / len(df_simulacao)
                        
                        elif estrategia_alocacao == "Por Dividend Yield":
                            total_dy = df_simulacao['DY %'].sum()
                            if total_dy > 0:
                                df_simulacao['Peso %'] = (df_simulacao['DY %'] / total_dy) * 100
                            else:
                                df_simulacao['Peso %'] = 100 / len(df_simulacao)
                        
                        else:  # Personalizada
                            st.subheader("⚖️ Defina os pesos manualmente:")
                            pesos = []
                            for i, acao in enumerate(acoes_selecionadas):
                                peso = st.slider(
                                    f"Peso para {acao} (%)",
                                    0, 100,
                                    int(100 / len(acoes_selecionadas)),
                                    key=f"peso_{i}"
                                )
                                pesos.append(peso)
                            
                            total_pesos = sum(pesos)
                            if total_pesos > 0:
                                df_simulacao['Peso %'] = [p/total_pesos*100 for p in pesos]
                            else:
                                df_simulacao['Peso %'] = 100 / len(df_simulacao)
                        
                        # Calcular alocação
                        df_simulacao['Valor Alocado'] = valor_aporte * (df_simulacao['Peso %'] / 100)
                        df_simulacao['Qtd Sugerida'] = (df_simulacao['Valor Alocado'] / df_simulacao['Preço']).apply(np.floor)
                        df_simulacao['Qtd Sugerida'] = df_simulacao['Qtd Sugerida'].clip(lower=0)
                        df_simulacao['Investimento Real'] = df_simulacao['Qtd Sugerida'] * df_simulacao['Preço']
                        df_simulacao['Renda Mensal'] = (df_simulacao['Qtd Sugerida'] * df_simulacao['Div_Anual']) / 12
                        
                        # Totais
                        total_investido = df_simulacao['Investimento Real'].sum()
                        renda_mensal = df_simulacao['Renda Mensal'].sum()
                        renda_anual = renda_mensal * 12
                        
                        # Calcular yield da carteira
                        if total_investido > 0:
                            yield_carteira = (renda_anual / total_investido) * 100
                        else:
                            yield_carteira = 0
                        
                        # Exibir resultados
                        st.success(f"## 📈 Projeção: **R$ {renda_mensal:,.2f} por mês**")
                        
                        # Métricas
                        col_met1, col_met2, col_met3 = st.columns(3)
                        
                        with col_met1:
                            st.metric("💰 Total Investido", f"R$ {total_investido:,.2f}")
                        
                        with col_met2:
                            st.metric("📅 Renda Mensal", f"R$ {renda_mensal:,.2f}")
                        
                        with col_met3:
                            st.metric("📊 Yield Anual", f"{yield_carteira:.2f}%")
                        
                        # Tabela detalhada
                        st.subheader("📋 Detalhes da Alocação")
                        
                        df_detalhes = df_simulacao[[
                            'Ação', 'Preço', 'DY %', 'Peso %',
                            'Qtd Sugerida', 'Investimento Real', 'Renda Mensal'
                        ]].copy()
                        
                        # Formatar para exibição
                        df_detalhes['Preço'] = df_detalhes['Preço'].apply(lambda x: f"R$ {x:,.2f}")
                        df_detalhes['DY %'] = df_detalhes['DY %'].apply(lambda x: f"{x:.2f}%")
                        df_detalhes['Peso %'] = df_detalhes['Peso %'].apply(lambda x: f"{x:.1f}%")
                        df_detalhes['Qtd Sugerida'] = df_detalhes['Qtd Sugerida'].apply(lambda x: f"{int(x):,}")
                        df_detalhes['Investimento Real'] = df_detalhes['Investimento Real'].apply(lambda x: f"R$ {x:,.2f}")
                        df_detalhes['Renda Mensal'] = df_detalhes['Renda Mensal'].apply(lambda x: f"R$ {x:,.2f}")
                        
                        st.dataframe(df_detalhes, use_container_width=True)
                        
                        # Gráfico de pizza
                        st.subheader("📊 Distribuição da Carteira")
                        
                        fig = px.pie(
                            df_simulacao,
                            values='Investimento Real',
                            names='Ação',
                            title='Distribuição do Investimento',
                            color_discrete_sequence=px.colors.sequential.Greens
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Resumo
                        st.info(f"""
                        **📈 Resumo da Simulação:**
                        
                        • **Aporte inicial:** R$ {valor_aporte:,.2f}
                        • **Investimento efetivo:** R$ {total_investido:,.2f}
                        • **Sobra para caixa:** R$ {valor_aporte - total_investido:,.2f}
                        • **Renda mensal estimada:** R$ {renda_mensal:,.2f}
                        • **Renda anual estimada:** R$ {renda_anual:,.2f}
                        • **Yield sobre investido:** {yield_carteira:.2f}% a.a.
                        
                        **⚠️ Importante:** Esta é uma projeção baseada em dados atuais.
                        Dividendos podem variar e os preços das ações flutuam ao longo do tempo.
                        """)
                    
                    else:
                        st.error("Não foi possível obter dados das ações selecionadas. Tente novamente.")

# ============================================================================
# 8. RODAPÉ E INFORMAÇÕES
# ============================================================================
st.divider()

# Informações do sistema
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption(f"**Versão:** 4.3 • **Data:** {datetime.now().strftime('%d/%m/%Y')}")

with col_footer2:
    num_tickers = len([t for t in tickers_input.split(',') if t.strip()])
    st.caption(f"**Tickers na lista:** {num_tickers}")

with col_footer3:
    st.caption("**Fonte:** Yahoo Finance")

# Ajuda e informações
with st.expander("📚 Ajuda e Instruções", expanded=False):
    st.markdown("""
    ### 🎯 **Como usar esta ferramenta:**
    
    1. **Adicione os tickers** que deseja analisar na caixa de texto da sidebar
    2. **Configure os critérios** de análise (Margem Graham e Yield Bazin)
    3. **Clique em "Analisar Mercado"** para buscar oportunidades
    4. **Use o simulador de renda** para planejar investimentos
    
    ### ⚡ **Dicas para melhor performance:**
    
    - **Use delay de 3-5 segundos** entre requisições
    - **Analise até 10 tickers** por vez
    - **Ative o cache** para evitar requisições repetidas
    - **Use tickers líquidos** (alta negociação na B3)
    
    ### 📊 **Interpretação dos resultados:**
    
    - **💎 BLINDADA:** Atende todos os critérios rigorosos (recomendada)
    - **⚠️ Observar:** Atende parcialmente, merece análise
    - **📊 Analisar:** Precisa de estudo mais aprofundado
    - **🔍 Dados Insuf.:** Informações incompletas para análise
    
    ### 🎯 **Critérios para ação BLINDADA:**
    
    1. Margem Graham ≥ configurada (padrão: 20%)
    2. Preço atual ≤ Preço Teto Bazin
    3. Score fundamentalista ≥ 3 (de 0-5)
    
    ### ⚠️ **Aviso importante:**
    
    Esta ferramenta fornece análises baseadas em dados públicos do Yahoo Finance.
    Os resultados são para fins educacionais e de análise. Sempre faça sua própria
    pesquisa antes de investir. O mercado de ações envolve riscos.
    """)

# Botão de reinício no final
if st.button("🔄 Reiniciar Aplicação", type="secondary", use_container_width=True):
    st.session_state.clear()
    st.rerun()
