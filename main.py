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
    for col in ['ATINGIMENTO % (VOL 2025)', 'ATINGIMENTO % (VOL 2026)']:
        if col in df_export.columns:
            df_export[col] = pd.to_numeric(df_export[col], errors='coerce').fillna(0) / 100

    # ✅ ORDEM FINAL + COLUNAS EM BRANCO (ESPAÇOS)
    # Obs: colunas "EM BRANCO" serão criadas só no Excel
    ordem_colunas = [
        "HIERARQUIA DE PRODUTOS",
        "META COBERTURA",
        "META CLIENTES (ABS)",
        "POSITIVAÇÃO",
        "PENDÊNCIA CLIENTES",
        "META 2025",
        "META 2026",
        "VOLUME",
        " ",  # espaço 1 (depois do VOLUME)
        "CRESCIMENTO 2025",
        "ATINGIMENTO % (VOL 2025)",
        "  ",  # espaço 2 (entre 2025 e 2026)
        "CRESCIMENTO 2026",
        "ATINGIMENTO % (VOL 2026)",
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
        grp1_cols = ["META COBERTURA", "META CLIENTES (ABS)", "POSITIVAÇÃO", "PENDÊNCIA CLIENTES"]
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
            "ATINGIMENTO % (VOL 2025)",
            "ATINGIMENTO % (VOL 2026)",
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
    import numpy as np

    def _to_float(v):
        try:
            if v is None:
                return None
            s = str(v).strip()
            if not s or s.lower() in ["nan", "none"]:
                return None

            # remove espaços
            s = s.replace(" ", "")

            # se vier no formato "lat,lon" por engano, separa
            # (não é o seu caso padrão, mas evita bug)
            if "," in s and s.count(",") == 1 and s.count(".") >= 1:
                # aqui pode ser "lat,lon" OU "10,5" (decimal pt-br)
                # decide: se tem ponto também, provavelmente é separador de coord.
                # então NÃO troca vírgula por ponto.
                pass
            elif s.count(",") == 1 and s.count(".") == 0:
                # decimal pt-br -> troca por ponto
                s = s.replace(",", ".")

            return float(s)
        except:
            return None

    lat1 = _to_float(lat1)
    lon1 = _to_float(lon1)
    lat2 = _to_float(lat2)
    lon2 = _to_float(lon2)

    # Se algum valor não vier válido, retorna 0 (igual teu comportamento atual de “não calcular”)
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0

    # Raio da Terra em KM
    R = 6371.0

    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    distancia = R * c * 1000  # Metros
    return float(distancia)


# --- CONFIGURAÇÃO DE COOKIES (Lembrar Login) ---
# O password abaixo é apenas para criptografia local do cookie
cookies = EncryptedCookieManager(password="marata_secret_key_2026")
if not cookies.ready():
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Maratá - GVP", page_icon="📅", layout="wide")

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
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
            <img src="https://raw.githubusercontent.com/lycioandreatto/marata/main/pngmarata" width="60">
            <h1 style="color: #000C75; margin: 0;">GESTÃO DE VISITAS PDV</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_login, tab_cadastro = st.tabs(["Login", "Novo Cadastro"])
    
    with tab_login:
        with st.form("login_form"):
            u_login = st.text_input("Usuário:").strip().upper()
            p_login = st.text_input("Senha:", type="password")
            lembrar = st.checkbox("Manter conectado")
            if st.form_submit_button("Entrar"):
                if "USUARIO" in df_usuarios.columns and "SENHA" in df_usuarios.columns:
                    valid = df_usuarios[(df_usuarios['USUARIO'].str.upper() == u_login) & (df_usuarios['SENHA'].astype(str) == p_login)]
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
                            existente = u_cad in df_usuarios['USUARIO'].str.upper().values
                        
                        if not existente:
                            novo_user = pd.DataFrame([{"USUARIO": u_cad, "SENHA": p_cad}])
                            df_final_u = pd.concat([df_usuarios, novo_user], ignore_index=True)
                            conn.update(spreadsheet=url_planilha, worksheet="USUARIOS", data=df_final_u)
                            st.cache_data.clear()
                            st.success("Cadastro realizado!")
                        else:
                            st.error("Este usuário já está cadastrado.")
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
    
    if eh_gestao:
        opcoes_menu.append("📊 Dashboard de Controle")
        opcoes_menu.append("📊 KPI Aprovação Analistas")  # ✅ NOVA OPÇÃO
    
    menu = st.selectbox("Menu Principal", opcoes_menu)
    
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

        # ✅ (NOVO) Permissão de validação: Gestão + Analista
        pode_validar = (is_admin or is_diretoria or is_analista)

        # --- LIMPEZA ---
        df_agenda = df_agenda.drop_duplicates(
            subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'], 
            keep='first'
        ).reset_index(drop=True)

        col_aprov_plan = next(
            (c for c in df_agenda.columns if ("APROVA" in c.upper() and "PLAN" in c.upper()) or c.upper() == "APROVACAO"),
            "APROVACAO"
        )
        col_aprov_exec = "VALIDACAO_GESTAO"
        col_just = "JUSTIFICATIVA"
        
        if col_aprov_exec not in df_agenda.columns:
            df_agenda[col_aprov_exec] = "PENDENTE"
        if col_just not in df_agenda.columns:
            df_agenda[col_just] = ""

        # --- FILTRO DO DIA ---
        df_dia = df_agenda[df_agenda['DATA'] == hoje_str].copy()
        df_dia = df_dia[df_dia[col_aprov_plan].astype(str).str.upper() == "APROVADO"]

        # --- CONTROLE DE ACESSO ---
        if not (is_admin or is_diretoria):
            if is_analista:
                df_dia = df_dia[df_dia['ANALISTA'].str.upper() == user_atual.upper()]
            elif is_supervisor:
                df_dia = df_dia[df_dia['SUPERVISOR'].str.upper() == user_atual.upper()]
            else:
                df_dia = df_dia[df_dia['VENDEDOR'].str.upper() == user_atual.upper()]

        df_dia = df_dia.reset_index(drop=True)

        # --- SLICERS (GESTÃO / ANALISTA) ---
        if pode_validar:
            st.markdown("### 🔍 Filtros")
            f1, f2 = st.columns(2)

            with f1:
                sup_sel = st.multiselect(
                    "Supervisor",
                    sorted(df_dia['SUPERVISOR'].dropna().unique())
                )
            if sup_sel:
                df_dia = df_dia[df_dia['SUPERVISOR'].isin(sup_sel)]

            with f2:
                vend_sel = st.multiselect(
                    "Vendedor",
                    sorted(df_dia['VENDEDOR'].dropna().unique())
                )
            if vend_sel:
                df_dia = df_dia[df_dia['VENDEDOR'].isin(vend_sel)]

        # --- MÉTRICAS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Aprovados p/ Hoje", len(df_dia))
        m2.metric("Realizados", len(df_dia[df_dia['STATUS'] == "Realizado"]))
        m3.metric("Validados", len(df_dia[df_dia[col_aprov_exec] == "OK"]))
        m4.metric("Reprovados", len(df_dia[df_dia[col_aprov_exec] == "REPROVADO"]), delta_color="inverse")

        # --- BOTÃO APROVAR EM MASSA (GESTÃO + ANALISTA) ---
        if pode_validar and not df_dia.empty:
            if st.button("✅ APROVAR TODAS AS VISITAS REALIZADAS", use_container_width=True):
                ids = df_dia[df_dia['STATUS'] == "Realizado"]['ID'].tolist()
                if ids:
                    df_agenda.loc[df_agenda['ID'].isin(ids), col_aprov_exec] = "OK"
                    conn.update(
                        spreadsheet=url_planilha,
                        worksheet="AGENDA",
                        data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA'], errors='ignore')
                    )
                    st.success("Todas as visitas realizadas foram aprovadas!")
                    time.sleep(1)
                    st.rerun()

        # --- TABELA ---
        if not df_dia.empty:
            if df_base is not None:
                df_cidades = df_base[['Cliente', 'Local']].drop_duplicates('Cliente')
                df_dia = df_dia.merge(
                    df_cidades,
                    left_on='CÓDIGO CLIENTE',
                    right_on='Cliente',
                    how='left'
                ).rename(columns={'Local': 'CIDADE'})

            cols_v = ['EDITAR', 'VENDEDOR', 'CLIENTE', 'CIDADE', 'STATUS', 'JUSTIFICATIVA']

            # ✅ (AJUSTE) Auditoria só aparece para quem pode validar
            if pode_validar:
                cols_v.append(col_aprov_exec)
                cols_v.append('DISTANCIA_LOG')

            df_dia["EDITAR"] = False
            df_display = df_dia[[c for c in cols_v if c in df_dia.columns or c == "EDITAR"]]

            edicao_dia = st.data_editor(
                df_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "EDITAR": st.column_config.CheckboxColumn("📝"),
                    col_aprov_exec: st.column_config.SelectboxColumn(
                        "AUDITORIA", options=["PENDENTE", "OK", "REPROVADO"]
                    ),
                },
                # ✅ (AJUSTE) Todo mundo pode clicar em EDITAR.
                # Quem NÃO pode validar não edita auditoria (e auditoria nem aparece).
                disabled=[c for c in df_display.columns if c not in (["EDITAR", col_aprov_exec] if pode_validar else ["EDITAR"])]
            )

            # --- EDIÇÃO INDIVIDUAL ---
            marcados = edicao_dia[edicao_dia["EDITAR"] == True]
            if not marcados.empty:
                idx = marcados.index[0]
                sel_row = df_dia.iloc[idx]

                st.markdown("---")
                st.subheader(f"⚙️ Detalhes: {sel_row['CLIENTE']}")

                # ✅ Vendedor pode marcar realizado
                status_list = ["Planejado", "Realizado", "Reagendado"]
                status_atual = sel_row['STATUS'] if sel_row['STATUS'] in status_list else "Planejado"
                novo_status = st.selectbox(
                    "Status:",
                    status_list,
                    index=status_list.index(status_atual)
                )

                # ✅ Só quem valida vê auditoria
                val_list = ["PENDENTE", "OK", "REPROVADO"]
                valor_atual = str(sel_row.get(col_aprov_exec, "PENDENTE")).strip().upper()
                if valor_atual not in val_list:
                    valor_atual = "PENDENTE"

                if pode_validar:
                    nova_val = st.selectbox(
                        "Validar:",
                        val_list,
                        index=val_list.index(valor_atual)
                    )
                else:
                    nova_val = valor_atual  # mantém como está


                # ✅✅✅ AJUSTE PEDIDO: VOLTAR MENU DE OBSERVAÇÕES (pré-selecionadas)
                opcoes_obs = [
                    "Selecione...",
                    "Pedido enviado",
                    "Cliente Inadimplente",
                    "Cliente fechado",
                    "Cliente inativo",
                    "Cliente sem limite de crédito",
                    "Outro (digitar)"
                ]

                just_atual = str(sel_row.get(col_just, "") or "").strip()

                # tenta pré-selecionar se a justificativa atual for igual a alguma opção
                idx_padrao = 0
                for i, opt in enumerate(opcoes_obs):
                    if just_atual.upper() == opt.upper():
                        idx_padrao = i
                        break

                obs_sel = st.selectbox(
                    "Observações:",
                    opcoes_obs,
                    index=idx_padrao,
                    key="obs_pre_def"
                )

                # se escolher "Outro", libera digitação; senão permite editar o texto mas já vem preenchido
                if obs_sel == "Outro (digitar)":
                    nova_just = st.text_input("Justificativa:", value=just_atual, key="just_txt")
                elif obs_sel != "Selecione...":
                    nova_just = st.text_input("Justificativa:", value=obs_sel, key="just_txt")
                else:
                    nova_just = st.text_input("Justificativa:", value=just_atual, key="just_txt")
                # ✅✅✅ FIM DO AJUSTE


                if st.button("💾 SALVAR ATUALIZAÇÃO"):
                    lat_v = st.session_state.get('lat', 0)
                    lon_v = st.session_state.get('lon', 0)
                    distancia_m = 0

                    try:
                        base_cliente = df_base[df_base['Cliente'].astype(str) == str(sel_row['CÓDIGO CLIENTE'])]
                        if not base_cliente.empty and 'COORDENADAS' in base_cliente.columns:
                            coord = base_cliente.iloc[0]['COORDENADAS']
                        if isinstance(coord, str) and ',' in coord:
                                    lat_c, lon_c = coord.split(',', 1)
                                    distancia_m = calcular_distancia(
                                            lat_c.strip(),
                                                lon_c.strip(),
                                                    lat_v,
                                                        lon_v
                    )

                    except:
                        distancia_m = 0

                    df_agenda.loc[
                        df_agenda['ID'] == str(sel_row['ID']),
                        ['STATUS', col_aprov_exec, col_just, 'COORDENADAS', 'DISTANCIA_LOG']
                    ] = [
                        novo_status,
                        nova_val,
                        nova_just,
                        f"{lat_v}, {lon_v}",
                        round(distancia_m, 1)
                    ]

                    conn.update(
                        spreadsheet=url_planilha,
                        worksheet="AGENDA",
                        data=df_agenda.drop(columns=['LINHA', 'DT_COMPLETA'], errors='ignore')
                    )

                    st.success("Dados atualizados!")
                    time.sleep(1)
                    st.rerun()

            # ============================
            # 🗺️ MAPA (NOVO - AO FINAL)
            # ============================
            st.markdown("---")
            st.markdown("### 🗺️ Mapa das Visitas do Dia")

            try:
                if df_base is not None and ("COORDENADAS" in df_base.columns):

                    # 🔧 COORDENADAS DA BASE
                    df_coords = df_base[['Cliente', 'COORDENADAS']].drop_duplicates(subset='Cliente').copy()
                    df_coords = df_coords.rename(columns={"COORDENADAS": "COORDENADAS_BASE"})
                    df_coords['Cliente'] = df_coords['Cliente'].astype(str).str.strip()

                    df_map = df_dia.copy()
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

                        # --- CÍRCULO 1 KM (GARANTIDO) ---
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
                              # ✅ estilo público (não precisa token) -> não fica branco
                              map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
                         ),
                         use_container_width=True
                         )


                else:
                    st.info("Coluna COORDENADAS não encontrada na BASE.")

            except Exception as e:
                st.warning(f"Não foi possível renderizar o mapa: {e}")

        else:
            st.info("Nenhum agendamento para hoje.")
    else:
        st.info("Nenhum agendamento para hoje.")










                    
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

        # --- MAPA DE CALOR (ABAIXO DO RANKING) ---
        st.markdown("---")
        st.subheader("🔥 Mapa de Calor")
        
        # Adicionamos uma 'key' única para evitar o erro de ID duplicado
        tipo_mapa = st.radio(
            "Selecione a camada visual:", 
            ["Visitas Realizadas", "Faturamento (Pedidos)"], 
            horizontal=True,
            key="radio_mapa_dashboard" 
        )
        
        try:
            import folium
            from folium.plugins import HeatMap
            from streamlit_folium import st_folium
            
            if tipo_mapa == "Visitas Realizadas":
                df_mapa = df_agenda[(df_agenda['STATUS'] == "Realizado") & (df_agenda['COORDENADAS'].astype(str).str.contains(',', na=False))].copy()
            else:
                # df_comp é gerado no bloco de SKUS acima
                df_mapa = df_comp[(df_comp['Qtd_Pedidos'] > 0) & (df_comp['COORDENADAS'].astype(str).str.contains(',', na=False))].copy()
            
            if not df_mapa.empty:
                # Separa latitude e longitude da coluna única COORDENADAS
                df_mapa[['lat', 'lon']] = df_mapa['COORDENADAS'].str.split(',', expand=True).astype(float)
                
                # Centraliza o mapa
                centro = [df_mapa['lat'].mean(), df_mapa['lon'].mean()]
                m = folium.Map(location=centro, zoom_start=7, tiles="cartodbpositron")
                
                # Adiciona a camada de calor
                HeatMap(df_mapa[['lat', 'lon']].dropna().values.tolist(), radius=15).add_to(m)
                
                st_folium(m, width="100%", height=500, returned_objects=[])
            else:
                st.warning("Sem dados de coordenadas para exibir no mapa com o filtro selecionado.")
                
        except Exception as e: 
            st.info(f"Aguardando dados geográficos válidos para renderizar o mapa.")
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
                    (df_verif['STATUS'] == "Planejado")
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
            
            if 'VENDEDOR' not in df_agenda.columns: df_agenda['VENDEDOR'] = ""

            # Normalização para comparação
            df_agenda['CÓDIGO CLIENTE'] = df_agenda['CÓDIGO CLIENTE'].astype(str)
            clientes_f['Cliente'] = clientes_f['Cliente'].astype(str)

            # Consideramos agendados os que estão Planejados, Realizados ou aguardando Aprovação (Pendente)
            codigos_agendados = df_agenda[
                (df_agenda['VENDEDOR'] == ven_sel) & 
                (df_agenda['STATUS'].isin(['Planejado', 'Realizado', 'Pendente']))
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
                analista_vinc = "N/I"; supervisor_vinc = "N/I"

       
            lista_c = sorted(clientes_pendentes_ag.apply(lambda x: f"{x['Cliente']} - {x['Nome 1']}", axis=1).tolist())
            
            if not lista_c:
                st.success(f"✅ Todos os clientes de {ven_sel} já foram processados!")
            else:
                cliente_sel = st.selectbox("Selecione o Cliente:", ["Selecione..."] + lista_c)
                if cliente_sel != "Selecione...":
                    qtd_visitas = st.number_input("Quantidade de visitas (Máx 4):", min_value=1, max_value=4, value=1)
                    
                    with st.form("form_novo_v", clear_on_submit=True):
                        cols_datas = st.columns(qtd_visitas)
                        hoje_dt = datetime.now(fuso_br).date()
                        datas_sel = [cols_datas[i].date_input(f"Data {i+1}:", value=hoje_dt, min_value=hoje_dt, key=f"d_{i}") for i in range(qtd_visitas)]
                        
                        if st.form_submit_button("💾 ENVIAR PARA APROVAÇÃO"):
                            cod_c, nom_c = cliente_sel.split(" - ", 1)
                            agora = datetime.now(fuso_br)
                            novas_linhas = []
                            
                            for i, dt in enumerate(datas_sel):
                                nid = agora.strftime("%Y%m%d%H%M%S") + str(i)
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
                                    "STATUS": "Pendente", # <--- AQUI ESTÁ A MUDANÇA PARA O WORKFLOW
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

            # --- 5. MÉTRICAS ---
            # ✅ (NOVO) Card de "fora do raio" > 50 metros
            fora_raio_50m = int((df_user['DISTANCIA_LOG'] > 50).sum()) if 'DISTANCIA_LOG' in df_user.columns else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📅 Total Agendado", len(df_user))
            # Ajustado para mostrar o que está planejado (já aprovado)
            m2.metric("⏳ Em Aguardo", len(df_user[df_user['STATUS'] == "Planejado"]))
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
                            df_agenda.loc[mask & (df_agenda['STATUS'] == "Pendente"), 'STATUS'] = "Planejado"
                        
                        df_save = df_agenda.drop_duplicates(subset=['DATA', 'VENDEDOR', 'CÓDIGO CLIENTE', 'STATUS'])
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_save.drop(columns=['LINHA', 'DT_COMPLETA'], errors='ignore'))
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
                t1, t2, t3 = st.tabs(["⚖️ Aprovação", "🔄 Reagendar", "🗑️ Excluir"])
                
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
                                df_agenda.loc[df_agenda['ID'] == sel_row['ID'], 'STATUS'] = "Planejado"
                            
                            conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                            st.cache_data.clear(); st.success("Salvo!"); time.sleep(1); st.rerun()
                    else:
                        st.warning("Apenas gestores podem alterar a aprovação.")

                with t2:
                    n_data = st.date_input("Nova Data:", value=datetime.now(), key="date_reag")
                    if st.button("Confirmar Reagendamento"):
                        # Reagendamento volta para Planejado ou Pendente? 
                        # Aqui mantive Planejado como estava no seu código original
                        df_agenda.loc[df_agenda['ID'] == sel_row['ID'], ['DATA', 'STATUS', 'APROVACAO']] = [n_data.strftime('%d/%m/%Y'), "Planejado", "Pendente"]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
                        st.cache_data.clear(); st.success("Reagendado!"); time.sleep(1); st.rerun()
                
                with t3:
                    st.error("Atenção: Esta ação excluirá o registro permanentemente.")
                    if st.button("🗑️ CONFIRMAR EXCLUSÃO"):
                        df_agenda = df_agenda[df_agenda['ID'] != sel_row['ID']]
                        conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda.drop(columns=['LINHA','DT_COMPLETA'], errors='ignore'))
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

    # ✅ AJUSTE VISUAL: milhar com ponto (sem mexer em cálculo)
    def fmt_pt_int(v):
        try:
            return f"{float(v):,.0f}".replace(",", ".")
        except:
            return str(v)

    # ✅ (AJUSTE MÍNIMO) normaliza Cliente (coluna K) SEM PERDER 1 CLIENTE:
    # - NÃO transforma NaN em "nan"
    # - NÃO zera/descarta valores como "0" (porque pode existir cliente "0"/outra exceção)
    # - só faz strip e remove ".0" quando for valor válido (não nulo)
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

            # ✅ Cliente é a coluna K (índice 10) da aba FATURADO
            col_cod_cliente = df_faturado.columns[11]

            df_faturado["QTD_VENDAS"] = pd.to_numeric(df_faturado["QTD_VENDAS"], errors="coerce").fillna(0)
            df_faturado["VENDEDOR_COD"] = df_faturado["VENDEDOR_COD"].astype(str).str.replace(r"\.0$", "", regex=True)

            # ✅ (AJUSTE MÍNIMO) normaliza Cliente (coluna K) sem perder 1 cliente
            df_faturado = _norm_cliente(df_faturado, col_cod_cliente)

            df_relacao = df_base[["VENDEDOR","SUPERVISOR","ANALISTA"]].drop_duplicates("VENDEDOR")
            df_faturado = df_faturado.merge(
                df_relacao, left_on="VENDEDOR_NOME", right_on="VENDEDOR", how="left"
            )

        # ✅ (NECESSÁRIO) Garantir base_total e META CLIENTES/PENDÊNCIA (usadas na tabela/cards)
        if df_param_metas is not None:
            df_param_metas.columns = [str(c).strip() for c in df_param_metas.columns]
            if "BASE" in df_param_metas.columns:
                df_param_metas["BASE"] = pd.to_numeric(df_param_metas["BASE"], errors="coerce").fillna(0)
            if "EscrV" in df_param_metas.columns:
                df_param_metas["EscrV"] = df_param_metas["EscrV"].astype(str).str.strip()

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

        if df_meta_sistema is not None:
            df_meta_sistema.columns = [str(c).strip() for c in df_meta_sistema.columns]
            if "RG" in df_meta_sistema.columns:
                df_meta_sistema["RG"] = df_meta_sistema["RG"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            if "QTD" in df_meta_sistema.columns:
                df_meta_sistema["QTD"] = pd.to_numeric(df_meta_sistema["QTD"], errors="coerce").fillna(0)

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

    # ✅ (AJUSTE MÍNIMO) garante novamente Cliente normalizado após merge/cópia
    df_f = _norm_cliente(df_f, col_cod_cliente)

    # ============================
    # 🔒 CONTROLE DE ACESSO
    # ============================
    df_base_perm = df_base.copy()

    # ✅ normaliza nomes na BASE (permissões)
    for c in ["VENDEDOR","SUPERVISOR","ANALISTA"]:
        if c in df_base_perm.columns:
            df_base_perm[c] = df_base_perm[c].astype(str).str.strip().str.upper()

    # ✅ normaliza estado e analista na BASE (permissões) - prioridade EscrV, mas mantém Estado também
    if "EscrV" in df_base_perm.columns:
        df_base_perm["EscrV"] = df_base_perm["EscrV"].astype(str).str.strip().str.upper()
    if "Estado" in df_base_perm.columns:
        df_base_perm["Estado"] = df_base_perm["Estado"].astype(str).str.strip().str.upper()
    if "ANALISTA" in df_base_perm.columns and "ANALISTA" not in ["ANALISTA","Analista"]:
        pass
    if "ANALISTA" in df_base_perm.columns:
        df_base_perm["ANALISTA"] = df_base_perm["ANALISTA"].astype(str).str.strip().str.upper()

    # ✅ normaliza também no FATURADO (df_f), pra não bugar filtro
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

    # ✅ (AJUSTE) coluna de estado na BASE de permissão: agora prioriza EscrV; senão usa Estado
    col_estado_perm = "EscrV" if "EscrV" in df_base_perm.columns else ("Estado" if "Estado" in df_base_perm.columns else None)

    # ✅ (AJUSTE) estados do usuário (AGORA vale para vendedor, supervisor E analista)
    estados_usuario = None
    if col_estado_perm and (is_vendedor or is_supervisor or is_analista):
        if is_vendedor and "VENDEDOR" in df_base_perm.columns:
            estados_usuario = df_base_perm.loc[df_base_perm["VENDEDOR"] == user_atual, col_estado_perm].dropna().unique().tolist()
        elif is_supervisor and "SUPERVISOR" in df_base_perm.columns:
            estados_usuario = df_base_perm.loc[df_base_perm["SUPERVISOR"] == user_atual, col_estado_perm].dropna().unique().tolist()
        elif is_analista:
            # ✅ pega estado(s) do analista na BASE (se tiver)
            if "ANALISTA" in df_base_perm.columns:
                estados_usuario = df_base_perm.loc[df_base_perm["ANALISTA"] == user_atual, col_estado_perm].dropna().unique().tolist()

        if estados_usuario:
            estados_usuario = [str(x).strip().upper() for x in estados_usuario if str(x).strip()]
        else:
            estados_usuario = None

    # ✅ (NOVO - MÍNIMO) pega o ANALISTA do vendedor pela BASE usando NOME (VENDEDOR)
    analista_usuario = None
    if is_vendedor and ("VENDEDOR" in df_base_perm.columns) and ("ANALISTA" in df_base_perm.columns):
        tmp_analista = df_base_perm.loc[df_base_perm["VENDEDOR"] == user_atual, "ANALISTA"].dropna().unique().tolist()
        if tmp_analista:
            analista_usuario = str(tmp_analista[0]).strip().upper()
    # ✅ (NOVO - MÍNIMO) fallback: se não achou o analista na BASE, tenta achar no FATURADO (já mergeado)
    if is_vendedor and not analista_usuario:
        if ("VENDEDOR" in df_f.columns) and ("ANALISTA" in df_f.columns):
            tmp_a = df_f.loc[df_f["VENDEDOR"] == user_atual, "ANALISTA"].dropna().unique().tolist()
            if tmp_a:
                analista_usuario = str(tmp_a[0]).strip().upper()

    # ✅ (CONDIÇÕES) Admin/Diretoria veem tudo;
    # ✅ (AJUSTE) Analista agora filtra pelo ANALISTA + estado(s) dele(s) (evita ver outros estados)
    # ✅ (AJUSTE) Supervisor continua no estado dele (e pode ver equipe do estado)
    # ✅ (AJUSTE) Vendedor enxerga SOMENTE o que for do seu ANALISTA + estados dele (na BASE)
    if is_analista:
        if "ANALISTA" in df_f.columns:
            df_f = df_f[df_f["ANALISTA"] == user_atual]

        if col_estado_perm and estados_usuario:
            # mantém só vendedores do(s) estado(s) do analista na BASE
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
        # ✅ (AJUSTE MÍNIMO) regra do vendedor = analista dele + estados dele (na BASE)
        if analista_usuario:
            # 1) filtra df_f pelo analista do vendedor (garantia total)
            if "ANALISTA" in df_f.columns:
                df_f = df_f[df_f["ANALISTA"] == analista_usuario]

            # 2) estados do vendedor (se existirem na BASE) limitam o que ele enxerga
            if col_estado_perm and estados_usuario:
                vendedores_permitidos = df_base_perm.loc[
                    (df_base_perm["ANALISTA"] == analista_usuario) &
                    (df_base_perm[col_estado_perm].isin(estados_usuario)),
                    "VENDEDOR"
                ].dropna().unique().tolist()

                # garante o df_f também só nesses estados (pelo EscrV do faturado)
                if "EscrV" in df_f.columns:
                    df_f = df_f[df_f["EscrV"].isin(estados_usuario)]
            else:
                # se não tiver estado definido pro vendedor na BASE, mais restrito possível: ele mesmo
                vendedores_permitidos = [user_atual]
        else:
            # fallback: mais restrito possível
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
    # 🔍 FILTROS
    # ============================
    st.markdown("### 🔍 Filtros")
    c1, c2, c3 = st.columns(3)

    # ✅ (AJUSTE) Estado no FATURADO é EscrV. Se não existir, cai para None.
    col_estado = "EscrV" if "EscrV" in df_f.columns else None

    # ✅ garante que df_f fique somente no(s) estado(s) do usuário
    if col_estado and (is_vendedor or is_supervisor or is_analista) and estados_usuario:
        df_f[col_estado] = df_f[col_estado].astype(str).str.strip().str.upper()
        df_f = df_f[df_f[col_estado].isin(estados_usuario)]

    with c1:
        if col_estado:
            # ✅ BLOQUEIO: vendedor/supervisor NÃO podem trocar estado (fica travado no(s) estado(s) permitido(s))
            if (is_vendedor or is_supervisor) and estados_usuario:
                sel_estado = st.multiselect(
                    "Estado",
                    sorted(estados_usuario),
                    default=sorted(estados_usuario),
                    disabled=True
                )
            # ✅ analista continua podendo ver só o(s) dele(s), mas se quiser deixar editável pra analista, mantém como estava:
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
    # BASE TOTAL (NECESSÁRIA PARA CARDS/TABELA)
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
    # PROCESSAMENTO FINAL
    # ============================
    df_agrup_f = (
        df_f.groupby("HIERARQUIA")
        .agg({"QTD_VENDAS":"sum", col_cod_cliente:"nunique"})
        .rename(columns={"QTD_VENDAS":"VOLUME", col_cod_cliente:"POSITIVAÇÃO"})
        .reset_index()
    )

    # Metas 2025/2026 por RG (se existirem)
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

    # ✅ colunas que seu layout usa
    df_final["META CLIENTES (ABS)"] = (df_final["META COBERTURA"] * base_total).apply(math.ceil) if base_total > 0 else 0
    df_final["PENDÊNCIA CLIENTES"] = (df_final["META CLIENTES (ABS)"] - df_final["POSITIVAÇÃO"]).apply(lambda x: x if x > 0 else 0)
    df_final["CRESCIMENTO 2025"] = df_final["VOLUME"] - df_final.get("META 2025", 0)
    df_final["ATINGIMENTO % (VOL 2025)"] = (df_final["VOLUME"] / df_final.get("META 2025", 0) * 100).replace([np.inf, -np.inf], 0).fillna(0)
    df_final["CRESCIMENTO 2026"] = df_final["VOLUME"] - df_final.get("META 2026", 0)
    df_final["ATINGIMENTO % (VOL 2026)"] = (df_final["VOLUME"] / df_final.get("META 2026", 0) * 100).replace([np.inf, -np.inf], 0).fillna(0)

    df_final.rename(columns={"HIERARQUIA":"HIERARQUIA DE PRODUTOS"}, inplace=True)

    # --- UI: CARDS E TABELA ---
    st.markdown("---")
    col_res, col_cob, col_pos = st.columns([1.2, 1, 1])

    # ✅ CARD 1 (MANTIDO): COBERTURA ATUAL (ajuste só visual do Base)
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

    # ✅ CARD 2 (NOVO): POSITIVAÇÃO (ajuste só visual do Positivados)
    with col_pos:
        # ✅ regra: quando NÃO tem vendedor nem supervisor selecionado, exclui STR/SMX pela EqVs
        # ✅ contagem SEMPRE é pela coluna Cliente (coluna K) da FATURADO (col_cod_cliente)
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
        "HIERARQUIA DE PRODUTOS",
        "META COBERTURA",
        "META CLIENTES (ABS)",
        "POSITIVAÇÃO",
        "PENDÊNCIA CLIENTES",
        " ",
        "META 2025",
        "META 2026",
        "  ",
        "VOLUME",
        "   ",
        "CRESCIMENTO 2025",
        "ATINGIMENTO % (VOL 2025)",
        "    ",
        "CRESCIMENTO 2026",
        "ATINGIMENTO % (VOL 2026)",
    ]

    def zebra_rows(row):
        return ["background-color: #FAFAFA" if row.name % 2 else "" for _ in row]

    def destacar_negativos(s):
        return ["background-color: #FFE5E5; color: #7A0000; font-weight: 600" if v < 0 else "" for v in s]

    def destacar_pendencia(s):
        return ["background-color: #FFD6D6; color: #7A0000; font-weight: 700" if v > 0 else "" for v in s]

    def limpar_espacos(s):
        return ["background-color: transparent" for _ in s]

    sty = (
        df_view[cols_view]
        .sort_values(by="HIERARQUIA DE PRODUTOS")
        .style
        .format(
            {
                "META COBERTURA": "{:.0%}",
                "META CLIENTES (ABS)": lambda v: fmt_pt_int(v),
                "POSITIVAÇÃO": lambda v: fmt_pt_int(v),
                "PENDÊNCIA CLIENTES": lambda v: fmt_pt_int(v),

                # ✅ AJUSTE VISUAL: essas estavam com vírgula
                "META 2025": lambda v: fmt_pt_int(v),
                "META 2026": lambda v: fmt_pt_int(v),
                "VOLUME": lambda v: fmt_pt_int(v),
                "CRESCIMENTO 2025": lambda v: fmt_pt_int(v),
                "CRESCIMENTO 2026": lambda v: fmt_pt_int(v),

                "ATINGIMENTO % (VOL 2025)": "{:.1f}%",
                "ATINGIMENTO % (VOL 2026)": "{:.1f}%",
            }
        )
        .apply(zebra_rows, axis=1)
        .apply(destacar_pendencia, subset=["PENDÊNCIA CLIENTES"])
        .apply(destacar_negativos, subset=["CRESCIMENTO 2025", "CRESCIMENTO 2026"])
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
    # ✅ ADIÇÕES (RANKINGS) — VOLUME (META 2025 e META 2026) + POSITIVAÇÃO
    # ============================
    try:
        st.markdown("---")
        st.markdown("## 📌 Quem está puxando pra cima e pra baixo")

        # --- Base por vendedor (volume + positivação real)
        df_rank_real = (
            df_f.groupby(["VENDEDOR_COD", "VENDEDOR_NOME"])
            .agg(
                VOLUME_REAL=("QTD_VENDAS", "sum"),
                POSITIVADOS=(col_cod_cliente, "nunique")
            )
            .reset_index()
        )

        # --- Metas por vendedor (2025/2026) somadas por RG
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

        # --- Meta de positivação por vendedor (RG, BASE, META)
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

        # --- Junta tudo
        df_rank = df_rank_real.merge(df_meta_v25, on="VENDEDOR_COD", how="left")
        df_rank = df_rank.merge(df_meta_v26, on="VENDEDOR_COD", how="left")
        df_rank = df_rank.merge(df_pos_meta[["VENDEDOR_COD", "META_ABS_POSIT"]] if "META_ABS_POSIT" in df_pos_meta.columns else df_pos_meta, on="VENDEDOR_COD", how="left")
        df_rank[["META_TOTAL_2025", "META_TOTAL_2026", "META_ABS_POSIT"]] = df_rank[["META_TOTAL_2025", "META_TOTAL_2026", "META_ABS_POSIT"]].fillna(0)

        # --- Atingimentos
        df_rank["ATINGIMENTO_VOL_2025"] = (df_rank["VOLUME_REAL"] / df_rank["META_TOTAL_2025"]).replace([np.inf, -np.inf], 0).fillna(0)
        df_rank["ATINGIMENTO_VOL_2026"] = (df_rank["VOLUME_REAL"] / df_rank["META_TOTAL_2026"]).replace([np.inf, -np.inf], 0).fillna(0)
        df_rank["ATINGIMENTO_POSIT"] = (df_rank["POSITIVADOS"] / df_rank["META_ABS_POSIT"]).replace([np.inf, -np.inf], 0).fillna(0)

        # ============================
        # 1) VOLUME (META 2025)
        # ============================
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

        # ============================
        # 2) VOLUME (META 2026)
        # ============================
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

        # ============================
        # 3) POSITIVAÇÃO
        # ============================
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

if st.button("📧 Enviar Excel por Vendedor"):

    import smtplib
    email_origem = st.secrets["email"]["sender_email"]
    senha_origem = st.secrets["email"]["sender_password"]
    smtp_server = st.secrets["email"]["smtp_server"]
    smtp_port = st.secrets["email"]["smtp_port"]

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(email_origem, senha_origem)

    vendedores = df_f['VENDEDOR_NOME'].dropna().unique()

    for vendedor in vendedores:
        vendedor_up = str(vendedor).strip().upper()

        email_destino = MAPA_EMAIL_VENDEDORES.get(vendedor_up)

        # Se não achou e-mail cadastrado, você decide:
        if not email_destino:
            st.warning(f"⚠️ Sem e-mail cadastrado para: {vendedor_up} (pulando)")
            continue

        # Aceita: string "a@x.com" OU lista ["a@x.com","b@x.com"]
        if isinstance(email_destino, list):
            email_destino_str = ",".join([str(x).strip() for x in email_destino if str(x).strip()])
        else:
            email_destino_str = str(email_destino).strip()

        df_vendedor = df_final.copy()

        enviar_excel_vendedor(
            server=server,
            email_origem=email_origem,
            email_destino=email_destino_str,
            nome_vendedor=vendedor,
            df_excel=df_vendedor
        )

    server.quit()
    st.success("📨 E-mails enviados com sucesso!")









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
        df_pendentes = df_agenda[df_agenda['STATUS'] == "Pendente"].copy()
    else:
        # Analista vê apenas os pendentes atribuídos a ele
        # Certifique-se que a coluna 'ANALISTA' existe na sua planilha
        df_pendentes = df_agenda[(df_agenda['STATUS'] == "Pendente") & (df_agenda['ANALISTA'] == user_atual)].copy()
    
    if df_pendentes.empty:
        st.success("Não há agendamentos aguardando sua aprovação!")
    else:
        st.warning(f"Existem {len(df_pendentes)} agendamentos aguardando sua ação.")
        
        for i, row in df_pendentes.iterrows():
            with st.expander(f"📍 {row['VENDEDOR']} -> {row['CLIENTE']} ({row['DATA']})"):
                col1, col2 = st.columns(2)
                
                # Botão para Aprovar
                if col1.button("✅ Aprovar", key=f"aprov_{row['ID']}"):
                    # Atualiza no DataFrame principal usando o ID único
                    df_agenda.loc[df_agenda['ID'] == row['ID'], ['STATUS', 'APROVACAO']] = ["Planejado", "Aprovado"]
                    conn.update(spreadsheet=url_planilha, worksheet="AGENDA", data=df_agenda)
                    st.success(f"Agendamento de {row['CLIENTE']} aprovado!")
                    st.cache_data.clear()
                    st.rerun()
                
                # Botão para Recusar
                if col2.button("❌ Recusar", key=f"recus_{row['ID']}"):
                    df_agenda.loc[df_agenda['ID'] == row['ID'], ['STATUS', 'APROVACAO']] = ["Reprovado", "Reprovado"]
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
