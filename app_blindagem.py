# --- APAGUE A FUNÇÃO get_session() INTEIRA ---
# Ela não é mais necessária e é a causa do erro atual.

# --- SUBSTITUA A FUNÇÃO get_yahoo_data_cached POR ESTA ---
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
