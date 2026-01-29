import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import os
import PyPDF2
import google.generativeai as genai

# 1. Configuração e Estilo
st.set_page_config(page_title="Blindagem 4.0: O Exégeta", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { background-color: #00cc66; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Protocolo de Segurança Máxima: Versão 4.0")

# --- 2. CONFIGURAÇÃO DA IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
except:
    st.warning("⚠️ Chave de API da IA não configurada nos Secrets.")

# --- 3. SISTEMA DE FAVORITOS ---
FAVORITOS_FILE = "favoritos.txt"

def carregar_favoritos():
    if os.path.exists(FAVORITOS_FILE):
        with open(FAVORITOS_FILE, "r") as f: return f.read()
    return "SAPR11, BBSE3, BBAS3, PETR4, TAEE11, EGIE3"

# --- 4. FUNÇÕES TÉCNICAS ---
def get_data(ticker):
    t_sa = ticker.strip().upper() + ".SA" if not ticker.endswith(".SA") else ticker
    try:
        stock = yf.Ticker(t_sa)
        info = stock.info
        preco = info.get('currentPrice', 0)
        dy_raw = info.get('dividendYield', 0) or info.get('trailingAnnualDividendYield', 0) or 0
        dy = dy_raw if dy_raw < 1.0 else dy_raw / 100
        return {
            "Ação": ticker.upper(), "Preço": preco, 
            "LPA": info.get('trailingEps', 0) or 0, "VPA": info.get('bookValue', 0) or 0,
            "DY %": dy * 100, "Div_Anual": preco * dy, "ROE": info.get('returnOnEquity', 0) or 0,
            "Margem_Liq": info.get('profitMargins', 0) or 0, "Liquidez_Corr": info.get('currentRatio', 0) or 0
        }
    except: return None

# --- 5. INTERFACE EM ABAS ---
tab1, tab2, tab3 = st.tabs(["🔍 Rastreador", "⚖️ Gestor de Aportes", "📖 O Exégeta (IA)"])

with tab1:
    st.sidebar.header("⚙️ Configurações")
    tickers_input = st.sidebar.text_area("Lista de Tickers:", value=carregar_favoritos(), height=150)
    if st.sidebar.button("💾 Salvar Favoritos"):
        with open(FAVORITOS_FILE, "w") as f: f.write(tickers_input)
        st.sidebar.success("✅ Salvo!")

    if st.button("🚀 Analisar Fundamentos"):
        lista = [t.strip() for t in tickers_input.split(',') if t.strip()]
        dados = [get_data(t) for t in lista if get_data(t)]
        df = pd.DataFrame(dados)
        df['Graham'] = np.sqrt(np.maximum(0, 22.5 * df['LPA'] * df['VPA']))
        df['Score'] = ((df['ROE'] > 0.10).astype(int) + (df['Margem_Liq'] > 0.10).astype(int) + (df['Liquidez_Corr'] > 1.0).astype(int) + (df['LPA'] > 0).astype(int))
        st.dataframe(df[['Ação', 'Preço', 'DY %', 'Graham', 'Score']].style.format({'Preço': 'R$ {:.2f}', 'DY %': '{:.2f}%', 'Graham': 'R$ {:.2f}'}))

with tab2:
    st.subheader("⚖️ Rebalanceamento e Aportes")
    st.info("Utilize esta aba para equilibrar sua carteira com novos aportes.")
    # (Mantém a lógica da versão 3.3 aqui...)

with tab3:
    st.subheader("📖 Exegese Qualitativa de Relatórios")
    st.markdown("""
    Faça o upload de um relatório **ITR (Trimestral)** ou **DFP (Anual)** da B3. 
    A IA buscará por riscos ocultos, itens não recorrentes e contradições na fala da diretoria.
    """)
    
    arquivo_pdf = st.file_uploader("Carregar Relatório (PDF)", type="pdf")
    
    if arquivo_pdf:
        with st.spinner("Lendo e interpretando o documento..."):
            # Extração de texto
            leitor = PyPDF2.PdfReader(arquivo_pdf)
            texto_pdf = ""
            # Lemos as primeiras 15 páginas (onde costuma estar o comentário da diretoria)
            for i in range(min(15, len(leitor.pages))):
                texto_pdf += leitor.pages[i].extract_text()
            
            # Prompt de Exegese
            prompt = f"""
            Como um analista fundamentalista sênior, realize uma exegese crítica do texto abaixo, extraído de um relatório financeiro.
            Busque especificamente por:
            1. Itens Não Recorrentes: O lucro foi inflado por eventos únicos?
            2. Riscos Jurídicos ou Regulatórios: Há menções a litígios perigosos?
            3. Mudança de Tom: A diretoria parece cautelosa ou excessivamente otimista?
            4. Endividamento: Há sinais de pressão na liquidez?
            
            Texto do Relatório:
            {texto_pdf[:15000]} 
            """
            
            try:
                resposta = model.generate_content(prompt)
                st.markdown("---")
                st.markdown("### 📝 Veredito do Exégeta")
                st.write(resposta.text)
            except Exception as e:
                st.error(f"Erro na análise da IA: {e}")
