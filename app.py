"""
================================================================================
 DÓLAR DESK — Dashboard de Monitoramento e Simulação de Operações USD/BRL
================================================================================
Como rodar:
    pip install -r requirements.txt
    streamlit run app.py
================================================================================
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, datetime

# ------------------------------------------------------------------------------
# CONFIGURAÇÃO GERAL DA PÁGINA
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Dólar Desk | USD/BRL Terminal",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# TEMA DARK CUSTOMIZADO (CSS)
# ------------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    .stApp { background-color: #0e1117; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #131722; border-right: 1px solid #2a2e39; }
    h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; font-family: 'Trebuchet MS', sans-serif; }

    div[data-testid="stMetric"] {
        background-color: #161b26;
        border: 1px solid #2a2e39;
        border-radius: 10px;
        padding: 15px 15px 5px 15px;
    }
    div[data-testid="stMetricLabel"] { color: #9aa0aa !important; font-size: 0.85rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }

    .stButton>button {
        background-color: #00ff66;
        color: #0e1117;
        font-weight: bold;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover { background-color: #00cc52; color: #0e1117; }

    hr { border-color: #2a2e39; }

    .risk-box {
        background-color: #161b26;
        border: 1px solid #2a2e39;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        margin-top: 10px;
    }
    .risk-box .value { font-size: 1.8rem; font-weight: 700; color: #00ff66; }
    .risk-box .label { font-size: 0.85rem; color: #9aa0aa; }

    .badge-long {
        background-color: rgba(0,255,102,0.15);
        color: #00ff66;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-short {
        background-color: rgba(255,60,60,0.15);
        color: #ff3c3c;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }

    .event-card {
        background-color: #161b26;
        border: 1px solid #2a2e39;
        border-left: 4px solid #00ff66;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .event-card.fed { border-left-color: #3aa0ff; }
    .event-card .title { font-weight: 700; font-size: 1.0rem; color: #FFFFFF; }
    .event-card .sub { color: #9aa0aa; font-size: 0.85rem; margin-top: 2px; }
    .event-card .countdown { color: #00ff66; font-weight: 700; font-size: 1.1rem; margin-top: 6px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

POSITIVE_COLOR = "#00ff66"
NEGATIVE_COLOR = "#ff3c3c"


def colored_text(value_text: str, is_positive: bool) -> str:
    color = POSITIVE_COLOR if is_positive else NEGATIVE_COLOR
    return f"<span style='color:{color}; font-weight:700;'>{value_text}</span>"


# ==============================================================================
# FUNÇÕES DE DADOS — BANCO CENTRAL (PTAX, SELIC, CDI) E YFINANCE (MACRO GLOBAL)
# ==============================================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_ptax():
    """Busca a última cotação PTAX (dólar oficial do Banco Central) disponível."""
    try:
        hoje = date.today()
        inicio = hoje.replace(day=1) if hoje.day > 10 else hoje
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
            f"?@dataInicial='{(hoje.replace(day=1)).strftime('%m-%d-%Y')}'"
            f"&@dataFinalCotacao='{hoje.strftime('%m-%d-%Y')}'"
            "&$top=100&$format=json&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
        )
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        valores = resp.json().get("value", [])
        if not valores:
            return None
        ultimo = sorted(valores, key=lambda x: x["dataHoraCotacao"])[-1]
        return {
            "compra": ultimo["cotacaoCompra"],
            "venda": ultimo["cotacaoVenda"],
            "data": ultimo["dataHoraCotacao"],
        }
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_live_usdbrl():
    """Busca a cotação real e recente do USD/BRL (mercado, não PTAX) via Yahoo Finance."""
    try:
        hist = yf.download("USDBRL=X", period="2d", interval="1m", progress=False)
        if hist.empty:
            hist = yf.download("USDBRL=X", period="5d", interval="5m", progress=False)
        if hist.empty:
            return None
        close = hist["Close"].dropna()
        atual = float(close.iloc[-1])
        referencia = float(close.iloc[0])
        variacao = ((atual - referencia) / referencia) * 100 if referencia else 0.0
        horario = hist.index[-1]
        return {"preco": atual, "variacao": variacao, "horario": horario}
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def get_bcb_sgs(codigo_serie: int):
    """Busca o último valor de uma série temporal do SGS/BCB (ex: Selic meta, CDI)."""
    try:
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados/ultimos/1?formato=json"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        dados = resp.json()
        if not dados:
            return None
        return float(dados[0]["valor"].replace(",", "."))
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def get_macro_globals():
    """Busca DXY, Treasury de 10 anos e Petróleo Brent via Yahoo Finance."""
    tickers = ["DX-Y.NYB", "^TNX", "BZ=F"]
    resultado = {}
    try:
        dados = yf.download(tickers, period="5d", interval="1d", progress=False, group_by="ticker")
        for t in tickers:
            try:
                serie = dados[t]["Close"].dropna()
                if len(serie) >= 2:
                    atual, anterior = serie.iloc[-1], serie.iloc[-2]
                    variacao = ((atual - anterior) / anterior) * 100
                    resultado[t] = {"valor": float(atual), "variacao": float(variacao)}
                elif len(serie) == 1:
                    resultado[t] = {"valor": float(serie.iloc[-1]), "variacao": 0.0}
            except Exception:
                resultado[t] = None
    except Exception:
        for t in tickers:
            resultado[t] = None
    return resultado


@st.cache_data(ttl=1800, show_spinner=False)
def get_usdbrl_volatility():
    """Calcula ATR(14) e volatilidade histórica anualizada do par USD/BRL."""
    try:
        hist = yf.download("USDBRL=X", period="3mo", interval="1d", progress=False)
        if hist.empty or len(hist) < 15:
            return None
        high, low, close = hist["High"], hist["Low"], hist["Close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [
                (high - low),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr14 = tr.rolling(window=14).mean().iloc[-1]

        log_returns = np.log(close / close.shift(1)).dropna()
        vol_diaria = log_returns.std()
        vol_anualizada = vol_diaria * np.sqrt(252) * 100

        return {
            "atr14": float(atr14),
            "vol_anualizada": float(vol_anualizada),
            "ultimo_fechamento": float(close.iloc[-1]),
        }
    except Exception:
        return None


# ==============================================================================
# CALENDÁRIO FIXO DE REUNIÕES DE JUROS — COPOM (BCB) E FOMC (FED) 2026
# Fonte: comunicados oficiais do Banco Central e do Federal Reserve.
# ==============================================================================
COPOM_2026 = [
    (date(2026, 1, 27), date(2026, 1, 28)),
    (date(2026, 3, 17), date(2026, 3, 18)),
    (date(2026, 4, 28), date(2026, 4, 29)),
    (date(2026, 6, 16), date(2026, 6, 17)),
    (date(2026, 8, 4), date(2026, 8, 5)),
    (date(2026, 9, 15), date(2026, 9, 16)),
    (date(2026, 11, 3), date(2026, 11, 4)),
    (date(2026, 12, 8), date(2026, 12, 9)),
]

FOMC_2026 = [
    (date(2026, 1, 27), date(2026, 1, 28)),
    (date(2026, 3, 17), date(2026, 3, 18)),
    (date(2026, 4, 28), date(2026, 4, 29)),
    (date(2026, 6, 16), date(2026, 6, 17)),
    (date(2026, 7, 28), date(2026, 7, 29)),
    (date(2026, 9, 15), date(2026, 9, 16)),
    (date(2026, 10, 27), date(2026, 10, 28)),
    (date(2026, 12, 8), date(2026, 12, 9)),
]


def proxima_reuniao(lista_reunioes, hoje):
    for inicio, fim in lista_reunioes:
        if fim >= hoje:
            return inicio, fim
    return None


# ==============================================================================
# SIDEBAR — SIMULADOR DE ORDENS FINANCEIRAS
# ==============================================================================
with st.sidebar:
    st.markdown("## 📟 Simulador de Ordens — USD/BRL")
    st.caption("Configure a operação para simular resultado, margem e risco/retorno.")
    st.markdown("---")

    tipo_operacao = st.selectbox(
        "Tipo de Operação",
        ["COMPRA (Long)", "VENDA (Short)"],
        help="COMPRA: você lucra se o dólar subir. VENDA: você lucra se o dólar cair.",
    )
    is_long = tipo_operacao.startswith("COMPRA")

    live_preview = get_live_usdbrl()
    if live_preview:
        st.caption(f"💹 USD/BRL agora: **R$ {live_preview['preco']:.4f}** ({live_preview['variacao']:+.2f}% no período)")
        usar_preco_atual = st.button("📥 Usar preço atual como entrada", use_container_width=True)
    else:
        usar_preco_atual = False
        st.caption("💹 Cotação ao vivo indisponível no momento — preencha manualmente.")

    if usar_preco_atual and live_preview:
        st.session_state["preco_entrada_input"] = round(live_preview["preco"], 4)

    lote_usd = st.number_input("Tamanho do Lote (USD)", min_value=1000.0, value=10000.0, step=1000.0, format="%.2f")
    preco_entrada = st.number_input(
        "Preço de Entrada (R$ por USD)",
        min_value=0.01,
        value=st.session_state.get("preco_entrada_input", 5.50),
        step=0.01,
        format="%.4f",
        key="preco_entrada_input",
    )
    preco_alvo = st.number_input("Preço Alvo / Take Profit (R$)", min_value=0.01, value=5.65, step=0.01, format="%.4f")
    preco_stop = st.number_input("Preço de Stop Loss (R$)", min_value=0.01, value=5.45, step=0.01, format="%.4f")

    st.markdown("---")
    alavancagem = st.selectbox(
        "Alavancagem Padrão de Mercado",
        [1, 2, 5, 10, 20, 30, 50],
        index=3,
        help="Alavancagem simulada, comum em contratos futuros e CFDs de câmbio.",
    )

    st.markdown("---")
    st.caption(
        "⚠️ Ferramenta educacional/simulação. Não constitui recomendação de "
        "investimento. Cotações reais podem divergir."
    )

# ------------------------------------------------------------------------------
# LÓGICA DE CÁLCULO — INVERTE CONFORME COMPRA / VENDA
# ------------------------------------------------------------------------------
if is_long:
    variacao_lucro = preco_alvo - preco_entrada
    variacao_prejuizo = preco_entrada - preco_stop
else:
    variacao_lucro = preco_entrada - preco_alvo
    variacao_prejuizo = preco_stop - preco_entrada

lucro_maximo_brl = variacao_lucro * lote_usd
prejuizo_maximo_brl = variacao_prejuizo * lote_usd
lucro_percentual = (variacao_lucro / preco_entrada) * 100 if preco_entrada else 0
prejuizo_percentual = (variacao_prejuizo / preco_entrada) * 100 if preco_entrada else 0
valor_total_operacao_brl = lote_usd * preco_entrada
margem_requerida_brl = valor_total_operacao_brl / alavancagem if alavancagem else valor_total_operacao_brl
relacao_risco_retorno = (lucro_maximo_brl / prejuizo_maximo_brl) if prejuizo_maximo_brl > 0 else 0.0

alerta_configuracao = None
if lucro_maximo_brl <= 0:
    alerta_configuracao = "⚠️ O Preço Alvo definido não gera lucro para o tipo de operação selecionado. Revise os valores de entrada/alvo."
elif prejuizo_maximo_brl <= 0:
    alerta_configuracao = "⚠️ O Stop Loss definido não gera perda coerente para o tipo de operação selecionado. Revise os valores de entrada/stop."

# ==============================================================================
# CABEÇALHO
# ==============================================================================
col_title, col_badge = st.columns([5, 1])
with col_title:
    st.title("💵 Dólar Desk — Terminal USD/BRL")
    st.caption("Monitoramento de câmbio em tempo real e simulação de operações no Dólar Comercial/Futuro")
with col_badge:
    st.markdown("<br>", unsafe_allow_html=True)
    badge_class = "badge-long" if is_long else "badge-short"
    st.markdown(f"<span class='{badge_class}'>{tipo_operacao}</span>", unsafe_allow_html=True)

if alerta_configuracao:
    st.warning(alerta_configuracao)

st.markdown("---")

# ==============================================================================
# PAINEL DE RESULTADOS DA SIMULAÇÃO
# ==============================================================================
st.subheader("📊 Resultado da Simulação")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric(label="Valor Total da Operação", value=f"R$ {valor_total_operacao_brl:,.2f}")
with m2:
    st.metric(label="Lucro Máximo Estimado", value=f"R$ {lucro_maximo_brl:,.2f}", delta=f"{lucro_percentual:,.2f}%")
with m3:
    st.metric(label="Prejuízo Máximo Aceitável", value=f"R$ {prejuizo_maximo_brl:,.2f}", delta=f"-{abs(prejuizo_percentual):,.2f}%", delta_color="inverse")
with m4:
    st.metric(label=f"Margem Requerida ({alavancagem}x)", value=f"R$ {margem_requerida_brl:,.2f}")
with m5:
    st.markdown(
        f"""<div class="risk-box"><div class="value">1 : {relacao_risco_retorno:,.2f}</div>
        <div class="label">Relação Risco x Retorno</div></div>""",
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------------------
# P&L FLUTUANTE — compara o preço real de mercado agora com o preço de entrada
# ------------------------------------------------------------------------------
live_now = get_live_usdbrl()
if live_now:
    preco_atual = live_now["preco"]
    if is_long:
        variacao_flutuante = preco_atual - preco_entrada
    else:
        variacao_flutuante = preco_entrada - preco_atual
    pnl_flutuante_brl = variacao_flutuante * lote_usd
    pnl_flutuante_pct = (variacao_flutuante / preco_entrada) * 100 if preco_entrada else 0
    is_pnl_positivo = pnl_flutuante_brl >= 0

    st.markdown("")
    pl1, pl2, pl3 = st.columns([2, 2, 2])
    with pl1:
        st.metric("Cotação Real Agora (USD/BRL)", f"R$ {preco_atual:.4f}", delta=f"{live_now['variacao']:+.2f}%")
    with pl2:
        st.markdown(
            f"""<div class="risk-box">
            <div class="value" style="color:{'#00ff66' if is_pnl_positivo else '#ff3c3c'};">
                {'+' if is_pnl_positivo else ''}R$ {pnl_flutuante_brl:,.2f}
            </div>
            <div class="label">P&L Flutuante (não realizado) — se fechasse agora</div></div>""",
            unsafe_allow_html=True,
        )
    with pl3:
        st.markdown(
            f"""<div class="risk-box">
            <div class="value" style="color:{'#00ff66' if is_pnl_positivo else '#ff3c3c'};">
                {'+' if is_pnl_positivo else ''}{pnl_flutuante_pct:,.2f}%
            </div>
            <div class="label">Variação sobre o preço de entrada</div></div>""",
            unsafe_allow_html=True,
        )
    st.caption(f"Cotação de mercado obtida às {live_now['horario'].strftime('%d/%m/%Y %H:%M')} (fuso da fonte de dados).")
else:
    st.caption("⚠️ Não foi possível obter a cotação ao vivo para calcular o P&L flutuante agora.")

st.markdown("---")

# ==============================================================================
# PAINEL MACRO GLOBAL — DXY, JUROS DOS EUA, BRENT, SELIC, CDI, PTAX
# ==============================================================================
st.subheader("🌎 Painel Macro Global")
st.caption("Fatores que historicamente pressionam o USD/BRL: força global do dólar, juros, commodities e juros locais.")

with st.spinner("Buscando dados macro..."):
    macro = get_macro_globals()
    selic = get_bcb_sgs(432)
    cdi = get_bcb_sgs(4389)
    ptax = get_ptax()

macro_cols = st.columns(6)

dxy = macro.get("DX-Y.NYB")
with macro_cols[0]:
    if dxy:
        st.metric("DXY (Índice do Dólar)", f"{dxy['valor']:.2f}", delta=f"{dxy['variacao']:.2f}%")
    else:
        st.metric("DXY (Índice do Dólar)", "—")

us10y = macro.get("^TNX")
with macro_cols[1]:
    if us10y:
        st.metric("Treasury EUA 10 anos", f"{us10y['valor']:.2f}%", delta=f"{us10y['variacao']:.2f}%")
    else:
        st.metric("Treasury EUA 10 anos", "—")

brent = macro.get("BZ=F")
with macro_cols[2]:
    if brent:
        st.metric("Petróleo Brent (USD)", f"US$ {brent['valor']:.2f}", delta=f"{brent['variacao']:.2f}%")
    else:
        st.metric("Petróleo Brent (USD)", "—")

with macro_cols[3]:
    st.metric("Selic Meta (BCB)", f"{selic:.2f}%" if selic is not None else "—")

with macro_cols[4]:
    st.metric("CDI (a.a.)", f"{cdi:.2f}%" if cdi is not None else "—")

with macro_cols[5]:
    if ptax:
        st.metric("PTAX (Dólar Oficial BCB)", f"R$ {ptax['venda']:.4f}")
    else:
        st.metric("PTAX (Dólar Oficial BCB)", "—")

if ptax:
    st.caption(f"PTAX compra: R$ {ptax['compra']:.4f} · venda: R$ {ptax['venda']:.4f} · referência: {ptax['data']}")

st.markdown("---")

# ==============================================================================
# DASHBOARD PRINCIPAL — GRÁFICO + TERMÔMETRO TÉCNICO (TRADINGVIEW)
# ==============================================================================
st.subheader("📈 Monitoramento em Tempo Real")

col_chart, col_gauge = st.columns([3, 1])

with col_chart:
    tradingview_chart_html = """
    <div class="tradingview-widget-container">
      <div id="tradingview_usdbrl_chart"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {
      "width": "100%", "height": 610, "symbol": "FX_IDC:USDBRL", "interval": "60",
      "timezone": "America/Sao_Paulo", "theme": "dark", "style": "1", "locale": "br",
      "toolbar_bg": "#0e1117", "enable_publishing": false, "hide_top_toolbar": false,
      "hide_legend": false, "withdateranges": true, "allow_symbol_change": true,
      "details": true, "hotlist": false, "calendar": false,
      "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"],
      "support_host": "https://www.tradingview.com",
      "container_id": "tradingview_usdbrl_chart"
      }
      );
      </script>
    </div>
    """
    components.html(tradingview_chart_html, height=620)

with col_gauge:
    tradingview_gauge_html = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript"
        src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
      {
      "interval": "1h", "width": "100%", "isTransparent": false, "height": 610,
      "symbol": "FX_IDC:USDBRL", "showIntervalTabs": true, "displayMode": "single",
      "locale": "br", "colorTheme": "dark"
      }
      </script>
    </div>
    """
    components.html(tradingview_gauge_html, height=620)

st.markdown("---")

# ==============================================================================
# COMPARATIVO COM MOEDAS EMERGENTES
# ==============================================================================
st.subheader("💱 Comparativo com Moedas Emergentes")
st.caption("Ajuda a identificar se o movimento do real é isolado ou parte de uma tendência geral de mercados emergentes.")

tradingview_em_html = """
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" async>
  {
  "colorTheme": "dark",
  "dateRange": "1M",
  "showChart": true,
  "locale": "br",
  "width": "100%",
  "height": 400,
  "largeChartUrl": "",
  "isTransparent": false,
  "showSymbolLogo": true,
  "showFloatingTooltip": false,
  "plotLineColorGrowing": "rgba(0, 255, 102, 1)",
  "plotLineColorFalling": "rgba(255, 60, 60, 1)",
  "gridLineColor": "rgba(42, 46, 57, 0)",
  "scaleFontColor": "rgba(154, 160, 170, 1)",
  "belowLineFillColorGrowing": "rgba(0, 255, 102, 0.12)",
  "belowLineFillColorFalling": "rgba(255, 60, 60, 0.12)",
  "symbolActiveColor": "rgba(0, 255, 102, 0.12)",
  "tabs": [
    {
      "title": "Moedas Emergentes vs USD",
      "symbols": [
        {"s": "FX_IDC:USDBRL", "d": "USD/BRL (Real)"},
        {"s": "FX_IDC:USDMXN", "d": "USD/MXN (Peso Mex.)"},
        {"s": "FX_IDC:USDZAR", "d": "USD/ZAR (Rand)"},
        {"s": "FX_IDC:USDCLP", "d": "USD/CLP (Peso Chileno)"},
        {"s": "FX_IDC:USDTRY", "d": "USD/TRY (Lira)"},
        {"s": "FX_IDC:USDINR", "d": "USD/INR (Rupia)"}
      ],
      "originalTitle": "Moedas Emergentes"
    }
  ]
  }
  </script>
</div>
"""
components.html(tradingview_em_html, height=420)

st.markdown("---")

# ==============================================================================
# VOLATILIDADE DO PAR (ATR e VOLATILIDADE ANUALIZADA)
# ==============================================================================
st.subheader("📉 Volatilidade do Par USD/BRL")
st.caption("Use esses valores como referência para calibrar Stop Loss e Take Profit de forma mais técnica.")

vol_data = get_usdbrl_volatility()
vol_cols = st.columns(3)

if vol_data:
    with vol_cols[0]:
        st.metric("ATR (14 dias)", f"R$ {vol_data['atr14']:.4f}")
    with vol_cols[1]:
        st.metric("Volatilidade Anualizada", f"{vol_data['vol_anualizada']:.2f}%")
    with vol_cols[2]:
        st.metric("Último Fechamento (Yahoo)", f"R$ {vol_data['ultimo_fechamento']:.4f}")
    st.info(
        f"💡 Nos últimos 14 dias, o USD/BRL variou em média **R$ {vol_data['atr14']:.4f}** por dia (ATR). "
        "Stops muito menores que esse valor tendem a ser 'estopados' por ruído normal do mercado."
    )
else:
    st.warning("Não foi possível calcular a volatilidade agora (dados do Yahoo Finance indisponíveis no momento).")

st.markdown("---")

# ==============================================================================
# PRÓXIMAS REUNIÕES DE JUROS — COPOM E FED
# ==============================================================================
st.subheader("🏦 Próximas Reuniões de Juros — Copom & FED")
st.caption("Os dois eventos que mais costumam mexer no USD/BRL: decisão de juros no Brasil e nos EUA.")

hoje = date.today()
prox_copom = proxima_reuniao(COPOM_2026, hoje)
prox_fomc = proxima_reuniao(FOMC_2026, hoje)

col_copom, col_fomc = st.columns(2)

with col_copom:
    if prox_copom:
        inicio, fim = prox_copom
        dias_restantes = (fim - hoje).days
        st.markdown(
            f"""
            <div class="event-card">
                <div class="title">🇧🇷 Copom (Banco Central do Brasil)</div>
                <div class="sub">Reunião: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}</div>
                <div class="countdown">Faltam {dias_restantes} dias</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Calendário do Copom para o próximo ano ainda não disponível. Consulte bcb.gov.br.")

with col_fomc:
    if prox_fomc:
        inicio, fim = prox_fomc
        dias_restantes = (fim - hoje).days
        st.markdown(
            f"""
            <div class="event-card fed">
                <div class="title">🇺🇸 FOMC (Federal Reserve)</div>
                <div class="sub">Reunião: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}</div>
                <div class="countdown">Faltam {dias_restantes} dias</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Calendário do FOMC para o próximo ano ainda não disponível. Consulte federalreserve.gov.")

st.markdown("---")

# ==============================================================================
# NOTÍCIAS DO MERCADO
# ==============================================================================
st.subheader("📰 Notícias do Mercado")

tradingview_news_html = """
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
  {
  "feedMode": "symbol",
  "symbol": "FX_IDC:USDBRL",
  "colorTheme": "dark",
  "isTransparent": false,
  "displayMode": "regular",
  "width": "100%",
  "height": 400,
  "locale": "br"
  }
  </script>
</div>
"""
components.html(tradingview_news_html, height=420)

st.markdown("---")

# ==============================================================================
# CALENDÁRIO ECONÔMICO — EVENTOS DE ALTO IMPACTO USD / BRL
# ==============================================================================
st.subheader("🗓️ Calendário Econômico — Eventos de Alto Impacto (USD / BRL)")
st.caption("Filtrado exclusivamente para moedas USD e BRL, importância alta.")

tradingview_calendar_html = """
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  {
  "colorTheme": "dark",
  "isTransparent": false,
  "width": "100%",
  "height": 500,
  "locale": "br",
  "importanceFilter": "1",
  "currencyFilter": "USD,BRL"
  }
  </script>
</div>
"""
components.html(tradingview_calendar_html, height=520)

st.markdown("---")
st.caption(
    "Dólar Desk © — Ferramenta de estudo e simulação. Cotações e widgets fornecidos pela TradingView, "
    "Yahoo Finance e Banco Central do Brasil (PTAX/SGS). Nenhuma informação aqui constitui recomendação de investimento."
)
