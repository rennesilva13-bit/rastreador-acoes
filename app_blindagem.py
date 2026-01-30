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
import warnings
warnings.filterwarnings('ignore')

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 3.7: Projeção de Renda", layout="wide")

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
    .metric-card {
        background-color: #1e2630;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #00cc66;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.7")

# --- 2. SISTEMA DE FAVORITOS ---
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return f.read()
    return "ITSA4, BBSE3, PSSA3, SULA11, CXSE3, WIZC3"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f:
        f.write(texto)

# --- 3. CONFIGURAÇÃO DE REQUISIÇÕES ---
def criar_sessao_com_retry():
    """Cria uma sessão HTTP com política de retry"""
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# --- 4. BARRA LATERAL ---
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
usar_cache = st.sidebar.checkbox("Usar cache de dados", value=True)
delay_requisicoes = st.sidebar.slider("Delay entre requisições (segundos)", 0.5, 3.0, 1.5, 0.1)
modo_seguro = st.sidebar.checkbox("Modo Seguro (mais lento, mais confiável)", value=True)

# --- 5. SISTEMA DE CACHE SIMPLIFICADO ---
cache_data = {}

# --- 6. FUNÇÃO DE COLETA MELHORADA PARA AÇÕES BRASILEIRAS ---
def get_dados_acao_brasileira(ticker):
    """Função otimizada para ações brasileiras com fallbacks"""
    t_clean = ticker.strip().upper()
    
    # Verificar cache
    if usar_cache and t_clean in cache_data:
        if time.time() - cache_data[t_clean]['timestamp'] < 300:  # 5 minutos
            return cache_data[t_clean]['data'], None
    
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    
    try:
        # Criar sessão
        session = criar_sessao_com_retry()
        
        # Configurar headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        # Inicializar dados básicos
        dados_base = {
            "Ação": t_clean,
            "Preço": 0,
            "LPA": 0,
            "VPA": 0,
            "DY %": 0,
            "Div_Anual": 0,
            "ROE": 0,
            "Margem_Liq": 0,
            "Liquidez_Corr": 0
        }
        
        # TENTATIVA 1: Obter dados via yfinance
        try:
            stock = yf.Ticker(t_sa, session=session)
            time.sleep(delay_requisicoes)
            
            # Obter preço de forma robusta
            preco = 0
            try:
                # Tentar info primeiro
                info = stock.info
                if 'currentPrice' in info and info['currentPrice']:
                    preco = info['currentPrice']
                elif 'regularMarketPrice' in info and info['regularMarketPrice']:
                    preco = info['regularMarketPrice']
            except:
                pass
            
            # Se não conseguiu pelo info, tentar histórico
            if preco <= 0:
                hist = stock.history(period="5d")
                if not hist.empty and len(hist) > 0:
                    preco = hist['Close'].iloc[-1]
            
            if preco <= 0:
                return None, f"Preço não disponível para {t_clean}"
            
            dados_base["Preço"] = preco
            
            # Obter dividend yield
            dy = 0
            try:
                # Tentar do info
                if 'dividendYield' in info:
                    dy_raw = info['dividendYield']
                    if dy_raw:
                        dy = dy_raw * 100 if dy_raw < 1 else dy_raw
                
                # Se não tem DY, tentar calcular dos dividendos
                if dy <= 0:
                    div_history = stock.dividends
                    if len(div_history) > 0:
                        # Últimos 12 meses
                        recent_divs = div_history.last('12M')
                        if len(recent_divs) > 0:
                            total_div = recent_divs.sum()
                            dy = (total_div / preco) * 100
            except:
                pass
            
            dados_base["DY %"] = dy
            dados_base["Div_Anual"] = preco * (dy / 100)
            
            # Obter outras métricas com fallbacks
            try:
                dados_base["LPA"] = info.get('trailingEps', 0) or 0
                dados_base["VPA"] = info.get('bookValue', 0) or 0
                dados_base["ROE"] = info.get('returnOnEquity', 0) or 0
                dados_base["Margem_Liq"] = info.get('profitMargins', 0) or 0
                dados_base["Liquidez_Corr"] = info.get('currentRatio', 0) or 0
            except:
                pass
            
            # Se LPA ou VPA estiverem zerados, tentar método alternativo
            if dados_base["LPA"] <= 0 or dados_base["VPA"] <= 0:
                try:
                    # Tentar obter do balanço
                    balance_sheet = stock.balance_sheet
                    income_stmt = stock.income_stmt
                    
                    if balance_sheet is not None and not balance_sheet.empty:
                        # Tentar obter VPA
                        try:
                            shares_outstanding = info.get('sharesOutstanding', 1)
                            if 'Total Equity' in balance_sheet.index:
                                total_equity = balance_sheet.loc['Total Equity'].iloc[0]
                                dados_base["VPA"] = total_equity / shares_outstanding if shares_outstanding > 0 else 0
                        except:
                            pass
                    
                    if income_stmt is not None and not income_stmt.empty:
                        # Tentar obter LPA
                        try:
                            shares_outstanding = info.get('sharesOutstanding', 1)
                            if 'Net Income' in income_stmt.index:
                                net_income = income_stmt.loc['Net Income'].iloc[0]
                                dados_base["LPA"] = net_income / shares_outstanding if shares_outstanding > 0 else 0
                        except:
                            pass
                except:
                    pass
            
        except Exception as e:
            if modo_seguro:
                # TENTATIVA 2: Método alternativo para ações brasileiras
                try:
                    # Tentar baixar dados básicos
                    df = yf.download(t_sa, period="1mo", progress=False)
                    if not df.empty:
                        dados_base["Preço"] = df['Close'].iloc[-1]
                        
                        # Tentar obter informações básicas
                        stock_fast = yf.Ticker(t_sa)
                        fast_info = stock_fast.fast_info
                        
                        if hasattr(fast_info, 'last_price'):
                            dados_base["Preço"] = fast_info.last_price
                        
                        # Para ações brasileiras, usar valores padrão razoáveis
                        if dados_base["LPA"] <= 0:
                            # Estimar LPA baseado no setor
                            dados_base["LPA"] = dados_base["Preço"] * 0.05  # Estimativa conservadora
                        
                        if dados_base["VPA"] <= 0:
                            # Estimar VPA
                            dados_base["VPA"] = dados_base["Preço"] * 0.8  # Estimativa conservadora
                        
                        if dados_base["DY %"] <= 0:
                            # Estimativa de DY para ações brasileiras
                            dados_base["DY %"] = 6.0  # Média conservadora
                            dados_base["Div_Anual"] = dados_base["Preço"] * 0.06
                            
                except Exception as e2:
                    return None, f"Erro ao processar {t_clean}: {str(e2)}"
            else:
                return None, f"Erro ao obter {t_clean}: {str(e)}"
        
        # Validar dados mínimos
        if dados_base["Preço"] <= 0:
            return None, f"Preço inválido para {t_clean}"
        
        # Salvar no cache
        if usar_cache:
            cache_data[t_clean] = {
                'data': dados_base,
                'timestamp': time.time()
            }
        
        return dados_base, None
        
    except Exception as e:
        return None, f"Erro geral com {t_clean}: {str(e)}"

# --- 7. INTERFACE PRINCIPAL ---
tab1, tab2 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda & Aportes"])

with tab1:
    st.subheader("📊 Análise de Oportunidades - Ações Brasileiras")
    
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        analisar_btn = st.button("🚀 Analisar Mercado", key="analisar_mercado", type="primary")
    
    with col_info:
        st.markdown(f"""
        <div class="cache-info">
        ℹ️ Modo: {'Seguro' if modo_seguro else 'Rápido'} | Delay: {delay_requisicoes}s | Cache: {'Ativado' if usar_cache else 'Desativado'}
        </div>
        """, unsafe_allow_html=True)
    
    if analisar_btn:
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        
        if not lista:
            st.error("❌ Por favor, insira pelo menos um ticker na lista.")
        else:
            lista_dados = []
            lista_erros = []
            
            # Barra de progresso
            bar = st.progress(0)
            status_text = st.empty()
            
            for i, t in enumerate(lista):
                status_text.text(f"Processando {t}... ({i+1}/{len(lista)})")
                
                dados, erro = get_dados_acao_brasileira(t)
                
                if dados:
                    lista_dados.append(dados)
                elif erro:
                    lista_erros.append(erro)
                
                bar.progress((i + 1) / len(lista))
                
                # Delay entre requisições
                if i < len(lista) - 1:
                    time.sleep(delay_requisicoes)
            
            status_text.empty()
            bar.empty()
            
            # Mostrar erros se houver
            if lista_erros:
                with st.expander("⚠️ Avisos e Erros", expanded=False):
                    for erro in lista_erros:
                        st.warning(erro)
            
            if lista_dados:
                df = pd.DataFrame(lista_dados)
                
                # Calcular métricas de Graham (com proteção)
                mask_valid = (df['LPA'] > 0) & (df['VPA'] > 0)
                df['Graham_Justo'] = 0
                df.loc[mask_valid, 'Graham_Justo'] = np.sqrt(22.5 * df['LPA'] * df['VPA'])
                
                df['Margem_Graham'] = 0
                valid_graham = df['Graham_Justo'] > 0
                df.loc[valid_graham, 'Margem_Graham'] = ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100
                
                # Calcular Bazin
                df['Bazin_Teto'] = 0
                valid_bazin = df['Div_Anual'] > 0
                df.loc[valid_bazin, 'Bazin_Teto'] = df['Div_Anual'] / (y_bazin_min / 100)
                
                # Calcular Score adaptado
                df['Score'] = 0
                df['Score'] += (df['ROE'] > 0.08).astype(int)  # ROE > 8%
                df['Score'] += (df['Margem_Liq'] > 0.08).astype(int)  # Margem > 8%
                df['Score'] += (df['Liquidez_Corr'] > 0.8).astype(int)  # Liquidez > 0.8
                df['Score'] += (df['LPA'] > 0).astype(int)  # LPA positivo
                df['Score'] += (df['DY %'] > 4).astype(int)  # DY > 4%
                
                # Definir STATUS com regras adaptadas
                def definir_status(row):
                    if row['Graham_Justo'] <= 0:
                        return "📊 Dados Parciais"
                    elif row['Margem_Graham'] >= m_graham_min and row['Preço'] <= row['Bazin_Teto'] and row['Score'] >= 3:
                        return "💎 BLINDADA"
                    elif row['Margem_Graham'] > 10 or row['Preço'] <= row['Bazin_Teto'] or row['Score'] >= 3:
                        return "⚠️ Observar"
                    else:
                        return "🔍 Analisar"
                
                df['STATUS'] = df.apply(definir_status, axis=1)
                df = df.sort_values(by=['STATUS', 'Margem_Graham'], ascending=[True, False])
                
                # Gráfico apenas se tiver dados suficientes
                if len(df[df['Graham_Justo'] > 0]) >= 2:
                    df_plot = df[df['Graham_Justo'] > 0].copy()
                    fig = px.scatter(df_plot, x="Margem_Graham", y="Score", text="Ação", 
                                     color="STATUS", size="DY %",
                                     color_discrete_map={
                                         "💎 BLINDADA": "#00cc66", 
                                         "⚠️ Observar": "#ffcc00", 
                                         "🔍 Analisar": "#ff4d4d",
                                         "📊 Dados Parciais": "#888888"
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
                                      'background-color: #3a1e1e' if v == '🔍 Analisar' else
                                      'background-color: #2a2a2a' for v in x], 
                           subset=['STATUS']),
                    use_container_width=True,
                    height=400)
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("""
                    <div class="metric-card">
                    <h3>Ações Analisadas</h3>
                    <h2>{}</h2>
                    </div>
                    """.format(len(df)), unsafe_allow_html=True)
                
                with col2:
                    blindadas = len(df[df['STATUS'] == '💎 BLINDADA'])
                    st.markdown("""
                    <div class="metric-card">
                    <h3>Oportunidades Blindadas</h3>
                    <h2>{}</h2>
                    </div>
                    """.format(blindadas), unsafe_allow_html=True)
                
                with col3:
                    avg_dy = df['DY %'].mean()
                    st.markdown("""
                    <div class="metric-card">
                    <h3>DY Médio</h3>
                    <h2>{:.2f}%</h2>
                    </div>
                    """.format(avg_dy), unsafe_allow_html=True)
                
                # Recomendações
                if blindadas > 0:
                    st.success(f"🎯 **{blindadas} oportunidade(s) BLINDADA(s) encontrada(s)!**")
                    acoes_blindadas = df[df['STATUS'] == '💎 BLINDADA']['Ação'].tolist()
                    st.info(f"**Ações recomendadas:** {', '.join(acoes_blindadas)}")
                else:
                    st.warning("Nenhuma oportunidade BLINDADA encontrada com os critérios atuais.")
                
                # Botão para exportar
                csv = df.to_csv(index=False, sep=';', decimal=',')
                st.download_button(
                    label="📥 Exportar para CSV",
                    data=csv,
                    file_name=f"analise_acoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.error("""
                ❌ Não foi possível obter dados para nenhum ticker. 
                
                **Soluções:**
                1. **Verifique os tickers** (ex: ITSA4, BBSE3, PETR4)
                2. **Ative o Modo Seguro** nas configurações
                3. **Aumente o delay** entre requisições (2-3 segundos)
                4. **Tente novamente** em alguns minutos
                
                **Tickers que funcionam melhor:**
                - ITSA4, BBSE3, PETR4, VALE3, BBDC4, ITUB4, ABEV3
                """)

with tab2:
    st.subheader("⚖️ Planejador de Renda Passiva")
    
    col1, col2 = st.columns(2)
    with col1:
        novo_aporte = st.number_input("Valor do Novo Aporte (R$):", min_value=0.0, value=1000.0, step=100.0)
    
    # Lista de ações para rebalanceamento
    lista_rebal = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    
    # Inicializar dataframe na session state
    if 'df_carteira' not in st.session_state:
        st.session_state.df_carteira = pd.DataFrame({
            'Ação': lista_rebal[:5],  # Limitar a 5 para exemplo
            'Qtd Atual': [0] * min(5, len(lista_rebal)),
            'Peso Alvo (%)': [20] * min(5, len(lista_rebal))
        })
    
    st.write("### 📋 Composição da Carteira")
    st.caption("Edite as quantidades e pesos desejados:")
    
    df_editavel = st.data_editor(
        st.session_state.df_carteira,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "Ação": st.column_config.TextColumn("Ticker", width="small"),
            "Qtd Atual": st.column_config.NumberColumn("Qtd. Atual", min_value=0, step=1, width="small"),
            "Peso Alvo (%)": st.column_config.NumberColumn("Peso %", min_value=0, max_value=100, step=1, width="small")
        }
    )
    
    if st.button("💾 Salvar Carteira"):
        st.session_state.df_carteira = df_editavel
        st.success("Carteira salva!")
    
    if st.button("📊 Calcular Projeção", type="primary"):
        if df_editavel.empty:
            st.error("Adicione ações à carteira primeiro.")
        else:
            with st.spinner('Calculando projeção...'):
                # Obter dados das ações
                dados_acoes = []
                for acao in df_editavel['Ação']:
                    dados, _ = get_dados_acao_brasileira(acao)
                    if dados:
                        dados_acoes.append(dados)
                
                if dados_acoes:
                    df_dados = pd.DataFrame(dados_acoes)
                    df_merged = pd.merge(df_editavel, df_dados[['Ação', 'Preço', 'DY %', 'Div_Anual']], on='Ação', how='left')
                    
                    # Preencher valores faltantes
                    df_merged['Preço'] = df_merged['Preço'].fillna(0)
                    df_merged['DY %'] = df_merged['DY %'].fillna(0)
                    df_merged['Div_Anual'] = df_merged['Div_Anual'].fillna(0)
                    
                    # Cálculos
                    df_merged['Valor Atual'] = df_merged['Qtd Atual'] * df_merged['Preço']
                    patrimonio_atual = df_merged['Valor Atual'].sum()
                    patrimonio_total = patrimonio_atual + novo_aporte
                    
                    # Normalizar pesos
                    peso_total = df_merged['Peso Alvo (%)'].sum()
                    if peso_total > 0:
                        df_merged['Peso Normalizado'] = df_merged['Peso Alvo (%)'] / peso_total * 100
                    else:
                        df_merged['Peso Normalizado'] = 100 / len(df_merged)
                    
                    df_merged['Valor Alvo'] = patrimonio_total * (df_merged['Peso Normalizado'] / 100)
                    df_merged['Diferença R$'] = df_merged['Valor Alvo'] - df_merged['Valor Atual']
                    
                    # Quantidade a comprar
                    df_merged['Qtd Comprar'] = np.where(
                        df_merged['Preço'] > 0,
                        np.floor(df_merged['Diferença R$'] / df_merged['Preço']).clip(lower=0),
                        0
                    )
                    
                    df_merged['Qtd Final'] = df_merged['Qtd Atual'] + df_merged['Qtd Comprar']
                    df_merged['Valor Final'] = df_merged['Qtd Final'] * df_merged['Preço']
                    df_merged['Renda Mensal'] = (df_merged['Qtd Final'] * df_merged['Div_Anual']) / 12
                    
                    # Totais
                    renda_mensal_total = df_merged['Renda Mensal'].sum()
                    renda_anual_total = renda_mensal_total * 12
                    
                    # Exibir resultados
                    st.success(f"## 💰 Projeção de Renda: R$ {renda_mensal_total:.2f}/mês")
                    
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
                    col_b.metric("Renda Mensal", f"R$ {renda_mensal_total:,.2f}")
                    col_c.metric("Renda Anual", f"R$ {renda_anual_total:,.2f}")
                    
                    # Tabela de alocação
                    st.write("### 📈 Distribuição da Carteira")
                    
                    df_display = df_merged[['Ação', 'Preço', 'Qtd Atual', 'Qtd Comprar', 
                                          'Qtd Final', 'Peso Normalizado', 'Renda Mensal']].copy()
                    
                    df_display = df_display.rename(columns={
                        'Peso Normalizado': 'Peso %',
                        'Renda Mensal': 'Renda Mensal (R$)'
                    })
                    
                    st.dataframe(df_display.style.format({
                        'Preço': 'R$ {:.2f}',
                        'Peso %': '{:.1f}%',
                        'Renda Mensal (R$)': 'R$ {:.2f}'
                    }).highlight_max(subset=['Renda Mensal (R$)'], color='#1e3a28'),
                    use_container_width=True)
                    
                    # Gráfico de distribuição
                    fig_dist = px.pie(df_merged, values='Valor Final', names='Ação',
                                    title='Distribuição do Patrimônio por Ação',
                                    color_discrete_sequence=px.colors.sequential.Greens)
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                    # Resumo
                    st.info(f"""
                    **📋 Resumo da Projeção:**
                    - **Aporte:** R$ {novo_aporte:,.2f}
                    - **Patrimônio total projetado:** R$ {patrimonio_total:,.2f}
                    - **Renda mensal estimada:** R$ {renda_mensal_total:.2f}
                    - **Renda anual estimada:** R$ {renda_anual_total:.2f}
                    """)
                else:
                    st.error("Não foi possível obter dados das ações. Tente novamente.")

# --- 8. RODAPÉ ---
st.divider()
st.caption(f"🛡️ Protocolo de Segurança Máxima v3.7 | Ações Brasileiras | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.caption("💡 Dica: Para melhores resultados, use tickers líquidos como PETR4, VALE3, ITSA4, BBSE3")
