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

# --- CONFIGURAÇÃO EMAIL (GMAIL SMTP) ---
GMAIL_USER = "gestao.queropassagem@gmail.com"
GMAIL_PASSWORD = "pakiujauoxbmihyy" 

# --- CONFIGURAÇÃO DISCORD ---
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSjPJtSD91ZkrvUi"
DISCORD_WEBHOOK_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI"

# --- CONFIGURAÇÃO SUPABASE ---
SUPABASE_URL = "https://gzozqxrlgdzjrqfvdxzw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6b3pxeHJsZ2R6anJxZnZkeHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0OTg1MjIsImV4cCI6MjA4MjA3NDUyMn0.dLEjBPESUz5KnVwxqEMaMxoy65gsLqG2QdjK2xFTUhU"

TIMEZONE_SP = pytz.timezone('America/Sao_Paulo')

def get_now():
    return datetime.now(TIMEZONE_SP)

def enviar_discord(webhook_url, mensagem):
    try:
        requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except:
        pass

# --- NOVA FUNÇÃO DE ENVIO DE EMAIL ---
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

        ⚠️ IMPORTANTE: No primeiro acesso, você será solicitado a criar uma nova senha (mínimo 6 caracteres).

        📋 COMO FUNCIONA O SISTEMA:
        1️⃣ SOLICITAR PAUSA: Faça login e clique em "VERIFICAR MINHA LIBERAÇÃO".
        2️⃣ INICIAR PAUSA: Quando autorizado, clique em "INICIAR". O cronômetro começará.
        3️⃣ ALERTA: O sistema emitirá um ALARME SONORO ao finalizar o tempo.
        4️⃣ FINALIZAR: BATA O PONTO NO VR antes de clicar em "FINALIZAR" no sistema.

        💡 DICA: Mantenha a aba do navegador aberta para ouvir o alarme.

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
    except Exception as e:
        return False

# --- FUNÇÕES DE RELATÓRIO ---
def gerar_relatorio_csv(df, nome_arquivo="relatorio"):
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    return csv

def gerar_relatorio_excel(df, nome_arquivo="relatorio"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
    return output.getvalue()

def formatar_dataframe_relatorio(df):
    if not df.empty:
        if 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d/%m/%Y %H:%M')
    return df

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

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def conectar_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table('usuarios').select('id').limit(1).execute()
        return client
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o Supabase: {e}")
        return None

supabase: Client = conectar_supabase()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div><div class="subtitulo-qp">Gestão de Pausa</div>', unsafe_allow_html=True)
    st.divider()

    if 'logado' not in st.session_state:
        st.session_state.logado = False
    if 'pausa_ativa' not in st.session_state:
        st.session_state.pausa_ativa = False

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_log = st.text_input("E-mail", key="email_login")
        p_log = st.text_input("Senha", type="password", key="senha_login")
        
        if st.button("ACESSAR SISTEMA"):
            u_log_clean = u_log.strip().lower() if u_log else ""
            p_log_clean = p_log.strip() if p_log else ""
            if not u_log_clean or not p_log_clean:
                st.error("⚠️ Preencha todos os campos!")
            else:
                try:
                    usuarios_response = supabase.table('usuarios').select('*').execute()
                    usuarios_db = {u['email'].strip().lower(): u for u in usuarios_response.data}
                    if u_log_clean in usuarios_db and usuarios_db[u_log_clean]['senha'] == p_log_clean:
                        st.session_state.logado = True
                        st.session_state.user_atual = u_log_clean
                        st.session_state.usuarios_db = usuarios_db
                        st.session_state.precisa_trocar_senha = usuarios_db[u_log_clean].get('primeiro_acesso', True)
                        st.rerun()
                    else:
                        st.error("❌ Login ou senha incorretos.")
                except Exception as e:
                    st.error(f"❌ Erro ao validar login: {e}")
    
    elif st.session_state.get('precisa_trocar_senha', False):
        st.markdown("### 🔐 Primeiro Acesso - Alterar Senha")
        st.warning("⚠️ Por segurança, você precisa criar uma nova senha.")
        nova_senha = st.text_input("Nova Senha", type="password", key="nova")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password", key="conf")
        if st.button("✅ ALTERAR SENHA"):
            if len(nova_senha) < 6:
                st.error("❌ A senha deve ter pelo menos 6 caracteres!")
            elif nova_senha != confirma_senha:
                st.error("❌ As senhas não coincidem!")
            else:
                supabase.table('usuarios').update({'senha': nova_senha, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
                st.success("✅ Senha alterada!")
                st.session_state.precisa_trocar_senha = False
                st.cache_resource.clear()
                st.rerun()

    else:
        usuarios_db = st.session_state.get('usuarios_db', {})
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        
        st.sidebar.markdown(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Liberar Pausa", "Histórico", "Relatórios", "Gestão de Equipe"], horizontal=True, label_visibility="collapsed")
            st.divider()
            
            if menu == "Liberar Pausa":
                st.subheader("Autorizar Pausa")
                atendentes = [email for email, info in usuarios_db.items() if 'atendente' in info.get('tipo', '').lower()]
                if not atendentes: st.warning("⚠️ Nenhum atendente cadastrado.")
                else:
                    alvo = st.selectbox("Atendente SAC:", atendentes)
                    tempo_alvo = st.number_input("Duração (minutos):", 1, 120, 15)
                    if st.button("AUTORIZAR PAUSA"):
                        supabase.table('escalas').insert({'email': alvo, 'nome': usuarios_db[alvo]['nome'], 'duracao': tempo_alvo, 'status': 'Pendente', 'inicio': get_now().isoformat()}).execute()
                        enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 **{usuarios_db[alvo]['nome']}**, sua pausa foi liberada!")
                        st.success("✅ Pausa liberada!")

            elif menu == "Gestão de Equipe":
                st.subheader("👥 Gerenciamento de Usuários")
                t1, t2 = st.tabs(["➕ Adicionar", "🗑️ Excluir"])
                with t1:
                    with st.form("cad_user", clear_on_submit=True):
                        f_nome = st.text_input("Nome")
                        f_email = st.text_input("Email").strip().lower()
                        f_senha = st.text_input("Senha Temporária")
                        f_tipo = st.selectbox("Perfil", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("SALVAR"):
                            try:
                                supabase.table('usuarios').insert({'nome': f_nome, 'email': f_email, 'senha': f_senha, 'tipo': f_tipo, 'primeiro_acesso': True}).execute()
                                with st.spinner('Enviando e-mail de boas-vindas...'):
                                    envio = enviar_email_boas_vindas(f_nome, f_email, f_senha)
                                if envio: st.success(f"✅ Usuário criado e e-mail enviado para {f_email}!")
                                else: st.warning("✅ Usuário criado, mas houve erro no envio do e-mail.")
                                st.cache_resource.clear()
                                st.rerun()
                            except Exception as e: st.error(f"❌ Erro: {e}")

            elif menu == "Histórico":
                hist_response = supabase.table('historico').select('*').order('created_at', desc=True).limit(50).execute()
                df = pd.DataFrame(hist_response.data)
                st.dataframe(formatar_dataframe_relatorio(df)[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']] if not df.empty else pd.DataFrame())

            elif menu == "Relatórios":
                st.subheader("📈 Relatórios")
                data_inicio = st.date_input("Início:", date.today() - timedelta(days=30))
                data_fim = st.date_input("Fim:", date.today())
                if st.button("🔍 GERAR"):
                    hist_response = supabase.table('historico').select('*').gte('data', data_inicio.isoformat()).lte('data', data_fim.isoformat()).execute()
                    df = pd.DataFrame(hist_response.data)
                    if not df.empty:
                        st.metric("Total de Pausas", len(df))
                        st.dataframe(formatar_dataframe_relatorio(df)[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']])
                    else: st.info("Nada encontrado.")

        else:
            # Lógica do Atendente (Verificação e Cronômetro)
            st.subheader("⏱️ Minha Pausa")
            if not st.session_state.pausa_ativa:
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO"):
                    pausa_response = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()
                    if pausa_response.data:
                        st.session_state.tempo_pausa = pausa_response.data[0]['duracao']
                        st.session_state.pausa_id = pausa_response.data[0]['id']
                        st.session_state.pausa_liberada = True
                        st.success(f"✅ Autorizado: {st.session_state.tempo_pausa} min!")
                        st.balloons()
                    else: st.info("⏳ Aguardando supervisor...")
                
                if st.session_state.get('pausa_liberada'):
                    if st.button(f"🚀 INICIAR {st.session_state.tempo_pausa} MINUTOS"):
                        supabase.table('escalas').update({'status': 'Em Pausa'}).eq('id', st.session_state.pausa_id).execute()
                        st.session_state.pausa_ativa = True
                        st.session_state.h_termino_ms = (get_now() + timedelta(minutes=st.session_state.tempo_pausa)).timestamp() * 1000
                        st.session_state.h_saida = get_now().strftime("%H:%M:%S")
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** INICIOU a pausa.")
                        st.rerun()
            else:
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px; background-color: #fffafa;">--:--</div>
                    <script>
                        var endTime = {st.session_state.h_termino_ms};
                        var alerted = false;
                        function playBeep() {{
                            var context = new (window.AudioContext || window.webkitAudioContext)();
                            var osc = context.createOscillator();
                            var gain = context.createGain();
                            osc.connect(gain); gain.connect(context.destination);
                            osc.type = 'square'; osc.frequency.value = 1200;
                            gain.gain.setValueAtTime(1, context.currentTime);
                            osc.start(); osc.stop(context.currentTime + 0.5);
                        }}
                        var x = setInterval(function() {{
                            var diff = endTime - new Date().getTime();
                            if (diff <= 0) {{
                                document.getElementById('timer').innerHTML = "00:00";
                                if (!alerted) {{ alerted = true; playBeep(); alert("🔴 TEMPO ESGOTADO! Bata o ponto no VR!"); }}
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
                    enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** FINALIZOU a pausa.")
                    st.session_state.pausa_ativa = False
                    st.session_state.pausa_liberada = False
                    st.rerun()

else: st.error("❌ Erro de conexão com o banco.")
