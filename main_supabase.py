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

def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- UI E ESTILO REFINADO ---
st.set_page_config(page_title="Gestão de Pausas - QP", layout="centered")

st.markdown("""
<style>
    :root { color-scheme: light !important; }
    body, .stApp { background-color: #f5f7fa !important; color: #262730 !important; }

    .logo-qp { font-family: 'Arial Black', sans-serif; font-size: 35pt; color: #004a99; text-align: center; margin-bottom: 5px; }
    .subtitulo-qp { font-size: 16pt; color: #666; text-align: center; margin-bottom: 30px; }

    /* Sidebar Estilizada */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #004a99 0%, #003366 100%) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Botão Sair na Sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: 1px solid white !important;
        width: 100% !important;
        height: 45px !important;
        font-weight: bold !important;
    }

    /* Correção visual Selectbox (Texto visível após seleção) */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        color: #262730 !important;
        -webkit-text-fill-color: #262730 !important;
        background-color: white !important;
    }
    
    [data-baseweb="popover"] li { color: #262730 !important; }

    /* Texto do Histórico/Tabelas */
    [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span {
        color: #262730 !important;
    }

    /* Botão Primário Azul */
    .stButton > button[kind="primary"] {
        background-color: #004a99 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def conectar_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

supabase = conectar_supabase()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div><div class="subtitulo-qp">Gestão de Pausa</div>', unsafe_allow_html=True)
    
    if 'logado' not in st.session_state: st.session_state.logado = False

    try:
        usuarios_resp = supabase.table('usuarios').select('*').execute()
        usuarios_db = {u['email'].lower(): u for u in usuarios_resp.data}
    except:
        st.error("❌ Erro ao carregar banco de dados.")
        st.stop()

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_input = st.text_input("E-mail").strip().lower()
        p_input = st.text_input("Senha", type="password")
        if st.button("ACESSAR SISTEMA", type="primary"):
            if u_input in usuarios_db and usuarios_db[u_input]['senha'] == p_input:
                st.session_state.update({"logado": True, "user_atual": u_input, "precisa_trocar": usuarios_db[u_input].get('primeiro_acesso', True)})
                st.rerun()
            else: st.error("❌ E-mail ou senha incorretos.")
    
    elif st.session_state.get('precisa_trocar'):
        st.markdown("### 🔑 Criar Nova Senha")
        nova = st.text_input("Nova Senha", type="password")
        confirma = st.text_input("Confirme a Senha", type="password")
        if st.button("ALTERAR SENHA", type="primary"):
            if len(nova) >= 6 and nova == confirma:
                supabase.table('usuarios').update({'senha': nova, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
                st.session_state.precisa_trocar = False
                st.rerun()
            else: st.error("❌ Erro: Verifique os campos.")

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
                at = [e for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()]
                if not at: st.warning("⚠️ Não há atendentes.")
                else:
                    alvo = st.selectbox("Selecione o Atendente SAC:", at)
                    minutos = st.number_input("Duração:", 1, 120, 15)
                    if st.button("✅ AUTORIZAR PAUSA", type="primary"):
                        supabase.table('escalas').insert({'email': alvo, 'nome': usuarios_db[alvo]['nome'], 'duracao': minutos, 'status': 'Pendente'}).execute()
                        enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 {usuarios_db[alvo]['nome']}, sua pausa foi liberada!")
                        st.success("✅ Autorizado!")

            elif menu == "Histórico":
                st.markdown("### 📊 Histórico de Pausas")
                try:
                    h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                    if h_resp.data:
                        df = pd.DataFrame(h_resp.data)
                        st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                        st.download_button("📥 Baixar CSV", data=gerar_csv(df), file_name="historico.csv", mime="text/csv")
                except: st.error("Erro ao carregar histórico.")

            elif menu == "Gestão de Equipe":
                tab_add, tab_del = st.tabs(["➕ Adicionar Usuário", "🗑️ Remover Usuário"])
                with tab_add:
                    with st.form("add_user"):
                        n = st.text_input("Nome Completo*")
                        e = st.text_input("E-mail*").lower().strip()
                        s = st.text_input("Senha Temporária*")
                        t = st.selectbox("Perfil de Acesso*", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("💾 CADASTRAR"):
                            supabase.table('usuarios').insert({'nome': n, 'email': e, 'senha': s, 'tipo': t, 'primeiro_acesso': True}).execute()
                            st.success("✅ Usuário cadastrado!")
                            st.rerun()
                
                with tab_del:
                    st.markdown("#### Remover Usuário do Sistema")
                    lista_remover = [f"{u['nome']} ({u['email']})" for u in usuarios_resp.data if u['email'] != st.session_state.user_atual]
                    if lista_remover:
                        alvo_remover = st.selectbox("Selecione quem remover:", lista_remover)
                        email_final = alvo_remover.split('(')[-1].replace(')', '')
                        cod_del = st.text_input("Código Mestre para Confirmar Exclusão:", type="password", key="del_secure")
                        if st.button("🗑️ EXCLUIR DEFINITIVAMENTE", type="primary"):
                            if cod_del == CODIGO_MESTRE_GESTAO:
                                supabase.table('usuarios').delete().eq('email', email_final).execute()
                                st.success(f"✅ {email_final} removido.")
                                st.rerun()
                            else: st.error("❌ Código Mestre incorreto.")
                    else: st.info("Não há outros usuários.")

            elif menu == "Correções":
                st.markdown("### ⚠️ Destravar Funcionário")
                esc = supabase.table('escalas').select('*').execute()
                if esc.data:
                    opcoes = [f"{x['nome']} ({x['email']})" for x in esc.data]
                    sel = st.selectbox("Selecione para destravar:", opcoes)
                    cod = st.text_input("Código Mestre:", type="password", key="unlock_secure")
                    if st.button("🔓 DESTRAVAR", type="primary"):
                        if cod == CODIGO_MESTRE_GESTAO:
                            idx = opcoes.index(sel)
                            supabase.table('escalas').delete().eq('id', esc.data[idx]['id']).execute()
                            st.success("✅ Destravado!")
                            st.rerun()
                        else: st.error("❌ Código Mestre incorreto.")
                else: st.success("✅ Nenhuma pausa travada.")

else: st.error("❌ Erro de conexão.")
