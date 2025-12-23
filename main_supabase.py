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

# --- FUNÇÕES DE EXPORTAÇÃO (PARA GOOGLE PLANILHAS) ---
def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

def gerar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Historico')
    return output.getvalue()

# --- INTERFACE E ESTILO ---
st.set_page_config(page_title="Gestão de Pausas - QP", layout="centered")
st.markdown("""<style>header, footer, .stDeployButton, #MainMenu {display: none !important;} .stApp { background-color: white !important; } [data-testid="stSidebar"] { background-color: #004a99 !important; } [data-testid="stSidebar"] * { color: white !important; } .logo-qp { font-family: 'Arial Black', sans-serif; font-size: 35pt; color: #004a99 !important; text-align: center; } .subtitulo-qp { font-size: 16pt; color: #666 !important; text-align: center; }</style>""", unsafe_allow_html=True)

@st.cache_resource
def conectar_supabase():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

supabase = conectar_supabase()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div><div class="subtitulo-qp">Gestão de Pausa</div>', unsafe_allow_html=True)
    if 'logado' not in st.session_state: st.session_state.logado = False

    usuarios_resp = supabase.table('usuarios').select('*').execute()
    usuarios_db = {u['email'].lower(): u for u in usuarios_resp.data}

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_input = st.text_input("E-mail").strip().lower()
        p_input = st.text_input("Senha", type="password")
        if st.button("ACESSAR SISTEMA"):
            if u_input in usuarios_db and usuarios_db[u_input]['senha'] == p_input:
                st.session_state.logado = True
                st.session_state.user_atual = u_input
                st.session_state.precisa_trocar = usuarios_db[u_input].get('primeiro_acesso', True)
                st.rerun()
            else: st.error("Login ou senha inválidos.")
    
    else:
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        st.sidebar.write(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Liberar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Histórico":
                st.subheader("📊 Histórico de Pausas")
                try:
                    # Busca os dados no Supabase
                    h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                    df_hist = pd.DataFrame(h_resp.data)

                    if not df_hist.empty:
                        # Formata a data para leitura brasileira
                        df_hist['data_formatada'] = pd.to_datetime(df_hist['data']).dt.strftime('%d/%m/%Y')
                        
                        # Exibe a tabela
                        st.dataframe(df_hist[['nome', 'data_formatada', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                        
                        # Botões de Download para Google Planilhas
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(label="📥 Baixar CSV (Google Planilhas)", data=gerar_csv(df_hist), file_name=f"historico_pausas_{date.today()}.csv", mime="text/csv")
                        with col2:
                            st.download_button(label="📥 Baixar Excel", data=gerar_excel(df_hist), file_name=f"historico_pausas_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.info("Nenhum registro encontrado no histórico.")
                except Exception as e:
                    st.error(f"Erro ao carregar dados: {e}")

            elif menu == "Gestão de Equipe":
                tab_add, tab_del = st.tabs(["➕ Adicionar", "🗑️ Excluir"])
                with tab_add:
                    with st.form("add_user", clear_on_submit=True):
                        n = st.text_input("Nome"); e = st.text_input("Email").lower(); s = st.text_input("Senha Temp")
                        t = st.selectbox("Perfil", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("SALVAR"):
                            supabase.table('usuarios').insert({'nome':n,'email':e,'senha':s,'tipo':t,'primeiro_acesso':True}).execute()
                            st.success("✅ Usuário criado!"); st.rerun()
                with tab_del:
                    remover = st.selectbox("Selecione para remover:", list(usuarios_db.keys()))
                    if st.button("REMOVER PERMANENTEMENTE"):
                        supabase.table('usuarios').delete().eq('id', usuarios_db[remover]['id']).execute()
                        st.success("🗑️ Usuário removido!"); st.rerun()

            # ... (Restante das opções Liberar Pausa e Correções permanecem iguais)
