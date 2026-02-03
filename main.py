import streamlit as st
from geoloc import capturar_coordenadas
import numpy as np
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import io
import uuid
from fpdf import FPDF
import pytz
import time
import os
import math
from streamlit_cookies_manager import EncryptedCookieManager

from email.message import EmailMessage
import io
import pandas as pd

def enviar_excel_vendedor(
    server,
    email_origem,
    email_destino,
    nome_vendedor,
    df_excel
):
    # 🔹 Gera Excel em memória
    output = io.BytesIO()

    # ✅ Trabalha numa cópia pra não mexer no df original do app
    df_export = df_excel.copy()

    # ✅ AJUSTE SÓ PARA O EXCEL:
    # Essas duas colunas no app estão em 0–100 (ex: 21.86),
    # mas no Excel com formato % precisa estar 0–1 (ex: 0.2186)
    for col in ['% 2025)', '% 2026)']:
        if col in df_export.columns:
            df_export[col] = pd.to_numeric(df_export[col], errors='coerce').fillna(0) / 100

    # ✅ ORDEM FINAL + COLUNAS EM BRANCO (ESPAÇOS)
    # Obs: colunas "EM BRANCO" serão criadas só no Excel
    ordem_colunas = [
        "HIERARQUIA DE PRODUTOS",
        "META COBERTURA",
        "CLIENTES",
        "POSITIVAÇÃO",
        "PENDÊNCIA",
        "META 2025",
        "META 2026",
        "VOLUME",
        " ",  # espaço 1 (depois do VOLUME)
        "CRESC 2025",
        "% (VOL 2025)",
        "  ",  # espaço 2 (entre 2025 e 2026)
        "CRESC 2026",
        "% (VOL 2026)",
    ]

    # Garante que colunas em branco existam
    for col in [" ", "  "]:
        if col not in df_export.columns:
            df_export[col] = ""

    # Reordena mantendo só o que existir (sem quebrar o app)
    cols_existentes = [c for c in ordem_colunas if c in df_export.columns]
    df_export = df_export[cols_existentes].copy()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # ✅ Começa a escrever a tabela a partir da linha 2 (row=2)
        # porque vamos criar 2 linhas de cabeçalho (mescladas) acima
        df_export.to_excel(writer, index=False, sheet_name="Relatório", startrow=2)

        workbook  = writer.book
        worksheet = writer.sheets["Relatório"]

        # =========================
        # FORMATOS
        # =========================
        formato_pct = workbook.add_format({'num_format': '0.00%'})

        # Cabeçalhos
        fmt_header_grp = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F2F2F2', 'border': 1
        })
        fmt_header_col = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F7F7F7', 'border': 1
        })

        # Células padrão com borda (linhas “divididas”)
        fmt_cell = workbook.add_format({
            'border': 1, 'valign': 'vcenter'
        })

        # Células padrão com borda + porcentagem
        fmt_cell_pct = workbook.add_format({
            'border': 1, 'valign': 'vcenter', 'num_format': '0.00%'
        })

        # Coluna em branco (sem borda) – para “espaço”
        fmt_blank = workbook.add_format({})

        # =========================
        # MAPA DE ÍNDICES DAS COLUNAS NO EXCEL
        # =========================
        # Como usamos startrow=2, os dados começam na linha 3 (índice 2),
        # mas os índices de colunas são os do DataFrame exportado
        col_names = list(df_export.columns)
        col_idx = {name: i for i, name in enumerate(col_names)}

        # =========================
        # CABEÇALHOS MESCLADOS (LINHA 1)
        # =========================
        # Linha 0: grupos
        # Linha 1: nomes das colunas (já estão no Excel pelo to_excel, na linha startrow=2,
        # então vamos reescrever os headers manualmente na linha 1 e apagar os do pandas (linha 2))
        #
        # Estratégia:
        # - Mescla grupos na linha 0
        # - Escreve headers na linha 1
        # - Reescreve dados com formatos (bordas)
        # - Oculta/neutraliza a linha de header gerada pelo pandas (linha 2) escrevendo vazio

        # Define ranges dos grupos (se existirem)
        # Grupo 1: COBERTURA X POSITIVAÇÃO (4 colunas)
        grp1_cols = ["META COBERTURA", "CLIENTES", "POSITIVAÇÃO", "PENDÊNCIA"]
        if all(c in col_idx for c in grp1_cols):
            c0 = col_idx[grp1_cols[0]]
            c1 = col_idx[grp1_cols[-1]]
            worksheet.merge_range(0, c0, 0, c1, "COBERTURA X POSITIVAÇÃO", fmt_header_grp)

        # Grupo 2: META 2026 (2 colunas: META 2025 e META 2026)
        grp2_cols = ["META 2025", "META 2026"]
        if all(c in col_idx for c in grp2_cols):
            c0 = col_idx[grp2_cols[0]]
            c1 = col_idx[grp2_cols[-1]]
            worksheet.merge_range(0, c0, 0, c1, "META 2026", fmt_header_grp)

        # Para as demais colunas (inclui HIERARQUIA, VOLUME e as colunas pós-espaços),
        # apenas cria “blocos” individuais na linha 0 para manter padrão visual
        for name in col_names:
            # pula as colunas que já fazem parte dos grupos mesclados
            if name in grp1_cols or name in grp2_cols:
                continue
            # pula colunas em branco
            if name in [" ", "  "]:
                continue
            c = col_idx[name]
            worksheet.merge_range(0, c, 0, c, name, fmt_header_grp)

        # =========================
        # CABEÇALHO DAS COLUNAS (LINHA 1)
        # =========================
        for name in col_names:
            c = col_idx[name]
            if name in [" ", "  "]:
                worksheet.write(1, c, "", fmt_blank)
            else:
                worksheet.write(1, c, name, fmt_header_col)

        # =========================
        # “APAGA” A LINHA DE HEADER GERADA PELO PANDAS (LINHA 2)
        # =========================
        for name in col_names:
            c = col_idx[name]
            worksheet.write(2, c, "", fmt_blank)

        # =========================
        # FORMATAÇÃO DAS COLUNAS (%)
        # =========================
        colunas_pct = [
            "META COBERTURA",
            "% (VOL 2025)",
            "% (VOL 2026)",
        ]

        # Ajuste de larguras (leve)
        for name in col_names:
            c = col_idx[name]
            if name == "HIERARQUIA DE PRODUTOS":
                worksheet.set_column(c, c, 28)
            elif name in [" ", "  "]:
                worksheet.set_column(c, c, 3)   # “espaço”
            else:
                worksheet.set_column(c, c, 18)

        # =========================
        # APLICA BORDAS EM TODAS AS CÉLULAS (EXCETO COLUNAS EM BRANCO)
        # =========================
        start_data_row = 3  # dados começam na linha 3 (por causa da linha 0 e 1, e linha 2 “apagada”)
        n_rows = len(df_export)

        for r in range(n_rows):
            excel_r = start_data_row + r
            for name in col_names:
                c = col_idx[name]
                if name in [" ", "  "]:
                    worksheet.write(excel_r, c, "", fmt_blank)
                    continue

                val = df_export.iloc[r, c]

                # Se for coluna %: usa formato pct com borda
                if name in colunas_pct:
                    worksheet.write(excel_r, c, val, fmt_cell_pct)
                else:
                    worksheet.write(excel_r, c, val, fmt_cell)

        # =========================
        # CONGELAR PAINEL (2 LINHAS DE CABEÇALHO)
        # =========================
        worksheet.freeze_panes(2, 0)  # congela as duas linhas do topo (grupo + colunas)

        # ✅ (continua o resto da sua função exatamente como você já tem, envio de e-mail, etc.)
        # aqui você provavelmente monta o attachment e envia pelo server
        # (não mexi nisso porque você não colou essa parte)


    output.seek(0)

    # 🔹 Monta e-mail
    msg = EmailMessage()
    msg["From"] = email_origem
    msg["To"] = email_destino
    msg["Subject"] = f"Relatório de Vendas – {nome_vendedor}"
    msg.set_content(
        f"Olá,\n\nSegue em anexo o relatório de vendas do vendedor {nome_vendedor}.\n\nAtenciosamente."
    )

    msg.add_attachment(
        output.read(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"Relatorio_{nome_vendedor}.xlsx"
    )

    server.send_message(msg)



# --- COLE A FUNÇÃO AQUI (LINHA 16 APROX.) ---

MAPA_EMAIL_VENDEDORES = {
    "ALIF NUNES": ["alif.nunes@marata.com", "thais.oliveira@marata.com.br", "lycio.oliveira@marata.com.br","marciajanaina@marata.com.br"],
    "JOAO SILVA": ["joao.silva@marata.com"],
    "MARIA COSTA": ["maria.costa@marata.com"],

    # TESTE
    "TESTE": ["lycio.oliveira@marata.com.br"]
}


# --- MAPEAMENTO DE CONTATOS (Fácil de alterar) ---
MAPA_EMAILS = {
    "BARBARA": ["barbara.costa@marata.com.br", "kaio.gomes@marata.com.br","marciajanaina@marata.com.br"],
    "THAIS": ["thais.oliveira@marata.com.br","marciajanaina@marata.com.br"],
    "REGIANE": ["regiane.santana@marata.com.br","marciajanaina@marata.com.br"],
    "ALLANA": ["allana.menezes@marata.com.br", "danilo.matos@marata.com.br","marciajanaina@marata.com.br"],
    "ROBERIO": ["roberio@marata.com.br", "dione.lima@marata.com.br","marciajanaina@marata.com.br"]
}

# E-mails que sempre recebem
EMAILS_GESTAO = ["lycio.oliveira@marata.com.br"]

def enviar_resumo_rota(destinatarios_lista, vendedor, dados_resumo, nome_analista, taxa, hora, link):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    try:
        email_origem = st.secrets["email"]["sender_email"]
        senha_origem = st.secrets["email"]["sender_password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        
        msg = MIMEMultipart()
        msg['From'] = msg['From'] = f"MARATÁ-GVP <{email_origem}>"
        msg['To'] = destinatarios_lista 
        msg['Subject'] = f"✅ Rota Finalizada - {vendedor} ({datetime.now().strftime('%d/%m')})"

        saudacao = nome_analista.title() if nome_analista != "NÃO LOCALIZADO" else "Gestão Maratá"

        corpo = f"""
        Olá, {saudacao},
        
        O vendedor {vendedor} acaba de finalizar a rota do dia.
        
        📊 RESUMO DE PERFORMANCE:
        ------------------------------------------
        - Total de Clientes na Agenda: {dados_resumo['total']}
        - Visitas Realizadas: {dados_resumo['realizados']}
        - Visitas com Pedido: {dados_resumo['pedidos']}
        - Clientes Pendentes: {dados_resumo['pendentes']}
        - Taxa de Conversão: {taxa:.1f}% (Pedidos / Visitas)
        
        📍 DADOS DE FINALIZAÇÃO:
        ------------------------------------------
        - Hora do Envio: {hora}
        - Localização Final: {link}
        
        E-mail gerado automaticamente pelo Sistema Maratá GVP.
        """
        msg.attach(MIMEText(corpo, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_origem, senha_origem)
        server.sendmail(email_origem, destinatarios_lista.split(','), msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return False

# --- CONTINUAÇÃO DO SEU CÓDIGO (calcular_distancia, etc) ---



def calcular_distancia(lat1, lon1, lat2, lon2):
    # Raio da Terra em KM
    R = 6371.0
    
    dlat = np.radians(float(lat2) - float(lat1))
    dlon = np.radians(float(lon2) - float(lon1))
    
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(float(lat1))) * np.cos(np.radians(float(lat2))) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distancia = R * c * 1000 # Retorna em Metros
    return distancia

# --- CONFIGURAÇÃO DE COOKIES (Lembrar Login) ---
# O password abaixo é apenas para criptografia local do cookie
cookies = EncryptedCookieManager(password="marata_secret_key_2026")
if not cookies.ready():
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Maratá - GVP", page_icon="📅", layout="wide")
# --- CONFIGURAÇÃO DA PÁGINA ---

# --- ESTILIZAÇÃO DOS CARDS E PERFIL ---
st.markdown("""
    
    <style>
    [data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #d3d3d3;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    [data-testid="stMetric"] label, 
    [data-testid="stMetric"] div {
        color: black !important;
    }
    
    /* Estilização do Card de Usuário Logado */
    .user-card {
        background-color: #1e1e1e;
        padding: 12px 20px;
        border-radius: 12px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 3px 3px 10px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .user-card-text {
        color: white;
        font-weight: bold;
        font-size: 1.1em;
        letter-spacing: 0.5px;
    }
    .user-card-icon {
        font-size: 1.5em;
    }

/* ===============================
   SIDEBAR PREMIUM NAV (APP STYLE)
   =============================== */

section[data-testid="stSidebar"]{
  width: 320px !important;
  min-width: 320px !important;
  max-width: 320px !important;
  background: linear-gradient(180deg, #f6f7fb 0%, #f3f4f8 100%);
}

/* padding interno */
section[data-testid="stSidebar"] .stSidebarContent{
  padding: 18px 18px 12px 18px !important;
}

/* tira bolinha do radio (input) */
section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"]{
  display:none !important;
}

/* tira a bolinha visual do streamlit (o "controle") */
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child{
  display:none !important;
}

/* wrapper do grupo */
section[data-testid="stSidebar"] div[role="radiogroup"]{
  gap: 10px;
}

/* cada item vira "card-button" */
section[data-testid="stSidebar"] div[role="radiogroup"] > label{
  position: relative;
  display:flex;
  align-items:center;

  width: 100% !important;
  min-height: 58px;
  height: 58px;
  box-sizing: border-box;

  background: rgba(255,255,255,0.75);
  border: 1px solid rgba(17,17,17,0.08);
  border-radius: 16px;
  padding: 12px 14px;
  margin: 10px 0;

  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
  overflow:hidden;
}

/* bolha do ícone */
section[data-testid="stSidebar"] div[role="radiogroup"] > label p::first-letter{
  display:inline-block;
  width: 34px;
  height: 34px;
  line-height: 34px;
  text-align:center;
  border-radius: 12px;
  margin-right: 10px;
  background: rgba(255,75,75,0.12);
  box-shadow: inset 0 0 0 1px rgba(255,75,75,0.20);
}

/* texto padronizado */
section[data-testid="stSidebar"] div[role="radiogroup"] > label p{
  margin:0;
  font-size: 0.95rem;
  font-weight: 700;
  color:#1c1c1c;
  letter-spacing: .2px;

  line-height: 1.15;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* hover */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{
  transform: translateY(-1px);
  border-color: rgba(255,75,75,0.35);
  box-shadow: 0 10px 26px rgba(255,75,75,0.10);
}

/* =========================================================
   ✅ SELECIONADO (FUNCIONA DE VERDADE)
   Agora usando :has(input:checked)
   - mantém contorno do hover FIXO
   - cria "ponte/encaixe" com a tela (sem mudar cor)
   ========================================================= */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){
  background: linear-gradient(90deg, #0B5ED7 0%, #084298 100%);
  border-color: rgba(255,75,75,0.85);
  box-shadow: 0 16px 34px rgba(255,75,75,0.22);

  /* contorno do hover fixo (mesma cor do hover) */
  outline: 2px solid rgba(255,75,75,0.35);
  outline-offset: 0px;

  /* deixa “encaixar” no lado direito */
  border-top-right-radius: 0px;
  border-bottom-right-radius: 0px;
  overflow: visible;
}

/* ✅ ponte para a tela (mesma cor/alpha do hover) */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked)::after{
  content: "";
  position: absolute;
  top: -1px;
  bottom: -1px;
  right: -18px;                 /* “entra” na área da tela */
  width: 18px;                  /* largura da ponte */
  background: rgba(255,75,75,0.12);
  border-top-right-radius: 16px;
  border-bottom-right-radius: 16px;

  /* mesma ideia do hover */
  box-shadow: 0 10px 26px rgba(255,75,75,0.10);
  pointer-events: none;
}

/* texto branco no ativo */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p{
  color: #ffffff !important;
}

/* bolha do ícone no ativo vira branca */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p::first-letter{
  background: rgba(255,255,255,0.18);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
}

/* barra lateral do ativo */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked)::before{
  content:"";
  position:absolute;
  left: 10px;
  top: 10px;
  bottom: 10px;
  width: 6px;
  border-radius: 10px;
  background: rgba(255,255,255,0.85);
}

/* some label do widget */
section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"]{
  display:none;
}



    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO E CONFIGURAÇÕES ---
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = "https://docs.google.com/spreadsheets/d/1pgral1qpyEsn3MnOFtkuxGzBPQ3R7SHYQSs0NHtag3I/edit"
fuso_br = pytz.timezone('America/Sao_Paulo')

# Administrador e Analista Especial
NOME_ADMIN = "LYCIO"
LISTA_ANALISTA = ["BARBARA","THAIS","ROBERIO","CAROL","REGIANE","ALLANA"]
NOME_DIRETORIA = "ALDO"

# --- FUNÇÕES DE EXPORTAÇÃO ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

def gerar_pdf(df, tipo_relatorio="GERAL"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    df_pdf = df.copy()
    if tipo_relatorio == "AGENDA" and "REGISTRO" in df_pdf.columns:
        try:
            df_pdf['REGISTRO_DT'] = pd.to_datetime(df_pdf['REGISTRO'], dayfirst=True)
            df_pdf = df_pdf.sort_values(by='REGISTRO_DT', ascending=False).drop(columns=['REGISTRO_DT'])
        except:
            df_pdf = df_pdf.sort_values(by='REGISTRO', ascending=False)
    
    pdf.set_font("Arial", 'B', 12)
    data_geracao = datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 8, f"Relatorio Marata - Gerado em {data_geracao}", ln=True, align='C')
    pdf.ln(3)
    
    cols = df_pdf.columns.tolist()
    largura_total = 275
    
    qtd_cols = len(cols)
    if qtd_cols > 8:
        tamanho_fonte_cabecalho = 5
        tamanho_fonte_dados = 4
        limite_texto = 25
    elif qtd_cols > 6:
        tamanho_fonte_cabecalho = 6
        tamanho_fonte_dados = 5
        limite_texto = 30
    else:
        tamanho_fonte_cabecalho = 8
        tamanho_fonte_dados = 7
        limite_texto = 40

    largura_cliente = 60  
    largura_supervisor = 30
    largura_agendado = 30
    largura_data = 18
    largura_justificativa = 50
    largura_registro = 25 
    largura_cidade = 40   
    
    especiais = []
    col_map = {str(c).upper(): c for c in cols}
    
    if "CLIENTE" in col_map: especiais.append("CLIENTE")
    if "SUPERVISOR" in col_map: especiais.append("SUPERVISOR")
    if "AGENDADO POR" in col_map: especiais.append("AGENDADO POR")
    if "DATA" in col_map: especiais.append("DATA")
    if "JUSTIFICATIVA" in col_map: especiais.append("JUSTIFICATIVA")
    if "REGISTRO" in col_map: especiais.append("REGISTRO")
    if "CIDADE" in col_map: especiais.append("CIDADE")
    
    ocupado = 0
    if "CLIENTE" in especiais: ocupado += largura_cliente
    if "SUPERVISOR" in especiais: ocupado += largura_supervisor
    if "AGENDADO POR" in especiais: ocupado += largura_agendado
    if "DATA" in especiais: ocupado += largura_data
    if "JUSTIFICATIVA" in especiais: ocupado += largura_justificativa
    if "REGISTRO" in especiais: ocupado += largura_registro
    if "CIDADE" in especiais: ocupado += largura_cidade
    
    outras_cols_count = len(cols) - len(especiais)
    largura_padrao = (largura_total - ocupado) / outras_cols_count if outras_cols_count > 0 else 0
    
    pdf.set_font("Arial", 'B', tamanho_fonte_cabecalho)
    for col in cols:
        c_up = str(col).upper()
        if c_up == "CLIENTE": w = largura_cliente
        elif c_up == "SUPERVISOR": w = largura_supervisor
        elif c_up == "AGENDADO POR": w = largura_agendado
        elif c_up == "DATA": w = largura_data
        elif c_up == "JUSTIFICATIVA": w = largura_justificativa
        elif c_up == "REGISTRO": w = largura_registro
        elif c_up == "CIDADE": w = largura_cidade
        else: w = largura_padrao
        pdf.cell(w, 6, str(col), border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", '', tamanho_fonte_dados) 
    for index, row in df_pdf.iterrows():
        for i, item in enumerate(row):
            col_name = str(cols[i]).upper()
            if col_name == "CLIENTE": w, limit = largura_cliente, 50
            elif col_name == "SUPERVISOR": w, limit = largura_supervisor, 30
            elif col_name == "AGENDADO POR": w, limit = largura_agendado, 30
            elif col_name == "DATA": w, limit = largura_data, 12
            elif col_name == "JUSTIFICATIVA": w, limit = largura_justificativa, 60
            elif col_name == "REGISTRO": w, limit = largura_registro, 20
            elif col_name == "CIDADE": w, limit = largura_cidade, 35
            else: w, limit = largura_padrao, limite_texto
            
            texto = str(item)[:limit].encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(w, 5, texto, border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_b = conn.read(spreadsheet=url_planilha, worksheet="BASE")
        df_j = conn.read(spreadsheet=url_planilha, worksheet="JUSTIFICATIVA DE ATENDIMENTOS")
        df_a = conn.read(spreadsheet=url_planilha, worksheet="AGENDA")
        df_u = conn.read(spreadsheet=url_planilha, worksheet="USUARIOS")
        
        df_u.columns = [str(c).strip().upper() for c in df_u.columns]
        df_b.columns = [str(c).strip() for c in df_b.columns]
        if 'COORDENADAS' not in df_b.columns:
            df_b['COORDENADAS'] = "0, 0"
        df_j.columns = [str(c).strip() for c in df_j.columns]
        df_a.columns = [str(c).strip() for c in df_a.columns]
            
        if 'REGISTRO' not in df_a.columns: df_a['REGISTRO'] = "-"
        if 'AGENDADO POR' not in df_a.columns: df_a['AGENDADO POR'] = "-"
        df_a['LINHA'] = df_a.index + 2
        
        for df in [df_b, df_a]:
            cols_cod = [c for c in df.columns if 'Cliente' in c or 'CÓDIGO' in c]
            for col in cols_cod:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
                df[col] = df[col].replace('0', '')
        
        if 'ID' in df_a.columns: df_a['ID'] = df_a['ID'].astype(str)
        return df_b, df_j, df_a, df_u
    except Exception: 
        return None, None, None, pd.DataFrame(columns=["USUARIO", "SENHA"])

df_base, df_just, df_agenda, df_usuarios = carregar_dados()

# --- CONFIGURAÇÃO DE ACESSOS (EDITE AQUI) ---
NOME_ADMIN = "lycio"         # Você (Admin)
NOME_DIRETORIA = "aldo"         # Aldo
LISTA_ANALISTA = ["Barbara", "Thais","Allana","Roberio","Regiane","Carol"] 
LISTA_SUPERVISORES = ["Francisco", "Teste"] 
LISTA_VENDEDORES = ["Carlos Antonio", "Rita", "Saraiva","Jose Carlos"]     

# --- SISTEMA DE ACESSO ---
if "logado" not in st.session_state:
    if "user_marata" in cookies:
        st.session_state.logado = True
        st.session_state.usuario = cookies["user_marata"]
    else:
        st.session_state.logado = False
        st.session_state.usuario = ""

if not st.session_state.logado:

    import os

    logo_path = None
    for p in ["pngmarata.png", "pngmarata.jpg", "pngmarata.jpeg", "pngmarata", "assets/pngmarata.png"]:
        if os.path.exists(p):
            logo_path = p
            break

    # ✅ CSS SAFE (não quebra mobile) + ✅ FIX do "olhinho" + ✅ remove a “barra branca” + ✅ título realmente centralizado
    st.markdown("""
    <style>
      /* Remove “barra branca” do topo (Header do Streamlit) */
      header[data-testid="stHeader"]{
        background: transparent !important;
      }
      div[data-testid="stDecoration"]{
        display:none !important;
      }

      /* Fundo suave */
      div[data-testid="stAppViewContainer"]{
        background: radial-gradient(circle at 20% 20%, #f7f9ff 0%, #f3f4f8 45%, #f6f7fb 100%);
      }

      /* Ajuste de padding do conteúdo */
      .block-container{
        padding-top: 18px !important;
      }

      /* Centraliza e limita largura */
      .login-wrap{
        max-width: 860px;
        margin: 0 auto;
      }

      /* Título */
      .login-h1{
        font-size: 42px;
        font-weight: 900;
        letter-spacing: .5px;
        color: #000C75;
        margin: 0;
        text-align: center;
      }

      .login-sub{
        text-align:center;
        color: rgba(17,17,17,.65);
        font-size: 14px;
        margin: 6px 0 16px 0;
      }

      /* Card */
      .login-card{
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(17,17,17,0.08);
        border-radius: 18px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 18px 42px rgba(0,0,0,0.07);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
      }

      /* Inputs */
      div[data-testid="stTextInput"] input{
        border-radius: 12px !important;
        padding: 12px 12px !important;
        border: 1px solid rgba(17,17,17,0.10) !important;
      }
      div[data-testid="stTextInput"] input:focus{
        border: 1px solid rgba(0,12,117,0.45) !important;
        box-shadow: 0 0 0 4px rgba(0,12,117,0.10) !important;
      }

      /* ✅ OLHINHO DA SENHA: pequeno e CENTRALIZADO no círculo */
      div[data-testid="stTextInput"] button{
        width: 38px !important;
        min-width: 38px !important;
        height: 38px !important;
        padding: 0 !important;
        border-radius: 999px !important;
        box-shadow: none !important;
        border: 1px solid rgba(17,17,17,0.08) !important;
        background: rgba(255,255,255,0.65) !important;

        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
      }

      /* Centraliza o ícone (SVG) dentro do botão */
      div[data-testid="stTextInput"] button svg{
        display: block !important;
        margin: 0 !important;
      }

      /* ✅ BOTÃO DO FORM (submit) */
      div[data-testid="stFormSubmitButton"] button{
        width: 100% !important;
        border-radius: 14px !important;
        padding: 12px 14px !important;
        font-weight: 900 !important;
        border: 1px solid rgba(17,17,17,0.08) !important;
        box-shadow: 0 10px 28px rgba(0,0,0,0.08) !important;
        background: rgba(255,255,255,0.70) !important;
      }

      /* Alerts arredondados */
      div[data-testid="stAlert"]{
        border-radius: 14px !important;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)

    # ✅ Header (logo | título central | espaço) => título fica REALMENTE centralizado na página
    col_logo, col_mid, col_spacer = st.columns([0.12, 0.76, 0.12], vertical_alignment="center")

    with col_logo:
        if logo_path:
            st.image(logo_path, width=60)
        else:
            st.write("")

    with col_mid:
        st.markdown("<h1 class='login-h1'>GESTÃO DE VISITAS PDV</h1>", unsafe_allow_html=True)
        st.markdown("<div class='login-sub'>Acesse com seu usuário e senha para continuar</div>", unsafe_allow_html=True)

    with col_spacer:
        st.write("")

    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    tab_login, tab_cadastro = st.tabs(["Login", "Novo Cadastro"])

    with tab_login:
        with st.form("login_form"):
            u_login = st.text_input("Usuário:").strip().upper()
            p_login = st.text_input("Senha:", type="password")
            lembrar = st.checkbox("Manter conectado")

            if st.form_submit_button("Entrar"):
                if "USUARIO" in df_usuarios.columns and "SENHA" in df_usuarios.columns:
                    valid = df_usuarios[
                        (df_usuarios["USUARIO"].str.upper() == u_login)
                        & (df_usuarios["SENHA"].astype(str) == p_login)
                    ]
                    if not valid.empty:
                        st.session_state.logado = True
                        st.session_state.usuario = u_login

                        if lembrar:
                            cookies["user_marata"] = u_login
                            cookies.save()

                        st.rerun()
                    else:
                        st.error("Usuário ou Senha incorretos.")
                else:
                    st.error("Colunas 'USUARIO' ou 'SENHA' não encontradas na aba USUARIOS.")

    with tab_cadastro:
        with st.form("cad_form"):
            st.write("Crie sua conta")
            u_cad = st.text_input("Nome de Usuário:").strip().upper()
            p_cad = st.text_input("Defina uma Senha:", type="password")
            p_cad_conf = st.text_input("Repita a Senha:", type="password")

            if st.form_submit_button("Finalizar Cadastro"):
                if u_cad and p_cad and p_cad_conf:
                    if p_cad != p_cad_conf:
                        st.error("As senhas não coincidem.")
                    else:
                        existente = False
                        if "USUARIO" in df_usuarios.columns:
                            existente = u_cad in df_usuarios["USUARIO"].str.upper().values

                        if not existente:
                            novo_user = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                            df_final_u = pd.concat([df_usuarios, novo_user], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_final_u)
                            st.cache_data.clear()
                            st.success("Cadastro realizado!")
                        else:
                            st.error("Este usuário já está cadastrado.")
                else:
                    st.warning("Preencha todos os campos.")

    st.markdown("</div></div>", unsafe_allow_html=True)  # fecha login-card e login-wrap
    st.stop()






# --- DEFINIÇÃO DE PERFIS E HIERARQUIA ---
# --- DEFINIÇÃO DE PERFIS E HIERARQUIA ---
user_atual = st.session_state.usuario.strip().upper()

is_admin = (user_atual == NOME_ADMIN.upper())
is_diretoria = (user_atual == NOME_DIRETORIA.upper())

# ✅ padroniza BASE para reconhecer usuário
df_base_perm = df_base.copy()
for c in ["VENDEDOR","SUPERVISOR","ANALISTA","EscrV","Estado"]:
    if c in df_base_perm.columns:
        df_base_perm[c] = df_base_perm[c].astype(str).str.strip().str.upper()

# ✅ analista: pela sua lista (mantém)
is_analista = (user_atual in [n.upper() for n in LISTA_ANALISTA])

# ✅ supervisor e vendedor: pela BASE (isso elimina o bug)
is_supervisor = ("SUPERVISOR" in df_base_perm.columns) and (user_atual in df_base_perm["SUPERVISOR"].dropna().unique())
is_vendedor   = ("VENDEDOR"   in df_base_perm.columns) and (user_atual in df_base_perm["VENDEDOR"].dropna().unique())

# ✅ gestão = admin/diretoria/analista (você já usa isso)
eh_gestao = is_admin or is_analista or is_diretoria

# ✅ fallback seguro:
# se não for gestão e também não achou na base como supervisor, assume vendedor (NUNCA "livre")
if (not eh_gestao) and (not is_supervisor) and (not is_vendedor):
    is_vendedor = True


# --- VALIDAÇÃO DE GPS ---
if "lat" not in st.session_state:
    with st.container():
        lat, lon = capturar_coordenadas()
        if lat and lon:
            st.session_state.lat = lat
            st.session_state.lon = lon
            st.success(f"📍 GPS Ativo")
            time.sleep(1)
            st.rerun()
        else:
            if eh_gestao:
                st.session_state.lat = 0.0
                st.session_state.lon = 0.0
                st.info("ℹ️ Perfil Gestão: GPS ignorado.")
                st.rerun()
            else:
                st.warning("⚠️ **Acesso Negado.** Geolocalização obrigatória.")
                if st.button("🔄 Tentar novamente", key="retry_gps"):
                    st.rerun()
                st.stop()

# --- CONFIGURAÇÃO VISUAL DO PERFIL ---
if is_admin:
    label_display = "ADMINISTRADOR"; user_icon = "👑"; border_color = "#FFD700"
elif is_diretoria:
    label_display = f"{user_atual} | DIRETORIA"; user_icon = "📈"; border_color = "#1E90FF"
elif is_analista:
    label_display = f"{user_atual} | ANALISTA"; user_icon = "🔬"; border_color = "#9370DB"
elif is_supervisor:
    label_display = f"{user_atual} | SUPERVISOR"; user_icon = "👔"; border_color = "#2ECC71"
else:
    label_display = f"{user_atual} | VENDEDOR"; user_icon = "👤"; border_color = "#ff4b4b"

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown(f"""
        <div class="user-card" style="border-left: 5px solid {border_color};">
            <div class="user-card-icon">{user_icon}</div>
            <div class="user-card-text">{label_display}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- AJUSTE: SINO DE NOTIFICAÇÃO FILTRADO ---
    # Só mostra se for Gestão (Adm/Analista). Supervisor e Vendedor não entram aqui.
    if eh_gestao:
        if df_agenda is not None:
            # Se for Admin, vê tudo. Se for Analista, vê apenas o que é dele.
            if is_admin:
                df_filtrado_sino = df_agenda[df_agenda['STATUS'] == "Pendente"]
            else:
                df_filtrado_sino = df_agenda[
                    (df_agenda['STATUS'] == "Pendente") &
                    (df_agenda['ANALISTA'] == user_atual)
                ]
            qtd_p = len(df_filtrado_sino)
        else:
            qtd_p = 0

        if qtd_p > 0:
            if st.button(f"🔔 {qtd_p} Pendências de Aprovação", use_container_width=True, type="primary"):
                st.session_state.pagina_direta = "🔔 Aprovações"
                st.rerun()
        else:
            st.caption("✅ Nenhuma aprovação pendente")

    # Texto dinâmico do menu
    if eh_gestao:
        texto_ver_agenda = "🔍 Agenda Geral"
    elif is_supervisor:
        texto_ver_agenda = "🔍 Agenda da Minha Equipe"
    else:
        texto_ver_agenda = "🔍 Minha Agenda de Visitas"

    opcoes_menu = [
        "📅 Agendamentos do Dia",
        "📋 Novo Agendamento",
        texto_ver_agenda
    ]
    
    opcoes_menu.append("📊 ACOMP. DIÁRIO")
    opcoes_menu.append("📚 Perfil do Cliente")
    opcoes_menu.append("🧪 TESTES")

    
    if eh_gestao:
        opcoes_menu.append("📊 Dashboard de Controle")
        opcoes_menu.append("📊 KPI Aprovação Analistas")  # ✅ NOVA OPÇÃO
    
    # ✅ ALTERAÇÃO AQUI: selectbox -> radio (menu moderno)
    menu = st.radio(
        "Menu Principal",
        opcoes_menu,
        label_visibility="collapsed",
        key="menu_principal_radio"
    )
    
    if "pagina_direta" not in st.session_state:
        st.session_state.pagina_direta = None

    if menu:
        if st.session_state.pagina_direta and menu != "📅 Agendamentos do Dia":
            st.session_state.pagina_direta = None

    if st.session_state.pagina_direta:
        menu_interna = st.session_state.pagina_direta
    elif menu == texto_ver_agenda:
        menu_interna = "🔍 Ver/Editar Minha Agenda"
    else:
        menu_interna = menu

    # Botão Sair
    if st.button("Sair", key="btn_logout_sidebar"):
        if "user_marata" in cookies:
            del cookies["user_marata"]
            cookies.save()
        st.session_state.logado = False
        st.session_state.usuario = ""
        st.session_state.pagina_direta = None
        st.cache_data.clear()
        st.rerun()
        
    for _ in range(5):
        st.sidebar.write("")

    if is_admin:
        st.markdown("---")
        st.subheader("🗑️ Limpeza em Massa")
        if df_agenda is not None and not df_agenda.empty:
            df_limpeza = df_agenda.drop_duplicates(
                subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS']
            )
            lista_sups_limpar = sorted(
                [str(x) for x in df_limpeza['SUPERVISOR'].unique() if x]
            )
            sup_limpar = st.selectbox(
                "Limpar agenda de:",
                ["Selecione..."] + lista_sups_limpar,
                key="sel_limpeza_admin"
            )

            if sup_limpar != "Selecione...":
                confirma = st.popover(f"⚠️ APAGAR: {sup_limpar}")
                if confirma.button(
                    f"Confirmar Exclusão de {sup_limpar}",
                    key="btn_conf_limpeza"
                ):
                    df_rest = df_agenda[
                        df_agenda['SUPERVISOR'] != sup_limpar
                    ].copy()
                    conn.update(
                        spreadsheet=url_planilha, 
                        worksheet="AGENDA", 
                        data=df_rest.drop(
                            columns=['LINHA', 'DT_COMPLETA', 'DIA_SEMANA', 'dist_val_calc'],
                            errors='ignore'
                        )
                    )
                    st.cache_data.clear()
                    st.success("Agenda limpa!")
                    time.sleep(1)
                    st.rerun()

# --- TÍTULO CENTRAL NO TOPO ---
st.markdown(
    "<h4 style='text-align: center; color: black; margin-top: -110px;'>"
    "GESTÃO DE VISITAS PDV (GVP) - MARATÁ</h4>",
    unsafe_allow_html=True
)
st.markdown("---")

# Mapeia menu_interna de volta para menu para o restante do código
menu = menu_interna


# --- PÁGINA: AGENDAMENTOS DO DIA ---
# --- PÁGINA: AGENDAMENTOS DO DIA ---
if menu == "📅 Agendamentos do Dia":
    col_titulo, col_btn = st.columns([0.8, 0.2])

    with col_titulo:
        st.header("📅 Agendamentos do Dia")

    with col_btn:
        if st.button("🔄 Atualizar Agenda", key="btn_refresh_dia"):
            st.cache_data.clear()
            st.rerun()

    hoje_str = datetime.now(fuso_br).strftime("%d/%m/%Y")

    if df_agenda is not None and not df_agenda.empty:

        # ✅ Permissão de validação: Gestão + Analista
        pode_validar = (is_admin or is_diretoria or is_analista)

        # --- LIMPEZA ---
        df_agenda = (
            df_agenda.drop_duplicates(
                subset=["DATA", "VENDEDOR", "CÓDIGO CLIENTE", "STATUS"],
                keep="first",
            )
            .reset_index(drop=True)
        )

        # --- COLUNAS PADRÃO ---
        col_aprov_plan = next(
            (
                c
                for c in df_agenda.columns
                if (("APROVA" in c.upper() and "PLAN" in c.upper()) or c.upper() == "APROVACAO")
            ),
            "APROVACAO",
        )
        col_aprov_exec = "VALIDACAO_GESTAO"
        col_just = "JUSTIFICATIVA"

        if col_aprov_exec not in df_agenda.columns:
            df_agenda[col_aprov_exec] = "PENDENTE"
        if col_just not in df_agenda.columns:
            df_agenda[col_just] = ""

        # ✅ NOVO: coluna para observação da gestão na validação diária (sem mexer no botão do vendedor)
        col_obs_rotina = "OBS_VALIDACAO_GESTAO"
        if col_obs_rotina not in df_agenda.columns:
            df_agenda[col_obs_rotina] = ""

        if "DISTANCIA_LOG" not in df_agenda.columns:
            df_agenda["DISTANCIA_LOG"] = 0.0
        if "COORDENADAS" not in df_agenda.columns:
            df_agenda["COORDENADAS"] = ""

        # --- FILTRO DO DIA ---
        df_dia = df_agenda[df_agenda["DATA"] == hoje_str].copy()
        df_dia = df_dia[df_dia[col_aprov_plan].astype(str).str.upper() == "APROVADO"]

        # --- CONTROLE DE ACESSO ---
        if not (is_admin or is_diretoria):
            if is_analista:
                df_dia = df_dia[df_dia["ANALISTA"].astype(str).str.upper() == user_atual.upper()]
            elif is_supervisor:
                df_dia = df_dia[df_dia["SUPERVISOR"].astype(str).str.upper() == user_atual.upper()]
            else:
                df_dia = df_dia[df_dia["VENDEDOR"].astype(str).str.upper() == user_atual.upper()]

        df_dia = df_dia.reset_index(drop=True)

        # --- SLICERS (GESTÃO / ANALISTA) ---
        if pode_validar and not df_dia.empty:
            st.markdown("### 🔍 Filtros")
            f1, f2 = st.columns(2)

            with f1:
                sup_sel = st.multiselect("Supervisor", sorted(df_dia["SUPERVISOR"].dropna().unique()))
            if sup_sel:
                df_dia = df_dia[df_dia["SUPERVISOR"].isin(sup_sel)]

            with f2:
                vend_sel = st.multiselect("Vendedor", sorted(df_dia["VENDEDOR"].dropna().unique()))
            if vend_sel:
                df_dia = df_dia[df_dia["VENDEDOR"].isin(vend_sel)]

        # --- MÉTRICAS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Aprovados p/ Hoje", len(df_dia))
        m2.metric("Realizados", len(df_dia[df_dia["STATUS"] == "Realizado"]))
        m3.metric("Validados", len(df_dia[df_dia[col_aprov_exec] == "OK"]))
        m4.metric("Reprovados", len(df_dia[df_dia[col_aprov_exec] == "REPROVADO"]), delta_color="inverse")

        # --- BOTÃO APROVAR EM MASSA (GESTÃO + ANALISTA) ---
        if pode_validar and not df_dia.empty:
            if st.button("✅ APROVAR TODAS AS VISITAS REALIZADAS", use_container_width=True):
                ids = df_dia[df_dia["STATUS"] == "Realizado"]["ID"].astype(str).tolist()
                if ids:
                    df_agenda.loc[df_agenda["ID"].astype(str).isin(ids), col_aprov_exec] = "OK"
                    conn.update(
                        spreadsheet=url_planilha,
                        worksheet="AGENDA",
                        data=df_agenda.drop(columns=["LINHA", "DT_COMPLETA"], errors="ignore"),
                    )
                    st.success("Todas as visitas realizadas foram aprovadas!")
                    time.sleep(1)
                    st.rerun()

        # --- TABELA ---
        if not df_dia.empty:

            # ✅ Cidade
            if df_base is not None and not df_base.empty and ("Cliente" in df_base.columns) and ("Local" in df_base.columns):
                df_cidades = df_base[["Cliente", "Local"]].drop_duplicates("Cliente").copy()
                df_cidades["Cliente"] = df_cidades["Cliente"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

                df_dia["CÓDIGO CLIENTE"] = df_dia["CÓDIGO CLIENTE"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
                df_dia = (
                    df_dia.merge(
                        df_cidades,
                        left_on="CÓDIGO CLIENTE",
                        right_on="Cliente",
                        how="left",
                    )
                    .rename(columns={"Local": "CIDADE"})
                )

            cols_v = ["EDITAR", "VENDEDOR", "CLIENTE", "CIDADE", "STATUS", col_just]

            # ✅ Auditoria só aparece para quem pode validar
            if pode_validar:
                cols_v.append(col_aprov_exec)
                cols_v.append("DISTANCIA_LOG")

            df_dia["EDITAR"] = False
            df_display = df_dia[[c for c in cols_v if c in df_dia.columns or c == "EDITAR"]].copy()

            edicao_dia = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "EDITAR": st.column_config.CheckboxColumn("📝"),
                    col_aprov_exec: st.column_config.SelectboxColumn("AUDITORIA", options=["PENDENTE", "OK", "REPROVADO"]),
                },
                disabled=[
                    c
                    for c in df_display.columns
                    if c not in (["EDITAR", col_aprov_exec] if pode_validar else ["EDITAR"])
                ],
            )

            # --- EDIÇÃO INDIVIDUAL ---
            marcados = edicao_dia[edicao_dia["EDITAR"] == True]
            if not marcados.empty:
                idx = marcados.index[0]
                sel_row = df_dia.iloc[idx]

                st.markdown("---")
                st.subheader(f"⚙️ Detalhes: {sel_row.get('CLIENTE','')}")

                # ✅ Status
                status_list = ["Agendado", "Realizado", "Reagendado"]
                status_atual = sel_row["STATUS"] if sel_row.get("STATUS") in status_list else "Agendado"
                novo_status = st.selectbox("Status:", status_list, index=status_list.index(status_atual))

                # ✅ Auditoria
                val_list = ["PENDENTE", "OK", "REPROVADO"]
                valor_atual = str(sel_row.get(col_aprov_exec, "PENDENTE")).strip().upper()
                if valor_atual not in val_list:
                    valor_atual = "PENDENTE"

                if pode_validar:
                    nova_val = st.selectbox("Validar:", val_list, index=val_list.index(valor_atual))
                else:
                    nova_val = valor_atual

                # ✅ Observações (pré-selecionadas)
                opcoes_obs = [
                    "Selecione...",
                    "Pedido enviado",
                    "Cliente Inadimplente",
                    "Cliente fechado",
                    "Cliente inativo",
                    "Cliente sem limite de crédito",
                    "Outro (digitar)",
                ]

                just_atual = str(sel_row.get(col_just, "") or "").strip()

                idx_padrao = 0
                for i, opt in enumerate(opcoes_obs):
                    if just_atual.upper() == opt.upper():
                        idx_padrao = i
                        break

                obs_sel = st.selectbox("Observações:", opcoes_obs, index=idx_padrao, key="obs_pre_def")

                if obs_sel == "Outro (digitar)":
                    nova_just = st.text_input("Justificativa:", value=just_atual, key="just_txt")
                elif obs_sel != "Selecione...":
                    nova_just = st.text_input("Justificativa:", value=obs_sel, key="just_txt")
                else:
                    nova_just = st.text_input("Justificativa:", value=just_atual, key="just_txt")

                # ✅ NOVO: BLOCO SEPARADO DA GESTÃO PARA VALIDAR A ROTINA + OBSERVAÇÃO (SEM MEXER NO BOTÃO DO VENDEDOR)
                if pode_validar:
                    st.markdown("#### ✅ Validação da Rotina (Gestão)")
                    obs_gestao_rotina = st.text_input(
                        "Observação da gestão (opcional):",
                        value=str(sel_row.get(col_obs_rotina, "") or ""),
                        key="obs_validacao_gestao_rotina",
                    )

                    c_val1, c_val2 = st.columns(2)
                    with c_val1:
                        if st.button("✅ APROVAR ROTINA (Gestão)", key="btn_aprovar_rotina_gestao"):
                            df_agenda.loc[
                                df_agenda["ID"].astype(str) == str(sel_row["ID"]),
                                [col_aprov_exec, col_obs_rotina],
                            ] = [
                                "OK",
                                obs_gestao_rotina,
                            ]

                            conn.update(
                                spreadsheet=url_planilha,
                                worksheet="AGENDA",
                                data=df_agenda.drop(columns=["LINHA", "DT_COMPLETA"], errors="ignore"),
                            )

                            st.success("Rotina aprovada pela gestão!")
                            time.sleep(1)
                            st.rerun()

                    with c_val2:
                        if st.button("❌ REPROVAR ROTINA (Gestão)", key="btn_reprovar_rotina_gestao"):
                            df_agenda.loc[
                                df_agenda["ID"].astype(str) == str(sel_row["ID"]),
                                [col_aprov_exec, col_obs_rotina],
                            ] = [
                                "REPROVADO",
                                obs_gestao_rotina,
                            ]

                            conn.update(
                                spreadsheet=url_planilha,
                                worksheet="AGENDA",
                                data=df_agenda.drop(columns=["LINHA", "DT_COMPLETA"], errors="ignore"),
                            )

                            st.error("Rotina reprovada pela gestão!")
                            time.sleep(1)
                            st.rerun()

                # ✅ BOTÃO DO VENDEDOR (FICA QUIETO / INTACTO — NÃO ALTERADO)
                if st.button("💾 SALVAR ATUALIZAÇÃO"):

                    # ✅ se for gestão (admin/diretoria/analista), NÃO atualiza GPS nem distância
                    if pode_validar:
                        # mantém coordenadas e distância já existentes no registro
                        coord_atual = str(sel_row.get("COORDENADAS", "") or "")
                        dist_atual = sel_row.get("DISTANCIA_LOG", 0.0)

                        try:
                            dist_atual = float(str(dist_atual).replace(",", ".").strip())
                        except:
                            dist_atual = 0.0

                        df_agenda.loc[
                            df_agenda["ID"].astype(str) == str(sel_row["ID"]),
                            ["STATUS", col_aprov_exec, col_just, "COORDENADAS", "DISTANCIA_LOG"],
                        ] = [
                            novo_status,
                            nova_val,
                            nova_just,
                            coord_atual,
                            dist_atual,
                        ]

                        conn.update(
                            spreadsheet=url_planilha,
                            worksheet="AGENDA",
                            data=df_agenda.drop(columns=["LINHA", "DT_COMPLETA"], errors="ignore"),
                        )
                        st.cache_data.clear()


                        st.success("Dados atualizados! (GPS do vendedor preservado)")
                        time.sleep(1)
                        st.rerun()

                    # ✅ caso contrário (vendedor/supervisor), aí sim captura coordenadas e recalcula distância
                    else:
                        lat_tmp, lon_tmp = capturar_coordenadas()

                        if lat_tmp and lon_tmp:
                            lat_v = lat_tmp
                            lon_v = lon_tmp
                            # ✅ só salva session_state para quem está na rua (não gestão)
                            st.session_state.lat = lat_v
                            st.session_state.lon = lon_v
                        else:
                            lat_v = st.session_state.get("lat", 0)
                            lon_v = st.session_state.get("lon", 0)

                        distancia_m = 0.0

                        try:
                            cod_sel = str(sel_row["CÓDIGO CLIENTE"]).strip().replace(".0", "")

                            base_cliente = df_base.copy()
                            if "Cliente" in base_cliente.columns:
                                base_cliente["Cliente"] = (
                                    base_cliente["Cliente"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
                                )

                            coord = None
                            if (base_cliente is not None) and (not base_cliente.empty) and ("COORDENADAS" in base_cliente.columns):
                                linha_cli = base_cliente[base_cliente["Cliente"] == cod_sel]
                                if not linha_cli.empty:
                                    coord = linha_cli.iloc[0]["COORDENADAS"]

                            if isinstance(coord, str) and ("," in coord):
                                lat_c, lon_c = coord.split(",", 1)

                                if float(lat_v) != 0 and float(lon_v) != 0:
                                    distancia_m = calcular_distancia(
                                        lat_c.strip(),
                                        lon_c.strip(),
                                        lat_v,
                                        lon_v,
                                    )
                                else:
                                    distancia_m = 0.0
                            else:
                                distancia_m = 0.0

                        except Exception as e:
                            distancia_m = 0.0
                            st.warning(f"Falha ao calcular distância: {e}")

                        df_agenda.loc[
                            df_agenda["ID"].astype(str) == str(sel_row["ID"]),
                            ["STATUS", col_aprov_exec, col_just, "COORDENADAS", "DISTANCIA_LOG"],
                        ] = [
                            novo_status,
                            nova_val,
                            nova_just,
                            f"{lat_v}, {lon_v}",
                            round(float(distancia_m), 1),
                        ]

                        conn.update(
                            spreadsheet=url_planilha,
                            worksheet="AGENDA",
                            data=df_agenda.drop(columns=["LINHA", "DT_COMPLETA"], errors="ignore"),
                        )
                        st.cache_data.clear()


                        st.success("Dados atualizados!")
                        time.sleep(1)
                        st.rerun()

            # ============================
            # 🗺️ MAPA (AO FINAL)
            # ============================
            st.markdown("---")
            st.markdown("### 🗺️ Mapa das Visitas do Dia")

            try:
                if df_base is not None and ("COORDENADAS" in df_base.columns):

                    # 🔧 Função única para normalizar códigos (BASE e AGENDA)
                    def _limpa_cod(x):
                        try:
                            if x is None:
                                return ""
                            s = str(x).strip()
                            if s.lower() in ["nan", "none", ""]:
                                return ""
                            s = s.replace("\n", " ").replace("\t", " ").strip()
                            if s.endswith(".0"):
                                s = s[:-2]
                            import re
                            s = re.sub(r"\.0$", "", s)
                            return s.strip()
                        except Exception:
                            return ""

                    # 🔧 COORDENADAS DA BASE (normaliza para o merge não falhar)
                    df_coords = df_base[["Cliente", "COORDENADAS"]].drop_duplicates(subset="Cliente").copy()
                    df_coords = df_coords.rename(columns={"COORDENADAS": "COORDENADAS_BASE"})

                    df_coords["Cliente"] = df_coords["Cliente"].apply(_limpa_cod)

                    if "COORDENADAS_BASE" in df_coords.columns:
                        df_coords["COORDENADAS_BASE"] = df_coords["COORDENADAS_BASE"].astype(str).str.strip()

                    mapa_coords = dict(
                        zip(
                            df_coords["Cliente"].astype(str),
                            df_coords["COORDENADAS_BASE"].astype(str)
                        )
                    )

                    df_map = df_dia.copy()
                    if "CÓDIGO CLIENTE" in df_map.columns:
                        df_map["CÓDIGO CLIENTE"] = df_map["CÓDIGO CLIENTE"].apply(_limpa_cod)

                    df_map = df_map.merge(
                        df_coords,
                        left_on="CÓDIGO CLIENTE",
                        right_on="Cliente",
                        how="left",
                    )

                    if "COORDENADAS_BASE" in df_map.columns:
                        df_map["COORDENADAS_BASE"] = df_map.apply(
                            lambda r: (
                                r["COORDENADAS_BASE"]
                                if pd.notnull(r["COORDENADAS_BASE"]) and str(r["COORDENADAS_BASE"]).strip() not in ["", "nan", "None", "-"]
                                else mapa_coords.get(str(r.get("CÓDIGO CLIENTE", "")).strip(), None)
                            ),
                            axis=1
                        )

                    def _parse_coord(x):
                        try:
                            if x is None:
                                return None, None
                            s = str(x).strip()
                            if s.lower() in ["nan", "none", ""]:
                                return None, None
                            s = s.replace(";", ",")
                            if "," not in s:
                                return None, None
                            lat, lon = s.split(",", 1)
                            lat = lat.strip().replace(" ", "")
                            lon = lon.strip().replace(" ", "")
                            lat = lat.replace(",", ".")
                            lon = lon.replace(",", ".")
                            lat_f = float(lat)
                            lon_f = float(lon)
                            if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
                                return None, None
                            return lat_f, lon_f
                        except Exception:
                            return None, None

                    df_map["LAT"] = df_map["COORDENADAS_BASE"].apply(lambda v: _parse_coord(v)[0])
                    df_map["LON"] = df_map["COORDENADAS_BASE"].apply(lambda v: _parse_coord(v)[1])

                    df_map = df_map.dropna(subset=["LAT", "LON"]).copy()

                    if df_map.empty:
                        st.info("Nenhuma coordenada válida encontrada para exibir no mapa.")
                    else:
                        for c in ["VENDEDOR", "CLIENTE", "STATUS"]:
                            if c in df_map.columns:
                                df_map[c] = df_map[c].astype(str).replace(["nan", "None"], "").fillna("")

                        df_map["COR_PINO"] = df_map["STATUS"].astype(str).str.upper().apply(
                            lambda s: [0, 160, 0, 255] if s == "REALIZADO" else [200, 0, 0, 255]
                        )
                        df_map["COR_RAIO"] = [[160, 160, 160, 70]] * len(df_map)

                        df_map["TOOLTIP"] = df_map.apply(
                            lambda r: f"Vendedor: {r.get('VENDEDOR','')} | Cliente: {r.get('CLIENTE','')} | Status: {r.get('STATUS','')}",
                            axis=1,
                        )

                        icone_vermelho = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"
                        icone_verde = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png"

                        def _icon_por_status(s):
                            s = str(s).strip().upper()
                            url = icone_verde if s == "REALIZADO" else icone_vermelho
                            return {"url": url, "width": 25, "height": 41, "anchorY": 41}

                        df_map["ICON"] = df_map["STATUS"].apply(_icon_por_status)

                        dados_mapa = df_map[["LON", "LAT", "COR_PINO", "COR_RAIO", "ICON", "TOOLTIP"]].to_dict(orient="records")

                        lat_center = float(df_map["LAT"].mean())
                        lon_center = float(df_map["LON"].mean())

                        import pydeck as pdk

                        layer_raio = pdk.Layer(
                            "CircleLayer",
                            data=dados_mapa,
                            get_position="[LON, LAT]",
                            get_radius=1000,
                            radius_units="meters",
                            get_fill_color="COR_RAIO",
                            get_line_color=[120, 120, 120, 180],
                            line_width_min_pixels=2,
                            filled=True,
                            stroked=True,
                            pickable=False,
                        )

                        layer_pinos = pdk.Layer(
                            "IconLayer",
                            data=dados_mapa,
                            get_position="[LON, LAT]",
                            get_icon="ICON",
                            get_size=4,
                            size_scale=10,
                            pickable=True,
                        )

                        view_state = pdk.ViewState(
                            latitude=lat_center,
                            longitude=lon_center,
                            zoom=11,
                            pitch=0,
                        )

                        tooltip = {"text": "{TOOLTIP}"}

                        st.pydeck_chart(
                            pdk.Deck(
                                layers=[layer_raio, layer_pinos],
                                initial_view_state=view_state,
                                tooltip=tooltip,
                                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                            ),
                            use_container_width=True,
                        )

                else:
                    st.info("Coluna COORDENADAS não encontrada na BASE.")

            except Exception as e:
                st.warning(f"Não foi possível renderizar o mapa: {e}")

            # --- BOTÃO ROTA FINALIZADA (SÓ PARA VENDEDOR) ---
            st.markdown("---")
            if is_vendedor:
                if st.button("🚩 FINALIZAR ROTA E ENVIAR RESUMO", use_container_width=True, type="primary"):
                    try:
                        analista_encontrado = (
                            df_base[df_base["VENDEDOR"].str.upper() == user_atual.upper()]["ANALISTA"]
                            .iloc[0]
                            .upper()
                            .strip()
                        )
                    except:
                        analista_encontrado = "NÃO LOCALIZADO"

                    lista_final = EMAILS_GESTAO.copy()
                    if analista_encontrado in MAPA_EMAILS:
                        lista_final.extend(MAPA_EMAILS[analista_encontrado])
                    string_destinatarios = ", ".join(lista_final)

                    resumo_dados = {
                        "total": len(df_dia),
                        "realizados": len(df_dia[df_dia["STATUS"] == "Realizado"]),
                        "pedidos": len(df_dia[df_dia["JUSTIFICATIVA"] == "Visita produtiva com pedido"]),
                        "pendentes": len(df_dia[df_dia["STATUS"] != "Realizado"]),
                    }
                    taxa_conversao = (resumo_dados["pedidos"] / resumo_dados["realizados"] * 100) if resumo_dados["realizados"] > 0 else 0
                    hora_finalizacao = datetime.now(fuso_br).strftime("%H:%M:%S")
                    link_mapas = f"https://www.google.com/maps?q={st.session_state.get('lat', 0)},{st.session_state.get('lon', 0)}"

                    with st.spinner("Enviando resumo..."):
                        sucesso = enviar_resumo_rota(
                            destinatarios_lista=string_destinatarios,
                            vendedor=user_atual,
                            dados_resumo=resumo_dados,
                            nome_analista=analista_encontrado,
                            taxa=taxa_conversao,
                            hora=hora_finalizacao,
                            link=link_mapas,
                        )
                    if sucesso:
                        st.success("✅ Rota finalizada e resumo enviado!")
                        # st.balloons()
                    else:
                        st.error("Falha ao enviar e-mail.")

        else:
            st.info("Nenhum agendamento para hoje.")
    else:
        st.info("Nenhum agendamento para hoje.")

# --- PÁGINA: TESTES (ACURÁCIA) ---
elif menu_interna == "🧪 TESTES":
    st.header("🧪 TESTES — ACURÁCIA DA PREVISÃO (SEMANAL | QTD)")

    # ============================
    # ✅ FUNÇÕES AUXILIARES
    # ============================
    def _to_datetime_safe(s):
        return pd.to_datetime(s, errors="coerce", dayfirst=True)

    def fmt_pt_int(v):
        try:
            return f"{float(v):,.0f}".replace(",", ".")
        except:
            return str(v)

    def _week_key(ts: pd.Series) -> pd.Series:
        # ISO week: "YYYY-Www"
        iso = ts.dt.isocalendar()
        return iso["year"].astype(str) + "-W" + iso["week"].astype(int).astype(str).str.zfill(2)

    def _make_weekly_series(df: pd.DataFrame, date_col: str, qty_col: str, group_cols=None) -> pd.DataFrame:
        """
        Retorna df semanal:
        - sem group_cols: colunas [WEEK, Y]
        - com group_cols: colunas group_cols + [WEEK, Y]
        """
        dfx = df.copy()
        dfx = dfx[dfx[date_col].notna()].copy()
        dfx["WEEK"] = _week_key(dfx[date_col])
        dfx[qty_col] = pd.to_numeric(dfx[qty_col], errors="coerce").fillna(0)

        if group_cols:
            out = (
                dfx.groupby(group_cols + ["WEEK"])[qty_col]
                .sum()
                .reset_index()
                .rename(columns={qty_col: "Y"})
            )
        else:
            out = (
                dfx.groupby(["WEEK"])[qty_col]
                .sum()
                .reset_index()
                .rename(columns={qty_col: "Y"})
            )

        # garantir ordenação por semana
        out["_year"] = out["WEEK"].str.slice(0, 4).astype(int)
        out["_w"] = out["WEEK"].str.slice(6, 8).astype(int)
        out = out.sort_values(["_year", "_w"]).drop(columns=["_year", "_w"]).reset_index(drop=True)
        return out

    def _predict_one_step(hist: list, model: str) -> float:
        """
        hist: lista de Y anteriores (semanas anteriores)
        modelo:
          - "baseline_last": última semana
          - "baseline_mean4": média 4 semanas
          - "model_wma4": média ponderada 4 semanas (40/30/20/10)
        """
        if not hist:
            return 0.0

        if model == "baseline_last":
            return float(hist[-1])

        if model == "baseline_mean4":
            window = hist[-4:] if len(hist) >= 4 else hist
            return float(np.mean(window)) if window else 0.0

        if model == "model_wma4":
            window = hist[-4:] if len(hist) >= 4 else hist
            if not window:
                return 0.0
            # pesos do mais recente pro mais antigo
            weights = [0.40, 0.30, 0.20, 0.10]
            weights = weights[:len(window)]
            weights = np.array(weights, dtype=float)
            weights = weights / weights.sum()
            window_arr = np.array(window[::-1], dtype=float)  # [t-1, t-2, ...]
            return float(np.sum(window_arr * weights))

        # fallback
        return float(hist[-1])

    def _safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        # MAPE ignorando zeros (pra não explodir)
        y_true = np.array(y_true, dtype=float)
        y_pred = np.array(y_pred, dtype=float)
        mask = y_true != 0
        if mask.sum() == 0:
            return 0.0
        return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

    def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        y_true = np.array(y_true, dtype=float)
        y_pred = np.array(y_pred, dtype=float)
        if len(y_true) == 0:
            return 0.0
        return float(np.mean(np.abs(y_true - y_pred)))

    def _walk_forward_backtest(df_week: pd.DataFrame, window_train: int, n_test: int,
                               model_name: str, baseline_name: str) -> dict:
        """
        df_week: colunas [WEEK, Y] ordenado
        retorna dict com:
          - table: df com weeks test + real + prev_model + prev_base + erros
          - metrics: MAE/MAPE model/baseline + win_rate
        """
        if df_week is None or df_week.empty or df_week["Y"].sum() == 0:
            return {"table": pd.DataFrame(), "metrics": {}}

        # garante apenas semanas com Y (pode ter 0, mas mantém)
        weeks = df_week["WEEK"].tolist()
        y = df_week["Y"].astype(float).tolist()

        # define recorte de teste (últimas n_test semanas, mas precisa ter treino antes)
        # índice do primeiro teste
        start_test_idx = max(len(y) - n_test, 1)
        # precisa ter pelo menos window_train semanas antes de start_test_idx
        start_test_idx = max(start_test_idx, window_train)

        rows = []
        for i in range(start_test_idx, len(y)):
            # treino: últimas window_train semanas antes de i
            train_hist = y[max(0, i - window_train): i]
            real = y[i]
            wk = weeks[i]

            pred_model = _predict_one_step(train_hist, model_name)
            pred_base = _predict_one_step(train_hist, baseline_name)

            err_abs_model = abs(real - pred_model)
            err_abs_base = abs(real - pred_base)

            err_pct_model = (err_abs_model / real * 100) if real != 0 else None
            err_pct_base = (err_abs_base / real * 100) if real != 0 else None

            rows.append({
                "SEMANA": wk,
                "REAL": real,
                "PREV_MODELO": pred_model,
                "PREV_BASELINE": pred_base,
                "ERRO_ABS_MODELO": err_abs_model,
                "ERRO_ABS_BASELINE": err_abs_base,
                "ERRO_%_MODELO": err_pct_model,
                "ERRO_%_BASELINE": err_pct_base,
                "MODELO_VENCEU": 1 if err_abs_model < err_abs_base else 0
            })

        df_bt = pd.DataFrame(rows)
        if df_bt.empty:
            return {"table": df_bt, "metrics": {}}

        mae_model = _mae(df_bt["REAL"].values, df_bt["PREV_MODELO"].values)
        mae_base = _mae(df_bt["REAL"].values, df_bt["PREV_BASELINE"].values)

        mape_model = _safe_mape(df_bt["REAL"].values, df_bt["PREV_MODELO"].values)
        mape_base = _safe_mape(df_bt["REAL"].values, df_bt["PREV_BASELINE"].values)

        win_rate = float(df_bt["MODELO_VENCEU"].mean() * 100)

        metrics = {
            "MAE_MODELO": mae_model,
            "MAE_BASELINE": mae_base,
            "MAPE_MODELO": mape_model,
            "MAPE_BASELINE": mape_base,
            "ACURACIA_MODELO": max(0.0, 100.0 - mape_model),
            "WIN_RATE": win_rate
        }
        return {"table": df_bt, "metrics": metrics}

    # ============================
    # ✅ CONTROLES (UI)
    # ============================
    c0, c1, c2, c3 = st.columns([1.2, 1, 1, 1])

    with c0:
        st.caption("⚙️ Ajustes do teste")
    with c1:
        window_train = st.selectbox("Janela de treino (semanas)", [8, 12, 16], index=1)
    with c2:
        n_test = st.selectbox("Qtd semanas de teste", [4, 8, 12], index=1)
    with c3:
        model_choice = st.selectbox(
            "Modelo",
            [
                "Média ponderada 4 semanas (40/30/20/10)",
                "Média 4 semanas",
                "Última semana"
            ],
            index=0
        )

    # baseline fixo (pra comparar)
    baseline_choice = st.selectbox(
        "Baseline para comparação",
        ["Última semana", "Média 4 semanas"],
        index=0
    )

    model_map = {
        "Última semana": "baseline_last",
        "Média 4 semanas": "baseline_mean4",
        "Média ponderada 4 semanas (40/30/20/10)": "model_wma4"
    }
    model_name = model_map.get(model_choice, "model_wma4")
    baseline_name = model_map.get(baseline_choice, "baseline_last")

    st.markdown("---")

    # ============================
    # ✅ LEITURA DO FATURADO
    # ============================
    try:
        df_faturado = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
    except Exception as e:
        st.error(f"Erro lendo FATURADO: {e}")
        st.stop()

    if df_faturado is None or df_faturado.empty:
        st.warning("FATURADO está vazio.")
        st.stop()

    df_faturado = df_faturado.dropna(how="all").copy()
    df_faturado.columns = [str(c).strip() for c in df_faturado.columns]

    # renomes padrão do seu projeto
    df_faturado.rename(columns={
        "Região de vendas": "VENDEDOR_NOME",
        "RG": "VENDEDOR_COD",
        "Qtd Vendas (S/Dec)": "QTD_VENDAS",
        "Hierarquia de produtos": "HIERARQUIA"
    }, inplace=True)

    # detectar coluna Data fat.
    col_data_fat = None
    for c in df_faturado.columns:
        c_norm = str(c).strip().lower().replace(" ", "")
        if "datafat" in c_norm or c_norm in ["datafat.", "datafat"]:
            col_data_fat = c
            break
    if not col_data_fat:
        for c in df_faturado.columns:
            c_low = str(c).strip().lower()
            if ("data" in c_low) and ("fat" in c_low):
                col_data_fat = c
                break
    if not col_data_fat:
        st.error("Não encontrei coluna de data de faturamento (Data fat.) no FATURADO.")
        st.stop()

    df_faturado[col_data_fat] = _to_datetime_safe(df_faturado[col_data_fat])
    df_faturado["QTD_VENDAS"] = pd.to_numeric(df_faturado.get("QTD_VENDAS", 0), errors="coerce").fillna(0)

    if "VENDEDOR_NOME" not in df_faturado.columns:
        st.error("Não encontrei coluna de vendedor (VENDEDOR_NOME / Região de vendas).")
        st.stop()

    # ============================
    # ✅ SOMENTE MESES FECHADOS (ignora o mês atual)
    # ============================
    hoje = pd.Timestamp.now().normalize()
    inicio_mes_atual = pd.Timestamp(year=hoje.year, month=hoje.month, day=1)
    fim_mes_fechado = (inicio_mes_atual - pd.Timedelta(days=1)).normalize()  # último dia do mês anterior

    # ============================
    # ✅ FILTRO (opcional) — Período do histórico usado no teste
    #    (mas o fim sempre é o último dia do mês fechado)
    # ============================
    default_inicio = (fim_mes_fechado - pd.Timedelta(days=120)).to_pydatetime()
    default_fim = fim_mes_fechado.to_pydatetime()

    st.markdown("### 🗓️ Período do histórico usado no teste (somente meses fechados)")
    st.caption(f"⚠️ O mês atual é ignorado. Fim máximo permitido: {fim_mes_fechado.strftime('%d/%m/%Y')}")

    d_ini, d_fim = st.date_input(
        "Selecione o intervalo (sugestão: últimos 120 dias)",
        value=(default_inicio.date(), default_fim.date()),
        key="teste_periodo_hist"
    )
    d_ini = pd.Timestamp(d_ini).normalize()
    d_fim = pd.Timestamp(d_fim).normalize()

    # força o fim no último mês fechado
    if d_fim > fim_mes_fechado:
        d_fim = fim_mes_fechado

    # se o usuário escolher só mês atual, corrige e pode ficar vazio
    if d_ini > d_fim:
        st.warning("O intervalo selecionado ficou inválido após ignorar o mês atual. Ajuste o período.")
        st.stop()

    df_base_hist = df_faturado[
        (df_faturado[col_data_fat].notna()) &
        (df_faturado[col_data_fat] >= d_ini) &
        (df_faturado[col_data_fat] <= d_fim)
    ].copy()

    if df_base_hist.empty:
        st.warning("Sem dados no período escolhido (considerando apenas meses fechados).")
        st.stop()

    # ============================
    # ✅ TOTAL GERAL — backtest
    # ============================
    st.markdown("## 📌 TOTAL GERAL (QTD)")

    df_week_total = _make_weekly_series(df_base_hist, date_col=col_data_fat, qty_col="QTD_VENDAS", group_cols=None)

    bt_total = _walk_forward_backtest(
        df_week_total,
        window_train=window_train,
        n_test=n_test,
        model_name=model_name,
        baseline_name=baseline_name
    )

    df_bt_total = bt_total["table"]
    met_total = bt_total["metrics"]

    if df_bt_total.empty or not met_total:
        st.info("Ainda não dá pra testar: precisa de mais semanas (treino + teste). Ajuste a janela ou o período.")
    else:
        # CARDS
        cA, cB, cC, cD = st.columns(4)

        with cA:
            st.metric("Acurácia (100 - MAPE)", f"{met_total['ACURACIA_MODELO']:.1f}%")
        with cB:
            st.metric("MAE (un/sem)", fmt_pt_int(met_total["MAE_MODELO"]))
        with cC:
            diff = met_total["MAPE_BASELINE"] - met_total["MAPE_MODELO"]
            st.metric("Ganho vs Baseline (MAPE)", f"{diff:.1f} p.p")
        with cD:
            selo = "✅ Confiável" if met_total["MAPE_MODELO"] < 10 else ("⚠️ Moderado" if met_total["MAPE_MODELO"] < 20 else "❌ Baixo")
            st.metric("Selo", selo)

        # Gráfico
        st.markdown("### 📈 Real x Previsto (teste)")
        chart_df = df_bt_total[["SEMANA", "REAL", "PREV_BASELINE", "PREV_MODELO"]].copy()
        chart_df = chart_df.rename(columns={
            "PREV_BASELINE": f"Previsto ({baseline_choice})",
            "PREV_MODELO": f"Previsto ({model_choice})"
        })
        chart_df = chart_df.set_index("SEMANA")
        st.line_chart(chart_df)

        # Tabela de rodadas
        st.markdown("### 🧾 Rodadas do teste (TOTAL)")
        view_total = df_bt_total.copy()
        st.dataframe(
            view_total.style.format({
                "REAL": lambda v: fmt_pt_int(v),
                "PREV_MODELO": lambda v: fmt_pt_int(v),
                "PREV_BASELINE": lambda v: fmt_pt_int(v),
                "ERRO_ABS_MODELO": lambda v: fmt_pt_int(v),
                "ERRO_ABS_BASELINE": lambda v: fmt_pt_int(v),
                "ERRO_%_MODELO": lambda v: "" if v is None else f"{v:.1f}%",
                "ERRO_%_BASELINE": lambda v: "" if v is None else f"{v:.1f}%",
                "MODELO_VENCEU": lambda v: "✅" if int(v) == 1 else "—"
            }),
            use_container_width=True,
            hide_index=True,
            height=320
        )

        # Texto de insight
        st.markdown("### 🧠 Resumo automático (TOTAL)")
        st.write(
            f"- Modelo venceu o baseline em **{met_total['WIN_RATE']:.0f}%** das semanas de teste.\n"
            f"- MAE: **{fmt_pt_int(met_total['MAE_MODELO'])}** un/sem | MAPE: **{met_total['MAPE_MODELO']:.1f}%**.\n"
            f"- Baseline MAPE: **{met_total['MAPE_BASELINE']:.1f}%** → ganho **{(met_total['MAPE_BASELINE']-met_total['MAPE_MODELO']):.1f} p.p**."
        )

    st.markdown("---")

    # ============================
    # ✅ POR VENDEDOR — ranking + detalhe
    # ============================
    st.markdown("## 👤 POR VENDEDOR (QTD)")

    # construir séries semanais por vendedor
    df_week_v = _make_weekly_series(
        df_base_hist,
        date_col=col_data_fat,
        qty_col="QTD_VENDAS",
        group_cols=["VENDEDOR_NOME"]
    )

    # filtro mínimo de semanas com dados (evita ranking lixo)
    min_weeks = st.slider("Mínimo de semanas com dados (por vendedor)", 6, 20, 10, 1)

    vendedores = df_week_v["VENDEDOR_NOME"].dropna().unique().tolist()
    vendedores = sorted([str(v) for v in vendedores])

    # ranking
    rank_rows = []
    for vnd in vendedores:
        df_vnd = df_week_v[df_week_v["VENDEDOR_NOME"] == vnd].copy()
        if df_vnd["WEEK"].nunique() < min_weeks:
            continue

        bt_v = _walk_forward_backtest(
            df_vnd[["WEEK", "Y"]].rename(columns={"WEEK": "WEEK", "Y": "Y"}),
            window_train=window_train,
            n_test=n_test,
            model_name=model_name,
            baseline_name=baseline_name
        )

        if bt_v["table"].empty or not bt_v["metrics"]:
            continue

        met = bt_v["metrics"]
        vol_med = float(df_vnd["Y"].mean()) if not df_vnd.empty else 0.0

        rank_rows.append({
            "VENDEDOR": vnd,
            "MAPE_MODELO": met["MAPE_MODELO"],
            "MAE_MODELO": met["MAE_MODELO"],
            "WIN_RATE_%": met["WIN_RATE"],
            "VOL_MÉDIO_SEM": vol_med
        })

    df_rank = pd.DataFrame(rank_rows)
    if df_rank.empty:
        st.info("Não foi possível montar ranking: ajuste período / min semanas / janela treino.")
        st.stop()

    df_rank = df_rank.sort_values(["MAPE_MODELO", "MAE_MODELO"], ascending=True).reset_index(drop=True)

    cR1, cR2 = st.columns([1.2, 1])
    with cR1:
        st.markdown("### 🏁 Ranking de previsibilidade (menor MAPE = mais previsível)")
        st.dataframe(
            df_rank.style.format({
                "MAPE_MODELO": "{:.1f}%",
                "MAE_MODELO": lambda v: fmt_pt_int(v),
                "WIN_RATE_%": "{:.0f}%",
                "VOL_MÉDIO_SEM": lambda v: fmt_pt_int(v)
            }),
            use_container_width=True,
            hide_index=True,
            height=360
        )

    with cR2:
        st.markdown("### 🔎 Detalhe do vendedor")
        vendedor_sel = st.selectbox("Selecione um vendedor", df_rank["VENDEDOR"].tolist(), index=0)

        # rodar backtest do selecionado
        df_vsel = df_week_v[df_week_v["VENDEDOR_NOME"] == vendedor_sel].copy()
        bt_sel = _walk_forward_backtest(
            df_vsel[["WEEK", "Y"]].rename(columns={"WEEK": "WEEK", "Y": "Y"}),
            window_train=window_train,
            n_test=n_test,
            model_name=model_name,
            baseline_name=baseline_name
        )
        df_bt_sel = bt_sel["table"]
        met_sel = bt_sel["metrics"]

        if df_bt_sel.empty or not met_sel:
            st.warning("Sem backtest suficiente para este vendedor (faltou histórico).")
        else:
            st.metric("Acurácia (100 - MAPE)", f"{met_sel['ACURACIA_MODELO']:.1f}%")
            st.metric("MAE (un/sem)", fmt_pt_int(met_sel["MAE_MODELO"]))
            st.metric("Modelo venceu baseline", f"{met_sel['WIN_RATE']:.0f}% das semanas")

            st.markdown("#### 📈 Real x Previsto (vendedor)")
            chart_v = df_bt_sel[["SEMANA", "REAL", "PREV_BASELINE", "PREV_MODELO"]].copy()
            chart_v = chart_v.rename(columns={
                "PREV_BASELINE": f"Previsto ({baseline_choice})",
                "PREV_MODELO": f"Previsto ({model_choice})"
            })
            chart_v = chart_v.set_index("SEMANA")
            st.line_chart(chart_v)

            st.markdown("#### 🧾 Rodadas do teste (vendedor)")
            st.dataframe(
                df_bt_sel.style.format({
                    "REAL": lambda v: fmt_pt_int(v),
                    "PREV_MODELO": lambda v: fmt_pt_int(v),
                    "PREV_BASELINE": lambda v: fmt_pt_int(v),
                    "ERRO_ABS_MODELO": lambda v: fmt_pt_int(v),
                    "ERRO_ABS_BASELINE": lambda v: fmt_pt_int(v),
                    "ERRO_%_MODELO": lambda v: "" if v is None else f"{v:.1f}%",
                    "ERRO_%_BASELINE": lambda v: "" if v is None else f"{v:.1f}%",
                    "MODELO_VENCEU": lambda v: "✅" if int(v) == 1 else "—"
                }),
                use_container_width=True,
                hide_index=True,
                height=260
            )

    st.markdown("---")


# --- PÁGINA: PERFIL DO CLIENTE (CURVA DE APRENDIZADO) ---
elif menu_interna == "📚 Perfil do Cliente":
    st.header("📚 Perfil do Cliente (Histórico e Mix)")

    # ============================
    # 1) Carrega FATURADO
    # ============================
    try:
        df_fat = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
        if df_fat is None or df_fat.empty:
            st.warning("A aba FATURADO está vazia.")
            st.stop()

        df_fat = df_fat.dropna(how="all").copy()
        df_fat.columns = [str(c).strip() for c in df_fat.columns]

    except Exception as e:
        st.error(f"Erro ao ler FATURADO: {e}")
        st.stop()

    # ============================
    # 2) Mapeamento dinâmico de colunas
    # ============================
    def pick_col(df, candidates, fallback=None):
        cols_up = {c.upper(): c for c in df.columns}
        for cand in candidates:
            if cand.upper() in cols_up:
                return cols_up[cand.upper()]
        return fallback

    col_cliente = pick_col(
        df_fat,
        ["Cliente", "CÓDIGO CLIENTE", "COD CLIENTE"],
        fallback=df_fat.columns[11] if len(df_fat.columns) > 11 else df_fat.columns[0],
    )
    col_data = pick_col(df_fat, ["Data fat.", "DATA FAT.", "DATA FAT", "DATA"], fallback=None)
    col_hier = pick_col(df_fat, ["Hierarquia de produtos", "HIERARQUIA", "HIERARQUIA DE PRODUTOS"], fallback=None)
    col_sku = pick_col(df_fat, ["N° artigo", "Nº artigo", "ARTIGO", "SKU"], fallback=None)
    col_qtd = pick_col(df_fat, ["Qtd Vendas (S/Dec)", "QTD VENDAS (S/DEC)", "QTD", "QUANTIDADE"], fallback=None)
    col_rec = pick_col(df_fat, ["Receita", "RECEITA", "Valor", "VALOR"], fallback=None)
    col_pedido = pick_col(
        df_fat,
        ["OrdCliente", "ORDCLIENTE", "PEDIDO", "NUM PEDIDO", "Nº PEDIDO"],
        fallback="OrdCliente",
    )

    # ✅ colunas para os filtros pedidos (vindas do FATURADO)
    col_analista = pick_col(df_fat, ["ANALISTA"], fallback=None)
    col_estado = pick_col(df_fat, ["EscrV", "ESCRV"], fallback=None)  # Estado
    col_vendedor = pick_col(
        df_fat,
        ["Região de vendas", "REGIÃO DE VENDAS", "REGIAO DE VENDAS"],
        fallback=None,
    )  # Vendedor
    col_supervisor = pick_col(df_fat, ["EqvS", "EQVS"], fallback=None)  # Código do supervisor

    # valida mínimos
    faltando = []
    if not col_data:
        faltando.append("Data fat.")
    if not col_sku:
        faltando.append("SKU/N° artigo")
    if not col_qtd:
        faltando.append("Qtd Vendas (S/Dec)")
    if not col_rec:
        faltando.append("Receita")
    if col_pedido not in df_fat.columns:
        faltando.append("OrdCliente (pedido)")

    # valida colunas dos filtros (não trava a página; só avisa e desliga o filtro correspondente)
    faltando_filtros = []
    if not col_analista:
        faltando_filtros.append("ANALISTA")
    if not col_estado:
        faltando_filtros.append("EscrV (Estado)")
    if not col_vendedor:
        faltando_filtros.append("Região de vendas (Vendedor)")
    if not col_supervisor:
        faltando_filtros.append("EqvS (Supervisor)")

    if faltando:
        st.error("Colunas obrigatórias não encontradas no FATURADO: " + ", ".join(faltando))
        st.stop()

    if faltando_filtros:
        st.info(
            "Filtros não disponíveis (colunas não encontradas no FATURADO): "
            + ", ".join(faltando_filtros)
        )

    # ============================
    # 3) Limpeza/normalização
    # ============================
    def limpar_cod(v):
        if pd.isna(v):
            return ""
        return str(v).strip().replace(".0", "")

    df_fat = df_fat.copy()
    df_fat[col_cliente] = df_fat[col_cliente].apply(limpar_cod)
    df_fat[col_pedido] = df_fat[col_pedido].apply(limpar_cod)

    # normaliza também as colunas dos filtros (se existirem)
    if col_analista and col_analista in df_fat.columns:
        df_fat[col_analista] = df_fat[col_analista].astype(str).str.strip().str.upper()
    if col_estado and col_estado in df_fat.columns:
        df_fat[col_estado] = df_fat[col_estado].astype(str).str.strip().str.upper()
    if col_vendedor and col_vendedor in df_fat.columns:
        df_fat[col_vendedor] = df_fat[col_vendedor].astype(str).str.strip().str.upper()
    if col_supervisor and col_supervisor in df_fat.columns:
        df_fat[col_supervisor] = (
            df_fat[col_supervisor].apply(limpar_cod).astype(str).str.strip().str.upper()
        )

    df_fat[col_qtd] = pd.to_numeric(df_fat[col_qtd], errors="coerce").fillna(0)
    df_fat[col_rec] = pd.to_numeric(df_fat[col_rec], errors="coerce").fillna(0)

    df_fat[col_data] = pd.to_datetime(df_fat[col_data], errors="coerce", dayfirst=True)
    df_fat = df_fat[df_fat[col_data].notna()].copy()

    # ============================
    # ✅ 4) FILTROS (Estado / Analista / Supervisor / Vendedor) - DIRETO DO FATURADO
    #    - Não muda nada do resto, só filtra a lista de clientes
    # ============================
    

    f1, f2, f3, f4 = st.columns(4)

    # base para filtros (começa pelo df_fat)
    df_fat_filtrado = df_fat.copy()

    # opções
    estados = ["(Todos)"]
    analistas = ["(Todos)"]
    supervisores = ["(Todos)"]
    vendedores = ["(Todos)"]

    if col_estado and col_estado in df_fat.columns:
        estados += sorted([x for x in df_fat[col_estado].dropna().unique().tolist() if str(x).strip() != ""])
    if col_analista and col_analista in df_fat.columns:
        analistas += sorted([x for x in df_fat[col_analista].dropna().unique().tolist() if str(x).strip() != ""])
    if col_supervisor and col_supervisor in df_fat.columns:
        supervisores += sorted([x for x in df_fat[col_supervisor].dropna().unique().tolist() if str(x).strip() != ""])
    if col_vendedor and col_vendedor in df_fat.columns:
        vendedores += sorted([x for x in df_fat[col_vendedor].dropna().unique().tolist() if str(x).strip() != ""])

    with f1:
        estado_sel = st.selectbox(
            "Estado",
            estados,
            index=0,
            disabled=(len(estados) == 1),
            key="f_estado_cli",
        )
    with f2:
        analista_sel = st.selectbox(
            "Analista",
            analistas,
            index=0,
            disabled=(len(analistas) == 1),
            key="f_analista_cli",
        )
    with f3:
        supervisor_sel = st.selectbox(
            "Supervisor",
            supervisores,
            index=0,
            disabled=(len(supervisores) == 1),
            key="f_supervisor_cli",
        )
    with f4:
        vendedor_sel = st.selectbox(
            "Vendedor",
            vendedores,
            index=0,
            disabled=(len(vendedores) == 1),
            key="f_vendedor_cli",
        )

    # aplica filtros no FATURADO (só afeta a lista de clientes e seleção)
    if col_estado and col_estado in df_fat_filtrado.columns and estado_sel != "(Todos)":
        df_fat_filtrado = df_fat_filtrado[df_fat_filtrado[col_estado] == estado_sel].copy()

    if col_analista and col_analista in df_fat_filtrado.columns and analista_sel != "(Todos)":
        df_fat_filtrado = df_fat_filtrado[df_fat_filtrado[col_analista] == analista_sel].copy()

    if col_supervisor and col_supervisor in df_fat_filtrado.columns and supervisor_sel != "(Todos)":
        df_fat_filtrado = df_fat_filtrado[df_fat_filtrado[col_supervisor] == supervisor_sel].copy()

    if col_vendedor and col_vendedor in df_fat_filtrado.columns and vendedor_sel != "(Todos)":
        df_fat_filtrado = df_fat_filtrado[df_fat_filtrado[col_vendedor] == vendedor_sel].copy()

    st.markdown("---")

    # ============================
    # 5) Filtros UI
    # ============================
    st.markdown("### 🔎 Selecione o Cliente")

    c1, c2 = st.columns([2, 1])

    lista_clientes = sorted(
        [x for x in df_fat_filtrado[col_cliente].dropna().unique().tolist() if str(x).strip() != ""]
    )
    if not lista_clientes:
        st.warning("Não encontrei clientes no FATURADO com os filtros selecionados.")
        st.stop()

    with c1:
        cli_sel = st.selectbox("Cliente (código):", lista_clientes)

    with c2:
        periodo = st.selectbox("Período:", ["Últimos 3 meses", "Últimos 6 meses", "Últimos 12 meses", "Tudo"])

    df_cli_full = df_fat_filtrado[df_fat_filtrado[col_cliente] == cli_sel].copy()
    if df_cli_full.empty:
        st.warning("Esse cliente não tem faturamento.")
        st.stop()

    # ✅ Mostra os atributos do cliente (vindos do próprio FATURADO filtrado)
    info_cli = df_cli_full.head(1)
    i1, i2, i3, i4 = st.columns(4)

    with i1:
        st.caption("Estado")
        if col_estado and col_estado in info_cli.columns:
            st.write(info_cli[col_estado].iloc[0] if str(info_cli[col_estado].iloc[0]).strip() else "-")
        else:
            st.write("-")

    with i2:
        st.caption("Analista")
        if col_analista and col_analista in info_cli.columns:
            st.write(info_cli[col_analista].iloc[0] if str(info_cli[col_analista].iloc[0]).strip() else "-")
        else:
            st.write("-")

    with i3:
        st.caption("Supervisor")
        if col_supervisor and col_supervisor in info_cli.columns:
            st.write(info_cli[col_supervisor].iloc[0] if str(info_cli[col_supervisor].iloc[0]).strip() else "-")
        else:
            st.write("-")

    with i4:
        st.caption("Vendedor")
        if col_vendedor and col_vendedor in info_cli.columns:
            st.write(info_cli[col_vendedor].iloc[0] if str(info_cli[col_vendedor].iloc[0]).strip() else "-")
        else:
            st.write("-")

    # aplica filtro principal de período (o resto da tela)
    df_cli = df_cli_full.copy()
    if periodo != "Tudo":
        meses = {"Últimos 3 meses": 3, "Últimos 6 meses": 6, "Últimos 12 meses": 12}[periodo]
        dt_min = df_cli[col_data].max() - pd.DateOffset(months=meses)
        df_cli = df_cli[df_cli[col_data] >= dt_min].copy()

    if df_cli.empty:
        st.warning("Esse cliente não tem faturamento no período selecionado.")
        st.stop()

    # ============================
    # 6) Métricas principais (FOCO VOLUME)
    # ============================
    ultima_compra = df_cli[col_data].max()
    dias_sem = (datetime.now(fuso_br).date() - ultima_compra.date()).days

    pedidos_unicos = df_cli[col_pedido].nunique()
    receita_total = float(df_cli[col_rec].sum())
    volume_total = float(df_cli[col_qtd].sum())

    # mix médio por pedido
    mix_medio = (df_cli[col_sku].nunique() / pedidos_unicos) if pedidos_unicos > 0 else 0

    # frequência média (dias entre pedidos)
    df_pedidos_data = (
        df_cli.groupby(col_pedido)[col_data]
        .max()
        .sort_values()
        .reset_index()
    )
    if len(df_pedidos_data) >= 2:
        diffs = df_pedidos_data[col_data].diff().dt.days.dropna()
        freq_media = float(diffs.mean()) if not diffs.empty else 0
    else:
        freq_media = 0

               # ✅ NOVO (1/3): RISCO DE ATRASO (FOCO FREQUÊNCIA) — mais didático
    # Regra: só calcula se tiver base mínima (evita "atrasado" com poucos dias de histórico)
    min_pedidos_base = 4          # ajuste se quiser (ex.: 3, 4, 5)
    min_dias_base = 15            # janela mínima de histórico (em dias)
    min_freq_media = 3            # evita médias muito baixas (ex.: 1 dia) com base curta

    # Base de datas do cliente no período atual
    dt_min_cli = df_cli[col_data].min()
    dt_max_cli = df_cli[col_data].max()
    dias_base = (dt_max_cli.date() - dt_min_cli.date()).days if pd.notna(dt_min_cli) and pd.notna(dt_max_cli) else 0

    base_ok = (
        (pedidos_unicos is not None and int(pedidos_unicos) >= int(min_pedidos_base))
        and (dias_base >= int(min_dias_base))
        and (freq_media is not None and float(freq_media) >= float(min_freq_media))
    )

    if base_ok and freq_media and freq_media > 0:
        dias_pra_atrasar = max(0, int(round(freq_media - dias_sem)))
        nivel = dias_sem / freq_media
    else:
        dias_pra_atrasar = None
        nivel = None

    if nivel is None:
        risco_txt = "Sem base"
        risco_delta = None
        risco_help = (
            f"Base insuficiente para estimar padrão: "
            f"mín. {min_pedidos_base} pedidos, {min_dias_base} dias de histórico e freq. média ≥ {min_freq_media}d."
        )
        msg_status = None
    else:
        # texto principal do card (curto)
        if dias_sem >= freq_media:
            risco_txt = "Atrasado"
        else:
            risco_txt = "No prazo"

        # delta em dias vs padrão
        diff_dias = int(round(dias_sem - freq_media))
        risco_delta = f"{diff_dias:+d}d"
        risco_help = "Comparação com o padrão do cliente: (Dias sem comprar) vs (Frequência média entre pedidos)."

        # mensagem de status (mantém a mesma lógica de corte do seu código)
        if nivel > 1.5:
            msg_status = ("warning", "⚠️ Cliente acima do padrão de compra (alto risco de estar atrasado).")
        elif nivel >= 1.0:
            msg_status = ("info", "ℹ️ Cliente no limite do padrão de compra (atenção).")
        else:
            msg_status = ("success", "✅ Cliente dentro do padrão de frequência de compra.")

    # Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Última compra", ultima_compra.strftime("%d/%m/%Y"))
    m2.metric("Dias sem comprar", dias_sem)
    m3.metric("Pedidos no período", int(pedidos_unicos))
    m4.metric("Volume total", f"{volume_total:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
    m5.metric("Mix médio (SKUs/pedido)", f"{mix_medio:.1f}")
    m6.metric("Regularidade", risco_txt, delta=risco_delta, help=risco_help)

    if msg_status is not None:
        tipo, texto = msg_status
        if tipo == "warning":
            st.warning(texto)
        elif tipo == "info":
            st.info(texto)
        else:
            st.success(texto)



    st.markdown("---")

       # ============================
    # 7) Top Hierarquias e Top SKUs (ordena por VOLUME)
    # ============================
    colA, colB = st.columns(2)

    # ✅ formatação BRL (R$) só para exibição
    def fmt_brl(v):
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "R$ 0,00"

    with colA:
        st.subheader("🏷️ Top Hierarquias (por Volume)")
        if col_hier and col_hier in df_cli.columns:
            top_h = (
                df_cli.groupby(col_hier)
                .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"), Receita=(col_rec, "sum"))
                .sort_values("Volume", ascending=False)
                .head(10)
                .reset_index()
            )

            top_h_show = top_h.copy()
            top_h_show["Receita"] = top_h_show["Receita"].apply(fmt_brl)

            st.dataframe(top_h_show, use_container_width=True, hide_index=True)
        else:
            st.info("Coluna de hierarquia não encontrada no FATURADO.")

    with colB:
        st.subheader("📦 Top SKUs (por Volume)")
        top_sku = (
            df_cli.groupby(col_sku)
            .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"), Receita=(col_rec, "sum"))
            .sort_values("Volume", ascending=False)
            .head(15)
            .reset_index()
        )

        top_sku_show = top_sku.copy()
        top_sku_show["Receita"] = top_sku_show["Receita"].apply(fmt_brl)

        st.dataframe(top_sku_show, use_container_width=True, hide_index=True)

    st.markdown("---")

       # ============================
    # ✅ NOVO (2/3): ABC DO CLIENTE (FOCO VOLUME)
    # ============================
    st.subheader("📌 Curva ABC do Cliente (por Volume)")

    df_abc = (
        df_cli.groupby(col_sku)
        .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"))
        .sort_values("Volume", ascending=False)
        .reset_index()
    )

    if df_abc.empty:
        st.info("Sem dados suficientes para calcular ABC.")
    else:
        vol_total_abc = df_abc["Volume"].sum()
        if vol_total_abc <= 0:
            st.info("Volume total zerado no período.")
        else:
            # ⚙️ cálculos (mantém numérico)
            df_abc["% Volume"] = (df_abc["Volume"] / vol_total_abc * 100)
            df_abc["% Acum."] = df_abc["% Volume"].cumsum()

            def class_abc(p):
                if p <= 80:
                    return "A"
                elif p <= 95:
                    return "B"
                return "C"

            df_abc["Classe"] = df_abc["% Acum."].apply(class_abc)

            resumo_abc = (
                df_abc.groupby("Classe")
                .agg(
                    SKUs=(col_sku, "count"),
                    Volume=("Volume", "sum"),
                    Perc_Vol=("% Volume", "sum"),
                )
                .reset_index()
                .sort_values("Classe")
            )

            # ✅ formatação de porcentagem (somente exibição)
            def fmt_pct(v, casas=1):
                try:
                    return f"{float(v):.{casas}f}%".replace(".", ",")
                except Exception:
                    return "-"

            resumo_show = resumo_abc.copy()
            resumo_show["Perc_Vol"] = resumo_show["Perc_Vol"].apply(lambda x: fmt_pct(x, 1))

            detalhe_show = df_abc.copy()
            detalhe_show["% Volume"] = detalhe_show["% Volume"].apply(lambda x: fmt_pct(x, 1))
            detalhe_show["% Acum."] = detalhe_show["% Acum."].apply(lambda x: fmt_pct(x, 1))

            cA, cB = st.columns([1, 2])
            with cA:
                st.dataframe(resumo_show, use_container_width=True, hide_index=True)
            with cB:
                st.caption("A = até 80% do volume acumulado | B = 80–95% | C = 95–100%")
                st.dataframe(
                    detalhe_show[[col_sku, "Classe", "Volume", "% Volume", "% Acum.", "Pedidos"]].head(30),
                    use_container_width=True,
                    hide_index=True,
                )


           # ============================
    # ✅ NOVO (2.1/3): ABC DE CLIENTES (FOCO FATURAMENTO / RECEITA)
    # - Classifica CLIENTES A/B/C por faturamento no recorte atual (filtros do topo)
    # - Respeita o mesmo período selecionado (periodo)
    # ============================
    st.subheader("📌 Curva ABC de Clientes (por Faturamento)")

    # base = carteira/recorte atual (Estado/Analista/Supervisor/Vendedor)
    df_cli_abc_base = df_fat_filtrado.copy()

    # aplica o mesmo período selecionado no topo (para ser coerente com a tela)
    if periodo != "Tudo":
        meses = {"Últimos 3 meses": 3, "Últimos 6 meses": 6, "Últimos 12 meses": 12}[periodo]
        dt_min_abc = df_cli_abc_base[col_data].max() - pd.DateOffset(months=meses)
        df_cli_abc_base = df_cli_abc_base[df_cli_abc_base[col_data] >= dt_min_abc].copy()

    df_abc_rec = (
        df_cli_abc_base.groupby(col_cliente)
        .agg(Receita=(col_rec, "sum"), Pedidos=(col_pedido, "nunique"))
        .sort_values("Receita", ascending=False)
        .reset_index()
        .rename(columns={col_cliente: "Cliente"})
    )

    if df_abc_rec.empty:
        st.info("Sem dados suficientes para calcular ABC de clientes por faturamento.")
    else:
        rec_total_abc = df_abc_rec["Receita"].sum()
        if rec_total_abc <= 0:
            st.info("Faturamento total zerado no período.")
        else:
            # ⚙️ cálculos (mantém numérico)
            df_abc_rec["% Receita"] = (df_abc_rec["Receita"] / rec_total_abc * 100)
            df_abc_rec["% Acum."] = df_abc_rec["% Receita"].cumsum()

            def class_abc_rec(p):
                if p <= 80:
                    return "A"
                elif p <= 95:
                    return "B"
                return "C"

            df_abc_rec["Classe"] = df_abc_rec["% Acum."].apply(class_abc_rec)

            resumo_abc_rec = (
                df_abc_rec.groupby("Classe")
                .agg(
                    Clientes=("Cliente", "count"),
                    Receita=("Receita", "sum"),
                    Perc_Rec=("% Receita", "sum"),
                )
                .reset_index()
                .sort_values("Classe")
            )

            # ✅ formatação BRL (R$) para exibição (sem alterar os cálculos)
            def fmt_brl(v):
                try:
                    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                except Exception:
                    return "R$ 0,00"

            # ✅ formatação % (somente exibição)
            def fmt_pct(v, casas=1):
                try:
                    return f"{float(v):.{casas}f}%".replace(".", ",")
                except Exception:
                    return "-"

            resumo_show = resumo_abc_rec.copy()
            resumo_show["Receita"] = resumo_show["Receita"].apply(fmt_brl)
            resumo_show["Perc_Rec"] = resumo_show["Perc_Rec"].apply(lambda x: fmt_pct(x, 1))

            detalhe_show = df_abc_rec.copy()
            detalhe_show["Receita"] = detalhe_show["Receita"].apply(fmt_brl)
            detalhe_show["% Receita"] = detalhe_show["% Receita"].apply(lambda x: fmt_pct(x, 1))
            detalhe_show["% Acum."] = detalhe_show["% Acum."].apply(lambda x: fmt_pct(x, 1))

            cA2, cB2 = st.columns([1, 2])
            with cA2:
                st.dataframe(resumo_show, use_container_width=True, hide_index=True)
            with cB2:
                st.caption("A = até 80% do faturamento acumulado | B = 80–95% | C = 95–100%")
                st.dataframe(
                    detalhe_show[["Cliente", "Classe", "Receita", "% Receita", "% Acum.", "Pedidos"]].head(30),
                    use_container_width=True,
                    hide_index=True,
                )


    
   

    st.markdown("---")

    # ============================
    # ✅ NOVO (3/3): GAPS (SKUs que SUMIRAM)
    # ============================
    st.subheader("🕳️ O que está faltando? (SKUs que o cliente comprava e parou)")

    dt_ref = df_cli_full[col_data].max()

    if periodo == "Últimos 3 meses":
        meses_agora = 3
        meses_total = 12
    elif periodo == "Últimos 6 meses":
        meses_agora = 6
        meses_total = 12
    elif periodo == "Últimos 12 meses":
        meses_agora = 12
        meses_total = 24
    else:
        meses_agora = 6
        meses_total = 12

    dt_ini_total = dt_ref - pd.DateOffset(months=meses_total)
    dt_ini_agora = dt_ref - pd.DateOffset(months=meses_agora)

    df_total = df_cli_full[df_cli_full[col_data] >= dt_ini_total].copy()
    df_agora = df_cli_full[df_cli_full[col_data] >= dt_ini_agora].copy()
    df_antes = df_total[df_total[col_data] < dt_ini_agora].copy()

    if df_antes.empty or df_agora.empty:
        st.info("Sem histórico suficiente para comparar 'antes' vs 'agora'.")
    else:
        vol_antes = (
            df_antes.groupby(col_sku)
            .agg(Volume_Antes=(col_qtd, "sum"), Pedidos_Antes=(col_pedido, "nunique"))
            .reset_index()
        )
        vol_agora = (
            df_agora.groupby(col_sku)
            .agg(Volume_Agora=(col_qtd, "sum"), Pedidos_Agora=(col_pedido, "nunique"))
            .reset_index()
        )

        df_gap = vol_antes.merge(vol_agora, on=col_sku, how="left")
        df_gap["Volume_Agora"] = df_gap["Volume_Agora"].fillna(0)
        df_gap["Pedidos_Agora"] = df_gap["Pedidos_Agora"].fillna(0)

        min_vol_antes = st.number_input(
            "Volume mínimo no 'antes' para considerar (evita ruído):",
            min_value=0.0,
            value=10.0,
            step=5.0,
            key="min_vol_antes_gap_sumiram",
        )

        df_sumiram = df_gap[
            (df_gap["Volume_Antes"] >= float(min_vol_antes)) & (df_gap["Volume_Agora"] <= 0)
        ].copy()
        df_sumiram["Diferença"] = df_sumiram["Volume_Agora"] - df_sumiram["Volume_Antes"]

        df_sumiram = df_sumiram.sort_values("Volume_Antes", ascending=False).head(30)

        cG1, cG2 = st.columns([2, 1])
        with cG2:
            st.caption(f"Agora = últimos {meses_agora}m | Antes = {meses_total}m (exceto agora)")
            st.caption(f"Base de comparação até: {dt_ref.strftime('%d/%m/%Y')}")

        with cG1:
            if df_sumiram.empty:
                st.success("✅ Não encontrei SKUs relevantes que o cliente parou de comprar (no critério definido).")
            else:
                st.dataframe(
                    df_sumiram[[col_sku, "Volume_Antes", "Pedidos_Antes", "Volume_Agora", "Pedidos_Agora"]],
                    use_container_width=True,
                    hide_index=True,
                )

    st.markdown("---")

    # ============================
    # 8) "Compram junto" (Market Basket por pedido)
    # ============================
    st.subheader("🧠 Compram junto (combos mais frequentes)")

    pedido_skus = (
        df_cli[[col_pedido, col_sku]]
        .dropna()
        .astype(str)
        .groupby(col_pedido)[col_sku]
        .apply(lambda x: sorted(set([i.strip() for i in x.tolist() if i.strip()])))
    )

    if pedido_skus.shape[0] < 3:
        st.info("Poucos pedidos no período para calcular combinações com confiança.")
    else:
        from itertools import combinations

        pares = {}
        for skus in pedido_skus:
            if len(skus) < 2:
                continue
            for a, b in combinations(skus, 2):
                key = tuple(sorted((a, b)))
                pares[key] = pares.get(key, 0) + 1

        if not pares:
            st.info("Não foi possível gerar pares (pedidos com 2+ SKUs).")
        else:
            df_pares = (
                pd.DataFrame([{"SKU_A": k[0], "SKU_B": k[1], "Frequência": v} for k, v in pares.items()])
                .sort_values("Frequência", ascending=False)
                .reset_index(drop=True)
            )
            df_pares["% dos pedidos"] = (df_pares["Frequência"] / pedido_skus.shape[0] * 100).round(1)

            sku_ancora = st.selectbox(
                "Ver combinações a partir do SKU:",
                ["(Mostrar todos)"] + sorted(df_cli[col_sku].dropna().astype(str).unique().tolist()),
                key="sku_ancora_pairs",
            )

            df_view_pares = df_pares.copy()
            if sku_ancora != "(Mostrar todos)":
                df_view_pares = df_view_pares[
                    (df_view_pares["SKU_A"] == sku_ancora) | (df_view_pares["SKU_B"] == sku_ancora)
                ].copy()

                df_view_pares["Sugestão"] = df_view_pares.apply(
                    lambda r: r["SKU_B"] if r["SKU_A"] == sku_ancora else r["SKU_A"], axis=1
                )

            st.dataframe(df_view_pares.head(30), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ============================
    # 9) Linha do tempo (simples)
    # ============================
    st.subheader("📆 Linha do tempo de compras")

    df_tempo = (
        df_cli.groupby(pd.Grouper(key=col_data, freq="M"))
        .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"), Receita=(col_rec, "sum"))
        .reset_index()
    )
    df_tempo["Mês"] = df_tempo[col_data].dt.strftime("%Y-%m")
    df_tempo = df_tempo[["Mês", "Volume", "Pedidos", "Receita"]].sort_values("Mês")

    st.dataframe(df_tempo, use_container_width=True, hide_index=True)

    # =========================================================
    # ✅ ADIÇÃO 1: SAZONALIDADE (DIA DA SEMANA)
    # =========================================================
    st.markdown("---")
    st.subheader("🗓️ Sazonalidade (Dia da Semana)")

    mapa_dias = {
        0: "Segunda",
        1: "Terça",
        2: "Quarta",
        3: "Quinta",
        4: "Sexta",
        5: "Sábado",
        6: "Domingo",
    }

    df_semana = df_cli.copy()
    df_semana["__dow"] = df_semana[col_data].dt.dayofweek
    df_semana["Dia da Semana"] = df_semana["__dow"].map(mapa_dias)

    compras_dow = (
        df_semana.groupby(["__dow", "Dia da Semana"])
        .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"))
        .reset_index()
        .sort_values("__dow")
        .drop(columns=["__dow"])
    )

    if compras_dow.empty:
        st.info("Sem dados suficientes para sazonalidade por dia da semana.")
    else:
        st.dataframe(compras_dow, use_container_width=True, hide_index=True)

        # =========================================================
    # ✅ ADIÇÃO 2: GAP / RECOMENDAÇÃO POR CARTEIRA
    # =========================================================
    st.markdown("---")
    st.subheader("🧩 Recomendações por carteira (SKUs que a carteira compra e este cliente não compra)")

    df_carteira = df_fat_filtrado.copy()

    df_carteira_periodo = df_carteira.copy()
    if periodo != "Tudo":
        meses = {"Últimos 3 meses": 3, "Últimos 6 meses": 6, "Últimos 12 meses": 12}[periodo]
        dt_min_carteira = df_carteira_periodo[col_data].max() - pd.DateOffset(months=meses)
        df_carteira_periodo = df_carteira_periodo[df_carteira_periodo[col_data] >= dt_min_carteira].copy()

    if df_carteira_periodo.empty:
        st.info("Sem dados na carteira (com os filtros/período atuais) para gerar recomendações.")
    else:
        skus_cliente = set(df_cli[col_sku].dropna().astype(str).str.strip().tolist())

        df_carteira_sem_cliente = df_carteira_periodo[df_carteira_periodo[col_cliente] != str(cli_sel)].copy()

        if df_carteira_sem_cliente.empty:
            st.info("Poucos dados na carteira para comparar (apenas este cliente no recorte atual).")
        else:
            carteira_sku = (
                df_carteira_sem_cliente.groupby(col_sku)
                .agg(
                    Volume_Carteira=(col_qtd, "sum"),
                    Pedidos_Carteira=(col_pedido, "nunique"),
                    Clientes_Carteira=(col_cliente, "nunique"),
                )
                .reset_index()
                .sort_values("Volume_Carteira", ascending=False)
            )

            carteira_sku["__sku_str"] = carteira_sku[col_sku].astype(str).str.strip()
            recs = carteira_sku[~carteira_sku["__sku_str"].isin(skus_cliente)].copy()
            recs = recs.drop(columns=["__sku_str"])

            if recs.empty:
                st.success("✅ Pelo recorte atual, não encontrei SKUs relevantes da carteira que este cliente ainda não compra.")
            else:
                vol_cart_total = recs["Volume_Carteira"].sum()
                if vol_cart_total > 0:
                    recs["% Volume na carteira"] = (recs["Volume_Carteira"] / vol_cart_total)
                else:
                    recs["% Volume na carteira"] = 0.0

                if col_hier and col_hier in df_carteira_sem_cliente.columns:
                    sku_hier = (
                        df_carteira_sem_cliente[[col_sku, col_hier]]
                        .dropna()
                        .astype(str)
                        .groupby(col_sku)[col_hier]
                        .agg(lambda x: x.value_counts().index[0] if len(x) else "")
                        .reset_index()
                        .rename(columns={col_hier: "Hierarquia (mais comum)"})
                    )
                    recs = recs.merge(sku_hier, on=col_sku, how="left")

                min_clientes = st.number_input(
                    "Recomendação: mínimo de clientes da carteira comprando o SKU (evita ruído):",
                    min_value=1,
                    value=2,
                    step=1,
                    key="min_clientes_recs",
                )

                recs = recs[recs["Clientes_Carteira"] >= int(min_clientes)].copy()
                recs = recs.sort_values("Volume_Carteira", ascending=False).head(25)

                if recs.empty:
                    st.info("Sem recomendações após o filtro mínimo de clientes.")
                else:
                    # ✅ aqui foi o ajuste: "Hierarquia (mais comum)" antes do SKU (N° artigo)
                    cols_show = []
                    if "Hierarquia (mais comum)" in recs.columns:
                        cols_show.append("Hierarquia (mais comum)")
                    cols_show.append(col_sku)
                    cols_show += ["Volume_Carteira", "% Volume na carteira", "Clientes_Carteira", "Pedidos_Carteira"]

                    recs_show = recs.copy()
                    recs_show["% Volume na carteira"] = (
                        pd.to_numeric(recs_show["% Volume na carteira"], errors="coerce")
                        .fillna(0)
                        .mul(100)
                        .round(1)
                        .astype(str)
                        .add("%")
                    )

                    st.dataframe(
                        recs_show[cols_show],
                        use_container_width=True,
                        hide_index=True,
                    )



    # =========================================================
    # ✅ ADIÇÃO 3: RANKING DO CLIENTE NA CARTEIRA (por Volume)
    # =========================================================
    st.markdown("---")
    st.subheader("🏆 Ranking do cliente na carteira (por Volume)")

    df_rank_base = df_fat_filtrado.copy()

    df_rank_periodo = df_rank_base.copy()
    if periodo != "Tudo":
        meses = {"Últimos 3 meses": 3, "Últimos 6 meses": 6, "Últimos 12 meses": 12}[periodo]
        dt_min_rank = df_rank_periodo[col_data].max() - pd.DateOffset(months=meses)
        df_rank_periodo = df_rank_periodo[df_rank_periodo[col_data] >= dt_min_rank].copy()

    if df_rank_periodo.empty:
        st.info("Sem dados suficientes para ranking no período/filtros atuais.")
    else:
        rank_cli = (
            df_rank_periodo.groupby(col_cliente)
            .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"))
            .reset_index()
            .sort_values("Volume", ascending=False)
            .reset_index(drop=True)
        )
        rank_cli["Posição"] = rank_cli.index + 1

        vol_total_carteira = float(rank_cli["Volume"].sum()) if not rank_cli.empty else 0.0

        row_me = rank_cli[rank_cli[col_cliente].astype(str) == str(cli_sel)].head(1)

        if row_me.empty:
            st.info("Não consegui localizar este cliente no ranking da carteira (no recorte atual).")
        else:
            pos = int(row_me["Posição"].iloc[0])
            vol_me = float(row_me["Volume"].iloc[0])
            ped_me = int(row_me["Pedidos"].iloc[0])
            total_cli = int(rank_cli.shape[0])

            part = (vol_me / vol_total_carteira * 100) if vol_total_carteira > 0 else 0.0

            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Posição", f"{pos} / {total_cli}")
            r2.metric("Volume do cliente", f"{vol_me:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
            r3.metric("Participação no volume", f"{part:.1f}%")
            r4.metric("Pedidos no período", ped_me)

            st.caption("Top 15 clientes da carteira (por volume):")
            st.dataframe(
                rank_cli[[col_cliente, "Posição", "Volume", "Pedidos"]].head(15),
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # ✅ ADIÇÃO FINAL: COMPARATIVO (Cliente/Período X vs Cliente/Período Y) POR DATA
    # - Não altera nada acima: só acrescenta no final
    # - Compara por intervalo de datas (início/fim) do FATURADO
    # - Mostra Volume total + (por mês) + Hierarquias + SKUs + quantidades
    # =========================================================
    st.markdown("---")
    st.subheader("🆚 Comparativo por período")

    # Base de comparação respeita os filtros do topo (Estado/Analista/Supervisor/Vendedor)
    df_comp_base = df_fat_filtrado.copy()

    lista_clientes_comp = sorted(
        [x for x in df_comp_base[col_cliente].dropna().unique().tolist() if str(x).strip() != ""]
    )

    if not lista_clientes_comp:
        st.info("Sem clientes disponíveis para comparativo (no recorte atual).")
    else:
        comp1, comp2 = st.columns(2)

        # referência de datas disponíveis no recorte atual
        dt_min_base = df_comp_base[col_data].min()
        dt_max_base = df_comp_base[col_data].max()

        if pd.isna(dt_min_base) or pd.isna(dt_max_base):
            st.info("Sem datas válidas no FATURADO (no recorte atual) para montar o comparativo.")
        else:
            dt_min_base_d = dt_min_base.date()
            dt_max_base_d = dt_max_base.date()

            with comp1:
                st.markdown("#### 📌 Lado A")
                cli_A = st.selectbox("Cliente A", lista_clientes_comp, index=0, key="comp_cli_A")

                # por padrão: últimos 3 meses dentro do recorte atual
                dtA_ini_default = max(dt_min_base_d, (dt_max_base - pd.DateOffset(months=3)).date())
                dtA_fim_default = dt_max_base_d

                dtA_ini, dtA_fim = st.date_input(
                    "Período A (início / fim)",
                    value=(dtA_ini_default, dtA_fim_default),
                    min_value=dt_min_base_d,
                    max_value=dt_max_base_d,
                    key="comp_dt_A",
                )

            with comp2:
                st.markdown("#### 📌 Lado B")
                # default: mesmo cliente selecionado na tela (se existir), senão o primeiro
                idx_default = 0
                try:
                    idx_default = lista_clientes_comp.index(str(cli_sel))
                except Exception:
                    idx_default = 0

                cli_B = st.selectbox("Cliente B", lista_clientes_comp, index=idx_default, key="comp_cli_B")

                # por padrão: últimos 6 meses dentro do recorte atual
                dtB_ini_default = max(dt_min_base_d, (dt_max_base - pd.DateOffset(months=6)).date())
                dtB_fim_default = dt_max_base_d

                dtB_ini, dtB_fim = st.date_input(
                    "Período B (início / fim)",
                    value=(dtB_ini_default, dtB_fim_default),
                    min_value=dt_min_base_d,
                    max_value=dt_max_base_d,
                    key="comp_dt_B",
                )

            # garante ordem caso o usuário selecione invertido
            if dtA_ini > dtA_fim:
                dtA_ini, dtA_fim = dtA_fim, dtA_ini
            if dtB_ini > dtB_fim:
                dtB_ini, dtB_fim = dtB_fim, dtB_ini

            def filtrar_por_datas(df_in, dt_ini, dt_fim, col_dt):
                if df_in is None or df_in.empty:
                    return df_in
                # converte para Timestamp e inclui o dia final inteiro
                ini_ts = pd.to_datetime(dt_ini)
                fim_ts = pd.to_datetime(dt_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                return df_in[(df_in[col_dt] >= ini_ts) & (df_in[col_dt] <= fim_ts)].copy()

            # df do cliente A/B (no recorte do topo) + filtro por datas
            df_A_full = df_comp_base[df_comp_base[col_cliente].astype(str) == str(cli_A)].copy()
            df_B_full = df_comp_base[df_comp_base[col_cliente].astype(str) == str(cli_B)].copy()

            df_A = filtrar_por_datas(df_A_full, dtA_ini, dtA_fim, col_data)
            df_B = filtrar_por_datas(df_B_full, dtB_ini, dtB_fim, col_data)

            def resumo_comp(df_in):
                # estrutura fixa (pra não quebrar UI)
                out = {
                    "volume": 0.0,
                    "pedidos": 0,
                    "mes": pd.DataFrame(columns=["Mês", "Volume", "Pedidos"]),
                    "hier": pd.DataFrame(columns=["Hierarquia", "Volume", "Pedidos"]),
                    "sku": pd.DataFrame(columns=["SKU", "Volume", "Pedidos"]),
                }

                if df_in is None or df_in.empty:
                    return out

                out["volume"] = float(df_in[col_qtd].sum())
                out["pedidos"] = int(df_in[col_pedido].nunique())

                # compras por mês (YYYY-MM)
                df_mes = (
                    df_in.groupby(pd.Grouper(key=col_data, freq="M"))
                    .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"))
                    .reset_index()
                )
                if not df_mes.empty:
                    df_mes["Mês"] = df_mes[col_data].dt.strftime("%Y-%m")
                    df_mes = df_mes[["Mês", "Volume", "Pedidos"]].sort_values("Mês")
                    out["mes"] = df_mes

                # hierarquias (todas) com volume/pedidos
                if col_hier and col_hier in df_in.columns:
                    hier_df = (
                        df_in.groupby(col_hier)
                        .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"))
                        .reset_index()
                        .rename(columns={col_hier: "Hierarquia"})
                        .sort_values("Volume", ascending=False)
                    )
                    out["hier"] = hier_df

                # skus (todos) com volume/pedidos
                sku_df = (
                    df_in.groupby(col_sku)
                    .agg(Volume=(col_qtd, "sum"), Pedidos=(col_pedido, "nunique"))
                    .reset_index()
                    .rename(columns={col_sku: "SKU"})
                    .sort_values("Volume", ascending=False)
                )
                out["sku"] = sku_df

                return out

            resA = resumo_comp(df_A)
            resB = resumo_comp(df_B)

            # cards: volume total + pedidos
            ca1, ca2, cb1, cb2 = st.columns(4)
            ca1.metric(
                "Volume total A",
                f"{resA['volume']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
            )
            ca2.metric("Pedidos A", resA["pedidos"])
            cb1.metric(
                "Volume total B",
                f"{resB['volume']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
            )
            cb2.metric("Pedidos B", resB["pedidos"])

            # blocos lado a lado
            t1, t2 = st.columns(2)

            with t1:
                st.markdown(
                    f"##### 📅 Compras por mês (A) — {dtA_ini.strftime('%d/%m/%Y')} a {dtA_fim.strftime('%d/%m/%Y')}"
                )
                if resA["mes"].empty:
                    st.info("Sem dados por mês (A).")
                else:
                    st.dataframe(resA["mes"], use_container_width=True, hide_index=True)

                st.markdown("##### 🏷️ Hierarquias faturadas (A)")
                if resA["hier"].empty:
                    st.info("Sem hierarquias (A).")
                else:
                    st.dataframe(resA["hier"], use_container_width=True, hide_index=True)

                st.markdown("##### 📦 SKUs faturados (A)")
                if resA["sku"].empty:
                    st.info("Sem SKUs (A).")
                else:
                    st.dataframe(resA["sku"], use_container_width=True, hide_index=True)

            with t2:
                st.markdown(
                    f"##### 📅 Compras por mês (B) — {dtB_ini.strftime('%d/%m/%Y')} a {dtB_fim.strftime('%d/%m/%Y')}"
                )
                if resB["mes"].empty:
                    st.info("Sem dados por mês (B).")
                else:
                    st.dataframe(resB["mes"], use_container_width=True, hide_index=True)

                st.markdown("##### 🏷️ Hierarquias faturadas (B)")
                if resB["hier"].empty:
                    st.info("Sem hierarquias (B).")
                else:
                    st.dataframe(resB["hier"], use_container_width=True, hide_index=True)

                st.markdown("##### 📦 SKUs faturados (B)")
                if resB["sku"].empty:
                    st.info("Sem SKUs (B).")
                else:
                    st.dataframe(resB["sku"], use_container_width=True, hide_index=True)

            # (opcional) comparação SKU a SKU (diferença)
            st.markdown("##### 📊 Comparação SKU a SKU — A vs B (Volume)")
            skuA = (
                resA["sku"][["SKU", "Volume"]].rename(columns={"Volume": "Volume_A"})
                if not resA["sku"].empty
                else pd.DataFrame(columns=["SKU", "Volume_A"])
            )
            skuB = (
                resB["sku"][["SKU", "Volume"]].rename(columns={"Volume": "Volume_B"})
                if not resB["sku"].empty
                else pd.DataFrame(columns=["SKU", "Volume_B"])
            )

            df_diff = skuA.merge(skuB, on="SKU", how="outer")
            df_diff["Volume_A"] = pd.to_numeric(df_diff["Volume_A"], errors="coerce").fillna(0)
            df_diff["Volume_B"] = pd.to_numeric(df_diff["Volume_B"], errors="coerce").fillna(0)
            df_diff["Diferença (A-B)"] = df_diff["Volume_A"] - df_diff["Volume_B"]
            df_diff = df_diff.sort_values("Diferença (A-B)", ascending=False)

            # filtro pra não ficar gigante (mas você pode deixar "Tudo" se quiser)
            top_n_diff = st.number_input(
                "Mostrar quantos SKUs na comparação (ordenado por Diferença A-B):",
                min_value=5,
                value=30,
                step=5,
                key="comp_topn_diff",
            )
            if df_diff.empty:
                st.info("Sem dados suficientes para comparar SKUs.")
            else:
                st.dataframe(df_diff.head(int(top_n_diff)), use_container_width=True, hide_index=True)



                    
# --- PÁGINA: DASHBOARD ---
elif menu == "📊 Dashboard de Controle":
    # Cabeçalho com Botão de Atualizar
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("📊 Resumo de Engajamento por Vendedor")
    
    with col_btn:
        st.write("") 
        if st.button("🔄 Atualizar Tudo"):
            st.cache_data.clear()
            st.success("Dados Atualizados!")
            time.sleep(1)
            st.rerun()
    
    if df_base is not None and df_agenda is not None:
        # --- MAPEAMENTO DINÂMICO DE COLUNAS DA BASE ---
        col_ana_base = next((c for c in df_base.columns if c.upper() == 'ANALISTA'), 'ANALISTA')
        col_sup_base = next((c for c in df_base.columns if c.upper() == 'SUPERVISOR'), 'SUPERVISOR')
        col_vend_base = next((c for c in df_base.columns if c.upper() == 'VENDEDOR'), 'VENDEDOR')
        col_cliente_base = next((c for c in df_base.columns if c.upper() == 'CLIENTE'), 'Cliente')
        col_nome_base = next((c for c in df_base.columns if c.upper() == 'NOME 1'), 'Nome 1')

        st.subheader("Filtros de Visualização")
        f_c1, f_c2, f_c3 = st.columns(3)
        df_base_filtrada = df_base.copy()
        
        with f_c1:
            if is_admin or is_diretoria:
                lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if pd.notnull(a) and str(a).strip() and str(a).lower() != 'nan'])
                ana_sel_dash = st.selectbox("Escolher Analista:", ["Todos"] + lista_analistas, key="ana_dash")
                if ana_sel_dash != "Todos":
                    df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base] == ana_sel_dash]
            else: 
                ana_sel_dash = user_atual
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_ana_base].astype(str).str.upper() == user_atual]

        with f_c2:
            lista_sups_dash = sorted([str(s) for s in df_base_filtrada[col_sup_base].unique() if pd.notnull(s) and str(s).strip() and str(s).lower() != 'nan'])
            sup_sel_dash = st.selectbox("Escolher Supervisor:", ["Todos"] + lista_sups_dash, key="sup_dash")
            if sup_sel_dash != "Todos":
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_sup_base] == sup_sel_dash]

        with f_c3:
            lista_vends_dash = sorted([str(v) for v in df_base_filtrada[col_vend_base].unique() if pd.notnull(v) and str(v).strip() and str(v).lower() != 'nan'])
            vend_sel_dash = st.selectbox("Escolher Vendedor:", ["Todos"] + lista_vends_dash, key="vend_dash")
            if vend_sel_dash != "Todos":
                df_base_filtrada = df_base_filtrada[df_base_filtrada[col_vend_base] == vend_sel_dash]

        # --- PROCESSAMENTO DE AGENDAMENTOS ---
        df_reg_agenda = df_agenda[['CÓDIGO CLIENTE', 'REGISTRO']].copy().drop_duplicates(subset='CÓDIGO CLIENTE', keep='last')
        df_base_detalhe = pd.merge(df_base_filtrada, df_reg_agenda, left_on=col_cliente_base, right_on='CÓDIGO CLIENTE', how='left')
        df_base_detalhe['STATUS AGENDAMENTO'] = df_base_detalhe['REGISTRO'].apply(lambda x: 'AGENDADO' if pd.notnull(x) and str(x).strip() != "" and str(x) != "-" else 'PENDENTE')
        df_base_detalhe['REGISTRO'] = df_base_detalhe['REGISTRO'].fillna("-")

        # --- TABELA RESUMO ---
        resumo_base = df_base_filtrada.groupby([col_ana_base, col_sup_base, col_vend_base]).size().reset_index(name='Total na Base')
        agenda_no_filtro = df_agenda[df_agenda['CÓDIGO CLIENTE'].isin(df_base_filtrada[col_cliente_base])]
        resumo_agenda = agenda_no_filtro.groupby('VENDEDOR')['CÓDIGO CLIENTE'].nunique().reset_index(name='Já Agendados')
        df_dash = pd.merge(resumo_base, resumo_agenda, left_on=col_vend_base, right_on='VENDEDOR', how='left').fillna(0)
        df_dash['Já Agendados'] = df_dash['Já Agendados'].astype(int)
        df_dash['Faltando'] = df_dash['Total na Base'] - df_dash['Já Agendados']
        df_dash['% Conclusão'] = df_dash.apply(lambda r: f"{(r['Já Agendados']/r['Total na Base']*100):.1f}%" if r['Total na Base'] > 0 else "0.0%", axis=1)
        st.dataframe(df_dash.drop(columns=['VENDEDOR_y'], errors='ignore'), use_container_width=True, hide_index=True)

        # --- CONVERSÃO E GAPS COM AGRUPAMENTO EXATO ---
        st.markdown("---")
        st.subheader("🎯 Conversão e Gap de Mix (SKUS)")
        
        try:
            df_fat = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
            df_skus_ref = conn.read(spreadsheet=url_planilha, worksheet="SKUS")
            df_fat.columns = [str(c).strip() for c in df_fat.columns]
            df_skus_ref.columns = [str(c).strip() for c in df_skus_ref.columns]

            # --- MAPEAMENTO INTELIGENTE (CORREÇÃO DO ERRO 'DESCRIÇÃO') ---
            col_h_ref = next((c for c in df_skus_ref.columns if "HIERARQUIA" in c.upper()), "Hierarquia de produtos")
            col_sku_ref = next((c for c in df_skus_ref.columns if any(x in c.upper() for x in ["SKU", "ARTIGO"])), "SKU")
            # Busca dinâmica: Aceita DESCRIÇÃO, DESCRICAO, DESC. ou TEXTO
            col_desc_ref = next((c for c in df_skus_ref.columns if any(x in c.upper() for x in ["DESC", "TEXTO", "NOME"])), col_sku_ref)

            def agrupar_hierarquia(nome):
                n = str(nome).upper().strip()
                if n in ["DESCARTAVEIS COPOS", "DESCARTAVEIS POTES", "DESCARTAVEIS PRATOS", "DESCARTAVEIS TAMPAS"]: return "DESCARTAVEIS"
                if n in ["MILHO", "MILHO CANJICA", "MILHO CANJIQUINHA", "MILHO CREME MILHO", "MILHO FUBA"]: return "MILHO"
                if n in ["MOLHOS ALHO", "MOLHOS ALHO PICANTE"]: return "MOLHOS ALHO"
                if n in ["PIMENTA CONSERVA", "PIMENTA CONSERVA BIQUINHO", "PIMENTA CONSERVA PASTA"]: return "PIMENTA CONSERVA"
                return n

            df_skus_ref['H_AGRUPADA'] = df_skus_ref[col_h_ref].apply(agrupar_hierarquia)
            total_h_alvo = df_skus_ref['H_AGRUPADA'].nunique()
            total_s_alvo = df_skus_ref[col_sku_ref].nunique()

            col_cod_fat = df_fat.columns[10] 
            col_h_fat = next((c for c in df_fat.columns if "HIERARQUIA" in c.upper()), col_h_ref)
            col_s_fat = next((c for c in df_fat.columns if any(x in c.upper() for x in ["ARTIGO", "SKU"])), col_sku_ref)
            
            df_fat['H_AGRUPADA'] = df_fat[col_h_fat].apply(agrupar_hierarquia)
            def limpar_cod(val): return str(val).split('.')[0].strip() if pd.notnull(val) else ""
            df_fat['Cod_Limpo'] = df_fat[col_cod_fat].apply(limpar_cod)
            
            df_fat_resumo = df_fat.groupby('Cod_Limpo').agg({
                'OrdCliente': 'nunique', 'Data fat.': 'max', 'H_AGRUPADA': 'nunique', col_s_fat: 'nunique'
            }).reset_index()
            df_fat_resumo.columns = ['Cod_Cliente', 'Qtd_Pedidos', 'Ultima_Data_Fat', 'H_Vendidas', 'S_Vendidos']

            df_base_detalhe['Cliente_Limpo'] = df_base_detalhe[col_cliente_base].apply(limpar_cod)
            df_comp = pd.merge(df_base_detalhe, df_fat_resumo, left_on='Cliente_Limpo', right_on='Cod_Cliente', how='left').fillna(0)
            df_agendados_ativos = df_comp[df_comp['STATUS AGENDAMENTO'] == 'AGENDADO'].copy()
            
            # Cards de Métricas
            t_ag, v_ag = len(df_agendados_ativos), len(df_agendados_ativos[df_agendados_ativos['Qtd_Pedidos'] > 0])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Clientes Agendados", t_ag)
            c2.metric("Agendados com Venda", v_ag)
            c3.metric("Taxa de Conversão", f"{(v_ag/t_ag*100 if t_ag > 0 else 0):.1f}%")
            c4.metric("Total de Pedidos", int(df_agendados_ativos['Qtd_Pedidos'].sum()))

            with st.expander("🔍 Detalhes de GAPs e Exportação", expanded=True):
                df_conv = df_agendados_ativos[df_agendados_ativos['Qtd_Pedidos'] > 0].copy()
                df_conv['GAP FAMÍLIA'] = (total_h_alvo - df_conv['H_Vendidas']).clip(lower=0).astype(int)
                df_conv['GAP SKU'] = (total_s_alvo - df_conv['S_Vendidos']).clip(lower=0).astype(int)
                df_conv['ÚLT. FAT.'] = pd.to_datetime(df_conv['Ultima_Data_Fat'], errors='coerce').dt.strftime('%d/%m/%Y').fillna("-")
                
                df_view = df_conv[[col_cliente_base, col_nome_base, 'H_Vendidas', 'GAP FAMÍLIA', 'S_Vendidos', 'GAP SKU', 'ÚLT. FAT.']].copy()
                df_view.columns = ['CÓDIGO', 'NOME', 'FAM. ATUAIS', 'GAP FAM', 'SKU ATUAIS', 'GAP SKU', 'ÚLT. FAT.']
                df_view.insert(0, "Selecionar", False)

                edited_df = st.data_editor(df_view, use_container_width=True, hide_index=True, key="editor_gap")
                sel_cods = [str(x) for x in edited_df[edited_df['Selecionar'] == True]['CÓDIGO'].tolist()]

                # ... (dentro do if sel_cods:)
                if sel_cods:
                    output_ex = io.BytesIO()
                    
                    # Lista para consolidar os dados de todos os clientes selecionados
                    dados_consolidados = []

                    for cod in sel_cods:
                        c_l = limpar_cod(cod)
                        # Localiza info do cliente na base filtrada
                        info_cli = df_base_detalhe[df_base_detalhe['Cliente_Limpo'] == c_l].iloc[0]
                        
                        # Identifica o que ele já comprou
                        ja_comprou_cods = df_fat[df_fat['Cod_Limpo'] == c_l][col_s_fat].unique()
                        
                        # Itera sobre a referência total de SKUs para classificar cada um
                        for _, row_ref in df_skus_ref.iterrows():
                            sku_id = row_ref[col_sku_ref]
                            status = "COMPRADO" if sku_id in ja_comprou_cods else "FALTANTE"
                            
                            dados_consolidados.append({
                                "ANALISTA": info_cli[col_ana_base],
                                "SUPERVISOR": info_cli[col_sup_base],
                                "VENDEDOR": info_cli[col_vend_base],
                                "CÓD. CLIENTE": cod,
                                "CLIENTE": info_cli[col_nome_base],
                                "HIERARQUIA": row_ref['H_AGRUPADA'],
                                "SKU": sku_id,
                                "DESCRIÇÃO": row_ref[col_desc_ref],
                                "STATUS": status
                            })

                    # Cria o DataFrame final para exportação
                    df_export = pd.DataFrame(dados_consolidados)

                    # Exportação para Excel
                    with pd.ExcelWriter(output_ex, engine='xlsxwriter') as writer:
                        df_export.to_excel(writer, sheet_name='Relatorio_Mix', index=False)
                        # Ajuste automático de colunas
                        worksheet = writer.sheets['Relatorio_Mix']
                        for i, col in enumerate(df_export.columns):
                            column_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 2
                            worksheet.set_column(i, i, column_len)

                    # --- GERAÇÃO DO PDF (Mantida como sugestão de compra rápido) ---
                    from fpdf import FPDF
                    pdf = FPDF()
                    for cod in sel_cods:
                        c_l = limpar_cod(cod)
                        info_cli = df_base_detalhe[df_base_detalhe['Cliente_Limpo'] == c_l].iloc[0]
                        pdf.add_page()
                        pdf.set_font("Arial", 'B', 12)
                        pdf.cell(0, 10, f"Sugestão de Mix - {info_cli[col_nome_base]} ({cod})", ln=True)
                        pdf.set_font("Arial", '', 8)
                        # Mostra apenas os faltantes no PDF para o vendedor focar no Gap
                        ja_comprou = df_fat[df_fat['Cod_Limpo'] == c_l][col_s_fat].unique()
                        faltantes = df_skus_ref[~df_skus_ref[col_sku_ref].isin(ja_comprou)]
                        for _, r in faltantes.head(50).iterrows():
                            pdf.cell(0, 6, f"[GAP] {r['H_AGRUPADA']} - {r[col_sku_ref]} - {str(r[col_desc_ref])[:45]}", ln=True)

                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        st.download_button("📊 Baixar Excel Consolidado", output_ex.getvalue(), "Relatorio_Mix_Completo.xlsx", "application/vnd.ms-excel")
                    with c_btn2:
                        st.download_button("📄 Baixar PDFs de Sugestão", pdf.output(dest='S').encode('latin-1', 'replace'), "Sugestao_Mix_Clientes.pdf", "application/pdf")

                st.info(f"📊 Meta do Mix: {total_h_alvo} Famílias e {total_s_alvo} SKUs únicos.")

        except Exception as e:
            st.error(f"Erro no processamento de SKUS: {e}")

       # --- NOVO BLOCO: RANKING DE ENGAJAMENTO (ACIMA DO MAPA) ---
        st.markdown("---")
        st.subheader("🏆 Ranking de Engajamento por Vendedor")
        
        # 1. Preparar dados para o Ranking
        if not df_agenda.empty:
            # Agrupar agendamentos realizados (Status = Realizado)
            ranking_realizado = df_agenda[df_agenda['STATUS'] == "Realizado"].groupby('VENDEDOR').size().reset_index(name='Realizados')
            
            # Agrupar total de agendamentos feitos
            ranking_total = df_agenda.groupby('VENDEDOR').size().reset_index(name='Total Agendado')
            
            # Unir as métricas
            df_ranking = pd.merge(ranking_total, ranking_realizado, on='VENDEDOR', how='left').fillna(0)
            df_ranking['Realizados'] = df_ranking['Realizados'].astype(int)
            
            # Calcular % de Cumprimento
            df_ranking['% Cumprimento'] = (df_ranking['Realizados'] / df_ranking['Total Agendado'] * 100).round(1)
            
            # Ordenar (quem realizou mais ganha)
            df_ranking = df_ranking.sort_values(by=['Realizados', '% Cumprimento'], ascending=False).reset_index(drop=True)
            
            # 2. Criar a coluna de Posição com Troféus
            def definir_posicao(idx):
                if idx == 0: return "🥇 1º"
                elif idx == 1: return "🥈 2º"
                elif idx == 2: return "🥉 3º"
                else: return f"{idx + 1}º"

            df_ranking.insert(0, "POS", [definir_posicao(i) for i in range(len(df_ranking))])
            
            # Exibir a Tabela de Ranking
            st.dataframe(
                df_ranking, 
                use_container_width=True, 
                hide_index=True, # Escondemos o índice original (0,1,2...)
                column_config={
                    "POS": "Posição",
                    "VENDEDOR": "Vendedor",
                    "Total Agendado": st.column_config.NumberColumn("Agendamentos"),
                    "Realizados": st.column_config.NumberColumn("Visitas Realizadas"),
                    "% Cumprimento": st.column_config.ProgressColumn("Taxa de Sucesso", format="%.1f%%", min_value=0, max_value=100)
                }
            )
        else:
            st.info("Aguardando dados de agendamento para gerar o ranking.")

# Seria útil eu gerar um resumo de quantos clientes faltam agendar por cidade agora?
# --- PÁGINA: NOVO AGENDAMENTO ---
elif menu == "📋 Novo Agendamento":
    st.header("📋 Agendar Visita")
    
    if df_base is not None:
        # Mapeamento das colunas da BASE
        col_ana_base = 'ANALISTA'
        col_sup_base = 'SUPERVISOR'
        col_ven_base = 'VENDEDOR' 

        # Inicialização de variáveis para evitar NameError
        ven_sel = "Selecione..."
        bloqueado = False

        # --- LÓGICA DE FILTROS CASCATA ---
        if is_admin or is_diretoria:
            lista_analistas = sorted([str(a) for a in df_base[col_ana_base].unique() if str(a).strip() and str(a).lower() != 'nan'])
            ana_sel = st.selectbox("1. Filtrar por Analista:", ["Todos"] + lista_analistas)
            df_sup_f = df_base if ana_sel == "Todos" else df_base[df_base[col_ana_base] == ana_sel]
            lista_sups = sorted([str(s) for s in df_sup_f[col_sup_base].unique() if str(s).strip() and str(s).lower() != 'nan'])
            sup_sel = st.selectbox("2. Filtrar por Supervisor:", ["Todos"] + lista_sups)
            df_ven_f = df_sup_f if sup_sel == "Todos" else df_sup_f[df_sup_f[col_sup_base] == sup_sel]
            vends = sorted([str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()])
            ven_sel = st.selectbox("3. Selecione o Vendedor:", ["Selecione..."] + vends)

        elif is_analista:
            df_ana_f = df_base[df_base[col_ana_base].str.upper() == user_atual]
            lista_sups = sorted([str(s) for s in df_ana_f[col_sup_base].unique() if str(s).strip()])
            sup_sel = st.selectbox("1. Filtrar seu Supervisor:", ["Todos"] + lista_sups)
            df_ven_f = df_ana_f if sup_sel == "Todos" else df_ana_f[df_ana_f[col_sup_base] == sup_sel]
            vends = sorted([str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()])
            ven_sel = st.selectbox("2. Selecione o Vendedor:", ["Selecione..."] + vends)

        elif any(df_base[col_sup_base].str.upper() == user_atual):
            df_ven_f = df_base[df_base[col_sup_base].str.upper() == user_atual]
            vends_equipe = [str(v) for v in df_ven_f[col_ven_base].unique() if str(v).strip()]
            lista_final_vends = sorted(list(set(vends_equipe + [user_atual])))
            ven_sel = st.selectbox("Selecione para quem agendar:", ["Selecione..."] + lista_final_vends)
        
        else:
            ven_sel = user_atual
            st.info(f"Agendando para sua própria base: {user_atual}")

        # --- VERIFICAÇÃO DE PUNIÇÃO (TRAVA) ---
        if ven_sel != "Selecione...":
            hoje_dt = datetime.now(fuso_br).date()
            df_verif = df_agenda[df_agenda['VENDEDOR'].str.upper() == ven_sel.upper()].copy()
            
            if not df_verif.empty:
                df_verif['DT_OBJ'] = pd.to_datetime(df_verif['DATA'], format='%d/%m/%Y', errors='coerce').dt.date
                pendencias_passadas = df_verif[
                    (df_verif['DT_OBJ'] < hoje_dt) & 
                    (df_verif['STATUS'] == "Agendado")
                ]

                if not pendencias_passadas.empty:
                    bloqueado = True
                    st.error(f"⚠️ **AGENDAMENTO BLOQUEADO PARA {ven_sel}**")
                    st.warning(f"O colaborador possui {len(pendencias_passadas)} visitas pendentes.")
                    with st.expander("Ver visitas pendentes"):
                        st.table(pendencias_passadas[['DATA', 'CLIENTE', 'STATUS']].sort_values(by='DATA'))

        # --- PROCESSAMENTO DO AGENDAMENTO ---
        if ven_sel != "Selecione..." and not bloqueado:
            clientes_f = df_base[df_base[col_ven_base] == ven_sel].copy()
            
            if 'VENDEDOR' not in df_agenda.columns: 
                df_agenda['VENDEDOR'] = ""

            # Normalização para comparação
            df_agenda['CÓDIGO CLIENTE'] = df_agenda['CÓDIGO CLIENTE'].astype(str)
            clientes_f['Cliente'] = clientes_f['Cliente'].astype(str)

            # Consideramos agendados os que estão Planejados, Realizados ou aguardando Aprovação (Pendente)
            codigos_agendados = df_agenda[
                (df_agenda['VENDEDOR'] == ven_sel) & 
                (df_agenda['STATUS'].isin(['Agendado', 'Realizado', 'Pendente']))
            ]['CÓDIGO CLIENTE'].unique()
            
            clientes_pendentes_ag = clientes_f[~clientes_f['Cliente'].isin(codigos_agendados)]
            
            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            n_total, n_agendados = len(clientes_f), len(codigos_agendados)
            m1.metric("Clientes na Base", n_total)
            m2.metric("Já Agendados/Pendentes", n_agendados)
            m3.metric("Faltando Agendar", len(clientes_pendentes_ag))
            m4.metric("% Adesão", f"{(n_agendados/n_total*100 if n_total>0 else 0):.1f}%")
            
            try:
                amostra = clientes_f.iloc[0]
                analista_vinc = str(amostra[col_ana_base]).upper()
                supervisor_vinc = str(amostra[col_sup_base]).upper()
            except:
                analista_vinc = "N/I"
                supervisor_vinc = "N/I"

            lista_c = sorted(clientes_pendentes_ag.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            
            if not lista_c:
                st.success(f"✅ Todos os clientes de {ven_sel} já foram processados!")
            else:
                # ✅ AQUI: agora pode selecionar MAIS DE 1 cliente
                clientes_sel = st.multiselect("Selecione o(s) Cliente(s):", lista_c)

                if clientes_sel:
                    qtd_visitas = st.number_input("Quantidade de visitas (Máx 4):", min_value=1, max_value=4, value=1)
                    
                    with st.form("form_novo_v", clear_on_submit=True):
                        cols_datas = st.columns(qtd_visitas)
                        hoje_dt = datetime.now(fuso_br).date()
                        datas_sel = [
                            cols_datas[i].date_input(
                                f"Data {i+1}:",
                                value=hoje_dt,
                                min_value=hoje_dt,
                                key=f"d_{i}"
                            )
                            for i in range(qtd_visitas)
                        ]
                        
                        if st.form_submit_button("💾 ENVIAR PARA APROVAÇÃO"):
                            agora = datetime.now(fuso_br)
                            novas_linhas = []

                            for j, cliente_item in enumerate(clientes_sel):
                                cod_c, nom_c = cliente_item.split(" - ", 1)

                                for i, dt in enumerate(datas_sel):
                                    nid = agora.strftime("%Y%m%d%H%M%S") + f"{j}{i}"
                                    novas_linhas.append({
                                        "ID": nid, 
                                        "REGISTRO": agora.strftime("%d/%m/%Y %H:%M"), 
                                        "DATA": dt.strftime("%d/%m/%Y"), 
                                        "ANALISTA": analista_vinc, 
                                        "SUPERVISOR": supervisor_vinc, 
                                        "VENDEDOR": ven_sel,
                                        "CÓDIGO CLIENTE": str(cod_c), 
                                        "CLIENTE": nom_c, 
                                        "JUSTIFICATIVA": "-", 
                                        "STATUS": "Pendente",  # <--- AQUI ESTÁ A MUDANÇA PARA O WORKFLOW
                                        "AGENDADO POR": user_atual 
                                    })
                            
                            df_antigo = df_agenda.drop(columns=['LINHA'], errors='ignore').copy()
                            df_novo = pd.DataFrame(novas_linhas)
                            
                            # Une e remove duplicados
                            df_final_a = pd.concat([df_antigo, df_novo], ignore_index=True)
                            df_final_a = df_final_a.drop_duplicates(subset=['VENDEDOR', 'CÓDIGO CLIENTE', 'DATA'], keep='first')
                            
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_final_a)
                            st.cache_data.clear()
                            st.info("🔔 Agendamento enviado! Aguardando aprovação na tela de Aprovações.")
                            time.sleep(2)
                            st.rerun()


      



# --- PÁGINA: VER/EDITAR ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
# --- PÁGINA: VER/EDITAR MINHA AGENDA ---
elif menu == "🔍 Ver/Editar Minha Agenda":
    col_titulo, col_btn = st.columns([0.8, 0.2])
    with col_titulo:
        st.header("🔍 Minha Agenda Completa")

    with col_btn:
        if st.button("🔄 Atualizar Dados", key="btn_refresh_agenda"):
            st.cache_data.clear()
            st.rerun()

    if df_agenda is not None and not df_agenda.empty:
        # --- 1. LIMPEZA DE DUPLICADOS E RESET DE ÍNDICE ---
        df_agenda = df_agenda.drop_duplicates(
            subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'],
            keep='first'
        ).reset_index(drop=True)

        # Garantir que colunas essenciais existam
        colunas_necessarias = ['APROVACAO', 'OBS_GESTAO', 'ANALISTA', 'SUPERVISOR', 'VENDEDOR', 'DISTANCIA_LOG']
        for col in colunas_necessarias:
            if col not in df_agenda.columns:
                df_agenda[col] = 0 if col == 'DISTANCIA_LOG' else ""

        # ✅ AJUSTE (NECESSÁRIO): garantir que DISTANCIA_LOG seja numérica (senão a tabela pode ficar em branco)
        if 'DISTANCIA_LOG' in df_agenda.columns:
            df_agenda['DISTANCIA_LOG'] = (
                df_agenda['DISTANCIA_LOG']
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            df_agenda['DISTANCIA_LOG'] = pd.to_numeric(df_agenda['DISTANCIA_LOG'], errors='coerce').fillna(0)

        # Padronização de valores vazios
        df_agenda['APROVACAO'] = df_agenda['APROVACAO'].fillna("Pendente").replace(["", "none", "None", "nan", "NaN"], "Pendente")

        # --- 2. PREPARAÇÃO DE DATAS ---
        df_agenda['DT_COMPLETA'] = pd.to_datetime(df_agenda['DATA'], dayfirst=True, errors='coerce')

        # ✅ (NOVO) DT_REGISTRO: data/hora do registro (quando agendou)
        # aceita "dd/mm/yyyy HH:MM" e também "dd/mm/yyyy"
        if 'REGISTRO' in df_agenda.columns:
            df_agenda['DT_REGISTRO'] = pd.to_datetime(df_agenda['REGISTRO'], dayfirst=True, errors='coerce')
        else:
            df_agenda['DT_REGISTRO'] = pd.NaT

        # --- 3. LÓGICA DE FILTRO POR HIERARQUIA E STATUS DE APROVAÇÃO ---
        if is_admin or is_diretoria:
            df_user = df_agenda.copy()
            st.info("💡 Visão de Administrador: Todos os registros exibidos.")
        elif is_analista:
            df_user = df_agenda[df_agenda['ANALISTA'].astype(str).str.upper() == user_atual.upper()].copy()
        elif is_supervisor:
            df_user = df_agenda[df_agenda['SUPERVISOR'].astype(str).str.upper() == user_atual.upper()].copy()
        else:
            df_user = df_agenda[df_agenda['VENDEDOR'].astype(str).str.upper() == user_atual.upper()].copy()

        # --- AQUI ESTÁ O AJUSTE SOLICITADO ---
        # Removemos os pendentes da visualização da agenda (exceto para Admin se quiser manter a visão total)
        # Se quiser que NINGUÉM veja na agenda antes de aprovar, remova o "if not is_admin"
        if not (is_admin or is_diretoria):
            df_user = df_user[df_user['STATUS'] != "Pendente"]
        # ---------------------------------------

        df_user = df_user.reset_index(drop=True)

        if not df_user.empty:
            # --- 4. FILTROS DINÂMICOS ---
            with st.expander("🎯 Filtros de Visualização", expanded=False):
                f_col1, f_col2, f_col3 = st.columns(3)
                def get_options(df, col):
                    return ["Todos"] + sorted([str(x) for x in df[col].unique() if x and str(x).lower() != 'nan'])

                ana_f = f_col1.selectbox("Filtrar Analista:", get_options(df_user, 'ANALISTA'))
                df_temp = df_user if ana_f == "Todos" else df_user[df_user['ANALISTA'] == ana_f]

                sup_f = f_col2.selectbox("Filtrar Supervisor:", get_options(df_temp, 'SUPERVISOR'))
                df_temp = df_temp if sup_f == "Todos" else df_temp[df_temp['SUPERVISOR'] == sup_f]

                vend_f = f_col3.selectbox("Filtrar Vendedor:", get_options(df_temp, 'VENDEDOR'))

                if ana_f != "Todos": df_user = df_user[df_user['ANALISTA'] == ana_f]
                if sup_f != "Todos": df_user = df_user[df_user['SUPERVISOR'] == sup_f]
                if vend_f != "Todos": df_user = df_user[df_user['VENDEDOR'] == vend_f]
                df_user = df_user.reset_index(drop=True)

            # ✅ (AJUSTE) SLICER DE DATA (slider range) SEM ESTOURAR EM VENDEDOR / TROCA DE MODO / STATE VELHO
            st.markdown("### 🗓️ Período")
            c_dt1, c_dt2 = st.columns([0.55, 0.45])

            with c_dt2:
                modo_data = st.radio(
                    "Filtrar datas por:",
                    ["Data da visita (DATA)", "Data do registro (REGISTRO)"],
                    horizontal=True,
                    key="modo_data_agenda"
                )

            # ✅ limpa a key antiga (muita gente já ficou com state salvo e isso causa StreamlitAPIException)
            if "slider_periodo_agenda" in st.session_state:
                del st.session_state["slider_periodo_agenda"]

            # Escolhe a coluna de data base do filtro
            col_dt_filtro = 'DT_COMPLETA' if modo_data == "Data da visita (DATA)" else 'DT_REGISTRO'

            # Prepara min/max só com datas válidas (date puro pro slider)
            serie_dt = pd.to_datetime(df_user[col_dt_filtro], errors='coerce').dropna()

            if not serie_dt.empty:
                dt_min = serie_dt.min().date()
                dt_max = serie_dt.max().date()

                # ✅ key única por usuário + modo (evita conflito e reaproveitamento errado entre perfis)
                slider_key = f"slider_periodo_agenda_{col_dt_filtro}_{str(user_atual).upper()}"

                # ✅ quando só existe 1 dia (min==max), slider de range pode quebrar -> vira filtro fixo
                if dt_min == dt_max:
                    with c_dt1:
                        st.caption(f"Período disponível: {dt_min.strftime('%d/%m/%Y')}")
                    dt_ini, dt_fim = dt_min, dt_max
                else:
                    # ✅ se já existe valor antigo no session_state, faz clamp dentro do novo range
                    valor_padrao = (dt_min, dt_max)
                    valor_antigo = st.session_state.get(slider_key, valor_padrao)

                    try:
                        a, b = valor_antigo
                        if a is None or b is None:
                            a, b = dt_min, dt_max
                    except Exception:
                        a, b = dt_min, dt_max

                    # clamp
                    if a < dt_min: a = dt_min
                    if b > dt_max: b = dt_max
                    if a > b: a, b = dt_min, dt_max

                    with c_dt1:
                        dt_ini, dt_fim = st.slider(
                            "Arraste para selecionar o período:",
                            min_value=dt_min,
                            max_value=dt_max,
                            value=(a, b),
                            key=slider_key
                        )

                # aplica filtro (inclusive)
                mask_dt = pd.to_datetime(df_user[col_dt_filtro], errors='coerce').dt.date.between(dt_ini, dt_fim)
                df_user = df_user[mask_dt].reset_index(drop=True)
            else:
                with c_dt1:
                    st.info("Sem datas válidas para filtrar no modo selecionado.")

            # --- 5. MÉTRICAS ---
            # ✅ (NOVO) Card de "fora do raio" > 50 metros
            fora_raio_50m = int((df_user['DISTANCIA_LOG'] > 50).sum()) if 'DISTANCIA_LOG' in df_user.columns else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📅 Total Agendado", len(df_user))
            # Ajustado para mostrar o que está planejado (já aprovado)
            m2.metric("⏳ Em Aguardo", len(df_user[df_user['STATUS'] == "Agendado"]))
            m3.metric("✅ Total Realizado", len(df_user[df_user['STATUS'] == "Realizado"]))
            m4.metric("📍 Fora do Raio (+50m)", fora_raio_50m, delta_color="inverse")
            st.markdown("---")

            # --- 6. APROVAÇÃO EM MASSA (GESTÃO) ---
            if (is_admin or is_diretoria or is_analista):
                with st.expander("⚖️ Painel de Aprovação de Agendas", expanded=False):
                    col_ap1, col_ap2, col_ap3 = st.columns([2, 2, 3])
                    vends_na_lista = sorted([str(x) for x in df_user['VENDEDOR'].unique() if x])
                    vend_alvo = col_ap1.selectbox("Vendedor:", ["Todos"] + vends_na_lista, key="sel_massa_v")
                    status_massa = col_ap2.selectbox("Definir:", ["Aprovado", "Reprovado"], key="sel_massa_s")
                    obs_massa = col_ap3.text_input("Observação:", key="obs_massa_input")

                    if st.button("🚀 Aplicar Decisão em Massa"):
                        mask = df_agenda['VENDEDOR'] == vend_alvo if vend_alvo != "Todos" else df_agenda['VENDEDOR'].isin(vends_na_lista)
                        df_agenda.loc[mask, 'APROVACAO'] = status_massa
                        df_agenda.loc[mask, 'OBS_GESTAO'] = obs_massa
                        if status_massa == "Reprovado":
                            df_agenda.loc[mask, 'STATUS'] = "Reprovado"
                        else:
                            # Se aprovado em massa, muda de Pendente para Planejado
                            df_agenda.loc[mask & (df_agenda['STATUS'] == "Pendente"), 'STATUS'] = "Agendado"

                        df_save = df_agenda.drop_duplicates(subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'])
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save.drop(columns=['LINHA', 'DT_COMPLETA', 'DT_REGISTRO'], errors='ignore'))
                        st.cache_data.clear(); st.success("Atualizado!"); time.sleep(1); st.rerun()

            # --- 7. TABELA COM ANALISTA E DISTÂNCIA ---
            df_user["AÇÃO"] = False
            cols_display = ['AÇÃO', 'REGISTRO', 'AGENDADO POR','DATA', 'ANALISTA', 'VENDEDOR', 'CLIENTE', 'STATUS', 'APROVACAO', 'DISTANCIA_LOG', 'OBS_GESTAO']
            df_display = df_user[[c for c in cols_display if c in df_user.columns or c == "AÇÃO"]].copy()

            edicao_user = st.data_editor(
                df_display,
                key="edit_agenda_final_v3",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "AÇÃO": st.column_config.CheckboxColumn("📌"),
                    "DISTANCIA_LOG": st.column_config.NumberColumn("Distância (m)", format="%d m"),
                    "DATA": st.column_config.TextColumn("Data"),
                    "ANALISTA": st.column_config.TextColumn("Analista")
                },
                disabled=[c for c in df_display.columns if c != "AÇÃO"]
            )

            # --- 8. GERENCIAMENTO INDIVIDUAL ---
            marcados = edicao_user[edicao_user["AÇÃO"] == True]
            if not marcados.empty:
                idx_selecionado = marcados.index[0]
                sel_row = df_user.iloc[idx_selecionado]

                st.markdown(f"### ⚙️ Gerenciar: {sel_row['CLIENTE']}")

                # ✅ (AJUSTE) Aba Excluir só aparece para ADMIN (você)
                if is_admin:
                    t1, t2, t3 = st.tabs(["⚖️ Aprovação", "🔄 Reagendar", "🗑️ Excluir"])
                else:
                    t1, t2 = st.tabs(["⚖️ Aprovação", "🔄 Reagendar"])

                with t1:
                    if is_admin or is_diretoria or is_analista:
                        col_ind1, col_ind2 = st.columns(2)
                        n_status = col_ind1.selectbox("Decisão:", ["Aprovado", "Reprovado"], key="n_status_ind")
                        n_obs = col_ind2.text_input("Motivo:", value=str(sel_row['OBS_GESTAO']), key="n_obs_ind")

                        if st.button("Salvar Decisão Individual"):
                            df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['APROVACAO', 'OBS_GESTAO']] = [n_status, n_obs]
                            if n_status == "Reprovado":
                                df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Reprovado"
                            else:
                                # Se aprovado individualmente, muda de Pendente para Planejado
                                df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Agendado"

                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA','DT_REGISTRO'], errors='ignore'))
                            st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()
                    else:
                        st.warning("Apenas gestores podem alterar a aprovação.")

                with t2:
                    n_data = st.date_input("Nova Data:", value=datetime.now(), key="date_reag")
                    if st.button("Confirmar Reagendamento"):
                        # Reagendamento volta para Planejado ou Pendente?
                        # Aqui mantive Planejado como estava no seu código original
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['DATA', 'STATUS', 'APROVACAO']] = [n_data.strftime('%d/%m/%Y'), "Agendado", "Pendente"]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA','DT_REGISTRO'], errors='ignore'))
                        st.cache_data.clear(); st.success("Reagendado!"); time.sleep(1); st.rerun()

                if is_admin:
                    with t3:
                        st.error("Atenção: Esta ação excluirá o registro permanentemente.")
                        if st.button("🗑️ CONFIRMAR EXCLUSÃO"):
                            df_agenda = df_agenda[df_agenda['ID'] != sel_row['ID']]
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA','DT_REGISTRO'], errors='ignore'))
                            st.cache_data.clear(); st.success("Excluído"); time.sleep(1); st.rerun()

            # ============================
            # 🗺️ MAPA (IGUAL AO DO DIA)
            # ============================
            st.markdown("---")
            st.markdown("### 🗺️ Mapa da Minha Agenda")

            try:
                if df_base is not None and ("COORDENADAS" in df_base.columns):

                    # 🔧 COORDENADAS DA BASE
                    df_coords = df_base[['Cliente', 'COORDENADAS']].drop_duplicates(subset='Cliente').copy()
                    df_coords = df_coords.rename(columns={"COORDENADAS": "COORDENADAS_BASE"})
                    df_coords['Cliente'] = df_coords['Cliente'].astype(str).str.strip()

                    df_map = df_user.copy()
                    df_map['CÓDIGO CLIENTE'] = df_map['CÓDIGO CLIENTE'].astype(str).str.strip()

                    df_map = df_map.merge(
                        df_coords,
                        left_on='CÓDIGO CLIENTE',
                        right_on='Cliente',
                        how='left'
                    )

                    # --- EXTRAI LAT / LON DA BASE ---
                    def _parse_coord(x):
                        try:
                            if isinstance(x, str) and ',' in x:
                                lat, lon = x.split(',', 1)
                                return float(lat.strip()), float(lon.strip())
                        except:
                            pass
                        return None, None

                    df_map['LAT'] = df_map['COORDENADAS_BASE'].apply(lambda v: _parse_coord(v)[0])
                    df_map['LON'] = df_map['COORDENADAS_BASE'].apply(lambda v: _parse_coord(v)[1])

                    # Remove sem coordenadas válidas
                    df_map = df_map.dropna(subset=['LAT', 'LON']).copy()

                    if df_map.empty:
                        st.info("Nenhuma coordenada válida encontrada para exibir no mapa.")
                    else:
                        # --- LIMPEZA EXTRA ---
                        for c in ['VENDEDOR', 'CLIENTE', 'STATUS']:
                            if c in df_map.columns:
                                df_map[c] = df_map[c].astype(str).replace(["nan", "None"], "").fillna("")

                        # --- CORES ---
                        # Pino (verde / vermelho)
                        df_map['COR_PINO'] = df_map['STATUS'].astype(str).str.upper().apply(
                            lambda s: [0, 160, 0, 255] if s == "REALIZADO" else [200, 0, 0, 255]
                        )

                        # Círculo 1km (cinza)
                        df_map['COR_RAIO'] = [[160, 160, 160, 70]] * len(df_map)

                        # --- TOOLTIP ---
                        df_map['TOOLTIP'] = df_map.apply(
                            lambda r: f"Vendedor: {r.get('VENDEDOR','')} | Cliente: {r.get('CLIENTE','')} | Status: {r.get('STATUS','')}",
                            axis=1
                        )

                        # --- ÍCONES ---
                        icone_vermelho = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"
                        icone_verde    = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png"

                        def _icon_por_status(s):
                            s = str(s).strip().upper()
                            url = icone_verde if s == "REALIZADO" else icone_vermelho
                            return {"url": url, "width": 25, "height": 41, "anchorY": 41}

                        df_map["ICON"] = df_map["STATUS"].apply(_icon_por_status)

                        # --- DADOS PARA O MAPA ---
                        dados_mapa = df_map[['LON', 'LAT', 'COR_PINO', 'COR_RAIO', 'ICON', 'TOOLTIP']].to_dict(orient="records")

                        # --- CENTRO ---
                        lat_center = float(df_map['LAT'].mean())
                        lon_center = float(df_map['LON'].mean())

                        import pydeck as pdk

                        # --- CÍRCULO 1 KM ---
                        layer_raio = pdk.Layer(
                            "CircleLayer",
                            data=dados_mapa,
                            get_position='[LON, LAT]',
                            get_radius=1000,
                            radius_units='meters',
                            get_fill_color="COR_RAIO",
                            get_line_color=[120, 120, 120, 180],
                            line_width_min_pixels=2,
                            filled=True,
                            stroked=True,
                            pickable=False,
                        )

                        # --- PINOS ---
                        layer_pinos = pdk.Layer(
                            "IconLayer",
                            data=dados_mapa,
                            get_position='[LON, LAT]',
                            get_icon="ICON",
                            get_size=4,
                            size_scale=10,
                            pickable=True,
                        )

                        view_state = pdk.ViewState(
                            latitude=lat_center,
                            longitude=lon_center,
                            zoom=11,
                            pitch=0
                        )

                        tooltip = {"text": "{TOOLTIP}"}

                        st.pydeck_chart(
                            pdk.Deck(
                                layers=[layer_raio, layer_pinos],
                                initial_view_state=view_state,
                                tooltip=tooltip,
                                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
                            ),
                            use_container_width=True
                        )

                else:
                    st.info("Coluna COORDENADAS não encontrada na BASE.")

            except Exception as e:
                st.warning(f"Não foi possível renderizar o mapa: {e}")

        else:
            st.info("Nenhum agendamento encontrado para os filtros selecionados.")



# --- PÁGINA: DESEMPENHO DE VENDAS (FATURADO)
elif menu_interna == "📊 ACOMP. DIÁRIO":
    st.header("📊 ACOMPANHAMENTO DIÁRIO")

    # ============================
    # ✅ CONTROLE DE ESTADO (Streamlit rerun)
    # ============================
    if "df_final_acomp_diario" not in st.session_state:
        st.session_state["df_final_acomp_diario"] = None

    if "df_envio_acomp_diario" not in st.session_state:
        st.session_state["df_envio_acomp_diario"] = None

    if "pedir_envio_excel_acomp_diario" not in st.session_state:
        st.session_state["pedir_envio_excel_acomp_diario"] = False

    # ✅ BOTÃO: agora só dispara a FLAG e força rerun
    if st.button("📧 Enviar Excel por Vendedor", key="btn_enviar_excel_acomp_diario"):
        st.session_state["pedir_envio_excel_acomp_diario"] = True
        st.rerun()

    # ✅ AJUSTE VISUAL: milhar com ponto (sem mexer em cálculo)
    def fmt_pt_int(v):
        try:
            return f"{float(v):,.0f}".replace(",", ".")
        except:
            return str(v)

    # ✅ Normaliza Cliente SEM PERDER cliente:
    def _norm_cliente(df, col):
        if df is None or df.empty or col not in df.columns:
            return df

        s = df[col]
        mask = s.notna()
        s2 = s.copy()

        s2.loc[mask] = (
            s.loc[mask]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

        df[col] = s2
        return df

    def _to_datetime_safe(s):
        return pd.to_datetime(s, errors="coerce", dayfirst=True)

    def _business_days_in_month(year, month):
        inicio = pd.Timestamp(year=year, month=month, day=1)
        fim = (inicio + pd.offsets.MonthEnd(1)).normalize()
        return len(pd.bdate_range(inicio, fim))

    def _business_days_elapsed_in_month(ref_date):
        inicio = pd.Timestamp(year=ref_date.year, month=ref_date.month, day=1)
        fim = pd.Timestamp(ref_date.date())
        return len(pd.bdate_range(inicio, fim))

    # ============================
    # >>> PROCESSAMENTO / LEITURA
    # ============================
    try:
        # 1. Leitura das abas
        df_faturado = conn.read(spreadsheet=url_planilha, worksheet="FATURADO")
        df_metas_cob = conn.read(spreadsheet=url_planilha, worksheet="META COBXPOSIT")
        df_param_metas = conn.read(spreadsheet=url_planilha, worksheet="PARAM_METAS")
        df_meta_sistema = conn.read(spreadsheet=url_planilha, worksheet="META SISTEMA")
        df_2025 = conn.read(spreadsheet=url_planilha, worksheet="META 2025")

        lista_hierarquia_fixa = [
            "ACHOCOLATADO","ACUCAR","ADOCANTE SACARINA","ADOCANTE SUCRALOSE","AZEITONA",
            "BALSAMICO","BEBIDA MISTA","CALDOS TABLETE","CATCHUP","CEBOLINHA","COGUMELO",
            "DESCARTAVEIS","ESPECIARIAS","FARINHA DE TRIGO FD","FARINHA DE TRIGO SC",
            "FARINHA LACTEA","MACARRAO INSTANTANEO","MARATINHO","MILHO",
            "MILHO FARINHA GOTA","MILHO FARINHA MARATA","MILHO FLOCAO GOTA",
            "MILHO FLOCAO MARATA","MILHO PIPOCA","MINGAU","MISTURA BOLO",
            "MOLHO PRONTO","MOLHOS ALHO","MOLHOS INGLES","MOLHOS LIMAO",
            "MOLHOS PIMENTA","MOLHOS PIMENTA 75ML","MOLHOS SALSA","MOLHOS SHOYO",
            "MOLHOS TEMPEROS CASEIROS","OLEAGINOSAS","PIMENTA CONSERVA",
            "PIPOCA PRONTA","REFRESCO","SALGADINHOS FARDO","SALGADINHOS NACHOS",
            "SALGADINHOS PASTEIS","SUCO D+ 1000ML","SUCO D+ 200ML",
            "SUCO MARATA 1000ML","SUCO MARATA 200ML","TEMPERO COLORIFICO GOTA",
            "TEMPERO COLORIFICO MARATA","TEMPERO CONDIMENTO GOTA",
            "TEMPERO CONDIMENTO MARATA","TEMPERO EM PO","VINAGRE","VINAGRE ESPECIAL"
        ]

        if df_faturado is not None and not df_faturado.empty:
            df_faturado = df_faturado.dropna(how="all")
            df_faturado.columns = [str(c).strip() for c in df_faturado.columns]

            df_faturado.rename(columns={
                "Região de vendas": "VENDEDOR_NOME",
                "RG": "VENDEDOR_COD",
                "Qtd Vendas (S/Dec)": "QTD_VENDAS",
                "Hierarquia de produtos": "HIERARQUIA"
            }, inplace=True)

            # ✅ Cliente é a coluna K (ajuste conforme seu arquivo; você usou [11])
            col_cod_cliente = df_faturado.columns[11]

            # ✅ Detecta coluna de data (Data fat. / Data fat / variações)
            col_data_fat = None
            for c in df_faturado.columns:
                c_norm = str(c).strip().lower().replace(" ", "")
                if "datafat" in c_norm or c_norm in ["datafat.", "datafat"]:
                    col_data_fat = c
                    break

            if not col_data_fat:
                # tenta achar qualquer coluna com "data" e "fat"
                for c in df_faturado.columns:
                    c_low = str(c).strip().lower()
                    if ("data" in c_low) and ("fat" in c_low):
                        col_data_fat = c
                        break

            if col_data_fat:
                df_faturado[col_data_fat] = _to_datetime_safe(df_faturado[col_data_fat])

            df_faturado["QTD_VENDAS"] = pd.to_numeric(df_faturado["QTD_VENDAS"], errors="coerce").fillna(0)
            df_faturado["VENDEDOR_COD"] = df_faturado["VENDEDOR_COD"].astype(str).str.replace(r"\.0$", "", regex=True)

            df_faturado = _norm_cliente(df_faturado, col_cod_cliente)

            df_relacao = df_base[["VENDEDOR","SUPERVISOR","ANALISTA"]].drop_duplicates("VENDEDOR")
            df_faturado = df_faturado.merge(
                df_relacao, left_on="VENDEDOR_NOME", right_on="VENDEDOR", how="left"
            )

        # ✅ (NECESSÁRIO) PARAM_METAS
        if df_param_metas is not None:
            df_param_metas.columns = [str(c).strip() for c in df_param_metas.columns]
            if "BASE" in df_param_metas.columns:
                df_param_metas["BASE"] = pd.to_numeric(df_param_metas["BASE"], errors="coerce").fillna(0)
            if "EscrV" in df_param_metas.columns:
                df_param_metas["EscrV"] = df_param_metas["EscrV"].astype(str).str.strip()

        # ✅ META COBXPOSIT
        if df_metas_cob is not None:
            df_metas_cob.columns = [str(c).strip() for c in df_metas_cob.columns]
            if "RG" in df_metas_cob.columns:
                df_metas_cob["RG"] = df_metas_cob["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "BASE" in df_metas_cob.columns:
                df_metas_cob["BASE"] = pd.to_numeric(df_metas_cob["BASE"], errors="coerce").fillna(0)
            if "META COBERTURA" in df_metas_cob.columns:
                df_metas_cob["META COBERTURA"] = (
                    pd.to_numeric(df_metas_cob["META COBERTURA"], errors="coerce")
                    .fillna(0)
                    .apply(lambda x: x / 100 if x > 1 else x)
                )
            if "META" in df_metas_cob.columns:
                df_metas_cob["META"] = pd.to_numeric(df_metas_cob["META"], errors="coerce").fillna(0)

        # ✅ META SISTEMA
        if df_meta_sistema is not None:
            df_meta_sistema.columns = [str(c).strip() for c in df_meta_sistema.columns]
            if "RG" in df_meta_sistema.columns:
                df_meta_sistema["RG"] = df_meta_sistema["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "QTD" in df_meta_sistema.columns:
                df_meta_sistema["QTD"] = pd.to_numeric(df_meta_sistema["QTD"], errors="coerce").fillna(0)

        # ✅ META 2025
        if df_2025 is not None:
            df_2025.columns = [str(c).strip() for c in df_2025.columns]
            if "RG" in df_2025.columns:
                df_2025["RG"] = df_2025["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "QUANTIDADE" in df_2025.columns:
                df_2025["QUANTIDADE"] = pd.to_numeric(df_2025["QUANTIDADE"], errors="coerce").fillna(0)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        st.stop()

    # ============================
    # BASE PRINCIPAL
    # ============================
    df_f = df_faturado.copy()
    df_f = _norm_cliente(df_f, col_cod_cliente)

    # ============================
    # 🔒 CONTROLE DE ACESSO
    # ============================
    df_base_perm = df_base.copy()

    for c in ["VENDEDOR","SUPERVISOR","ANALISTA"]:
        if c in df_base_perm.columns:
            df_base_perm[c] = df_base_perm[c].astype(str).str.strip().str.upper()

    if "EscrV" in df_base_perm.columns:
        df_base_perm["EscrV"] = df_base_perm["EscrV"].astype(str).str.strip().str.upper()
    if "Estado" in df_base_perm.columns:
        df_base_perm["Estado"] = df_base_perm["Estado"].astype(str).str.strip().str.upper()
    if "ANALISTA" in df_base_perm.columns:
        df_base_perm["ANALISTA"] = df_base_perm["ANALISTA"].astype(str).str.strip().str.upper()

    for c in ["VENDEDOR","SUPERVISOR","ANALISTA"]:
        if c in df_f.columns:
            df_f[c] = df_f[c].astype(str).str.strip().str.upper()
    if "ANALISTA" in df_f.columns:
        df_f["ANALISTA"] = df_f["ANALISTA"].astype(str).str.strip().str.upper()
    if "EscrV" in df_f.columns:
        df_f["EscrV"] = df_f["EscrV"].astype(str).str.strip().str.upper()
    if "Estado" in df_f.columns:
        df_f["Estado"] = df_f["Estado"].astype(str).str.strip().str.upper()

    user_atual = user_atual.strip().upper()
    vendedores_permitidos = None

    col_estado_perm = "EscrV" if "EscrV" in df_base_perm.columns else ("Estado" if "Estado" in df_base_perm.columns else None)

    estados_usuario = None
    if col_estado_perm and (is_vendedor or is_supervisor or is_analista):
        if is_vendedor and "VENDEDOR" in df_base_perm.columns:
            estados_usuario = df_base_perm.loc[df_base_perm["VENDEDOR"] == user_atual, col_estado_perm].dropna().unique().tolist()
        elif is_supervisor and "SUPERVISOR" in df_base_perm.columns:
            estados_usuario = df_base_perm.loc[df_base_perm["SUPERVISOR"] == user_atual, col_estado_perm].dropna().unique().tolist()
        elif is_analista and "ANALISTA" in df_base_perm.columns:
            estados_usuario = df_base_perm.loc[df_base_perm["ANALISTA"] == user_atual, col_estado_perm].dropna().unique().tolist()

        if estados_usuario:
            estados_usuario = [str(x).strip().upper() for x in estados_usuario if str(x).strip()]
        else:
            estados_usuario = None

    analista_usuario = None
    if is_vendedor and ("VENDEDOR" in df_base_perm.columns) and ("ANALISTA" in df_base_perm.columns):
        tmp_analista = df_base_perm.loc[df_base_perm["VENDEDOR"] == user_atual, "ANALISTA"].dropna().unique().tolist()
        if tmp_analista:
            analista_usuario = str(tmp_analista[0]).strip().upper()

    if is_vendedor and not analista_usuario:
        if ("VENDEDOR" in df_f.columns) and ("ANALISTA" in df_f.columns):
            tmp_a = df_f.loc[df_f["VENDEDOR"] == user_atual, "ANALISTA"].dropna().unique().tolist()
            if tmp_a:
                analista_usuario = str(tmp_a[0]).strip().upper()

    if is_analista:
        if "ANALISTA" in df_f.columns:
            df_f = df_f[df_f["ANALISTA"] == user_atual]

        if col_estado_perm and estados_usuario:
            vendedores_permitidos = df_base_perm.loc[
                (df_base_perm["ANALISTA"] == user_atual) & (df_base_perm[col_estado_perm].isin(estados_usuario)),
                "VENDEDOR"
            ].dropna().unique().tolist()
        else:
            vendedores_permitidos = df_base_perm.loc[
                df_base_perm["ANALISTA"] == user_atual, "VENDEDOR"
            ].dropna().unique().tolist()

    elif is_supervisor:
        if col_estado_perm and estados_usuario:
            vendedores_permitidos = df_base_perm.loc[
                df_base_perm[col_estado_perm].isin(estados_usuario), "VENDEDOR"
            ].dropna().unique().tolist()
        else:
            vendedores_permitidos = df_base_perm.loc[
                df_base_perm["SUPERVISOR"] == user_atual, "VENDEDOR"
            ].dropna().unique().tolist()

    elif is_vendedor:
        if analista_usuario:
            if "ANALISTA" in df_f.columns:
                df_f = df_f[df_f["ANALISTA"] == analista_usuario]

            if col_estado_perm and estados_usuario:
                vendedores_permitidos = df_base_perm.loc[
                    (df_base_perm["ANALISTA"] == analista_usuario) &
                    (df_base_perm[col_estado_perm].isin(estados_usuario)),
                    "VENDEDOR"
                ].dropna().unique().tolist()

                if "EscrV" in df_f.columns:
                    df_f = df_f[df_f["EscrV"].isin(estados_usuario)]
            else:
                vendedores_permitidos = [user_atual]
        else:
            if col_estado_perm and estados_usuario:
                vendedores_permitidos = df_base_perm.loc[
                    df_base_perm[col_estado_perm].isin(estados_usuario), "VENDEDOR"
                ].dropna().unique().tolist()
            else:
                vendedores_permitidos = [user_atual]

    if vendedores_permitidos:
        if "VENDEDOR" in df_f.columns:
            df_f = df_f[df_f["VENDEDOR"].isin(vendedores_permitidos)]

    # ============================
    # ✅ FILTRO DO MÊS ATUAL (slider dentro do mês atual)
    # ============================
    hoje = pd.Timestamp.now().normalize()
    inicio_mes_atual = pd.Timestamp(year=hoje.year, month=hoje.month, day=1)
    fim_mes_atual = (inicio_mes_atual + pd.offsets.MonthEnd(1)).normalize()

    if not col_data_fat or col_data_fat not in df_f.columns:
        st.error("Não encontrei a coluna de data de faturamento (Data fat.) no FATURADO.")
        st.stop()

    if df_f[col_data_fat].isna().all():
        st.error(f"A coluna '{col_data_fat}' está vazia/ inválida (tudo NaT). Verifique o formato de data no FATURADO.")
        st.stop()

    st.markdown("### 🗓️ Período (mês atual)")
    d1, d2 = st.slider(
        "Selecione o intervalo dentro do mês",
        min_value=inicio_mes_atual.to_pydatetime(),
        max_value=fim_mes_atual.to_pydatetime(),
        value=(inicio_mes_atual.to_pydatetime(), fim_mes_atual.to_pydatetime()),
        format="DD/MM/YYYY",
        key="slider_mes_atual_acomp"
    )
    d1 = pd.Timestamp(d1).normalize()
    d2 = pd.Timestamp(d2).normalize()

    linhas_antes = len(df_f)
    df_f = df_f[(df_f[col_data_fat] >= d1) & (df_f[col_data_fat] <= d2)]


    # ============================
    # 🔍 FILTROS
    # ============================
    st.markdown("### 🔍 Filtros")
    c1, c2, c3 = st.columns(3)

    col_estado = "EscrV" if "EscrV" in df_f.columns else None

    if col_estado and (is_vendedor or is_supervisor or is_analista) and estados_usuario:
        df_f[col_estado] = df_f[col_estado].astype(str).str.strip().str.upper()
        df_f = df_f[df_f[col_estado].isin(estados_usuario)]

    with c1:
        if col_estado:
            if (is_vendedor or is_supervisor) and estados_usuario:
                sel_estado = st.multiselect(
                    "Estado",
                    sorted(estados_usuario),
                    default=sorted(estados_usuario),
                    disabled=True
                )
            elif is_analista and estados_usuario:
                sel_estado = st.multiselect("Estado", sorted(estados_usuario), default=sorted(estados_usuario))
            else:
                sel_estado = st.multiselect("Estado", sorted(df_f[col_estado].dropna().unique()))
        else:
            sel_estado = []

    if sel_estado and col_estado:
        df_f = df_f[df_f[col_estado].isin(sel_estado)]

    with c2:
        sel_supervisor = st.multiselect("Supervisor", sorted(df_f["SUPERVISOR"].dropna().unique()))
    if sel_supervisor:
        df_f = df_f[df_f["SUPERVISOR"].isin(sel_supervisor)]

    with c3:
        sel_vendedor = st.multiselect("Vendedor", sorted(df_f["VENDEDOR_NOME"].dropna().unique()))
    if sel_vendedor:
        df_f = df_f[df_f["VENDEDOR_NOME"].isin(sel_vendedor)]

    vendedores_ids = df_f["VENDEDOR_COD"].unique()

    # ============================
    # BASE TOTAL
    # ============================
    base_total = 0
    if df_param_metas is not None and not df_param_metas.empty and col_estado:
        if not (sel_supervisor or sel_vendedor):
            dados_base = df_param_metas[df_param_metas["EscrV"].isin(df_f[col_estado].unique())] if "EscrV" in df_param_metas.columns else df_param_metas.copy()
            if "BASE" in dados_base.columns:
                base_total = float(dados_base["BASE"].sum())
        else:
            if df_metas_cob is not None and "RG" in df_metas_cob.columns:
                dados_base = df_metas_cob[df_metas_cob["RG"].isin(vendedores_ids)]
                if "BASE" in dados_base.columns:
                    base_total = float(dados_base.drop_duplicates("RG")["BASE"].sum())

    # ============================
    # ✅ PACING DO MÊS (ritmo atual x necessário)
    # ============================
    try:
        dias_uteis_total = _business_days_in_month(inicio_mes_atual.year, inicio_mes_atual.month)
        ref_pacing = min(pd.Timestamp(d2).normalize(), pd.Timestamp.now().normalize())
        dias_uteis_passados = max(_business_days_elapsed_in_month(ref_pacing), 1)

        volume_mtd = float(df_f["QTD_VENDAS"].sum())

        meta_mes_2026 = 0.0
        if df_meta_sistema is not None and not df_meta_sistema.empty and "RG" in df_meta_sistema.columns:
            meta_mes_2026 = float(
                df_meta_sistema[df_meta_sistema["RG"].isin(vendedores_ids)]["QTD"].sum()
            )

        ritmo_atual = (volume_mtd / dias_uteis_passados) if dias_uteis_passados > 0 else 0
        ritmo_necessario = (meta_mes_2026 / dias_uteis_total) if dias_uteis_total > 0 else 0

        projecao_mes = ritmo_atual * dias_uteis_total
        status_ok = projecao_mes >= meta_mes_2026 if meta_mes_2026 > 0 else True

        selo = "✅ NO RITMO" if status_ok else "⚠️ ABAIXO DO RITMO"
        cor_selo = "#28a745" if status_ok else "#d9534f"
    except:
        ritmo_atual = 0
        ritmo_necessario = 0
        projecao_mes = 0
        meta_mes_2026 = 0
        selo = "—"
        cor_selo = "#999999"

    # ============================
    # PROCESSAMENTO FINAL
    # ============================
    df_agrup_f = (
        df_f.groupby("HIERARQUIA")
        .agg({"QTD_VENDAS":"sum", col_cod_cliente:"nunique"})
        .rename(columns={"QTD_VENDAS":"VOLUME", col_cod_cliente:"POSITIVAÇÃO"})
        .reset_index()
    )

    df_agrup_25 = (
        df_2025[df_2025["RG"].isin(vendedores_ids)]
        .groupby("HIERARQUIA DE PRODUTOS")["QUANTIDADE"]
        .sum()
        .reset_index()
        .rename(columns={"HIERARQUIA DE PRODUTOS":"HIERARQUIA","QUANTIDADE":"META 2025"})
        if df_2025 is not None and not df_2025.empty and "HIERARQUIA DE PRODUTOS" in df_2025.columns
        else pd.DataFrame(columns=["HIERARQUIA","META 2025"])
    )

    df_agrup_26 = (
        df_meta_sistema[df_meta_sistema["RG"].isin(vendedores_ids)]
        .groupby("HIERARQUIA DE PRODUTOS")["QTD"]
        .sum()
        .reset_index()
        .rename(columns={"HIERARQUIA DE PRODUTOS":"HIERARQUIA","QTD":"META 2026"})
        if df_meta_sistema is not None and not df_meta_sistema.empty and "HIERARQUIA DE PRODUTOS" in df_meta_sistema.columns
        else pd.DataFrame(columns=["HIERARQUIA","META 2026"])
    )

    df_meta_cob_h = (
        df_metas_cob.groupby("HIERARQUIA DE PRODUTOS")["META COBERTURA"]
        .mean()
        .reset_index()
        .rename(columns={"HIERARQUIA DE PRODUTOS":"HIERARQUIA"})
        if df_metas_cob is not None and not df_metas_cob.empty and "HIERARQUIA DE PRODUTOS" in df_metas_cob.columns
        else pd.DataFrame(columns=["HIERARQUIA","META COBERTURA"])
    )

    df_final = pd.DataFrame(lista_hierarquia_fixa, columns=["HIERARQUIA"])
    df_final = df_final.merge(df_agrup_f, on="HIERARQUIA", how="left")
    df_final = df_final.merge(df_meta_cob_h, on="HIERARQUIA", how="left")
    df_final = df_final.merge(df_agrup_25, on="HIERARQUIA", how="left")
    df_final = df_final.merge(df_agrup_26, on="HIERARQUIA", how="left").fillna(0)

    df_final["CLIENTES"] = (df_final["META COBERTURA"] * base_total).apply(math.ceil) if base_total > 0 else 0
    df_final["PENDÊNCIA"] = (df_final["CLIENTES"] - df_final["POSITIVAÇÃO"]).apply(lambda x: x if x > 0 else 0)
    df_final["CRESC 2025"] = df_final["VOLUME"] - df_final.get("META 2025", 0)
    df_final["% (VOL 2025)"] = (df_final["VOLUME"] / df_final.get("META 2025", 0) * 100).replace([np.inf, -np.inf], 0).fillna(0)
    df_final["CRESC 2026"] = df_final["VOLUME"] - df_final.get("META 2026", 0)
    df_final["% (VOL 2026)"] = (df_final["VOLUME"] / df_final.get("META 2026", 0) * 100).replace([np.inf, -np.inf], 0).fillna(0)

    def _trend_icon(row):
        try:
            m26 = float(row.get("META 2026", 0))
            m25 = float(row.get("META 2025", 0))
        except:
            m26, m25 = 0, 0

        if m26 > 0:
            v = float(row.get("CRESC 2026", 0))
        elif m25 > 0:
            v = float(row.get("CRESC 2025", 0))
        else:
            v = 0

        if v > 0:
            return "📈"
        if v < 0:
            return "📉"
        return "➖"

    df_final["TENDÊNCIA"] = df_final.apply(_trend_icon, axis=1)

    df_final.rename(columns={"HIERARQUIA":"HIERARQUIA DE PRODUTOS"}, inplace=True)

    # ============================
    # ✅ ADIÇÕES FODAS (RESUMO + ITENS ABAIXO + SUGESTÕES)  ✅
    # ============================
    try:
        df_resumo = df_final.copy()

        # Meta referência: prioridade 2026; se não tiver, cai em 2025
        df_resumo["META_REF"] = df_resumo.apply(
            lambda r: float(r.get("META 2026", 0)) if float(r.get("META 2026", 0)) > 0 else float(r.get("META 2025", 0)),
            axis=1
        )

        df_resumo["ATING_%"] = df_resumo.apply(
            lambda r: (float(r.get("VOLUME", 0)) / float(r.get("META_REF", 0)) * 100) if float(r.get("META_REF", 0)) > 0 else 0,
            axis=1
        )

        df_resumo["FALTA_P_BATER"] = df_resumo.apply(
            lambda r: max(float(r.get("META_REF", 0)) - float(r.get("VOLUME", 0)), 0),
            axis=1
        )

        itens_com_meta = int((df_resumo["META_REF"] > 0).sum())
        itens_bateram = int(((df_resumo["META_REF"] > 0) & (df_resumo["VOLUME"] >= df_resumo["META_REF"])).sum())
        itens_abaixo = int(((df_resumo["META_REF"] > 0) & (df_resumo["VOLUME"] < df_resumo["META_REF"])).sum())
        itens_sem_meta = int((df_resumo["META_REF"] <= 0).sum())
        perc_itens_no_alvo = (itens_bateram / itens_com_meta * 100) if itens_com_meta > 0 else 0

        st.markdown("---")
        st.markdown("## ✅ Resumo rápido (Metas por item)")

        c_r1, c_r2, c_r3, c_r4 = st.columns(4)

        with c_r1:
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 14px; border-radius: 10px; background-color: #f9f9f9;">
                    <small>ITENS COM META</small><br>
                    <span style="font-size: 2.0em; font-weight: 900;">{fmt_pt_int(itens_com_meta)}</span><br>
                    <span style="color:#666;">(Meta 2026 ou 2025)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_r2:
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 14px; border-radius: 10px; background-color: #f9f9f9;">
                    <small>ITENS QUE BATERAM</small><br>
                    <span style="font-size: 2.0em; font-weight: 900; color:#28a745;">{fmt_pt_int(itens_bateram)}</span><br>
                    <span style="color:#666;">{perc_itens_no_alvo:.1f}% no alvo</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_r3:
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 14px; border-radius: 10px; background-color: #f9f9f9;">
                    <small>ITENS ABAIXO</small><br>
                    <span style="font-size: 2.0em; font-weight: 900; color:#d9534f;">{fmt_pt_int(itens_abaixo)}</span><br>
                    <span style="color:#666;">prioridade do dia</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_r4:
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 14px; border-radius: 10px; background-color: #f9f9f9;">
                    <small>ITENS SEM META</small><br>
                    <span style="font-size: 2.0em; font-weight: 900; color:#999;">{fmt_pt_int(itens_sem_meta)}</span><br>
                    <span style="color:#666;">não entram na conta</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### 📌 Itens abaixo da meta (resumo)")
        df_abaixo_meta = df_resumo[(df_resumo["META_REF"] > 0) & (df_resumo["VOLUME"] < df_resumo["META_REF"])].copy()
        df_abaixo_meta["ATING_%"] = df_abaixo_meta["ATING_%"].fillna(0)

        df_abaixo_view = (
            df_abaixo_meta[["HIERARQUIA DE PRODUTOS", "VOLUME", "META_REF", "ATING_%", "FALTA_P_BATER"]]
            .rename(columns={
                "META_REF": "META (ref.)",
                "ATING_%": "% Ating.",
                "FALTA_P_BATER": "Falta p/ bater"
            })
            .sort_values(by=["% Ating.", "Falta p/ bater"], ascending=[True, False])
            .reset_index(drop=True)
        )

        if df_abaixo_view.empty:
            st.success("🎉 Todos os itens com meta bateram a meta no período selecionado!")
        else:
            st.dataframe(
                df_abaixo_view.style.format({
                    "VOLUME": lambda v: fmt_pt_int(v),
                    "META (ref.)": lambda v: fmt_pt_int(v),
                    "% Ating.": "{:.1f}%",
                    "Falta p/ bater": lambda v: fmt_pt_int(v),
                }),
                use_container_width=True,
                hide_index=True,
                height=320
            )

        # ----------------------------
        # ✅ SUGESTÕES (beta) - só aparece quando selecionar vendedor
        # ----------------------------
        st.markdown("## 🧠 Sugestões automáticas")

        if not (sel_vendedor and len(sel_vendedor) > 0):
            st.info("Selecione um vendedor no filtro para exibir as sugestões.")
        else:
            # 🔎 Coluna K = nome do cliente ("CLIENTE")
            col_nome_cliente = "CLIENTE" if ("CLIENTE" in df_faturado.columns) else (df_faturado.columns[10] if len(df_faturado.columns) > 10 else None)

            # base histórica (não mexe no df_f atual)
            df_hist = df_faturado.copy()
            df_hist = _norm_cliente(df_hist, col_cod_cliente)

            # normaliza nome do cliente, se existir
            if col_nome_cliente and (col_nome_cliente in df_hist.columns):
                df_hist[col_nome_cliente] = df_hist[col_nome_cliente].astype(str).str.strip()

            # aplica o mesmo recorte de permissão/filtros do usuário (vendedores permitidos + estados)
            for c in ["VENDEDOR","SUPERVISOR","ANALISTA"]:
                if c in df_hist.columns:
                    df_hist[c] = df_hist[c].astype(str).str.strip().str.upper()
            if "ANALISTA" in df_hist.columns:
                df_hist["ANALISTA"] = df_hist["ANALISTA"].astype(str).str.strip().str.upper()
            if "EscrV" in df_hist.columns:
                df_hist["EscrV"] = df_hist["EscrV"].astype(str).str.strip().str.upper()
            if "Estado" in df_hist.columns:
                df_hist["Estado"] = df_hist["Estado"].astype(str).str.strip().str.upper()

            if vendedores_permitidos and ("VENDEDOR" in df_hist.columns):
                df_hist = df_hist[df_hist["VENDEDOR"].isin(vendedores_permitidos)]

            if col_estado and estados_usuario and (col_estado in df_hist.columns):
                df_hist = df_hist[df_hist[col_estado].isin(estados_usuario)]

            if sel_supervisor and ("SUPERVISOR" in df_hist.columns):
                df_hist = df_hist[df_hist["SUPERVISOR"].isin(sel_supervisor)]

            if sel_vendedor and ("VENDEDOR_NOME" in df_hist.columns):
                df_hist = df_hist[df_hist["VENDEDOR_NOME"].isin(sel_vendedor)]

            # histórico desde novembro (do ano anterior ao atual quando estiver em jan-out)
            if hoje.month >= 11:
                inicio_hist = pd.Timestamp(year=hoje.year, month=11, day=1)
            else:
                inicio_hist = pd.Timestamp(year=hoje.year - 1, month=11, day=1)

            if col_data_fat in df_hist.columns:
                df_hist = df_hist[(df_hist[col_data_fat].notna()) & (df_hist[col_data_fat] >= inicio_hist)]

            if df_hist.empty:
                st.info("Sem sugestões agora: histórico vazio para o vendedor selecionado (desde novembro).")
            else:
                # ============================
                # 1) Sugestão: RECOMPRA de itens críticos (abaixo da meta)
                # ============================
                itens_criticos = set(df_abaixo_meta["HIERARQUIA DE PRODUTOS"].dropna().astype(str).tolist())

                if len(itens_criticos) == 0:
                    st.info("Sem sugestão de recompra agora: não há itens abaixo da meta no período selecionado.")
                else:
                    if col_nome_cliente and (col_nome_cliente in df_hist.columns):
                        keys = ["VENDEDOR_NOME", col_nome_cliente, col_cod_cliente, "HIERARQUIA"]
                    else:
                        keys = ["VENDEDOR_NOME", col_cod_cliente, "HIERARQUIA"]

                    df_hist_grp = (
                        df_hist.groupby(keys)
                        .agg(
                            VOL_HIST=("QTD_VENDAS", "sum"),
                            ULT_COMPRA=(col_data_fat, "max")
                        )
                        .reset_index()
                    )

                    df_atual_grp = (
                        df_f.groupby(keys)["QTD_VENDAS"]
                        .sum()
                        .reset_index()
                        .rename(columns={"QTD_VENDAS": "VOL_ATUAL"})
                    )

                    df_sug = df_hist_grp.merge(df_atual_grp, on=keys, how="left")
                    df_sug["VOL_ATUAL"] = pd.to_numeric(df_sug["VOL_ATUAL"], errors="coerce").fillna(0)
                    df_sug["VOL_HIST"] = pd.to_numeric(df_sug["VOL_HIST"], errors="coerce").fillna(0)

                    # só oportunidades: histórico > 0 e no período atual ainda não comprou
                    df_sug = df_sug[(df_sug["VOL_HIST"] > 0) & (df_sug["VOL_ATUAL"] <= 0)].copy()

                    # foca em itens críticos (abaixo da meta)
                    df_sug = df_sug[df_sug["HIERARQUIA"].astype(str).isin(itens_criticos)].copy()

                    if df_sug.empty:
                        st.info("Sem recompra clara: nos itens abaixo da meta, não encontrei clientes que compravam no histórico e ainda não compraram no período atual.")
                    else:
                        # dias sem comprar (referência: último dia do filtro OU hoje, o menor)
                        ref_sug = min(pd.Timestamp(d2).normalize(), pd.Timestamp.now().normalize())
                        df_sug["ULT_COMPRA"] = pd.to_datetime(df_sug["ULT_COMPRA"], errors="coerce")
                        df_sug["DIAS_SEM_COMPRAR"] = df_sug["ULT_COMPRA"].apply(
                            lambda x: int((ref_sug - pd.Timestamp(x).normalize()).days) if pd.notna(x) else None
                        )

                        # score simples: mais volume histórico e mais dias sem comprar = mais prioridade
                        df_sug["SCORE"] = df_sug["VOL_HIST"].fillna(0) * 0.7 + df_sug["DIAS_SEM_COMPRAR"].fillna(0) * 0.3

                        df_sug = df_sug.sort_values(by=["SCORE", "VOL_HIST"], ascending=False)

                        st.markdown("### 🎯 Recompra de itens críticos (abaixo da meta)")
                        st.caption("Regra: cliente comprou no histórico (desde novembro) e ainda não comprou no período atual, filtrado só para hierarquias abaixo da meta.")

                        vendedores_list = df_sug["VENDEDOR_NOME"].dropna().unique().tolist()
                        vendedores_list = sorted([str(v) for v in vendedores_list])

                        for vnd in vendedores_list:
                            df_v = df_sug[df_sug["VENDEDOR_NOME"] == vnd].copy()
                            df_v = df_v.head(12)

                            with st.expander(f"📌 Sugestões para: {vnd}  (top {len(df_v)})", expanded=False):
                                if col_nome_cliente and (col_nome_cliente in df_v.columns):
                                    df_show = df_v[["HIERARQUIA", col_nome_cliente, col_cod_cliente, "VOL_HIST", "ULT_COMPRA", "DIAS_SEM_COMPRAR"]].copy()
                                    df_show.rename(columns={
                                        "HIERARQUIA": "HIERARQUIA (item)",
                                        col_nome_cliente: "CLIENTE (nome)",
                                        col_cod_cliente: "CLIENTE (cód.)",
                                        "VOL_HIST": "VOLUME HIST.",
                                        "ULT_COMPRA": "ÚLT. COMPRA",
                                        "DIAS_SEM_COMPRAR": "DIAS S/ COMPRA"
                                    }, inplace=True)
                                else:
                                    df_show = df_v[["HIERARQUIA", col_cod_cliente, "VOL_HIST", "ULT_COMPRA", "DIAS_SEM_COMPRAR"]].copy()
                                    df_show.rename(columns={
                                        "HIERARQUIA": "HIERARQUIA (item)",
                                        col_cod_cliente: "CLIENTE (cód.)",
                                        "VOL_HIST": "VOLUME HIST.",
                                        "ULT_COMPRA": "ÚLT. COMPRA",
                                        "DIAS_SEM_COMPRAR": "DIAS S/ COMPRA"
                                    }, inplace=True)

                                st.dataframe(
                                    df_show.style.format({
                                        "VOLUME HIST.": lambda x: fmt_pt_int(x),
                                        "ÚLT. COMPRA": lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "",
                                    }),
                                    use_container_width=True,
                                    hide_index=True,
                                    height=320
                                )

                                st.markdown(
                                    """
                                    **Como usar isso na prática (rápido):**
                                    - Priorize as linhas com **mais VOLUME HIST.** e **mais DIAS S/ COMPRA**.
                                    - Aborde o cliente com foco no item da hierarquia (ex.: “reposição / ponto extra / promoção / mix completo”).
                                    """
                                )

                

    except Exception as e:
        st.warning(f"Não foi possível gerar o resumo/sugestões: {e}")

    # ============================
    # ✅ SESSION STATE
    # ============================
    try:
        st.session_state["df_final_acomp_diario"] = df_final.copy() if (df_final is not None and not df_final.empty) else None
        st.session_state["df_envio_acomp_diario"] = df_f.copy() if (df_f is not None and not df_f.empty) else None
    except:
        st.session_state["df_final_acomp_diario"] = None
        st.session_state["df_envio_acomp_diario"] = None

    # ============================
    # ✅ EXECUTOR DO ENVIO
    # ============================
    if st.session_state.get("pedir_envio_excel_acomp_diario", False):
        import smtplib

        st.session_state["pedir_envio_excel_acomp_diario"] = False

        df_relatorio = st.session_state.get("df_final_acomp_diario")
        df_envio = st.session_state.get("df_envio_acomp_diario")

        if df_relatorio is None or df_relatorio.empty:
            st.error("Relatório (df_final) não foi gerado nesta execução. Atualize a página (F5) e tente novamente.")
            st.stop()

        if df_envio is None or df_envio.empty:
            st.error("Base de vendedores não carregada. Verifique a leitura/processamento do FATURADO.")
            st.stop()

        if "VENDEDOR_NOME" not in df_envio.columns:
            if "Região de vendas" in df_envio.columns:
                df_envio = df_envio.copy()
                df_envio["VENDEDOR_NOME"] = df_envio["Região de vendas"]
            else:
                st.error("Não encontrei a coluna do vendedor (VENDEDOR_NOME / Região de vendas).")
                st.stop()

        if sel_vendedor and len(sel_vendedor) > 0:
            vendedores = sel_vendedor
        else:
            vendedores = df_envio["VENDEDOR_NOME"].dropna().unique()

        if len(vendedores) == 0:
            st.warning("Não há vendedores disponíveis para envio (base filtrada ficou vazia).")
            st.stop()

        email_origem = st.secrets["email"]["sender_email"]
        senha_origem = st.secrets["email"]["sender_password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_origem, senha_origem)

        enviados = 0
        pulados = 0

        for vendedor in vendedores:
            vendedor_up = str(vendedor).strip().upper()
            email_destino = MAPA_EMAIL_VENDEDORES.get(vendedor_up)

            if not email_destino:
                st.warning(f"⚠️ Sem e-mail cadastrado para: {vendedor_up} (pulando)")
                pulados += 1
                continue

            if isinstance(email_destino, list):
                email_destino_str = ",".join([str(x).strip() for x in email_destino if str(x).strip()])
            else:
                email_destino_str = str(email_destino).strip()

            enviar_excel_vendedor(
                server=server,
                email_origem=email_origem,
                email_destino=email_destino_str,
                nome_vendedor=vendedor,
                df_excel=df_relatorio
            )
            enviados += 1

        server.quit()
        st.success(f"📨 E-mails enviados com sucesso! Enviados: {enviados} | Pulados (sem e-mail): {pulados}")

    # --- UI: CARDS E TABELA ---
    st.markdown("---")
    col_pace, col_cob, col_pos = st.columns([1.25, 1, 1])

    with col_pace:
        st.markdown(
            f"""
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                <small>PACING DO MÊS (Meta 2026)</small><br>
                <span style="font-size: 1.0em;">Meta mês: <b>{fmt_pt_int(meta_mes_2026)}</b></span><br>
                <span style="font-size: 1.0em;">Proj. mês: <b>{fmt_pt_int(projecao_mes)}</b></span><br>
                <span style="font-size: 1.0em;">Ritmo atual: <b>{fmt_pt_int(ritmo_atual)}</b>/dia útil</span><br>
                <span style="font-size: 1.0em;">Ritmo necessário: <b>{fmt_pt_int(ritmo_necessario)}</b>/dia útil</span><br>
                <span style="color:{cor_selo}; font-size: 1.4em; font-weight: 800;">{selo}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_cob:
        real_perc = (df_f[col_cod_cliente].nunique() / base_total * 100) if base_total > 0 else 0
        st.markdown(
            f"""
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                <small>COBERTURA ATUAL</small><br>
                <span style="font-size: 1.1em;">Base: <b>{fmt_pt_int(base_total)}</b></span><br>
                Atingido: <span style="color:#28a745; font-size: 1.8em; font-weight: bold;">{real_perc:.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_pos:
        if not (sel_supervisor or sel_vendedor) and ("EqVs" in df_f.columns):
            positivos_total = df_f.loc[~df_f["EqVs"].isin(["STR", "SMX"]), col_cod_cliente].nunique()
        else:
            positivos_total = df_f[col_cod_cliente].nunique()

        dados_pos = df_metas_cob[df_metas_cob["RG"].isin(vendedores_ids)].drop_duplicates("RG") if df_metas_cob is not None else pd.DataFrame()
        base_pos = pd.to_numeric(dados_pos["BASE"], errors="coerce").fillna(0).sum() if "BASE" in dados_pos.columns else 0

        meta_pos = pd.to_numeric(dados_pos["META"], errors="coerce").fillna(0).mean() if "META" in dados_pos.columns else 0
        meta_pos = (meta_pos / 100) if meta_pos > 1 else meta_pos

        meta_abs = math.ceil(base_pos * meta_pos) if base_pos > 0 else 0
        perc_pos = (positivos_total / meta_abs * 100) if meta_abs > 0 else 0

        st.markdown(
            f"""
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                <small>POSITIVAÇÃO</small><br>
                <span style="font-size: 1.1em;">Meta: <b>{meta_pos:.0%}</b></span><br>
                <span style="font-size: 1.1em;">Positivados: <b>{fmt_pt_int(positivos_total)}</b></span><br>
                Atingido: <span style="color:#1f77b4; font-size: 1.8em; font-weight: bold;">{perc_pos:.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### 📈 Desempenho por Hierarquia")

    df_view = df_final.copy()
    df_view[" "] = ""
    df_view["  "] = ""
    df_view["   "] = ""
    df_view["    "] = ""

    cols_view = [
        "TENDÊNCIA",
        "HIERARQUIA DE PRODUTOS",
        "META COBERTURA",
        "CLIENTES",
        "POSITIVAÇÃO",
        "PENDÊNCIA",
        " ",
        "META 2025",
        "META 2026",
        "  ",
        "VOLUME",
        "   ",
        "CRESC 2025",
        "% (VOL 2025)",
        "    ",
        "CRESC 2026",
        "% (VOL 2026)",
    ]

    def zebra_rows(row):
        return ["background-color: #FAFAFA" if row.name % 2 else "" for _ in row]

    def destacar_negativos(s):
        return ["background-color: #FFE5E5; color: #7A0000; font-weight: 600" if v < 0 else "" for v in s]

    def destacar_pendencia(s):
        return ["background-color: #FFD6D6; color: #7A0000; font-weight: 700" if v > 0 else "" for v in s]

    def destacar_tendencia(s):
        out = []
        for v in s:
            if v == "📈":
                out.append("background-color: #E8F5E9; font-weight: 900;")
            elif v == "📉":
                out.append("background-color: #FFEBEE; font-weight: 900;")
            else:
                out.append("background-color: #F7F7F7; font-weight: 900;")
        return out

    def limpar_espacos(s):
        return ["background-color: transparent" for _ in s]

    sty = (
        df_view[cols_view]
        .sort_values(by="HIERARQUIA DE PRODUTOS")
        .style
        .format(
            {
                "META COBERTURA": "{:.0%}",
                "CLIENTES": lambda v: fmt_pt_int(v),
                "POSITIVAÇÃO": lambda v: fmt_pt_int(v),
                "PENDÊNCIA": lambda v: fmt_pt_int(v),
                "META 2025": lambda v: fmt_pt_int(v),
                "META 2026": lambda v: fmt_pt_int(v),
                "VOLUME": lambda v: fmt_pt_int(v),
                "CRESC 2025": lambda v: fmt_pt_int(v),
                "CRESC 2026": lambda v: fmt_pt_int(v),
                "% (VOL 2025)": "{:.1f}%",
                "% (VOL 2026)": "{:.1f}%",
            }
        )
        .apply(zebra_rows, axis=1)
        .apply(destacar_tendencia, subset=["TENDÊNCIA"])
        .apply(destacar_pendencia, subset=["PENDÊNCIA"])
        .apply(destacar_negativos, subset=["CRESC 2025", "CRESC 2026"])
        .apply(limpar_espacos, subset=[" ", "  ", "   ", "    "])
        .set_table_styles(
            [
                {"selector": "th", "props": [("background-color", "#F2F2F2"), ("color", "#111"), ("font-weight", "700")]},
                {"selector": "td", "props": [("border-bottom", "1px solid #EEE")]},
            ]
        )
    )

    st.dataframe(
        sty,
        use_container_width=True,
        hide_index=True,
        height=560,
    )

    # ============================
    # ✅ ADIÇÕES (RANKINGS)  -- (mantive o restante do seu código igual)
    # ============================
    try:
        st.markdown("---")
        st.markdown("## 📌 Quem está puxando pra cima e pra baixo")

        df_rank_real = (
            df_f.groupby(["VENDEDOR_COD", "VENDEDOR_NOME"])
            .agg(
                VOLUME_REAL=("QTD_VENDAS", "sum"),
                POSITIVADOS=(col_cod_cliente, "nunique")
            )
            .reset_index()
        )

        df_meta_v25 = (
            df_2025[df_2025["RG"].isin(vendedores_ids)]
            .groupby("RG")["QUANTIDADE"].sum()
            .reset_index()
            .rename(columns={"RG": "VENDEDOR_COD", "QUANTIDADE": "META_TOTAL_2025"})
            if df_2025 is not None and not df_2025.empty and "RG" in df_2025.columns and "QUANTIDADE" in df_2025.columns
            else pd.DataFrame(columns=["VENDEDOR_COD", "META_TOTAL_2025"])
        )

        df_meta_v26 = (
            df_meta_sistema[df_meta_sistema["RG"].isin(vendedores_ids)]
            .groupby("RG")["QTD"].sum()
            .reset_index()
            .rename(columns={"RG": "VENDEDOR_COD", "QTD": "META_TOTAL_2026"})
            if df_meta_sistema is not None and not df_meta_sistema.empty and "RG" in df_meta_sistema.columns and "QTD" in df_meta_sistema.columns
            else pd.DataFrame(columns=["VENDEDOR_COD", "META_TOTAL_2026"])
        )

        df_pos_meta = (
            df_metas_cob[df_metas_cob["RG"].isin(vendedores_ids)]
            .drop_duplicates("RG")
            .copy()
            if df_metas_cob is not None and not df_metas_cob.empty and "RG" in df_metas_cob.columns
            else pd.DataFrame(columns=["RG", "BASE", "META"])
        )

        if not df_pos_meta.empty:
            df_pos_meta.rename(columns={"RG": "VENDEDOR_COD"}, inplace=True)
            if "META" in df_pos_meta.columns:
                df_pos_meta["META"] = df_pos_meta["META"].apply(lambda x: x / 100 if x > 1 else x)
            if ("BASE" in df_pos_meta.columns) and ("META" in df_pos_meta.columns):
                df_pos_meta["META_ABS_POSIT"] = (df_pos_meta["BASE"] * df_pos_meta["META"]).apply(lambda x: math.ceil(x) if x > 0 else 0)
            else:
                df_pos_meta["META_ABS_POSIT"] = 0
        else:
            df_pos_meta = pd.DataFrame(columns=["VENDEDOR_COD", "META_ABS_POSIT"])

        df_rank = df_rank_real.merge(df_meta_v25, on="VENDEDOR_COD", how="left")
        df_rank = df_rank.merge(df_meta_v26, on="VENDEDOR_COD", how="left")
        df_rank = df_rank.merge(
            df_pos_meta[["VENDEDOR_COD", "META_ABS_POSIT"]] if "META_ABS_POSIT" in df_pos_meta.columns else df_pos_meta,
            on="VENDEDOR_COD",
            how="left"
        )
        df_rank[["META_TOTAL_2025", "META_TOTAL_2026", "META_ABS_POSIT"]] = df_rank[["META_TOTAL_2025", "META_TOTAL_2026", "META_ABS_POSIT"]].fillna(0)

        df_rank["ATINGIMENTO_VOL_2025"] = (df_rank["VOLUME_REAL"] / df_rank["META_TOTAL_2025"]).replace([np.inf, -np.inf], 0).fillna(0)
        df_rank["ATINGIMENTO_VOL_2026"] = (df_rank["VOLUME_REAL"] / df_rank["META_TOTAL_2026"]).replace([np.inf, -np.inf], 0).fillna(0)
        df_rank["ATINGIMENTO_POSIT"] = (df_rank["POSITIVADOS"] / df_rank["META_ABS_POSIT"]).replace([np.inf, -np.inf], 0).fillna(0)

        st.markdown("### 📦 Ranking — Volume x Meta 2025")
        rank_2025 = df_rank.sort_values("ATINGIMENTO_VOL_2025", ascending=False)

        top_2025 = rank_2025.head(10)[["VENDEDOR_NOME", "VOLUME_REAL", "META_TOTAL_2025", "ATINGIMENTO_VOL_2025"]]
        bot_2025 = rank_2025.tail(10).sort_values("ATINGIMENTO_VOL_2025")[["VENDEDOR_NOME", "VOLUME_REAL", "META_TOTAL_2025", "ATINGIMENTO_VOL_2025"]]

        c25_1, c25_2 = st.columns(2)
        with c25_1:
            st.markdown("**🟢 Puxando pra cima (2025)**")
            st.dataframe(
                top_2025.style.format({
                    "VOLUME_REAL": lambda v: fmt_pt_int(v),
                    "META_TOTAL_2025": lambda v: fmt_pt_int(v),
                    "ATINGIMENTO_VOL_2025": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True
            )
        with c25_2:
            st.markdown("**🔴 Puxando pra baixo (2025)**")
            st.dataframe(
                bot_2025.style.format({
                    "VOLUME_REAL": lambda v: fmt_pt_int(v),
                    "META_TOTAL_2025": lambda v: fmt_pt_int(v),
                    "ATINGIMENTO_VOL_2025": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### 📦 Ranking — Volume x Meta 2026")
        rank_2026 = df_rank.sort_values("ATINGIMENTO_VOL_2026", ascending=False)

        top_2026 = rank_2026.head(10)[["VENDEDOR_NOME", "VOLUME_REAL", "META_TOTAL_2026", "ATINGIMENTO_VOL_2026"]]
        bot_2026 = rank_2026.tail(10).sort_values("ATINGIMENTO_VOL_2026")[["VENDEDOR_NOME", "VOLUME_REAL", "META_TOTAL_2026", "ATINGIMENTO_VOL_2026"]]

        c26_1, c26_2 = st.columns(2)
        with c26_1:
            st.markdown("**🟢 Puxando pra cima (2026)**")
            st.dataframe(
                top_2026.style.format({
                    "VOLUME_REAL": lambda v: fmt_pt_int(v),
                    "META_TOTAL_2026": lambda v: fmt_pt_int(v),
                    "ATINGIMENTO_VOL_2026": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True
            )
        with c26_2:
            st.markdown("**🔴 Puxando pra baixo (2026)**")
            st.dataframe(
                bot_2026.style.format({
                    "VOLUME_REAL": lambda v: fmt_pt_int(v),
                    "META_TOTAL_2026": lambda v: fmt_pt_int(v),
                    "ATINGIMENTO_VOL_2026": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### 🎯 Ranking — Positivação")
        rank_pos = df_rank.sort_values("ATINGIMENTO_POSIT", ascending=False)

        top_pos = rank_pos.head(10)[["VENDEDOR_NOME", "POSITIVADOS", "META_ABS_POSIT", "ATINGIMENTO_POSIT"]]
        bot_pos = rank_pos.tail(10).sort_values("ATINGIMENTO_POSIT")[["VENDEDOR_NOME", "POSITIVADOS", "META_ABS_POSIT", "ATINGIMENTO_POSIT"]]

        cp_1, cp_2 = st.columns(2)
        with cp_1:
            st.markdown("**🟢 Puxando pra cima (Positivação)**")
            st.dataframe(
                top_pos.style.format({
                    "POSITIVADOS": lambda v: fmt_pt_int(v),
                    "META_ABS_POSIT": lambda v: fmt_pt_int(v),
                    "ATINGIMENTO_POSIT": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True
            )
        with cp_2:
            st.markdown("**🔴 Puxando pra baixo (Positivação)**")
            st.dataframe(
                bot_pos.style.format({
                    "POSITIVADOS": lambda v: fmt_pt_int(v),
                    "META_ABS_POSIT": lambda v: fmt_pt_int(v),
                    "ATINGIMENTO_POSIT": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.warning(f"Não foi possível gerar os rankings finais: {e}")

    # Exportação
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Dashboard")
    st.download_button("📥 Baixar Excel", buffer.getvalue(), "relatorio.xlsx", "application/vnd.ms-excel")
    st.markdown("---")




    # ===========================================================
    # ✅ BLOCO DUPLICADO DO SEU CÓDIGO (MANTIDO, MAS NÃO EXECUTA)
    # Se isso rodar, você lê/reescreve tudo duas vezes e volta o bug.
    # ===========================================================
   



# --- PÁGINA: APROVAÇÕES ---
elif menu_interna == "🔔 Aprovações":
    st.header("🔔 Agendamentos Pendentes de Aprovação")
    
    # SEGURANÇA: Se por algum erro de estado um vendedor/supervisor cair aqui, bloqueia.
    if not eh_gestao:
        st.error("Você não tem permissão para acessar esta página.")
        st.stop()

    # Filtrar apenas os pendentes e respeitar a hierarquia
    if is_admin:
        # Admin vê todos os pendentes
        df_pendentes = df_agenda[df_agenda["STATUS"] == "Pendente"].copy()
    else:
        # Analista vê apenas os pendentes atribuídos a ele
        # Certifique-se que a coluna 'ANALISTA' existe na sua planilha
        df_pendentes = df_agenda[
            (df_agenda["STATUS"] == "Pendente") &
            (df_agenda["ANALISTA"] == user_atual)
        ].copy()
    
    # ✅ SLICER / FILTRO DE VENDEDOR
    df_pendentes_filtrado = df_pendentes.copy()
    if not df_pendentes_filtrado.empty and "VENDEDOR" in df_pendentes_filtrado.columns:
        op_vend = sorted(df_pendentes_filtrado["VENDEDOR"].dropna().astype(str).unique())
        vend_sel = st.multiselect("Filtrar por Vendedor:", op_vend, key="filtro_vendedor_aprovacoes")
        if vend_sel:
            df_pendentes_filtrado = df_pendentes_filtrado[
                df_pendentes_filtrado["VENDEDOR"].isin(vend_sel)
            ].copy()

    if df_pendentes_filtrado.empty:
        st.success("Não há agendamentos aguardando sua aprovação!")
    else:
        st.warning(f"Existem {len(df_pendentes_filtrado)} agendamentos aguardando sua ação.")
        
        # ✅ BOTÕES: APROVAR / REPROVAR TUDO (do que estiver visível após filtro)
        c1, c2 = st.columns(2)

        if c1.button("✅ Aprovar tudo (filtrado)", use_container_width=True, key="btn_aprovar_tudo_aprovacoes"):
            ids_aprovar = df_pendentes_filtrado["ID"].astype(str).tolist()
            if ids_aprovar:
                df_agenda.loc[
                    df_agenda["ID"].astype(str).isin(ids_aprovar),
                    ["STATUS", "APROVACAO"]
                ] = ["Agendado", "Aprovado"]

                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                st.cache_data.clear()
                st.success(f"✅ {len(ids_aprovar)} agendamentos aprovados!")
                st.rerun()

        if c2.button("❌ Reprovar tudo (filtrado)", use_container_width=True, key="btn_reprovar_tudo_aprovacoes"):
            ids_reprovar = df_pendentes_filtrado["ID"].astype(str).tolist()
            if ids_reprovar:
                df_agenda.loc[
                    df_agenda["ID"].astype(str).isin(ids_reprovar),
                    ["STATUS", "APROVACAO"]
                ] = ["Reprovado", "Reprovado"]

                conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                st.cache_data.clear()
                st.error(f"❌ {len(ids_reprovar)} agendamentos reprovados!")
                st.rerun()
        
        for i, row in df_pendentes_filtrado.iterrows():
            with st.expander(f"📍 {row['VENDEDOR']} -> {row['CLIENTE']} ({row['DATA']})"):
                col1, col2 = st.columns(2)
                
                # Botão para Aprovar
                if col1.button("✅ Aprovar", key=f"aprov_{row['ID']}"):
                    # Atualiza no DataFrame principal usando o ID único
                    df_agenda.loc[df_agenda["ID"] == row["ID"], ["STATUS", "APROVACAO"]] = ["Agendado", "Aprovado"]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                    st.success(f"Agendamento de {row['CLIENTE']} aprovado!")
                    st.cache_data.clear()
                    st.rerun()
                
                # Botão para Recusar
                if col2.button("❌ Recusar", key=f"recus_{row['ID']}"):
                    df_agenda.loc[df_agenda["ID"] == row["ID"], ["STATUS", "APROVACAO"]] = ["Reprovado", "Reprovado"]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                    st.error(f"Agendamento de {row['CLIENTE']} recusado.")
                    st.cache_data.clear()
                    st.rerun()


# --- PÁGINA: KPI APROVAÇÃO POR ANALISTA ---
elif menu == "📊 KPI Aprovação Analistas":

    # Segurança extra
    if not (is_admin or is_diretoria):
        st.error("Você não tem permissão para acessar esta página.")
        st.stop()

    st.header("📊 KPI de Aprovação por Analista")

    if df_agenda is None or df_agenda.empty:
        st.warning("Nenhum dado disponível para análise.")
        st.stop()

    # Garantia de coluna
    if 'APROVACAO' not in df_agenda.columns:
        st.warning("Coluna APROVACAO não encontrada.")
        st.stop()

    # Normalização
    df_agenda['APROVACAO'] = (
        df_agenda['APROVACAO']
        .fillna("Pendente")
        .astype(str)
    )

    # Base apenas com decisões tomadas
    df_decisoes = df_agenda[
        df_agenda['APROVACAO'].isin(['Aprovado', 'Reprovado'])
    ].copy()

    if df_decisoes.empty:
        st.info("Ainda não há agendamentos avaliados.")
        st.stop()

    # KPI por analista
    kpi_analista = (
        df_decisoes
        .groupby('ANALISTA')
        .agg(
            total_avaliados=('APROVACAO', 'count'),
            aprovados=('APROVACAO', lambda x: (x == 'Aprovado').sum()),
            reprovados=('APROVACAO', lambda x: (x == 'Reprovado').sum())
        )
        .reset_index()
    )

    kpi_analista['taxa_aprovacao'] = (
        kpi_analista['aprovados'] / kpi_analista['total_avaliados'] * 100
    ).round(1)

    # --- KPIs GERAIS ---
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "📌 Total Avaliações",
        int(kpi_analista['total_avaliados'].sum())
    )

    col2.metric(
        "✅ Taxa Média de Aprovação",
        f"{kpi_analista['taxa_aprovacao'].mean():.1f}%"
    )

    col3.metric(
        "👤 Analistas Ativos",
        kpi_analista['ANALISTA'].nunique()
    )

    st.markdown("---")

    # --- TABELA ---
    st.subheader("📋 Performance por Analista")

    df_show = kpi_analista.sort_values(
        by='taxa_aprovacao',
        ascending=False
    ).reset_index(drop=True)

    st.dataframe(
        df_show,
        use_container_width=True
    )

    # --- EXPORTAÇÃO ---
    with st.expander("📤 Exportar Relatório"):
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            st.download_button(
                "📥 Exportar Excel",
                converter_para_excel(df_show),
                file_name="kpi_aprovacao_analistas.xlsx"
            )

        with col_e2:
            st.download_button(
                "📄 Exportar PDF",
                gerar_pdf(df_show, tipo_relatorio="KPI_ANALISTA"),
                file_name="kpi_aprovacao_analistas.pdf"
            )
