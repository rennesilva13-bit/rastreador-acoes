import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 3.5: Projeção Otimizada", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #00cc66;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 3.5")

# --- 2. SISTEMA DE FAVORITOS (Adaptado para Session State para Demo) ---
# Nota: Para persistência em nuvem real, recomenda-se banco de dados.
if 'lista_favoritos' not in st.session_state:
    st.session_state.lista_favoritos = "SAPR11, BBSE3, BBAS3, CMIG4, PETR4, VALE3, TAEE11, EGIE3, KLBN11"

# --- 3. BARRA LATERAL ---
st.sidebar.header("⚙️ Configurações")
tickers_input = st.sidebar.text_area("Lista de Tickers:", value=st.session_state.lista_favoritos, height=150)

if st.sidebar.button("💾 Atualizar Lista Temporária"):
    st.session_state.lista_favoritos = tickers_input
    st.sidebar.success("Lista atualizada para esta sessão!")

st.sidebar.divider()
st.sidebar.subheader("Parâmetros de Filtro")
m_graham_min = st.sidebar.slider("Margem Graham Mínima (%)", 0, 50, 20)
y_bazin_min = st.sidebar.slider("Yield Bazin Mínimo (%)", 4, 12, 6)

# --- 4. FUNÇÃO DE COLETA (COM CACHE) ---
@st.cache_data(ttl=3600) # Cache dura 1 hora para não travar o app
def get_data_v3_cached(ticker):
    t_clean = ticker.strip().upper()
    t_sa = t_clean + ".SA" if not t_clean.endswith(".SA") else t_clean
    try:
        stock = yf.Ticker(t_sa)
        info = stock.info
        
        # Validação básica se o ticker existe
        if 'currentPrice' not in info and 'regularMarketPrice' not in info:
            return None
            
        preco = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        dy_raw = info.get('dividendYield', 0) or 0
        
        # Correção para DY vindo como porcentagem ou decimal
        dy_corrigido = dy_raw if dy_raw < 1.0 else dy_raw / 100
        
        return {
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
    except Exception as e:
        print(f"Erro ao buscar {t_clean}: {e}")
        return None

# --- 5. INTERFACE EM ABAS ---
tab1, tab2 = st.tabs(["🔍 Rastreador de Oportunidades", "💰 Gestor de Renda & Aportes"])

# --- ABA 1: RASTREADOR ---
with tab1:
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        analisar = st.button("🚀 Analisar Mercado")
    
    if analyzing := analisar: # Walrus operator para manter estado simples
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        lista_dados = []
        
        progress_text = "Consultando API do Yahoo Finance..."
        my_bar = st.progress(0, text=progress_text)
        
        for i, t in enumerate(lista):
            d = get_data_v3_cached(t)
            if d: lista_dados.append(d)
            my_bar.progress((i + 1) / len(lista), text=f"Analisando {t}...")
        
        my_bar.empty()
        
        if lista_dados:
            df = pd.DataFrame(lista_dados)
            
            # Cálculos Fundamentalistas
            df['Graham_Justo'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
            df['Margem_Graham'] = ((df['Graham_Justo'] - df['Preço']) / df['Graham_Justo']) * 100
            df['Bazin_Teto'] = df['Div_Anual'] / (y_bazin_min / 100)
            
            # Score de Qualidade (0 a 4)
            df['Score'] = ((df['ROE'] > 0.10).astype(int) + 
                           (df['Margem_Liq'] > 0.10).astype(int) + 
                           (df['Liquidez_Corr'] > 1.0).astype(int) + 
                           (df['LPA'] > 0).astype(int))
            
            # Lógica de Status
            def definir_status(row):
                criterio_graham = row['Margem_Graham'] >= m_graham_min
                criterio_bazin = row['Preço'] <= row['Bazin_Teto']
                criterio_score = row['Score'] >= 3
                
                if criterio_graham and criterio_bazin and criterio_score:
                    return "💎 BLINDADA"
                elif (criterio_graham or criterio_bazin) and row['Score'] >= 2:
                    return "⚠️ Observar" 
                return "🛑 Reprovada"

            df['STATUS'] = df.apply(definir_status, axis=1)
            
            # Ordenação inteligente
            status_order = {"💎 BLINDADA": 0, "⚠️ Observar": 1, "🛑 Reprovada": 2}
            df['sort_key'] = df['STATUS'].map(status_order)
            df = df.sort_values(by=['sort_key', 'Margem_Graham'], ascending=[True, False]).drop(columns=['sort_key'])

            # Gráfico Interativo
            fig = px.scatter(df, x="Margem_Graham", y="DY %", text="Ação", color="STATUS", 
                             size="Score", hover_data=["Preço", "Graham_Justo"],
                             color_discrete_map={"💎 BLINDADA": "#00cc66", "⚠️ Observar": "#ffcc00", "🛑 Reprovada": "#ff4d4d"},
                             title="Mapa de Oportunidades (Graham vs Yield)")
            fig.add_vline(x=m_graham_min, line_dash="dash", line_color="white", annotation_text="Graham Min")
            st.plotly_chart(fig, use_container_width=True)

            # Tabela Final
            st.dataframe(
                df[['Ação', 'Preço', 'DY %', 'Graham_Justo', 'Margem_Graham', 'Bazin_Teto', 'Score', 'STATUS']].style
                .format({'Preço': 'R$ {:.2f}', 'DY %': '{:.2f}%', 'Graham_Justo': 'R$ {:.2f}', 'Margem_Graham': '{:.1f}%', 'Bazin_Teto': 'R$ {:.2f}'})
                .applymap(lambda v: 'color: #00cc66; font-weight: bold;' if v == '💎 BLINDADA' else ('color: #ffcc00;' if v == '⚠️ Observar' else 'color: #ff4d4d;'), subset=['STATUS']),
                use_container_width=True
            )
        else:
            st.error("Não foi possível obter dados. Verifique os tickers.")

# --- ABA 2: GESTOR DE RENDA ---
with tab2:
    st.subheader("⚖️ Planejador de Renda Passiva Inteligente")
    st.info("O sistema priorizará a compra de ativos que estão abaixo da % alvo desejada.")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        novo_aporte = st.number_input("Valor do Novo Aporte (R$):", min_value=0.0, value=1000.0, step=100.0)
    
    # Preparação dos dados para edição
    lista_rebal = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
    
    # Inicializa ou atualiza o DataFrame se a lista de tickers mudou
    if 'df_rebal' not in st.session_state or len(st.session_state.df_rebal) != len(lista_rebal):
        st.session_state.df_rebal = pd.DataFrame({
            'Ação': lista_rebal,
            'Qtd Atual': [0] * len(lista_rebal),
            'Peso Alvo (%)': [round(100/len(lista_rebal), 1)] * len(lista_rebal)
        })

    # Editor de Dados
    df_usuario = st.data_editor(
        st.session_state.df_rebal, 
        column_config={
            "Peso Alvo (%)": st.column_config.NumberColumn(
                "Peso Alvo (%)",
                help="A soma deve ser 100%",
                min_value=0,
                max_value=100,
                step=1,
            ),
            "Qtd Atual": st.column_config.NumberColumn(
                "Qtd Atual",
                min_value=0,
                step=1,
            )
        },
        use_container_width=True, 
        num_rows="dynamic"
    )
    
    # Validação da Soma dos Pesos
    soma_pesos = df_usuario['Peso Alvo (%)'].sum()
    if not (99.0 <= soma_pesos <= 101.0):
        st.warning(f"⚠️ Atenção: A soma dos pesos alvo está em {soma_pesos:.1f}%. Ajuste para 100%.")

    if st.button("📊 Projetar Renda e Rebalancear"):
        with st.spinner('Calculando rebalanceamento inteligente...'):
            lista_dados_rebal = []
            
            # Usa a função com cache para ser rápido
            for t in df_usuario['Ação']:
                d = get_data_v3_cached(t)
                if d: 
                    lista_dados_rebal.append({'Ação': t, 'Preço': d['Preço'], 'Div_Anual': d['Div_Anual']})
            
            if lista_dados_rebal:
                df_precos = pd.DataFrame(lista_dados_rebal)
                df_merged = pd.merge(df_usuario, df_precos, on='Ação')
                
                # Matemática do Rebalanceamento
                df_merged['Valor Atual'] = df_merged['Qtd Atual'] * df_merged['Preço']
                patrimonio_existente = df_merged['Valor Atual'].sum()
                patrimonio_total_novo = patrimonio_existente + novo_aporte
                
                df_merged['Valor Alvo'] = patrimonio_total_novo * (df_merged['Peso Alvo (%)'] / 100)
                
                # Define quanto falta para o alvo. Se negativo (está acima), zera a necessidade de compra
                df_merged['Diferença (R$)'] = df_merged['Valor Alvo'] - df_merged['Valor Atual']
                
                # Distribuição do Aporte:
                # 1. Filtra apenas quem tem Diferença positiva (quem está pra trás)
                df_deficit = df_merged[df_merged['Diferença (R$)'] > 0].copy()
                
                if df_deficit.empty:
                    st.success("Carteira perfeitamente balanceada ou aporte insuficiente para mover ponteiros.")
                else:
                    # Calcula peso relativo do deficit
                    total_deficit = df_deficit['Diferença (R$)'].sum()
                    df_deficit['Fator Compra'] = df_deficit['Diferença (R$)'] / total_deficit
                    
                    # Aloca o aporte novo proporcionalmente ao "buraco" de cada ativo
                    # Nota: Isso garante que o aporte novo vai onde mais precisa
                    df_deficit['Dinheiro Alocado'] = novo_aporte * df_deficit['Fator Compra']
                    df_deficit['Comprar (Qtd)'] = np.floor(df_deficit['Dinheiro Alocado'] / df_deficit['Preço'])
                    
                    # Merge de volta para o df principal
                    df_merged = pd.merge(df_merged, df_deficit[['Ação', 'Comprar (Qtd)']], on='Ação', how='left').fillna(0)

                # Projeções Finais
                df_merged['Qtd Final'] = df_merged['Qtd Atual'] + df_merged['Comprar (Qtd)']
                df_merged['Renda Anual Proj.'] = df_merged['Qtd Final'] * df_merged['Div_Anual']
                df_merged['Renda Mensal Média'] = df_merged['Renda Anual Proj.'] / 12
                
                # Métricas de Resumo
                total_mensal = df_merged['Renda Mensal Média'].sum()
                total_anual = df_merged['Renda Anual Proj.'].sum()
                div_yield_on_cost = (total_anual / patrimonio_total_novo) * 100 if patrimonio_total_novo > 0 else 0
                
                st.divider()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Patrimônio Final", f"R$ {patrimonio_total_novo:,.2f}")
                c2.metric("Renda Mensal Média", f"R$ {total_mensal:,.2f}", delta="Projeção")
                c3.metric("Renda Anual", f"R$ {total_anual:,.2f}")
                c4.metric("Yield da Carteira", f"{div_yield_on_cost:.2f}%")
                
                st.write("### 🛒 Ordem de Compra Sugerida")
                
                compra_df = df_merged[df_merged['Comprar (Qtd)'] > 0][['Ação', 'Preço', 'Comprar (Qtd)', 'Renda Mensal Média']].copy()
                compra_df['Custo Total'] = compra_df['Preço'] * compra_df['Comprar (Qtd)']
                
                if not compra_df.empty:
                    st.dataframe(compra_df.style.format({
                        'Preço': 'R$ {:.2f}', 
                        'Renda Mensal Média': 'R$ {:.2f}',
                        'Custo Total': 'R$ {:.2f}'
                    }), use_container_width=True)
                else:
                    st.warning("O valor do aporte não foi suficiente para comprar 1 lote inteiro de nenhuma das ações atrasadas.")

                st.write("### 📋 Visão Geral da Carteira")
                st.dataframe(df_merged[['Ação', 'Qtd Final', 'Peso Alvo (%)', 'Renda Mensal Média']].style.format({
                     'Renda Mensal Média': 'R$ {:.2f}',
                     'Peso Alvo (%)': '{:.1f}%'
                }), use_container_width=True)
