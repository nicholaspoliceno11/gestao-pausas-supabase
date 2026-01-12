import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, date
import time
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
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1458111767115989005/HbH2dBcht1qREqLSwf7yqxgAgmIFUYPABtLGWHrD8i8xLabHBIfnOLKRs9D-xWh69KBP"
DISCORD_WEBHOOK_SAC_QP = "https://discord.com/api/webhooks/1453463270517244091/x1KdnNbW8oR-yslJLb5zL5hdLHZXzHLq-I5RwTb67O16d8ccWh69FI63J2i1KJlYmQq4"
SUPABASE_URL = "https://gzozqxrlgdzjrqfvdxzw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6b3pxeHJsZ2R6anJxZnZkeHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0OTg1MjIsImV4cCI6MjA4MjA3NDUyMn0.dLEjBPESUz5KnVwxqEMaMxoy65gsLqG2QdjK2xFTUhU"

CODIGO_MESTRE_GESTAO = "QP2025"
TIMEZONE_SP = pytz.timezone('America/Sao_Paulo')

def get_now():
    return datetime.now(TIMEZONE_SP)

def enviar_discord(webhook_url, mensagem):
    try:
        requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except: pass

def enviar_email_cadastro(nome, email_destino, senha_temp):
    corpo_email = f"""
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
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = email_destino
    msg['Subject'] = "🚀 Seu Acesso: Sistema de Gestão de Pausas QP"
    msg.attach(MIMEText(corpo_email, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False

def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- UI E ESTILO (MANTIDO CONFORME SOLICITADO) ---
st.set_page_config(page_title="Gestão de Pausas - QP", layout="centered")

st.markdown("""
<style>
    :root { color-scheme: light !important; }
    body, .stApp { background-color: #f5f7fa !important; color: #262730 !important; }
    .logo-qp { font-family: 'Arial Black', sans-serif; font-size: 35pt; color: #004a99; text-align: center; margin-bottom: 5px; }
    .subtitulo-qp { font-size: 16pt; color: #666; text-align: center; margin-bottom: 30px; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #004a99 0%, #003366 100%) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: 1px solid white !important;
        width: 100% !important;
        height: 45px !important;
        font-weight: bold !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        color: #262730 !important;
        -webkit-text-fill-color: #262730 !important;
        background-color: white !important;
    }
    [data-baseweb="popover"] li { color: #262730 !important; }
    [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span { color: #262730 !important; }
    .stButton > button[kind="primary"] { background-color: #004a99 !important; color: white !important; }
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
    except Exception as e:
        st.error(f"❌ Erro ao conectar com banco de dados: {e}")
        st.stop()

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_input = st.text_input("E-mail").strip().lower()
        p_input = st.text_input("Senha", type="password")
        if st.button("ACESSAR SISTEMA", type="primary"):
            if u_input in usuarios_db and usuarios_db[u_input]['senha'] == p_input:
                st.session_state.update({"logado": True, "user_atual": u_input, "precisa_trocar": usuarios_db[u_input].get('primeiro_acesso', True)})
                st.rerun()
            else: st.error("❌ Credenciais incorretas.")

    elif st.session_state.get('precisa_trocar'):
        st.markdown("### 🔑 Criar Nova Senha")
        nova = st.text_input("Nova Senha", type="password")
        confirma = st.text_input("Confirme a Senha", type="password")
        if st.button("ALTERAR SENHA", type="primary"):
            if len(nova) >= 6 and nova == confirma:
                supabase.table('usuarios').update({'senha': nova, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
                st.session_state.precisa_trocar = False
                st.rerun()
            else: st.error("❌ Verifique os campos.")

    else:
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        st.sidebar.write(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"): 
            st.session_state.clear()
            st.rerun()

        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Agendar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Agendar Pausa":
                st.markdown("### 🗓️ Agendar Pausa para Atendente")
                escalas_ativas_resp = supabase.table('escalas').select('email, status').execute()
                escalas_ativas_emails = {x['email'] for x in escalas_ativas_resp.data if x['status'] in ['Agendada', 'Em Pausa']}

                at_list_disponiveis = [e for e, info in usuarios_db.items() if 'atendente' in info['tipo'].lower() and e not in escalas_ativas_emails]

                if not at_list_disponiveis:
                    st.info("✅ Todos os atendentes SAC já têm uma pausa agendada ou estão em pausa.")
                else:
                    alvo = st.selectbox("Selecione o Atendente SAC:", at_list_disponiveis)
                    
                    tipo_pausa = st.selectbox(
                        "Selecione o tipo de Pausa:",
                        ["Feedback", "Liberado pela Supervisão", "Pausa 15", "Pausa 1h", "Pausa pessoal"]
                    )
                    
                    minutos = st.number_input("Duração (Minutos):", 1, 120, 15)
                    horario_agendado_str = st.text_input("Horário Agendado (HH:MM):", value=get_now().strftime("%H:%M"))

                    if st.button("✅ AGENDAR PAUSA", type="primary"):
                        try:
                            supabase.table('escalas').insert({
                                'email': alvo, 
                                'nome': usuarios_db[alvo]['nome'],
                                'duracao': minutos, 
                                'status': 'Agendada',
                                'horario_agendado': horario_agendado_str,
                                'tipo_pausa': tipo_pausa
                            }).execute()
                            
                            enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 Supervisor {u_info['nome']} programou **{tipo_pausa}** de {usuarios_db[alvo]['nome']} ({minutos} min) para as {horario_agendado_str}.")
                            st.success(f"✅ {tipo_pausa} de {usuarios_db[alvo]['nome']} agendada com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao agendar: {str(e)}")
                            st.info("💡 Verifique se a coluna 'tipo_pausa' existe nas tabelas 'escalas' e 'historico' no Supabase.")

            elif menu == "Histórico":
                st.markdown("### 📊 Histórico de Pausas")
                h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                if h_resp.data:
                    df = pd.DataFrame(h_resp.data)
                    # Adiciona tipo_pausa ao histórico se existir
                    colunas_exibir = ['nome', 'data', 'h_saida', 'h_retorno', 'duracao']
                    if 'tipo_pausa' in df.columns:
                        colunas_exibir.insert(1, 'tipo_pausa')
                    st.dataframe(df[colunas_exibir], use_container_width=True)
                    st.download_button("📥 Baixar CSV", data=gerar_csv(df), file_name="historico.csv", mime="text/csv")

            elif menu == "Gestão de Equipe":
                st.markdown("### 👥 Gestão de Usuários")
                tab_add, tab_del = st.tabs(["➕ Adicionar Usuário", "🗑️ Remover Usuário"])
                with tab_add:
                    with st.form("add_user"):
                        n_f = st.text_input("Nome Completo*")
                        e_f = st.text_input("E-mail*").lower().strip()
                        s_f = st.text_input("Senha Temporária*", type="password")
                        t_f = st.selectbox("Perfil*", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("💾 SALVAR USUÁRIO"):
                            if n_f and e_f and s_f and len(s_f) >= 6:
                                if e_f in usuarios_db: st.error("❌ E-mail já cadastrado.")
                                else:
                                    supabase.table('usuarios').insert({'nome': n_f, 'email': e_f, 'senha': s_f, 'tipo': t_f, 'primeiro_acesso': True}).execute()
                                    if enviar_email_cadastro(n_f, e_f, s_f):
                                        st.success(f"✅ Usuário '{n_f}' cadastrado e e-mail enviado!")
                                    else:
                                        st.warning("⚠️ Cadastrado, mas falha no e-mail.")
                                    time.sleep(1)
                                    st.rerun()
                            else: st.error("❌ Preencha corretamente.")
                with tab_del:
                    lista_del = [f"{u['nome']} ({u['email']})" for u in usuarios_resp.data if u['email'] != st.session_state.user_atual]
                    if lista_del:
                        sel_del = st.selectbox("Remover:", lista_del)
                        email_final = sel_del.split('(')[-1].replace(')', '')
                        cod_del = st.text_input("Código Mestre p/ Deletar:", type="password")
                        if st.button("🗑️ EXCLUIR DEFINITIVAMENTE", type="primary"):
                            if cod_del == CODIGO_MESTRE_GESTAO:
                                supabase.table('usuarios').delete().eq('email', email_final).execute()
                                st.success("✅ Removido.")
                                st.rerun()
                            else: st.error("❌ Código incorreto.")

            elif menu == "Correções":
                st.markdown("### ⚠️ Destravar Funcionário")
                esc_resp = supabase.table('escalas').select('*').execute()
                if esc_resp.data:
                    sel_un = st.selectbox("Pausa ativa:", [f"{x['nome']} ({x['email']})" for x in esc_resp.data])
                    cod_un = st.text_input("Código Mestre:", type="password")
                    if st.button("🔓 DESTRAVAR"):
                        if cod_un == CODIGO_MESTRE_GESTAO:
                            supabase.table('escalas').delete().eq('email', sel_un.split('(')[-1].split(')')[0]).execute()
                            st.success("✅ Destravado.")
                            st.rerun()
                        else: st.error("❌ Código incorreto.")

        else: # ATENDENTE
            st.markdown("### ⏱️ Minha Pausa")
            res_agendada = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).execute()
            
            if not st.session_state.get('pausa_ativa'):
                if res_agendada.data:
                    pausa = res_agendada.data[0]
                    tipo_info = f" - {pausa.get('tipo_pausa', 'Pausa')}" if pausa.get('tipo_pausa') else ""
                    st.info(f"✅ Pausa autorizada{tipo_info}: {pausa['duracao']} min às {pausa['horario_agendado']}.")
                    if st.button("🚀 INICIAR PAUSA AGORA", type="primary"):
                        hora_s = get_now().strftime("%H:%M:%S")
                        supabase.table('escalas').update({'status': 'Em Pausa', 'h_saida': hora_s}).eq('id', pausa['id']).execute()
                        st.session_state.update({
                            "pausa_ativa": True, 
                            "fim": (get_now() + timedelta(minutes=pausa['duracao'])).timestamp() * 1000, 
                            "saida": hora_s, 
                            "p_id": pausa['id'], 
                            "t_pausa": pausa['duracao'],
                            "tipo_pausa": pausa.get('tipo_pausa', 'Pausa')
                        })
                        tipo_msg = pausa.get('tipo_pausa', 'pausa').lower()
                        enviar_discord(DISCORD_WEBHOOK_SAC_QP, f"Atendente {u_info['nome']} iniciou a pausa **{tipo_msg}**.")
                        st.rerun()
                else: st.info("⏳ Aguardando agendamento...")
            else:
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px;">--:--</div>
                    <script>
                        var endTime = {st.session_state.fim};
                        var x = setInterval(function() {{
                            var diff = endTime - new Date().getTime();
                            if (diff <= 0) {{
                                clearInterval(x); document.getElementById('timer').innerHTML = "00:00";
                                alert("🚨 ATENÇÃO! Sua pausa finalizou!");
                            }} else {{
                                var m = Math.floor(diff / 60000); var s = Math.floor((diff % 60000) / 1000);
                                document.getElementById('timer').innerHTML = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
                            }}
                        }}, 1000);
                    </script>""", height=220)
                if st.button("✅ FINALIZAR E VOLTAR", type="primary"):
                    supabase.table('historico').insert({
                        'email': st.session_state.user_atual, 
                        'nome': u_info['nome'], 
                        'data': get_now().date().isoformat(), 
                        'h_saida': st.session_state.saida, 
                        'h_retorno': get_now().strftime("%H:%M:%S"), 
                        'duracao': st.session_state.t_pausa,
                        'tipo_pausa': st.session_state.get('tipo_pausa', 'Pausa')
                    }).execute()
                    supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()
                    tipo_msg = st.session_state.get('tipo_pausa', 'pausa').lower()
                    enviar_discord(DISCORD_WEBHOOK_SAC_QP, f"Atendente {u_info['nome']} finalizou a pausa **{tipo_msg}**.")
                    st.session_state.pausa_ativa = False
                    st.rerun()

else: st.error("Erro de conexão.")
