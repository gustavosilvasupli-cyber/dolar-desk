"""
================================================================================
 DÓLAR DESK — Dashboard de Monitoramento e Simulação de Operações USD/BRL
================================================================================
Como rodar:
    pip install streamlit
    streamlit run app.py
================================================================================
"""

import streamlit as st
import streamlit.components.v1 as components

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
    /* Fundo geral */
    .stApp {
        background-color: #0e1117;
        color: #FFFFFF;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #131722;
        border-right: 1px solid #2a2e39;
    }

    /* Títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
        font-family: 'Trebuchet MS', sans-serif;
    }

    /* Cards de métrica nativos do Streamlit */
    div[data-testid="stMetric"] {
        background-color: #161b26;
        border: 1px solid #2a2e39;
        border-radius: 10px;
        padding: 15px 15px 5px 15px;
    }
    div[data-testid="stMetricLabel"] {
        color: #9aa0aa !important;
        font-size: 0.85rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
    }

    /* Inputs */
    .stSelectbox, .stNumberInput {
        color: #FFFFFF;
    }

    /* Botões */
    .stButton>button {
        background-color: #00ff66;
        color: #0e1117;
        font-weight: bold;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #00cc52;
        color: #0e1117;
    }

    /* Divisores */
    hr {
        border-color: #2a2e39;
    }

    /* Caixa de destaque customizada (Risco x Retorno) */
    .risk-box {
        background-color: #161b26;
        border: 1px solid #2a2e39;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        margin-top: 10px;
    }
    .risk-box .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00ff66;
    }
    .risk-box .label {
        font-size: 0.85rem;
        color: #9aa0aa;
    }

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
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Cores auxiliares para uso em markdown
POSITIVE_COLOR = "#00ff66"
NEGATIVE_COLOR = "#ff3c3c"


def colored_text(value_text: str, is_positive: bool) -> str:
    """Retorna um span HTML colorido de acordo com o sinal do valor."""
    color = POSITIVE_COLOR if is_positive else NEGATIVE_COLOR
    return f"<span style='color:{color}; font-weight:700;'>{value_text}</span>"


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

    lote_usd = st.number_input(
        "Tamanho do Lote (USD)",
        min_value=1000.0,
        value=10000.0,
        step=1000.0,
        format="%.2f",
    )

    preco_entrada = st.number_input(
        "Preço de Entrada (R$ por USD)",
        min_value=0.01,
        value=5.50,
        step=0.01,
        format="%.4f",
    )

    preco_alvo = st.number_input(
        "Preço Alvo / Take Profit (R$)",
        min_value=0.01,
        value=5.65,
        step=0.01,
        format="%.4f",
    )

    preco_stop = st.number_input(
        "Preço de Stop Loss (R$)",
        min_value=0.01,
        value=5.45,
        step=0.01,
        format="%.4f",
    )

    st.markdown("---")

    alavancagem = st.selectbox(
        "Alavancagem Padrão de Mercado",
        [1, 2, 5, 10, 20, 30, 50],
        index=3,  # padrão 10x
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
    # COMPRA: lucra se preço subir (alvo > entrada), perde se cair (stop < entrada)
    variacao_lucro = preco_alvo - preco_entrada
    variacao_prejuizo = preco_entrada - preco_stop
else:
    # VENDA: lucra se preço cair (alvo < entrada), perde se subir (stop > entrada)
    variacao_lucro = preco_entrada - preco_alvo
    variacao_prejuizo = preco_stop - preco_entrada

lucro_maximo_brl = variacao_lucro * lote_usd
prejuizo_maximo_brl = variacao_prejuizo * lote_usd

lucro_percentual = (variacao_lucro / preco_entrada) * 100 if preco_entrada else 0
prejuizo_percentual = (variacao_prejuizo / preco_entrada) * 100 if preco_entrada else 0

valor_total_operacao_brl = lote_usd * preco_entrada
margem_requerida_brl = valor_total_operacao_brl / alavancagem if alavancagem else valor_total_operacao_brl

if prejuizo_maximo_brl > 0:
    relacao_risco_retorno = lucro_maximo_brl / prejuizo_maximo_brl
else:
    relacao_risco_retorno = 0.0

# Alertas de configuração inconsistente (ex: alvo do lado errado)
alerta_configuracao = None
if lucro_maximo_brl <= 0:
    alerta_configuracao = (
        "⚠️ O Preço Alvo definido não gera lucro para o tipo de operação selecionado. "
        "Revise os valores de entrada/alvo."
    )
elif prejuizo_maximo_brl <= 0:
    alerta_configuracao = (
        "⚠️ O Stop Loss definido não gera perda coerente para o tipo de operação selecionado. "
        "Revise os valores de entrada/stop."
    )

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
    st.metric(
        label="Valor Total da Operação",
        value=f"R$ {valor_total_operacao_brl:,.2f}",
    )

with m2:
    st.metric(
        label="Lucro Máximo Estimado",
        value=f"R$ {lucro_maximo_brl:,.2f}",
        delta=f"{lucro_percentual:,.2f}%",
    )

with m3:
    st.metric(
        label="Prejuízo Máximo Aceitável",
        value=f"R$ {prejuizo_maximo_brl:,.2f}",
        delta=f"-{abs(prejuizo_percentual):,.2f}%",
        delta_color="inverse",
    )

with m4:
    st.metric(
        label=f"Margem Requerida ({alavancagem}x)",
        value=f"R$ {margem_requerida_brl:,.2f}",
    )

with m5:
    st.markdown(
        f"""
        <div class="risk-box">
            <div class="value">1 : {relacao_risco_retorno:,.2f}</div>
            <div class="label">Relação Risco x Retorno</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
      "width": "100%",
      "height": 610,
      "symbol": "FX_IDC:USDBRL",
      "interval": "60",
      "timezone": "America/Sao_Paulo",
      "theme": "dark",
      "style": "1",
      "locale": "br",
      "toolbar_bg": "#0e1117",
      "enable_publishing": false,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "withdateranges": true,
      "allow_symbol_change": true,
      "details": true,
      "hotlist": false,
      "calendar": false,
      "studies": [
        "MASimple@tv-basicstudies",
        "RSI@tv-basicstudies"
      ],
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
        src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js"
        async>
      {
      "interval": "1h",
      "width": "100%",
      "isTransparent": false,
      "height": 610,
      "symbol": "FX_IDC:USDBRL",
      "showIntervalTabs": true,
      "displayMode": "single",
      "locale": "br",
      "colorTheme": "dark"
      }
      </script>
    </div>
    """
    components.html(tradingview_gauge_html, height=620)

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
    src="https://s3.tradingview.com/external-embedding/embed-widget-events.js"
    async>
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
    "Dólar Desk © — Ferramenta de estudo e simulação. Cotações e widgets fornecidos pela TradingView. "
    "Nenhuma informação aqui constitui recomendação de investimento."
)
