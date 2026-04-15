"""
Dashboard de Churn - Nummy / PagSeguro
Churn comportamental: estabelecimentos que transacionaram no P1 mas nao no P2.

Instalacao:
    pip install streamlit plotly pandas

Execucao:
    streamlit run app.py
"""

import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os
import datetime
import requests
import csv


def get_secret(key, default=None):
    return st.secrets.get(key, default)

def perform_auth():
    base_url = get_secret("PAYTIME_BASE_URL", "https://api.paytime.com.br")
    url = f"{base_url}/v1/auth/login"
    
    # Payload EXATAMENTE igual ao seu auth.py original
    payload = {
        "x-token": get_secret("PAYTIME_X_TOKEN"),
        "authentication-key": get_secret("PAYTIME_AUTH_KEY"),
        "integration-key": get_secret("PAYTIME_INTEGRATION_KEY")
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    # Puxando o token com as mesmas margens de segurança do seu arquivo original
    token = data.get("token") or data.get("access_token") or data.get("data", {}).get("token")
    
    if not token:
        raise ValueError(f"Token não encontrado na resposta: {data}")
        
    return token

def parse_transaction(tx: dict) -> dict:
    customer = tx.get("customer", {}) or {}
    card     = tx.get("card", {})      or {}
    estab    = tx.get("establishment", {}) or {}
    acquirer = tx.get("acquirer", {})  or {}
    plan     = tx.get("plan", {})      or {}

    return {
        "id":                 tx.get("_id", ""),
        "status":             tx.get("status", ""),
        "type":               tx.get("type", ""),
        "amount":             tx.get("amount", ""),
        "original_amount":    tx.get("original_amount", ""),
        "fees":               tx.get("fees", ""),
        "installments":       tx.get("installments", ""),
        "gateway_key":        tx.get("gateway_key", ""),
        "gateway_auth":       tx.get("gateway_authorization", ""),
        "created_at":         tx.get("created_at", ""),
        "customer_name":      f"{customer.get('first_name','')} {customer.get('last_name','')}".strip(),
        "customer_document":  customer.get("document", ""),
        "customer_email":     customer.get("email", ""),
        "customer_phone":     customer.get("phone", ""),
        "card_brand":         card.get("brand_name", ""),
        "card_first4":        card.get("first4_digits", ""),
        "card_last4":         card.get("last4_digits", ""),
        "card_holder":        card.get("holder_name", ""),
        "establishment_id":   estab.get("id", ""),
        "establishment_name": estab.get("first_name", "").strip(),
        "acquirer":           acquirer.get("name", ""),
        "plan_name":          plan.get("name", ""),
    }

# --- FUNÇÕES DO EXPORT.PY ---
def fetch_and_save_data(token):
    base_url = get_secret("PAYTIME_BASE_URL", "https://api.paytime.com.br")
    url = f"{base_url}/v1/marketplace/transactions?perPage=30000"
    
    headers = {
        "accept": "application/json",
        "integration-key": get_secret("PAYTIME_INTEGRATION_KEY"),
        "x-token": get_secret("PAYTIME_X_TOKEN"),
        "authorization": f"Bearer {token}",
    }
    
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()
    transactions = response.json()
    
    # Normaliza a lista de transações (ajustado conforme seu JSON)
    if isinstance(transactions, dict):
        transactions = transactions.get("data", [])
        
    if not transactions:
        return False

    # Processamento e Salvamento (Usando o nome fixo que definimos)
    rows = [parse_transaction(tx) for tx in transactions]
    output_path = "export_transacoes.csv"
    
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return True

# --- INTERFACE NO STREAMLIT ---
with st.sidebar:
    st.markdown("---")
    st.markdown("<p class='sidebar-title'>Gerenciamento de Dados</p>", unsafe_allow_html=True)
    
    if st.button("🔄 Sincronizar Paytime", type="primary", use_container_width=True):
        with st.status("Iniciando sincronização...", expanded=True) as status:
            try:
                status.write("Autenticando na API...")
                token = perform_auth()
                
                status.write("Buscando transações (isso pode demorar)...")
                sucesso = fetch_and_save_data(token)
                
                if sucesso:
                    status.update(label="Sincronização concluída!", state="complete", expanded=False)
                    st.toast("Dados atualizados com sucesso!", icon="✅")
                    st.rerun()
                else:
                    status.update(label="Nenhum dado novo encontrado.", state="error")
            except Exception as e:
                status.update(label=f"Erro na sincronização", state="error")
                st.error(f"Detalhes: {e}")

st.markdown("<p class='dash-title'><span>Nummy</span> · Dashboard de Churn</p>", unsafe_allow_html=True)

# 1. Cria uma área amigável para o cliente atualizar os dados
with st.expander("🔄 Atualizar Dados da Paytime", expanded=False):
    st.write("Clique no botão abaixo para buscar as transações mais recentes da API.")
    
    if st.button("Buscar Novas Transações", type="primary"):
        with st.spinner("Conectando à Paytime e baixando histórico... Isso pode levar um minuto."):
            try:
                # Aqui você chama as funções que já criou no export.py!
                # token = load_token()
                # headers = build_headers(token)
                # transacoes = fetch_transactions(headers)
                # save_csv(transacoes, output_dir=".") 
                
                st.success("Dados atualizados com sucesso! A página será recarregada.")
                st.rerun() # Faz o dashboard piscar e carregar o CSV novo automaticamente
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

st.markdown("---")

st.set_page_config(
    page_title="Nummy · Dashboard de Churn",
    page_icon="💳",
    layout="wide",
)

# Paleta Nummy
DARK_BG  = "#1A1A1A"
CARD_BG  = "#242424"
CARD_BG2 = "#1E1E1E"
YELLOW1  = "#F5C518"
YELLOW2  = "#FFD94D"
DARK_TXT = "#2B2B2B"
AMBER    = "#FF9F1C"
RED      = "#FF4D6A"
GREEN    = "#4ADE80"
BLUE     = "#5B9BF5"
MUTED    = "#7A7A7A"
TEXT_MAIN= "#F0F0F0"
BORDER   = "#333333"
P1_COLOR = YELLOW1
P2_COLOR = BLUE

# ATIVO: prova de uso real da plataforma (exclui FAILED e CANCELED)
ACTIVE_STATUS = {"APPROVED", "PAID", "AUTHORIZED", "REFUNDED", "CHARGEBACK", "DISPUTE"}

# TPV: apenas dinheiro que de fato transitou (exclui estornos e disputas)
TPV_STATUS = {"APPROVED", "PAID", "AUTHORIZED"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor=CARD_BG,
    plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_MAIN, family="sans-serif", size=12),
    margin=dict(l=16, r=16, t=44, b=16),
    title_font=dict(size=13, color=TEXT_MAIN),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_MAIN),
                traceorder="reversed"),
)
AXIS_DEF = dict(
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, color=MUTED),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, color=MUTED),
)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {DARK_BG}; }}
    .block-container {{ padding-top: 3.5rem !important; padding-bottom: 2rem; }}
    section[data-testid="stSidebar"] {{
        background-color: {CARD_BG}; border-right: 1px solid {BORDER};
    }}
    .dash-title {{ font-size:1.6rem; font-weight:800; color:{TEXT_MAIN}; margin:0 0 4px 0; }}
    .dash-title span {{ color:{YELLOW1}; }}
    .dash-subtitle {{ font-size:0.85rem; color:{MUTED}; margin-bottom:20px; }}

    .kpi-card {{
        background: linear-gradient(145deg, {CARD_BG}, {CARD_BG2});
        border-radius:14px; padding:18px 14px; text-align:center;
        border:1.5px solid {BORDER}; position:relative; overflow:hidden;
    }}
    .kpi-card::before {{
        content:''; position:absolute; top:0; left:0; right:0;
        height:3px; border-radius:14px 14px 0 0;
    }}
    .kpi-card.c1::before {{ background:{YELLOW1}; }}
    .kpi-card.c2::before {{ background:{RED}; }}
    .kpi-card.c3::before {{ background:{GREEN}; }}
    .kpi-card.c4::before {{ background:{BLUE}; }}
    .kpi-value {{ font-size:1.9rem; font-weight:800; line-height:1; margin-bottom:4px; }}
    .kpi-label {{ font-size:0.72rem; color:{MUTED}; text-transform:uppercase; letter-spacing:0.08em; font-weight:600; }}
    .kpi-sub   {{ font-size:0.72rem; color:{MUTED}; margin-top:5px; }}

    .section-label {{
        font-size:0.7rem; font-weight:700; letter-spacing:0.12em;
        text-transform:uppercase; color:{MUTED}; margin:24px 0 10px;
    }}
    hr {{ border-color:{BORDER} !important; }}
    .rank-table {{ width:100%; border-collapse:separate; border-spacing:0 4px; font-size:0.9rem; }}
    .rank-table th {{
        color:{MUTED}; font-weight:600; font-size:0.7rem; text-transform:uppercase;
        letter-spacing:0.08em; padding:6px 12px; border-bottom:1px solid {BORDER};
    }}
    .rank-table td {{ padding:10px 12px; color:{TEXT_MAIN}; background:{CARD_BG}; }}
    .rank-table tr td:first-child {{ border-radius:8px 0 0 8px; }}
    .rank-table tr td:last-child  {{ border-radius:0 8px 8px 0; }}
    .rank-table tr:hover td {{ background:#2e2e2e; }}
    .medal-gold   {{ color:{YELLOW1}; font-weight:800; }}
    .medal-silver {{ color:#C0C0C0;   font-weight:800; }}
    .medal-bronze {{ color:#CD7F32;   font-weight:800; }}
    .tag-churn  {{ background:rgba(255,77,106,0.15);  color:{RED};    padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:700; }}
    .tag-new    {{ background:rgba(245,197,24,0.15);  color:{YELLOW1}; padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:700; }}
    .tag-retain {{ background:rgba(74,222,128,0.15);  color:{GREEN};  padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:700; }}
    .sidebar-title {{ font-size:0.72rem; font-weight:700; letter-spacing:0.1em;
                      text-transform:uppercase; color:{MUTED}; margin-bottom:6px; }}
    h1,h2,h3 {{ color:{TEXT_MAIN} !important; }}
    [data-testid="stPlotlyChart"] > div {{
        border-radius:12px; border:1px solid {BORDER}; overflow:hidden;
    }}
</style>
""", unsafe_allow_html=True)


# Helpers
def brl(v):
    return f"R$ {v/100:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def date_selector(prefix, default_date, all_years, dias, meses, label):
    st.markdown(f"<p class='sidebar-title'>{label}</p>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    d = c1.selectbox("Dia", dias, index=dias.index(default_date.day),
                     key=f"{prefix}_d", label_visibility="visible")
    m = c2.selectbox("Mes", list(meses.values()), index=default_date.month-1,
                     key=f"{prefix}_m", label_visibility="visible")
    a = c3.selectbox("Ano", all_years, index=all_years.index(default_date.year),
                     key=f"{prefix}_a", label_visibility="visible")
    m_num = list(meses.keys())[list(meses.values()).index(m)]
    try:    return datetime.date(a, m_num, d)
    except: return default_date

@st.cache_data
def load_data(path):
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    df.columns = df.columns.str.strip()
    for col in ["amount","original_amount","fees","installments"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["date"] = df["created_at"].dt.date
    return df

def filter_period(df, est_list, ini, fim):
    return df[
        df["establishment_name"].isin(est_list) &
        (df["date"] >= ini) & (df["date"] <= fim)
    ].copy()

def active_ests(df_period):
    """Estabelecimentos com pelo menos uma transacao de uso real (exclui FAILED/CANCELED)."""
    df_active = df_period[df_period["status"].str.upper().isin(ACTIVE_STATUS)]
    return set(df_active["establishment_name"].dropna().unique())

def volume_by_est(df_period):
    """Volume financeiro real (TPV): apenas APPROVED, PAID, AUTHORIZED."""
    df_tpv = df_period[df_period["status"].str.upper().isin(TPV_STATUS)]
    return df_tpv.groupby("establishment_name")["original_amount"].sum().to_dict()

def count_by_est(df_period):
    """Contagem de transacoes ativas (exclui FAILED/CANCELED)."""
    df_active = df_period[df_period["status"].str.upper().isin(ACTIVE_STATUS)]
    return df_active.groupby("establishment_name").size().to_dict()


# Carregamento
CSV_PATH = "export_transacoes.csv"

st.markdown(f"""
<p class="dash-title"><span>Nummy</span> · Dashboard de Churn</p>
<p class="dash-subtitle">Churn = estabelecimentos que transacionaram no P1 mas nao no P2 · Gateway: PAYTIME</p>
""", unsafe_allow_html=True)

try:
    df_raw = load_data(CSV_PATH)
except FileNotFoundError:
    st.error(f"Arquivo '{CSV_PATH}' nao encontrado.")
    st.stop()

all_dates = sorted(df_raw["date"].dropna().unique())
min_date  = all_dates[0]
today    = datetime.date.today()
max_date  = all_dates[-1]
all_years = sorted({d.year for d in all_dates} | {today.year})
dias  = list(range(1, 32))
meses = {1:"Janeiro",2:"Fevereiro",3:"Marco",4:"Abril",5:"Maio",6:"Junho",
          7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}
# Defaults WoW: P2 = ultimos 7 dias (hoje - 6 ate hoje), P1 = 7 dias anteriores
p2_def_fim = today - datetime.timedelta(days=1)
p2_def_ini = today - datetime.timedelta(days=7)
p1_def_fim = today - datetime.timedelta(days=8)
p1_def_ini = today - datetime.timedelta(days=14)

# Se as datas WoW estiverem fora do range da base, cai para o range disponivel
def clamp(d, lo, hi): return max(lo, min(hi, d))
p2_def_fim = clamp(p2_def_fim, min_date, max_date)
p2_def_ini = clamp(p2_def_ini, min_date, max_date)
p1_def_fim = clamp(p1_def_fim, min_date, max_date)
p1_def_ini = clamp(p1_def_ini, min_date, max_date)


# Sidebar
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center; margin-bottom:20px;'>
        <div style='display:inline-block; background:{YELLOW1}; border-radius:50%;
                    width:44px; height:44px; line-height:44px; font-size:1.3rem;
                    font-weight:900; color:{DARK_TXT}; margin-bottom:6px;'>N</div>
        <span style='color:{MUTED}; font-size:0.8rem; display:block'>Dashboard · Filtros</span>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"<p class='sidebar-title'>Estabelecimento</p>", unsafe_allow_html=True)
    estabelecimentos = sorted(df_raw["establishment_name"].dropna().unique())
    sel_est = st.multiselect(
        label="estab", options=estabelecimentos, default=estabelecimentos,
        placeholder="Selecione...", label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f"<div style='background:rgba(245,197,24,0.1); border:1px solid {YELLOW1}; border-radius:8px; padding:8px 10px; margin-bottom:10px; font-size:0.72rem; font-weight:700; color:{YELLOW1}'>Periodo 1</div>", unsafe_allow_html=True)
    p1_ini = date_selector("p1i", p1_def_ini, all_years, dias, meses, "Inicio")
    p1_fim = date_selector("p1f", p1_def_fim, all_years, dias, meses, "Fim")
    if p1_ini > p1_fim:
        st.warning("P1: data inicial maior que a final.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div style='background:rgba(91,155,245,0.1); border:1px solid {BLUE}; border-radius:8px; padding:8px 10px; margin-bottom:10px; font-size:0.72rem; font-weight:700; color:{BLUE}'>Periodo 2</div>", unsafe_allow_html=True)
    p2_ini = date_selector("p2i", p2_def_ini, all_years, dias, meses, "Inicio")
    p2_fim = date_selector("p2f", p2_def_fim, all_years, dias, meses, "Fim")
    if p2_ini > p2_fim:
        st.warning("P2: data inicial maior que a final.")

    st.markdown("---")
    st.markdown(f"""
    <div style='font-size:0.75rem; color:{MUTED}'>
        <div style='color:{YELLOW1}; font-weight:700; margin-bottom:2px'>P1:
            <span style='color:{TEXT_MAIN}; font-weight:400'> {p1_ini.strftime("%d/%m/%Y")} a {p1_fim.strftime("%d/%m/%Y")}</span>
        </div>
        <div style='color:{BLUE}; font-weight:700'>P2:
            <span style='color:{TEXT_MAIN}; font-weight:400'> {p2_ini.strftime("%d/%m/%Y")} a {p2_fim.strftime("%d/%m/%Y")}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('---')
    st.markdown("<p class='sidebar-title'>Top N Estabelecimentos</p>", unsafe_allow_html=True)
    top_n = st.slider(
        label='top_n_slider',
        min_value=5,
        max_value=200,
        value=15,
        step=5,
        label_visibility='collapsed',
        help='Quantidade de estabelecimentos em churn exibidos nos graficos e no ranking'
    )
    st.markdown(
        f"<div style='font-size:0.72rem; color:#7A7A7A; margin-top:4px'>"
        f"Exibindo os <b style='color:#F0F0F0'>{top_n}</b> com maior volume perdido"
        f"</div>",
        unsafe_allow_html=True
    )


# Mapa de id por estabelecimento
est_id_map = df_raw.dropna(subset=["establishment_name","establishment_id"])                    .drop_duplicates("establishment_name")                    .set_index("establishment_name")["establishment_id"].to_dict()

# Filtragem
df_p1 = filter_period(df_raw, sel_est, p1_ini, p1_fim)
df_p2 = filter_period(df_raw, sel_est, p2_ini, p2_fim)

if df_p1.empty and df_p2.empty:
    st.warning("Nenhuma transacao encontrada para os periodos selecionados.")
    st.stop()

lp1 = f"{p1_ini.strftime('%d/%m/%y')} - {p1_fim.strftime('%d/%m/%y')}"
lp2 = f"{p2_ini.strftime('%d/%m/%y')} - {p2_fim.strftime('%d/%m/%y')}"

# Logica de churn comportamental
ests_p1  = active_ests(df_p1)
ests_p2  = active_ests(df_p2)
churned  = ests_p1 - ests_p2      # estavam no P1, sumiram no P2 (nenhuma transacao ativa)
retained = ests_p1 & ests_p2      # ativo nos dois periodos
new_ests = ests_p2 - ests_p1      # apareceram so no P2

vol_p1      = volume_by_est(df_p1)
vol_p2      = volume_by_est(df_p2)
cnt_p1      = count_by_est(df_p1)
cnt_p2      = count_by_est(df_p2)
vol_churned = sum(vol_p1.get(e, 0) for e in churned)

# Lojas retidas mas com TPV zerado no P2 — possivel churn de receita
# (transacionou mas nao gerou faturamento: so estornos/disputas no P2)
tpv_zero_p2 = {e for e in retained if vol_p2.get(e, 0) == 0}

churn_rate  = (len(churned)  / len(ests_p1) * 100) if ests_p1 else 0
retain_rate = (len(retained) / len(ests_p1) * 100) if ests_p1 else 0


# KPI Cards — mesmos 4 da versao anterior, com nova logica
st.markdown(f"<p class='section-label'>Visao Geral</p>", unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)

# Total de churns (antes: total de refunded)
# Volume de churn (antes: volume estornado)
# Taxa de churn % (antes: ticket medio)
# Volume perdido (antes: total em taxas)
kpis = [
    (k1, "c1", "Total de Churns",   f"{len(churned)}",
     f"{churn_rate:.1f}% dos clientes P1",              RED),
    (k2, "c2", "Volume de Churn",   brl(vol_churned),
     f"receita perdida dos clientes que saíram",         RED),
    (k3, "c3", "Taxa de Retencao",  f"{retain_rate:.1f}%",
     f"{len(retained)} de {len(ests_p1)} retidos",       GREEN),
    (k4, "c4", "Novos no P2",       f"{len(new_ests)}",
     f"estabelecimentos que nao estavam no P1",          YELLOW1),
]
for col, css, label, value, sub, color in kpis:
    col.markdown(f"""
    <div class="kpi-card {css}">
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Banner TPV zero (ativo mas sem faturamento real no P2)

if churned or tpv_zero_p2:
    st.markdown("<br>", unsafe_allow_html=True)


# Graficos linha 1
st.markdown(f"<p class='section-label'>Volume & Quantidade · P1 vs P2 (apenas churns)</p>", unsafe_allow_html=True)
col_a, col_b = st.columns(2)

# Graficos e ranking mostram apenas churned para legibilidade com muitos estabelecimentos
# 1. Ordena os clientes em churn pelo MAIOR volume perdido no P1
churn_ordenado = sorted(churned, key=lambda e: vol_p1.get(e, 0), reverse=True)

# 2. Seleciona apenas os 15 maiores ofensores (ajuste esse número se quiser ver mais ou menos)
# TOP_N agora vem do slider na sidebar
top_churns = churn_ordenado[:top_n]

# 3. O Plotly desenha de baixo para cima. Invertemos a lista [::-1] 
# para garantir que o cliente que deu o maior prejuízo fique no TOPO do gráfico.
all_ests_sorted = top_churns[::-1]
show_charts = len(all_ests_sorted) > 0
show_charts = len(all_ests_sorted) > 0

def est_color(e):
    if e in churned:  return RED
    if e in new_ests: return YELLOW1
    return GREEN

if show_charts:
  with col_a:
    # Volume — apenas churned
    v1_list = [vol_p1.get(e, 0) for e in all_ests_sorted]
    v2_list = [vol_p2.get(e, 0) for e in all_ests_sorted]
    fig1 = go.Figure([
        go.Bar(name=f"P2 · {lp2}", y=all_ests_sorted, x=v2_list, orientation="h",
               marker=dict(color=P2_COLOR, line=dict(width=0)),
               text=[brl(v) for v in v2_list], textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
        go.Bar(name=f"P1 · {lp1}", y=all_ests_sorted, x=v1_list, orientation="h",
               marker=dict(color=P1_COLOR, line=dict(width=0)),
               text=[brl(v) for v in v1_list], textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
    ])
    fig1.update_layout(**PLOTLY_LAYOUT, **AXIS_DEF,
                       title="Volume Transacionado - Estabelecimentos em Churn",
                       barmode="group", height=320,
                       xaxis_tickformat=",.0f")
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    # Quantidade por estabelecimento P1 vs P2
    c1_list = [cnt_p1.get(e, 0) for e in all_ests_sorted]
    c2_list = [cnt_p2.get(e, 0) for e in all_ests_sorted]
    fig2 = go.Figure([
        go.Bar(name=f"P2 · {lp2}", y=all_ests_sorted, x=c2_list, orientation="h",
               marker=dict(color=P2_COLOR, line=dict(width=0)),
               text=c2_list, textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
        go.Bar(name=f"P1 · {lp1}", y=all_ests_sorted, x=c1_list, orientation="h",
               marker=dict(color=P1_COLOR, line=dict(width=0)),
               text=c1_list, textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
    ])
    fig2.update_layout(**PLOTLY_LAYOUT, **AXIS_DEF,
                       title="Qtd. de Transacoes - Estabelecimentos em Churn",
                       barmode="group", height=320)
    st.plotly_chart(fig2, use_container_width=True)


# Graficos linha 2
st.markdown(f"<p class='section-label'>Taxa de Churn & Ticket Medio · P1 vs P2 (apenas churns)</p>", unsafe_allow_html=True)
col_c, col_d = st.columns(2)


if show_charts:
  with col_c:
    # % participacao — apenas churned
    all_total_p1 = sum(cnt_p1.values())
    all_total_p2 = sum(cnt_p2.values())

    pct1_list = [(cnt_p1.get(e, 0) / all_total_p1 * 100) if all_total_p1 > 0 else 0
                 for e in all_ests_sorted]
    pct2_list = [(cnt_p2.get(e, 0) / all_total_p2 * 100) if all_total_p2 > 0 else 0
                 for e in all_ests_sorted]

    fig3 = go.Figure([
        go.Bar(name=f"P2 · {lp2}", y=all_ests_sorted, x=pct2_list, orientation="h",
               marker=dict(color=P2_COLOR, line=dict(width=0)),
               text=[f"{v:.1f}%" for v in pct2_list], textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
        go.Bar(name=f"P1 · {lp1}", y=all_ests_sorted, x=pct1_list, orientation="h",
               marker=dict(color=P1_COLOR, line=dict(width=0)),
               text=[f"{v:.1f}%" for v in pct1_list], textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
    ])
    # Linha vertical indicando media P1
    if pct1_list:
        avg_p1 = sum(pct1_list) / len(pct1_list)
        fig3.add_vline(x=avg_p1, line_dash="dot", line_color=MUTED,
                       annotation_text="media P1", annotation_font_color=MUTED,
                       annotation_font_size=10)
    fig3.update_layout(**PLOTLY_LAYOUT, **AXIS_DEF,
                       title="Participacao % no Volume Total - Estabelecimentos em Churn",
                       xaxis_ticksuffix="%", barmode="group", height=320)
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    # Ticket Medio por estabelecimento P1 vs P2
    # TPV_STATUS: apenas transacoes que geraram receita real
    def ticket_medio(df_period):
        df_tpv = df_period[df_period["status"].str.upper().isin(TPV_STATUS)]
        g = df_tpv.groupby("establishment_name")["original_amount"]
        return (g.sum() / g.count()).to_dict()

    tm1 = ticket_medio(df_p1)
    tm2 = ticket_medio(df_p2)
    tm1_list = [tm1.get(e, 0) for e in all_ests_sorted]
    tm2_list = [tm2.get(e, 0) for e in all_ests_sorted]

    fig4 = go.Figure([
        go.Bar(name=f"P2 · {lp2}", y=all_ests_sorted, x=tm2_list, orientation="h",
               marker=dict(color=P2_COLOR, line=dict(width=0)),
               text=[brl(v) for v in tm2_list], textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
        go.Bar(name=f"P1 · {lp1}", y=all_ests_sorted, x=tm1_list, orientation="h",
               marker=dict(color=P1_COLOR, line=dict(width=0)),
               text=[brl(v) for v in tm1_list], textposition="outside",
               textfont=dict(color=TEXT_MAIN, size=10)),
    ])
    fig4.update_layout(**PLOTLY_LAYOUT, **AXIS_DEF,
                       title="Ticket Medio - Estabelecimentos em Churn",
                       barmode="group", height=320,
                       xaxis_tickformat=",.0f")
    st.plotly_chart(fig4, use_container_width=True)


# Ranking
st.markdown("---")
# Resumo geral acima do ranking
st.markdown(
    f"<div style='display:flex; gap:24px; flex-wrap:wrap; margin-bottom:12px; font-size:0.82rem'>"
    f"<span style='color:{MUTED}'>Base total P1: <b style='color:{TEXT_MAIN}'>{len(ests_p1)}</b> estabelecimentos</span>"
    f"<span>&#8195;</span>"
    f"<span style='color:{GREEN}'>Retidos: <b style='color:{TEXT_MAIN}'>{len(retained)}</b></span>"
    f"<span style='color:{YELLOW1}'>Novos no P2: <b style='color:{TEXT_MAIN}'>{len(new_ests)}</b></span>"
    f"<span style='color:{RED}'>Churn: <b style='color:{TEXT_MAIN}'>{len(churned)}</b></span>"
    f"</div>",
    unsafe_allow_html=True
)
st.markdown(f"<p class='section-label'>Ranking — Top {top_n} Churns por Volume Perdido ({len(churned)} total · {len(ests_p1)} clientes P1)</p>", unsafe_allow_html=True)

medal_map = {1:"medal-gold", 2:"medal-silver", 3:"medal-bronze"}
medal_lbl = {1:"1o", 2:"2o", 3:"3o"}

# Ranking: apenas churned, ordenado por maior volume perdido
all_ests_rank = sorted(churned, key=lambda e: -vol_p1.get(e, 0))[:top_n]

rows_html = ""
for pos, est in enumerate(all_ests_rank, 1):
    tag = '<span class="tag-churn">CHURN</span>'
    v1e  = vol_p1.get(est, 0)
    v2e  = vol_p2.get(est, 0)
    c1e  = cnt_p1.get(est, 0)
    c2e  = cnt_p2.get(est, 0)
    dv   = v2e - v1e
    dvc  = RED if dv < 0 else (GREEN if dv > 0 else MUTED)
    dvs  = ("+" if dv >= 0 else "-") + brl(abs(dv))
    mc   = medal_map.get(pos, "")
    ml   = medal_lbl.get(pos, str(pos))
    mtd  = f'<span class="{mc}">{ml}</span>' if mc else f'<span style="color:{MUTED}">{ml}</span>'

    eid = est_id_map.get(est, "—")
    rows_html += f"""<tr>
        <td style="text-align:center">{mtd}</td>
        <td style="font-weight:{'700' if pos<=3 else '400'}">{est}</td>
        <td style="color:{MUTED}; font-size:0.82rem">{eid}</td>
        <td>{tag}</td>
        <td style="color:{YELLOW1}; text-align:right">{brl(v1e)}</td>
        <td style="color:{BLUE}; text-align:right">{brl(v2e)}</td>
        <td style="color:{dvc}; font-weight:700; text-align:right">{dvs}</td>
        <td style="text-align:right; color:{MUTED}">{int(c1e)}</td>
        <td style="text-align:right; color:{MUTED}">{int(c2e)}</td>
    </tr>"""

st.markdown(f"""
<table class="rank-table">
  <thead><tr>
    <th style="text-align:center">#</th>
    <th>Estabelecimento</th>
    <th>ID</th>
    <th>Status</th>
    <th style="text-align:right">Volume P1</th>
    <th style="text-align:right">Volume P2</th>
    <th style="text-align:right">Delta Volume</th>
    <th style="text-align:right">Transacoes P1</th>
    <th style="text-align:right">Transacoes P2</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>
<br>
<div style='display:flex; gap:20px; font-size:0.75rem; color:{MUTED}; flex-wrap:wrap'>
    <span style='color:{RED}'>CHURN = estava no P1, sumiu no P2 · ordenado por volume perdido</span>
    <span style='color:{MUTED}'>Retidos ({len(retained)}) e novos ({len(new_ests)}) omitidos dos graficos para legibilidade</span>
    <span style='color:{AMBER}'>TPV ZERO = ativo mas sem faturamento real no P2</span>
</div>""", unsafe_allow_html=True)
