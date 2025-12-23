import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, date
import pandas as pd
import pytz
import requests
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES ---
GMAIL_USER = "gestao.queropassagem@gmail.com"
GMAIL_PASSWORD = "pakiujauoxbmihyy" 
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSjPJtSD91ZkrvUi"
DISCORD_WEBHOOK_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI"
SUPABASE_URL = "https://gzozqxrlgdzjrqfvdxzw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6b3pxeHJsZ2R6anJxZnZkeHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0OTg1MjIsImV4cCI6MjA4MjA3NDUyMn0.dLEjBPESUz5KnVwxqEMaMxoy65gsLqG2QdjK2xFTUhU"

CODIGO_MESTRE_GESTAO = "QP2025" 
TIMEZONE_SP = pytz.timezone('America/Sao_Paulo')

def get_now():
    return datetime.now(TIMEZONE_SP)

def enviar_discord(webhook_url, mensagem):
    try: 
        requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except: 
        pass

# --- FUNÇÃO DE E-MAIL COM MODELO COMPLETO ---
def enviar_email_boas_vindas(nome, email_destino, senha_temp):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestão de Pausas QP <{GMAIL_USER}>"
        msg['To'] = email_destino
        msg['Subject'] = "🎉 Bem-vindo ao Sistema de Gestão de Pausas - Quero Passagem"

        corpo = f"""Olá {nome},

Você foi cadastrado no Sistema de Gestão de Pausas da Quero Passagem!

🔐 SEUS DADOS DE ACESSO:
━━━━━━━━━━━━━━━━━━━━━━━━━━
Link: https://gestao-pausas-supabase-rytpzdbzurqiuf53rgnusb.streamlit.app/
Email: {email_destino}
Senha Temporária: {senha_temp}
━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANTE: No primeiro acesso, você será solicitado a criar uma nova senha (mínimo 6 caracteres).

📋 COMO FUNCIONA O SISTEMA:
1️⃣ SOLICITAR PAUSA: Faça login e clique em "VERIFICAR MINHA LIBERAÇÃO".
2️⃣ INICIAR PAUSA: Quando autorizado, clique em "INICIAR". O cronômetro começará.
3️⃣ ALERTA: O sistema emitirá um ALARME SONORO ao finalizar o tempo.
4️⃣ FINALIZAR: BATA O PONTO NO VR antes de clicar em "FINALIZAR" no sistema.

💡 DICA: Mantenha a aba do navegador aberta para ouvir o alarme.

Atenciosamente,
Gestão de Pausas - Quero Passagem"""

        msg.attach(MIMEText(corpo, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- UI E ESTILO ---
st.set_page_config(page_title="Gestão de Pausas - QP", layout="centered")
st.markdown("""<style>
/* Forçar tema claro globalmente */
:root {
    color-scheme: light !important;
}

body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #f5f7fa !important;
    color: #262730 !important;
}

/* Esconder elementos do Streamlit */
header, footer, .stDeployButton, #MainMenu {
    display: none !important;
} 

/* Logo e título */
.logo-qp { 
    font-family: 'Arial Black', sans-serif; 
    font-size: 35pt; 
    color: #004a99 !important; 
    text-align: center;
    margin-bottom: 5px;
    text-shadow: 2px 2px 4px rgba(0,74,153,0.2);
} 

.subtitulo-qp { 
    font-size: 16pt; 
    color: #666 !important; 
    text-align: center;
    margin-bottom: 30px;
    font-weight: 300;
}

/* Sidebar */
[data-testid="stSidebar"] { 
    background: linear-gradient(180deg, #004a99 0%, #003366 100%) !important;
    box-shadow: 2px 0 10px rgba(0,0,0,0.1);
} 

[data-testid="stSidebar"] * { 
    color: white !important;
}

/* Botão SAIR na sidebar - CRÍTICO */
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255, 255, 255, 0.25) !important;
    color: white !important;
    border: 2px solid rgba(255, 255, 255, 0.4) !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    width: 100% !important;
    margin-top: 10px !important;
    font-size: 15px !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255, 255, 255, 0.4) !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    border-color: rgba(255, 255, 255, 0.6) !important;
}

/* Forçar texto branco no botão da sidebar */
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] button *,
[data-testid="stSidebar"] button span,
[data-testid="stSidebar"] button div,
[data-testid="stSidebar"] button p {
    color: white !important;
    background-color: transparent !important;
}

/* Forçar visibilidade do texto "Sair" */
[data-testid="stSidebar"] button[kind="secondary"] {
    color: white !important;
}

[data-testid="stSidebar"] button::before {
    color: white !important;
}

/* Nome do usuário na sidebar */
[data-testid="stSidebar"] h2 {
    background-color: rgba(255,255,255,0.15) !important;
    padding: 15px !important;
    border-radius: 8px !important;
    margin: 10px 0 20px 0 !important;
    text-align: center !important;
    color: white !important;
    font-size: 18px !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
}

/* Container principal com card */
.block-container {
    padding: 2rem 1rem !important;
    max-width: 1200px !important;
}

/* Remover bordas brancas vazias - aplicar apenas em divs com conteúdo */
div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* Card bonito apenas para seções principais */
section[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlock"] {
    background-color: white !important;
    padding: 30px !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    border: 1px solid #e5e7eb !important;
    margin-bottom: 20px !important;
}

/* Remover padding extra de containers vazios */
div[data-testid="stVerticalBlock"]:empty {
    display: none !important;
}

/* Header do usuário na sidebar */
[data-testid="stSidebar"] h2 {
    background-color: rgba(255,255,255,0.1) !important;
    padding: 15px !important;
    border-radius: 8px !important;
    margin: 10px 0 !important;
    text-align: center !important;
}

/* Melhorar visual das tabs */
.stTabs {
    background-color: white !important;
    padding: 20px !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    border: 1px solid #e5e7eb !important;
}

/* INPUTS DE TEXTO */
.stTextInput > div > div > input,
.stTextInput input,
input[type="text"],
input[type="email"],
input[type="password"] {
    background-color: white !important;
    color: #262730 !important;
    border: 2px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus,
input[type="text"]:focus,
input[type="email"]:focus,
input[type="password"]:focus {
    border-color: #004a99 !important;
    box-shadow: 0 0 0 3px rgba(0,74,153,0.1) !important;
    outline: none !important;
}

.stTextInput > div > div > input::placeholder {
    color: #9ca3af !important;
}

/* SELECTBOX - SOLUÇÃO DEFINITIVA */
.stSelectbox > div > div,
.stSelectbox > div > div > div,
[data-baseweb="select"],
[data-baseweb="select"] > div {
    background-color: white !important;
    color: #262730 !important;
    border: 2px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    transition: all 0.3s ease !important;
}

[data-baseweb="select"]:hover {
    border-color: #004a99 !important;
}

/* CRÍTICO - Forçar preto em ABSOLUTAMENTE TUDO no selectbox */
.stSelectbox *,
[data-baseweb="select"] *,
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="select"] p,
.stSelectbox span,
.stSelectbox div,
.stSelectbox p {
    color: #262730 !important;
}

/* Valor selecionado - MÁXIMA PRIORIDADE */
[data-baseweb="select"] [role="combobox"],
[data-baseweb="select"] [data-baseweb="input"],
.stSelectbox [data-baseweb="select"] > div > div {
    color: #262730 !important;
    background-color: white !important;
}

/* Forçar texto preto no valor exibido após seleção - TODAS AS VARIAÇÕES */
[data-baseweb="select"] [role="button"] > div,
[data-baseweb="select"] [role="button"] span,
[data-baseweb="select"] [role="button"] *,
.stSelectbox [data-baseweb="select"] span[role="option"],
div[class*="StyledControlContainer"] > div,
div[class*="StyledControlContainer"] *,
div[class*="StyledValueContainer"],
div[class*="StyledValueContainer"] *,
div[class*="StyledSingleValue"],
div[class*="StyledSingleValue"] * {
    color: #262730 !important;
    background-color: transparent !important;
}

/* Texto do input do selectbox */
[data-baseweb="select"] input[role="combobox"],
[data-baseweb="select"] input {
    color: #262730 !important;
    caret-color: #262730 !important;
}

/* Placeholder do selectbox */
[data-baseweb="select"] [data-baseweb="placeholder"],
.stSelectbox [data-baseweb="placeholder"] {
    color: #9ca3af !important;
}

/* Dropdown do selectbox */
[data-baseweb="popover"] {
    background-color: white !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    border: 1px solid #e5e7eb !important;
}

/* Lista de opções */
[role="listbox"],
[role="option"] {
    background-color: white !important;
    color: #262730 !important;
    padding: 10px 16px !important;
}

[role="option"]:hover {
    background-color: #f3f4f6 !important;
    color: #262730 !important;
}

/* Opções do dropdown com texto preto - TODAS AS VARIAÇÕES */
[data-baseweb="popover"] li,
[data-baseweb="popover"] span,
[data-baseweb="popover"] div,
[data-baseweb="popover"] * {
    color: #262730 !important;
}

[data-baseweb="popover"] li:hover {
    background-color: #f3f4f6 !important;
}

/* Input interno do selectbox quando está aberto */
.stSelectbox input {
    color: #262730 !important;
    background-color: white !important;
}

/* Sobrescrever QUALQUER estilo inline do Streamlit */
.stSelectbox [style*="color"] {
    color: #262730 !important;
}

/* Tags e chips dentro do selectbox (caso exista) */
[data-baseweb="tag"],
[data-baseweb="tag"] * {
    color: #262730 !important;
}

/* NUMBER INPUT */
.stNumberInput > div > div > input,
input[type="number"] {
    background-color: white !important;
    color: #262730 !important;
    border: 2px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    transition: all 0.3s ease !important;
}

.stNumberInput > div > div > input:focus {
    border-color: #004a99 !important;
    box-shadow: 0 0 0 3px rgba(0,74,153,0.1) !important;
}

/* BOTÕES */
.stButton > button {
    background-color: white !important;
    color: #262730 !important;
    border: 2px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

.stButton > button:hover {
    background-color: #f9fafb !important;
    border-color: #004a99 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #004a99 0%, #0066cc 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 6px rgba(0,74,153,0.2) !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #003d7a 0%, #0052a3 100%) !important;
    box-shadow: 0 6px 12px rgba(0,74,153,0.3) !important;
}

/* RADIO BUTTONS */
.stRadio {
    background-color: white !important;
    padding: 20px !important;
    border-radius: 12px !important;
    border: 1px solid #e5e7eb !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

.stRadio > div {
    gap: 8px !important;
}

.stRadio label {
    color: #262730 !important;
    font-weight: 500 !important;
    padding: 12px 20px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    border: 2px solid transparent !important;
}

.stRadio label:hover {
    background-color: #f3f4f6 !important;
    border-color: #e5e7eb !important;
}

.stRadio input[type="radio"]:checked + label {
    background-color: #eff6ff !important;
    border-color: #004a99 !important;
    color: #004a99 !important;
    font-weight: 600 !important;
}

/* Títulos de seção */
h1, h2, h3 {
    padding: 15px 0 10px 0 !important;
    border-bottom: 3px solid #004a99 !important;
    margin-bottom: 20px !important;
}

h2 {
    font-size: 24px !important;
    color: #004a99 !important;
}

h3 {
    font-size: 20px !important;
    border-bottom: 2px solid #e5e7eb !important;
}

/* DATAFRAMES */
[data-testid="stDataFrame"],
.stDataFrame {
    background-color: white !important;
    border-radius: 8px !important;
    border: 1px solid #e5e7eb !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

[data-testid="stDataFrame"] * {
    color: #262730 !important;
}

/* Headers das tabelas */
[data-testid="stDataFrame"] thead th {
    background-color: #f9fafb !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #e5e7eb !important;
}

/* TEXTO GERAL */
p, span, div, label, h1, h2, h3, h4, h5, h6 {
    color: #262730 !important;
}

h1, h2, h3 {
    font-weight: 700 !important;
}

/* Exceção para sidebar */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label {
    color: white !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
    background-color: #f3f4f6 !important;
    border-radius: 8px !important;
    padding: 4px !important;
    gap: 4px !important;
}

.stTabs [data-baseweb="tab"] {
    color: #4b5563 !important;
    background-color: transparent !important;
    border-radius: 6px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: #e5e7eb !important;
    color: #1f2937 !important;
}

.stTabs [aria-selected="true"] {
    background-color: #004a99 !important;
    color: white !important;
}

/* Forçar texto branco na tab ativa */
.stTabs [aria-selected="true"] * {
    color: white !important;
}

/* FORMS */
form {
    background-color: white !important;
    padding: 20px !important;
    border-radius: 12px !important;
    border: 1px solid #e5e7eb !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

/* INFO/WARNING/SUCCESS BOXES */
.stAlert {
    border-radius: 8px !important;
    border-left: 4px solid !important;
    padding: 16px !important;
    margin: 12px 0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
}

/* Info box */
div[data-baseweb="notification"][kind="info"] {
    background-color: #eff6ff !important;
    border-left-color: #3b82f6 !important;
}

/* Success box */
div[data-baseweb="notification"][kind="success"] {
    background-color: #f0fdf4 !important;
    border-left-color: #22c55e !important;
}

/* Warning box */
div[data-baseweb="notification"][kind="warning"] {
    background-color: #fffbeb !important;
    border-left-color: #f59e0b !important;
}

/* Error box */
div[data-baseweb="notification"][kind="error"] {
    background-color: #fef2f2 !important;
    border-left-color: #ef4444 !important;
}

/* Markdown e texto */
.stMarkdown {
    color: #262730 !important;
}

/* Divider */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #e5e7eb, transparent) !important;
    margin: 24px 0 !important;
}

/* Cronômetro Timer */
#timer {
    font-family: 'Courier New', monospace !important;
    background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%) !important;
    box-shadow: 0 4px 12px rgba(239,68,68,0.3) !important;
}

/* Download button */
.stDownloadButton > button {
    background-color: #10b981 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 4px rgba(16,185,129,0.2) !important;
}

.stDownloadButton > button:hover {
    background-color: #059669 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(16,185,129,0.3) !important;
}

/* Columns spacing */
[data-testid="column"] {
    padding: 0 8px !important;
}

/* Expander */
.streamlit-expanderHeader {
    background-color: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    font-weight: 600 !important;
}

.streamlit-expanderHeader:hover {
    background-color: #f9fafb !important;
    border-color: #004a99 !important;
}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def conectar_supabase():
    try: 
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: 
        return None

supabase = conectar_supabase()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div><div class="subtitulo-qp">Gestão de Pausa</div>', unsafe_allow_html=True)
    
    if 'logado' not in st.session_state: 
        st.session_state.logado = False

    try:
        usuarios_resp = supabase.table('usuarios').select('*').execute()
        usuarios_db = {u['email'].lower(): u for u in usuarios_resp.data}
    except Exception as e:
        st.error("❌ Erro ao carregar usuários do banco de dados.")
        st.stop()

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_input = st.text_input("E-mail").strip().lower()
        p_input = st.text_input("Senha", type="password")
        if st.button("ACESSAR SISTEMA"):
            if u_input in usuarios_db and usuarios_db[u_input]['senha'] == p_input:
                st.session_state.update({
                    "logado": True, 
                    "user_atual": u_input, 
                    "precisa_trocar": usuarios_db[u_input].get('primeiro_acesso', True)
                })
                st.rerun()
            else: 
                st.error("❌ Login ou senha inválidos.")
    
    elif st.session_state.get('precisa_trocar'):
        st.markdown("### 🔑 Primeira Senha - Criar Nova Senha")
        st.info("Por segurança, você precisa criar uma nova senha no primeiro acesso.")
        nova = st.text_input("Nova Senha (mínimo 6 caracteres)", type="password")
        confirma = st.text_input("Confirme a Nova Senha", type="password")
        
        if st.button("ALTERAR SENHA"):
            if len(nova) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres!")
            elif nova != confirma:
                st.error("❌ As senhas não coincidem!")
            else:
                try:
                    supabase.table('usuarios').update({
                        'senha': nova, 
                        'primeiro_acesso': False
                    }).eq('email', st.session_state.user_atual).execute()
                    st.session_state.precisa_trocar = False
                    st.success("✅ Senha alterada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error("❌ Erro ao alterar senha. Tente novamente.")

    else:
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        st.sidebar.write(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"): 
            st.session_state.clear()
            st.rerun()

        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Liberar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Liberar Pausa":
                st.markdown("### 🚀 Liberar Pausa para Atendente")
                st.divider()
                
                at = [e for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()]
                
                if not at:
                    st.warning("⚠️ Não há atendentes cadastrados no sistema.")
                else:
                    alvo = st.selectbox("Selecione o Atendente SAC:", at)
                    minutos = st.number_input("Duração da Pausa (minutos):", min_value=1, max_value=120, value=15)
                    
                    if st.button("✅ AUTORIZAR PAUSA"):
                        try:
                            supabase.table('escalas').insert({
                                'email': alvo,
                                'nome': usuarios_db[alvo]['nome'],
                                'duracao': minutos,
                                'status': 'Pendente'
                            }).execute()
                            enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 {usuarios_db[alvo]['nome']}, sua pausa foi liberada!")
                            st.success(f"✅ Pausa de {minutos} minutos liberada para {usuarios_db[alvo]['nome']}!")
                        except Exception as e:
                            st.error("❌ Erro ao liberar pausa. Tente novamente.")

            elif menu == "Histórico":
                st.markdown("### 📊 Histórico de Pausas")
                st.divider()
                
                try:
                    h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                    if h_resp.data and len(h_resp.data) > 0:
                        df = pd.DataFrame(h_resp.data)
                        df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
                        
                        st.dataframe(
                            df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], 
                            use_container_width=True,
                            height=400
                        )
                        
                        st.download_button(
                            "📥 Baixar Histórico (CSV para Google Planilhas)", 
                            data=gerar_csv(df), 
                            file_name=f"historico_pausas_{date.today().strftime('%Y%m%d')}.csv", 
                            mime="text/csv"
                        )
                    else: 
                        st.info("📭 Histórico vazio. Ainda não há registros de pausas finalizadas.")
                except Exception as e:
                    st.error("❌ Erro ao carregar histórico. Tente novamente.")

            elif menu == "Gestão de Equipe":
                st.markdown("### 👥 Gerenciamento de Equipe")
                st.divider()
                
                tab_add, tab_del = st.tabs(["➕ Adicionar Usuário", "🗑️ Remover Usuário"])
                
                with tab_add:
                    st.markdown("#### Cadastrar Novo Usuário")
                    with st.form("add_user", clear_on_submit=True):
                        n = st.text_input("Nome Completo*")
                        e = st.text_input("E-mail Corporativo*").strip().lower()
                        s = st.text_input("Senha Temporária* (mínimo 6 caracteres)")
                        t = st.selectbox("Perfil de Acesso*", ["atendente sac", "supervisor", "administrador"])
                        
                        if st.form_submit_button("💾 CADASTRAR USUÁRIO"):
                            if not n or not e or not s:
                                st.error("❌ Preencha todos os campos obrigatórios!")
                            elif len(s) < 6:
                                st.error("❌ A senha temporária deve ter pelo menos 6 caracteres!")
                            elif e in usuarios_db:
                                st.error("❌ Este e-mail já está cadastrado no sistema!")
                            else:
                                try:
                                    supabase.table('usuarios').insert({
                                        'nome': n,
                                        'email': e,
                                        'senha': s,
                                        'tipo': t,
                                        'primeiro_acesso': True
                                    }).execute()
                                    
                                    email_enviado = enviar_email_boas_vindas(n, e, s)
                                    
                                    if email_enviado:
                                        st.success(f"✅ Usuário **{n}** criado com sucesso! E-mail de boas-vindas enviado.")
                                    else:
                                        st.warning(f"✅ Usuário **{n}** criado, mas houve erro ao enviar e-mail. Informe os dados manualmente.")
                                    
                                    st.rerun()
                                except Exception as e:
                                    st.error("❌ Erro ao cadastrar usuário. Verifique os dados e tente novamente.")
                
                with tab_del:
                    st.markdown("#### Remover Usuário do Sistema")
                    st.warning("⚠️ **ATENÇÃO:** Esta ação é permanente e não pode ser desfeita!")
                    
                    if len(usuarios_db) == 0:
                        st.info("Não há usuários cadastrados para remover.")
                    else:
                        remover = st.selectbox("Selecione o usuário para remover:", list(usuarios_db.keys()))
                        
                        st.markdown(f"""
                        **Dados do usuário:**
                        - **Nome:** {usuarios_db[remover]['nome']}
                        - **E-mail:** {remover}
                        - **Perfil:** {usuarios_db[remover]['tipo']}
                        """)
                        
                        confirmacao = st.text_input("Digite 'CONFIRMAR' para remover o usuário:", key="confirmar_exclusao")
                        
                        if st.button("🗑️ REMOVER PERMANENTEMENTE"):
                            if confirmacao == "CONFIRMAR":
                                try:
                                    supabase.table('usuarios').delete().eq('id', usuarios_db[remover]['id']).execute()
                                    st.success(f"🗑️ Usuário **{usuarios_db[remover]['nome']}** removido com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error("❌ Erro ao remover usuário. Tente novamente.")
                            else:
                                st.error("❌ Você precisa digitar 'CONFIRMAR' para prosseguir!")

            elif menu == "Correções":
                st.markdown("### ⚠️ Destravar Funcionário")
                st.divider()
                
                st.markdown("""
                <div style="background-color: #fffbeb; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin-bottom: 20px;">
                    <p style="margin: 0; color: #92400e;"><strong>ℹ️ Sobre esta funcionalidade:</strong></p>
                    <p style="margin: 5px 0 0 0; color: #92400e;">Esta ferramenta permite destravar funcionários que ficaram com pausas ativas no sistema devido a problemas técnicos ou fechamento acidental da página.</p>
                </div>
                """, unsafe_allow_html=True)
                
                try:
                    esc = supabase.table('escalas').select('*').execute()
                    
                    if esc.data and len(esc.data) > 0:
                        st.warning(f"⚠️ Existem **{len(esc.data)}** registro(s) de pausa ativa no sistema.")
                        
                        # Criar lista de opções com informações detalhadas
                        opcoes = [f"{x['nome']} ({x['email']}) - Status: {x['status']}" for x in esc.data]
                        sel = st.selectbox("Selecione o funcionário para destravar:", opcoes)
                        
                        # Exibir informações do registro selecionado
                        idx = opcoes.index(sel)
                        registro = esc.data[idx]
                        
                        st.info(f"""
                        **Detalhes do registro:**
                        - **Nome:** {registro['nome']}
                        - **E-mail:** {registro['email']}
                        - **Status:** {registro['status']}
                        - **Duração:** {registro.get('duracao', 'N/A')} minutos
                        """)
                        
                        st.warning("⚠️ Esta ação irá **remover completamente** o registro de pausa ativa do funcionário.")
                        
                        cod = st.text_input("Digite o Código Mestre para confirmar:", type="password", key="codigo_mestre")
                        
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if st.button("🔓 DESTRAVAR"):
                                if cod == CODIGO_MESTRE_GESTAO:
                                    try:
                                        id_e = registro['id']
                                        supabase.table('escalas').delete().eq('id', id_e).execute()
                                        enviar_discord(
                                            DISCORD_WEBHOOK_GESTAO, 
                                            f"🔓 **{registro['nome']}** foi destravado pela gestão através do código mestre."
                                        )
                                        st.success(f"✅ Funcionário **{registro['nome']}** destravado com sucesso!")
                                        st.balloons()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao destravar funcionário: {str(e)}")
                                else:
                                    st.error("❌ Código Mestre incorreto!")
                    else:
                        st.success("✅ Não há funcionários com pausas ativas ou travadas no momento.")
                        st.info("O sistema está funcionando normalmente. Esta tela só exibe registros quando há problemas.")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao carregar dados de escalas: {str(e)}")
                    st.write("Por favor, tente novamente. Se o erro persistir, contate o suporte técnico.")

        else: # ATENDENTE
            st.markdown("### ⏱️ Minha Pausa")
            st.divider()
            
            if 'pausa_ativa' not in st.session_state or not st.session_state.pausa_ativa:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO", use_container_width=True):
                        try:
                            res = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()
                            if res.data and len(res.data) > 0:
                                st.session_state.update({
                                    "t_pausa": res.data[0]['duracao'], 
                                    "p_id": res.data[0]['id'], 
                                    "liberado": True
                                })
                                st.success(f"✅ Pausa autorizada: {st.session_state.t_pausa} minutos!")
                                st.balloons()
                                st.rerun()
                            else: 
                                st.info("⏳ Aguardando liberação da gestão...")
                        except Exception as e:
                            st.error("❌ Erro ao verificar liberação. Tente novamente.")
                
                if st.session_state.get('liberado'):
                    with col2:
                        if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True, type="primary"):
                            try:
                                supabase.table('escalas').update({'status': 'Em Pausa'}).eq('id', st.session_state.p_id).execute()
                                st.session_state.update({
                                    "pausa_ativa": True, 
                                    "fim": (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000, 
                                    "saida": get_now().strftime("%H:%M:%S")
                                })
                                enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** iniciou pausa de {st.session_state.t_pausa} minutos.")
                                st.rerun()
                            except Exception as e:
                                st.error("❌ Erro ao iniciar pausa. Tente novamente.")
            else:
                st.markdown("### ⏱️ Cronômetro de Pausa")
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px; margin-bottom: 20px;">--:--</div>
                    <script>
                        var endTime = {st.session_state.fim};
                        function playBeep() {{
                            var ctx = new (window.AudioContext || window.webkitAudioContext)();
                            var osc = ctx.createOscillator(); 
                            var g = ctx.createGain();
                            osc.connect(g); 
                            g.connect(ctx.destination);
                            osc.type = 'square'; 
                            osc.frequency.value = 1000;
                            g.gain.setValueAtTime(1, ctx.currentTime);
                            osc.start(); 
                            osc.stop(ctx.currentTime + 2);
                        }}
                        var x = setInterval(function() {{
                            var diff = endTime - new Date().getTime();
                            if (diff <= 0) {{
                                document.getElementById('timer').innerHTML = "00:00";
                                playBeep(); 
                                alert("🔴 TEMPO ESGOTADO! BATA O PONTO NO VR ANTES DE FINALIZAR!");
                                clearInterval(x);
                            }} else {{
                                var m = Math.floor(diff / 60000); 
                                var s = Math.floor((diff % 60000) / 1000);
                                document.getElementById('timer').innerHTML = (m<10?"0":"")+m+":"+(s<10?"0":"")+s;
                            }}
                        }}, 1000);
                    </script>""", height=220)
                
                st.warning("⚠️ **IMPORTANTE:** Bata o ponto no VR ANTES de clicar em 'FINALIZAR'!")
                
                if st.button("✅ FINALIZAR E VOLTAR AO TRABALHO", use_container_width=True, type="primary"):
                    try:
                        supabase.table('historico').insert({
                            'email': st.session_state.user_atual, 
                            'nome': u_info['nome'], 
                            'data': get_now().date().isoformat(), 
                            'h_saida': st.session_state.saida, 
                            'h_retorno': get_now().strftime("%H:%M:%S"), 
                            'duracao': st.session_state.t_pausa
                        }).execute()
                        
                        supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()
                        
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** finalizou pausa e retornou ao trabalho.")
                        
                        st.session_state.pausa_ativa = False
                        st.success("✅ Pausa finalizada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error("❌ Erro ao finalizar pausa. Tente novamente ou contate a gestão.")
else: 
    st.error("❌ Erro ao conectar ao banco de dados. Verifique sua conexão e tente novamente.")
