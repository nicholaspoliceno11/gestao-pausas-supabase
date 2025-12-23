import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import pytz
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO EMAIL (GMAIL SMTP) ---
GMAIL_USER = "gestao.queropassagem@gmail.com"
GMAIL_PASSWORD = "pakiujauoxbmihyy" 

# --- CONFIGURAÇÃO DISCORD ---
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSjPJtSD91ZkrvUi"
DISCORD_WEBHOOK_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI"

# --- CONFIGURAÇÃO SUPABASE ---
SUPABASE_URL = "https://gzozqxrlgdzjrqfvdxzw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6b3pxeHJsZ2R6anJxZnZkeHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0OTg1MjIsImV4cCI6MjA4MjA3NDUyMn0.dLEjBPESUz5KnVwxqEMaMxoy65gsLqG2QdjK2xFTUhU"

CODIGO_MESTRE_DESTRAVAR = "QP2025" # Código para o supervisor destravar pausas
TIMEZONE_SP = pytz.timezone('America/Sao_Paulo')

def get_now():
    return datetime.now(TIMEZONE_SP)

def enviar_discord(webhook_url, mensagem):
    try:
        requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except:
        pass

def enviar_email_boas_vindas(nome, email_destino, senha_temp):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestão de Pausas QP <{GMAIL_USER}>"
        msg['To'] = email_destino
        msg['Subject'] = "🎉 Bem-vindo ao Sistema de Gestão de Pausas - Quero Passagem"

        corpo = f"""
        Olá {nome},

        Você foi cadastrado no Sistema de Gestão de Pausas da Quero Passagem!

        🔐 SEUS DADOS DE ACESSO:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━
        Link: https://gestao-pausas-supabase-rytpzdbzurqiuf53rgnusb.streamlit.app/
        Email: {email_destino}
        Senha Temporária: {senha_temp}
        ━━━━━━━━━━━━━━━━━━━━━━━━━━

        ⚠️ IMPORTANTE: No primeiro acesso, você será solicitado a criar uma nova senha.
        
        Atenciosamente,
        Gestão de Pausas - Quero Passagem
        """
        msg.attach(MIMEText(corpo, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Gestão de Pausas - QP", layout="centered")

st.markdown("""
    <style>
    header, footer, .stDeployButton, #MainMenu {display: none !important;}
    .stApp { background-color: white !important; }
    [data-testid="stSidebar"] { background-color: #004a99 !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #004a99 !important; font-weight: bold !important; }
    input[type="text"], input[type="email"], input[type="password"] { background-color: white !important; color: black !important; border: 1px solid #ddd !important; }
    .logo-qp { font-family: 'Arial Black', sans-serif; font-size: 35pt; color: #004a99 !important; text-align: center; }
    .subtitulo-qp { font-size: 16pt; color: #666 !important; text-align: center; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def conectar_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase: Client = conectar_supabase()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div><div class="subtitulo-qp">Gestão de Pausa</div>', unsafe_allow_html=True)
    st.divider()

    if 'logado' not in st.session_state:
        st.session_state.logado = False
    if 'pausa_ativa' not in st.session_state:
        st.session_state.pausa_ativa = False

    usuarios_response = supabase.table('usuarios').select('*').execute()
    usuarios_db = {u['email'].lower(): u for u in usuarios_response.data}

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_log = st.text_input("E-mail").strip().lower()
        p_log = st.text_input("Senha", type="password")
        
        if st.button("ACESSAR SISTEMA"):
            if u_log in usuarios_db and usuarios_db[u_log]['senha'] == p_log:
                st.session_state.logado = True
                st.session_state.user_atual = u_log
                st.session_state.precisa_trocar_senha = usuarios_db[u_log].get('primeiro_acesso', True)
                st.rerun()
            else:
                st.error("Login ou senha incorretos.")
    
    elif st.session_state.get('precisa_trocar_senha', False):
        st.markdown("### 🔐 Primeiro Acesso - Alterar Senha")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
        if st.button("✅ ALTERAR SENHA"):
            if len(nova_senha) >= 6 and nova_senha == confirma_senha:
                supabase.table('usuarios').update({'senha': nova_senha, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
                st.session_state.precisa_trocar_senha = False
                st.rerun()
            else:
                st.error("Verifique os campos (mínimo 6 caracteres).")

    else:
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        st.sidebar.markdown(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"):
            st.session_state.clear()
            st.rerun()

        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Liberar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()
            
            if menu == "Liberar Pausa":
                atendentes = [e for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()]
                alvo = st.selectbox("Atendente SAC:", atendentes)
                tempo = st.number_input("Duração:", 1, 120, 15)
                if st.button("AUTORIZAR PAUSA"):
                    supabase.table('escalas').insert({'email': alvo, 'nome': usuarios_db[alvo]['nome'], 'duracao': tempo, 'status': 'Pendente', 'inicio': get_now().isoformat()}).execute()
                    enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 **{usuarios_db[alvo]['nome']}**, sua pausa foi liberada!")
                    st.success("✅ Pausa liberada!")

            elif menu == "Correções":
                st.subheader("⚠️ Destravar Funcionário")
                esc_resp = supabase.table('escalas').select('*').execute()
                if esc_resp.data:
                    travado = st.selectbox("Selecione:", [f"{x['nome']} ({x['email']})" for x in esc_resp.data])
                    idx = [f"{x['nome']} ({x['email']})" for x in esc_resp.data].index(travado)
                    id_del = esc_resp.data[idx]['id']
                    cod = st.text_input("Código Mestre", type="password")
                    if st.button("DESTRAVAR AGORA"):
                        if cod == CODIGO_MESTRE_DESTRAVAR:
                            supabase.table('escalas').delete().eq('id', id_del).execute()
                            st.success("Resetado!")
                            st.rerun()
                        else: st.error("Código incorreto.")
                else: st.write("Ninguém travado.")

            elif menu == "Gestão de Equipe":
                with st.form("cad_user", clear_on_submit=True):
                    f_nome = st.text_input("Nome")
                    f_email = st.text_input("Email").strip().lower()
                    f_senha = st.text_input("Senha Temporária")
                    f_tipo = st.selectbox("Perfil", ["atendente sac", "supervisor", "administrador"])
                    if st.form_submit_button("SALVAR"):
                        supabase.table('usuarios').insert({'nome': f_nome, 'email': f_email, 'senha': f_senha, 'tipo': f_tipo, 'primeiro_acesso': True}).execute()
                        enviar_email_boas_vindas(f_nome, f_email, f_senha)
                        st.success("✅ Criado e E-mail enviado!")
                        st.rerun()

        else:
            st.subheader("⏱️ Minha Pausa")
            if not st.session_state.pausa_ativa:
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO"):
                    res = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()
                    if res.data:
                        st.session_state.update({"tempo_pausa": res.data[0]['duracao'], "pausa_id": res.data[0]['id'], "pausa_liberada": True})
                        st.success("✅ Autorizado!"); st.balloons()
                    else: st.info("⏳ Aguardando...")
                
                if st.session_state.get('pausa_liberada'):
                    if st.button(f"🚀 INICIAR"):
                        supabase.table('escalas').update({'status': 'Em Pausa'}).eq('id', st.session_state.pausa_id).execute()
                        st.session_state.update({"pausa_ativa": True, "h_termino_ms": (get_now() + timedelta(minutes=st.session_state.tempo_pausa)).timestamp() * 1000, "h_saida": get_now().strftime("%H:%M:%S")})
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** INICIOU.")
                        st.rerun()
            else:
                # CRONÔMETRO COM ALARME SONORO
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px;">--:--</div>
                    <script>
                        var endTime = {st.session_state.h_termino_ms};
                        function playBeep() {{
                            var context = new (window.AudioContext || window.webkitAudioContext)();
                            var osc = context.createOscillator();
                            var gain = context.createGain();
                            osc.connect(gain); gain.connect(context.destination);
                            osc.type = 'square'; osc.frequency.value = 1000;
                            gain.gain.setValueAtTime(1, context.currentTime);
                            osc.start(); osc.stop(context.currentTime + 1);
                        }}
                        var x = setInterval(function() {{
                            var now = new Date().getTime();
                            var diff = endTime - now;
                            if (diff <= 0) {{
                                document.getElementById('timer').innerHTML = "00:00";
                                playBeep();
                                alert("🔴 TEMPO ESGOTADO! Bata o ponto no VR!");
                                clearInterval(x);
                            }} else {{
                                var m = Math.floor(diff / 60000);
                                var s = Math.floor((diff % 60000) / 1000);
                                document.getElementById('timer').innerHTML = (m<10?"0":"")+m+":"+(s<10?"0":"")+s;
                            }}
                        }}, 1000);
                    </script>
                """, height=220)
                if st.button("✅ FINALIZAR E VOLTAR"):
                    supabase.table('historico').insert({'email': st.session_state.user_atual, 'nome': u_info['nome'], 'data': get_now().date().isoformat(), 'h_saida': st.session_state.h_saida, 'h_retorno': get_now().strftime("%H:%M:%S"), 'duracao': st.session_state.tempo_pausa}).execute()
                    supabase.table('escalas').delete().eq('id', st.session_state.pausa_id).execute()
                    enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** FINALIZOU.")
                    st.session_state.pausa_ativa = False
                    st.rerun()
else: st.error("Erro de conexão.")
