import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os
import time
from datetime import datetime

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 3.5: Projeção de Renda", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 5px;
    }
    .stAlert { background-color: #1e2630; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.5")

# --- 2. SISTEMA DE FAVORITOS ---
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f:
            return f.read()
    return "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3"

def salvar_favoritos(texto):
    with open(FAVORITOS_FILE, "w") as f:
        f.write(texto)

# --- 3. BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações")
lista_inicial = carregar_favoritos()
tickers_input = st.sidebar.text_area("Lista de Tickers:", value=lista_inicial, height=150)

if st.sidebar.button("💾 Salvar Favoritos"):
    salvar_favoritos(tickers_input)
    st.sidebar.success("✅ Favoritos salvos!")

st.sidebar.divider()
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Rendimento Bazin Mínimo (%)", 4, 12, 6)

# --- 4. FUNÇÃO DE COLETA MELHORADA ---
def get_data_v3(ticker):
    t_clean = ticker.strip().upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    
    try:
        # Adicionar timeout e retry
        stock = yf.Ticker(t_sa)
        time.sleep(0.1)  # Evitar rate limiting
        
        info = stock.info
        
        if not info or 'currentPrice' not in info or info['currentPrice'] is None:
            # Tentar método alternativo para obter preço
            hist = stock.history(period="1d")
            if hist.empty:
                return None, f"Sem dados históricos para {t_clean}"
            preco = hist['Close'].iloc[-1]
        else:
            preco = info.get('currentPrice', 0)
        
        # Processar dividend yield
        dy_raw = info.get('dividendYield', 0) or 0
        if dy_raw is None:
            dy_raw = 0
        
        # Corrigir se dividend yield está em formato decimal ou percentual
        dy_corrigido = dy_raw if dy_raw < 1.0 else dy_raw / 100
        
        # Obter outros dados com fallbacks
        lpa = info.get('trailingEps', 0) or 0
        vpa = info.get('bookValue', 0) or 0
        
        return {
            "Ação": t_clean, 
            "Preço": preco, 
            "LPA": lpa,
            "VPA": vpa, 
            "DY %": dy_corrigido * 100,
            "Div_Anual": preco * dy_corrigido, 
            "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0, 
            "Liquidez_Corr": info.get('currentRatio', 0) or 0
        }, None
        
    except Exception as e:
        return None, f"Erro ao obter {t_clean}: {str(e)}"

# --- 5. INTERFACE EM ABAS ---
tab1, tab2 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda & Aportes"])

with tab1:
    st.subheader("📊 Análise de Oportunidades")
    
    if st.button("🚀 Analisar Mercado", key="analisar_mercado"):
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
                status_text.text(f"Buscando {t}... ({i+1}/{len(lista)})")
                dados, erro = get_data_v3(t)
                
                if dados:
                    lista_dados.append(dados)
                elif erro:
                    lista_erros.append(erro)
                
                bar.progress((i + 1) / len(lista))
                time.sleep(0.2)  # Delay para evitar bloqueio
            
            status_text.empty()
            bar.empty()
            
            # Mostrar erros se houver
            if lista_erros:
                with st.expander("⚠️ Avisos e Erros", expanded=True):
                    for erro in lista_erros:
                        st.warning(erro)
            
            if lista_dados:
                df = pd.DataFrame(lista_dados)
                
                # Calcular métricas de Graham
                df['Graham_Justo'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
                df['Margem_Graham'] = ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100
                
                # Calcular Bazin
                df['Bazin_Teto'] = np.where(df['Div_Anual'] > 0, 
                                           df['Div_Anual'] / (y_bazin_min / 100), 
                                           0)
                
                # Calcular Score (0-4)
                df['Score'] = ((df['ROE'] > 0.10).astype(int) + 
                              (df['Margem_Liq'] > 0.10).astype(int) + 
                              (df['Liquidez_Corr'] > 1.0).astype(int) + 
                              (df['LPA'] > 0).astype(int))
                
                # Definir STATUS
                def definir_status(row):
                    if pd.isna(row['Graham_Justo']) or row['Graham_Justo'] <= 0:
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
                fig = px.scatter(df, x="Margem_Graham", y="Score", text="Ação", 
                                 color="STATUS", size="DY %",
                                 color_discrete_map={
                                     "💎 BLINDADA": "#00cc66", 
                                     "⚠️ Observar": "#ffcc00", 
                                     "🛑 Reprovada": "#ff4d4d",
                                     "🔍 Dados Insuficientes": "#888888"
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
                                      '' for v in x], 
                           subset=['STATUS']),
                    use_container_width=True,
                    height=400)
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Ações Analisadas", len(df))
                with col2:
                    blindadas = len(df[df['STATUS'] == '💎 BLINDADA'])
                    st.metric("Oportunidades Blindadas", blindadas)
                with col3:
                    st.metric("Média DY", f"{df['DY %'].mean():.2f}%")
            else:
                st.error("""
                ❌ Não foi possível obter dados. Possíveis causas:
                1. O Yahoo Finance pode estar bloqueando a conexão temporariamente
                2. Os tickers podem estar incorretos
                3. Problema de conexão com a internet
                
                **Soluções:**
                - Verifique os tickers (ex: PETR4, VALE3, ITSA4)
                - Tente novamente em alguns minutos
                - Verifique sua conexão com a internet
                """)

with tab2:
    st.subheader("⚖️ Planejador de Renda Passiva")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        novo_aporte = st.number_input("Valor do Novo Aporte (R$):", min_value=0.0, value=1000.0, step=100.0)
    with col_input2:
        st.write("")  # Espaçador
        st.write(f"Margem Graham: **{m_graham_min}%** | Yield Bazin: **{y_bazin_min}%**")
    
    lista_rebal = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    
    if 'df_rebal' not in st.session_state:
        st.session_state.df_rebal = pd.DataFrame({
            'Ação': lista_rebal,
            'Qtd Atual': [0] * len(lista_rebal),
            'Peso Alvo (%)': [round(100/len(lista_rebal), 1) if len(lista_rebal) > 0 else 0] * len(lista_rebal)
        })
    
    st.write("### 📋 Composição da Carteira")
    st.caption("Edite as quantidades atuais e pesos alvo:")
    
    df_usuario = st.data_editor(
        st.session_state.df_rebal, 
        use_container_width=True, 
        num_rows="dynamic",
        column_config={
            "Ação": st.column_config.TextColumn("Ticker", width="medium"),
            "Qtd Atual": st.column_config.NumberColumn("Quantidade Atual", min_value=0, format="%d"),
            "Peso Alvo (%)": st.column_config.NumberColumn("Peso Alvo %", min_value=0, max_value=100, format="%.1f")
        }
    )
    
    # Salvar alterações
    if st.button("💾 Salvar Composição"):
        st.session_state.df_rebal = df_usuario
        st.success("Composição salva!")
    
    if st.button("📊 Projetar Renda e Rebalancear", key="projetar_renda"):
        if df_usuario.empty or df_usuario['Ação'].isnull().all():
            st.error("❌ Adicione pelo menos uma ação à carteira.")
        else:
            with st.spinner('Calculando projeções...'):
                lista_dados_rebal = []
                for t in df_usuario['Ação']:
                    dados, _ = get_data_v3(t)
                    if dados:
                        lista_dados_rebal.append({
                            'Ação': t, 
                            'Preço': dados['Preço'], 
                            'Div_Anual': dados['Div_Anual']
                        })
                
                if lista_dados_rebal:
                    df_precos = pd.DataFrame(lista_dados_rebal)
                    df_merged = pd.merge(df_usuario, df_precos, on='Ação', how='left')
                    
                    # Preencher valores nulos
                    df_merged['Preço'] = df_merged['Preço'].fillna(0)
                    df_merged['Div_Anual'] = df_merged['Div_Anual'].fillna(0)
                    
                    # Cálculos
                    df_merged['Valor Atual'] = df_merged['Qtd Atual'] * df_merged['Preço']
                    patrimonio_existente = df_merged['Valor Atual'].sum()
                    patrimonio_total_novo = patrimonio_existente + novo_aporte
                    
                    # Normalizar pesos para somar 100%
                    pesos_totais = df_merged['Peso Alvo (%)'].sum()
                    if pesos_totais > 0:
                        df_merged['Peso Normalizado'] = df_merged['Peso Alvo (%)'] / pesos_totais * 100
                    else:
                        df_merged['Peso Normalizado'] = 100 / len(df_merged)
                    
                    df_merged['Valor Alvo'] = patrimonio_total_novo * (df_merged['Peso Normalizado'] / 100)
                    df_merged['Diferença (R$)'] = df_merged['Valor Alvo'] - df_merged['Valor Atual']
                    
                    # Cálculo de Compra e Renda
                    df_merged['Comprar (Qtd)'] = np.where(
                        df_merged['Preço'] > 0,
                        (df_merged['Diferença (R$)'] / df_merged['Preço']).apply(lambda x: max(0, np.floor(x))),
                        0
                    )
                    df_merged['Qtd Final'] = df_merged['Qtd Atual'] + df_merged['Comprar (Qtd)']
                    df_merged['Renda Anual Proj.'] = df_merged['Qtd Final'] * df_merged['Div_Anual']
                    df_merged['Renda Mensal Média'] = df_merged['Renda Anual Proj.'] / 12
                    
                    # Métricas de Resumo
                    total_mensal = df_merged['Renda Mensal Média'].sum()
                    total_anual = df_merged['Renda Anual Proj.'].sum()
                    
                    # Display metrics
                    st.subheader("📈 Projeção de Renda")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("💰 Patrimônio Total", f"R$ {patrimonio_total_novo:,.2f}")
                    c2.metric("📅 Renda Mensal Média", f"R$ {total_mensal:,.2f}")
                    c3.metric("📊 Renda Anual Estimada", f"R$ {total_anual:,.2f}")
                    
                    # Tabela de alocação
                    st.write("### 🎯 Sugestão de Alocação")
                    
                    df_display = df_merged[['Ação', 'Preço', 'Qtd Atual', 'Comprar (Qtd)', 
                                          'Qtd Final', 'Peso Normalizado', 'Renda Mensal Média']].copy()
                    df_display = df_display.rename(columns={
                        'Peso Normalizado': 'Peso (%)',
                        'Renda Mensal Média': 'Renda Mensal (R$)'
                    })
                    
                    st.dataframe(df_display.style.format({
                        'Preço': 'R$ {:.2f}',
                        'Peso (%)': '{:.1f}%',
                        'Renda Mensal (R$)': 'R$ {:.2f}'
                    }).highlight_max(subset=['Renda Mensal (R$)'], color='#1e2630'), 
                    use_container_width=True)
                    
                    # Gráfico de pizza da renda
                    fig_pizza = px.pie(df_merged, values='Renda Mensal Média', names='Ação',
                                     title='Distribuição da Renda Mensal por Ação',
                                     color_discrete_sequence=px.colors.sequential.Greens)
                    st.plotly_chart(fig_pizza, use_container_width=True)
                    
                    st.info(f"""
                    💡 **Resumo da Projeção:**
                    - Com um aporte de **R$ {novo_aporte:,.2f}**
                    - Sua carteira passará a render **R$ {total_mensal:.2f} por mês**
                    - O que equivale a **R$ {total_anual:.2f} por ano**
                    """)
                    
                else:
                    st.error("❌ Não foi possível obter dados das ações. Verifique os tickers e tente novamente.")

# --- 6. RODAPÉ ---
st.divider()
st.caption(f"🛡️ Protocolo de Segurança Máxima v3.5 | Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
