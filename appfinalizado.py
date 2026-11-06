"""
Dashboard de Churn - Nummy / PagSeguro
Churn comportamental: estabelecimentos que transacionaram no P1 mas nao no P2.

Instalacao:
    pip install streamlit plotly pandas

Execucao:
    streamlit run app.py
"""

import datetime
import gzip
import os
import shutil
import tempfile
import threading
import io

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

CSV_PATH = "export_transacoes.csv"
VERSION_PATH = "export_transacoes.versao"
DATA_RELEASE = "dados"
DATA_CHECK_SECONDS = 600
STALE_AFTER = datetime.timedelta(days=2)
BRASILIA = datetime.timezone(datetime.timedelta(hours=-3))


def github_headers(accept="application/vnd.github+json"):
    return {"accept": accept, "authorization": f"Bearer {st.secrets['DADOS_GITHUB_TOKEN']}"}


@st.cache_data(ttl=DATA_CHECK_SECONDS, show_spinner=False)
def latest_data_asset():
    """Consulta o arquivo mais recente publicado pela sincronização no repositório privado."""
    api_url = st.secrets.get("DADOS_API_URL", "https://api.github.com")
    url = f"{api_url}/repos/{st.secrets['DADOS_REPO']}/releases/tags/{DATA_RELEASE}"
    response = requests.get(url, headers=github_headers(), timeout=30)
    response.raise_for_status()
    assets = [a for a in response.json().get("assets", []) if a["name"].startswith("transacoes-")]
    if not assets:
        return None
    asset = max(assets, key=lambda a: a["name"])
    return {"name": asset["name"], "url": asset["url"], "updated_at": asset["updated_at"]}


@st.cache_resource
def data_lock():
    return threading.Lock()


def local_data_version():
    try:
        with open(VERSION_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def download_data(asset):
    gz_fd, gz_path = tempfile.mkstemp(suffix=".csv.gz", dir=".")
    csv_fd, csv_path = tempfile.mkstemp(suffix=".csv", dir=".")
    try:
        with os.fdopen(gz_fd, "wb") as destino:
            with requests.get(asset["url"], headers=github_headers("application/octet-stream"),
                              stream=True, timeout=120) as response:
                response.raise_for_status()
                for bloco in response.iter_content(chunk_size=1024 * 1024):
                    destino.write(bloco)
        with gzip.open(gz_path, "rb") as origem, os.fdopen(csv_fd, "wb") as destino:
            shutil.copyfileobj(origem, destino)
        os.replace(csv_path, CSV_PATH)
        with open(VERSION_PATH, "w", encoding="utf-8") as f:
            f.write(asset["name"])
    finally:
        for path in (gz_path, csv_path):
            if os.path.exists(path):
                os.remove(path)


def sync_local_data():
    """Atualiza o CSV local se houver versão nova. Em caso de falha, mantém o que já foi baixado."""
    asset = latest_data_asset()
    if asset is None:
        return None
    if local_data_version() != asset["name"] or not os.path.exists(CSV_PATH):
        with data_lock():
            if local_data_version() != asset["name"] or not os.path.exists(CSV_PATH):
                with st.spinner("Baixando os dados mais recentes..."):
                    download_data(asset)
    return asset


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

    /* O botão de reabrir o menu lateral fica dentro do header escondido acima */
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {{visibility: visible !important;}}
    [data-testid="stExpandSidebarButton"] *,
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="collapsedControl"] * {{color: {TEXT_MAIN} !important;}}
    
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

# csv_mtime entra na chave do cache: quando chega um CSV novo, os dados são relidos
@st.cache_data(max_entries=1)
def load_data(path, csv_mtime):
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
st.markdown(f"""
<p class="dash-title"><span>Nummy</span> · Dashboard de Churn</p>
<p class="dash-subtitle">Churn = estabelecimentos que transacionaram no P1 mas nao no P2 · Gateway: PAYTIME</p>
""", unsafe_allow_html=True)

data_asset = None
try:
    data_asset = sync_local_data()
except (requests.exceptions.RequestException, OSError, EOFError) as e:
    print(f"Falha ao buscar os dados: {type(e).__name__}", flush=True)
    if os.path.exists(CSV_PATH):
        st.warning("Não foi possível verificar se há dados novos. Mostrando a última versão baixada.")
    else:
        st.error("Não foi possível baixar os dados. Tente novamente em alguns minutos.")
        st.stop()

try:
    csv_mtime = os.path.getmtime(CSV_PATH)
    df_raw = load_data(CSV_PATH, csv_mtime)
except FileNotFoundError:
    st.info("Os dados ainda não foram publicados. A primeira sincronização pode levar algumas horas.")
    st.stop()

if data_asset is not None:
    atualizado_em = datetime.datetime.fromisoformat(data_asset["updated_at"].replace("Z", "+00:00"))
    if datetime.datetime.now(datetime.timezone.utc) - atualizado_em > STALE_AFTER:
        st.warning(
            f"Os dados não são atualizados desde {atualizado_em.astimezone(BRASILIA).strftime('%d/%m/%Y %H:%M')}. "
            "Verifique a sincronização no GitHub Actions."
        )
    with st.sidebar:
        st.caption(f"Dados atualizados em {atualizado_em.astimezone(BRASILIA).strftime('%d/%m/%Y %H:%M')}")

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
        max_value=1000,
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

    st.markdown('---')
    st.markdown("<p class='sidebar-title'>Exportar Dados</p>", unsafe_allow_html=True)

    # O "_" em _df evita que o Streamlit faça o hash do DataFrame; quem identifica a versão é o csv_mtime
    @st.cache_data(max_entries=1)
    def convert_to_xlsx(_df, csv_mtime):
        df_export = _df.copy()

        # 1. Garante o formato de data puro e remove o fuso horário (Timezone)
        if "created_at" in df_export.columns:
            df_export["created_at"] = pd.to_datetime(df_export["created_at"]).dt.tz_localize(None)
        if "date" in df_export.columns:
            df_export["date"] = pd.to_datetime(df_export["date"])

        output = io.BytesIO()

        # 2. Cria o arquivo usando openpyxl
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Transacoes')

            # 3. MÁGICA: Acessa a planilha gerada para forçar o estilo das células
            worksheet = writer.sheets['Transacoes']

            # Localiza qual é o número da coluna 'created_at' e 'date'
            idx_created = df_export.columns.get_loc("created_at") + 1 if "created_at" in df_export.columns else None
            idx_date = df_export.columns.get_loc("date") + 1 if "date" in df_export.columns else None

            # Aplica a máscara visual da linha 2 até a última (pulando o cabeçalho)
            for row in range(2, worksheet.max_row + 1):
                if idx_created:
                    # Formato completo com horas
                    worksheet.cell(row=row, column=idx_created).number_format = 'dd/mm/yyyy hh:mm:ss'
                if idx_date:
                    # Formato apenas dia, mês e ano
                    worksheet.cell(row=row, column=idx_date).number_format = 'dd/mm/yyyy'

        return output.getvalue()

    # Gerar o XLSX é a etapa mais lenta do app, então ele só é montado quando alguém pede
    if st.button('📄 Gerar planilha (.xlsx)', use_container_width=True):
        with st.spinner("Gerando planilha..."):
            convert_to_xlsx(df_raw, csv_mtime)
        st.session_state["xlsx_csv_mtime"] = csv_mtime

    if st.session_state.get("xlsx_csv_mtime") == csv_mtime:
        st.download_button(
            label='⬇ Baixar dados (.xlsx)',
            data=convert_to_xlsx(df_raw, csv_mtime),
            file_name=f"transacoes_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
        )
    st.markdown(
        f"<div style='font-size:0.7rem; color:#7A7A7A; margin-top:4px; text-align:center'>"
        f"{len(df_raw):,} transacoes · todos os status"
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

st.markdown(f"<p class='section-label'>Ranking — Top {top_n} Estabelecimentos (Churn & Retidos)</p>", unsafe_allow_html=True)

# --- NOVO: Botões para alternar a ordenação ---
ordem = st.radio(
    "Modo de Exibição da Tabela:",
    options=[
        "🔴 Foco em Churn (Maior perda de volume no P1)", 
        "🟢 Foco em Retidos (Maior queda de volume no período)"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

medal_map = {1:"medal-gold", 2:"medal-silver", 3:"medal-bronze"}
medal_lbl = {1:"1º", 2:"2º", 3:"3º"}

# --- Lógica de Ordenação Mista ---
if "Foco em Churn" in ordem:
    # 1º Mostra os Churns (ordenados do MAIOR volume perdido para o menor)
    # 2º Se sobrar espaço no Top N, mostra os Retidos
    all_ests_rank = sorted(
        list(churned) + list(retained), 
        key=lambda e: (0 if e in churned else 1, -vol_p1.get(e, 0))
    )[:top_n]
else:
    # 1º Mostra os Retidos (ordenados pela MAIOR QUEDA: P2 - P1 mais negativo vem primeiro)
    # 2º Se sobrar espaço no Top N, mostra os Churns no final
    all_ests_rank = sorted(
        list(churned) + list(retained), 
        key=lambda e: (0 if e in retained else 1, vol_p2.get(e, 0) - vol_p1.get(e, 0))
    )[:top_n]

rows_html = ""
for pos, est in enumerate(all_ests_rank, 1):
    # Lógica para a Tag Colorida
    if est in churned:
        tag = '<span class="tag-churn">CHURN</span>'
    else:
        tag = '<span class="tag-retain">RETIDO</span>'
        
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
    <span style='color:{RED}'>CHURN = Estava no P1, sumiu no P2</span>
    <span style='color:{GREEN}'>RETIDO = Ativo no P1 e P2 (Risco se o P2 for muito baixo)</span>
    <span style='color:{AMBER}'>TPV ZERO = Ativo, mas sem faturamento real no P2</span>
</div>""", unsafe_allow_html=True)