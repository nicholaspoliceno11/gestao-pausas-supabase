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

# --- CONFIGURAÇÕES DE AMBIENTE ---
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
    try: requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except: pass

def enviar_email_boas_vindas(nome, email_destino, senha_temp):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestão de Pausas QP <{GMAIL_USER}>"
        msg['To'] = email_destino
        msg['Subject'] = "🎉 Bem-vindo ao Sistema de Gestão de Pausas - Quero Passagem"
        corpo = f"Olá {nome},\n\nSeu acesso ao sistema Quero Passagem foi criado!\n\nLink: https://gestao-pausas-supabase-rytpzdbzurqiuf53rgnusb.streamlit.app/\nE-mail: {email_destino}\nSenha Temporária: {senha_temp}\n\nIMPORTANTE: No primeiro acesso, você deverá criar uma nova senha."
        msg.attach(MIMEText(corpo, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg); server.quit()
        return True
    except: return False

# --- FUNÇÕES DE EXPORTAÇÃO ---
def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- CONFIGURAÇÃO VISUAL ---
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

    # Carregar base de usuários para validação
    usuarios_resp = supabase.table('usuarios').select('*').execute()
    usuarios_db = {u['email'].lower(): u for u in usuarios_resp.data}

    if not st.session_state.logado:
        st.markdown("### 🔐 Login")
        u_input = st.text_input("E-mail").strip().lower()
        p_input = st.text_input("Senha", type="password")
        if st.button("ACESSAR SISTEMA"):
            if u_input in usuarios_db and usuarios_db[u_input]['senha'] == p_input:
                st.session_state.update({"logado": True, "user_atual": u_input, "precisa_trocar": usuarios_db[u_input].get('primeiro_acesso', True)})
                st.rerun()
            else: st.error("E-mail ou senha incorretos.")
    
    elif st.session_state.get('precisa_trocar'):
        nova = st.text_input("Defina sua nova senha (mínimo 6 caracteres)", type="password")
        if st.button("CONFIRMAR SENHA") and len(nova) >= 6:
            supabase.table('usuarios').update({'senha': nova, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
            st.session_state.precisa_trocar = False; st.rerun()

    else:
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        st.sidebar.write(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

        # REESTRUTURAÇÃO DAS OPÇÕES DE GESTÃO
        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Selecione a Ação:", ["Liberar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Liberar Pausa":
                st.subheader("Autorizar Saída para Pausa")
                at = [e for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()]
                alvo = st.selectbox("Selecione o Atendente:", at)
                minutos = st.number_input("Duração Autorizada (min):", 1, 120, 15)
                if st.button("LIBERAR AGORA"):
                    supabase.table('escalas').insert({'email':alvo,'nome':usuarios_db[alvo]['nome'],'duracao':minutos,'status':'Pendente','inicio':get_now().isoformat()}).execute()
                    enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 **{usuarios_db[alvo]['nome']}**, sua pausa foi liberada!")
                    st.success("Pausa autorizada com sucesso!")

            elif menu == "Histórico":
                st.subheader("📊 Relatório Geral de Pausas")
                h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                if h_resp.data:
                    df = pd.DataFrame(h_resp.data)
                    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
                    st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                    st.download_button("📥 Exportar para Google Planilhas (CSV)", data=gerar_csv(df), file_name=f"pausas_{date.today()}.csv", mime="text/csv")
                else: st.info("Histórico vazio.")

            elif menu == "Gestão de Equipe":
                tab_add, tab_del = st.tabs(["➕ Adicionar Funcionário", "🗑️ Remover Funcionário"])
                with tab_add:
                    with st.form("add_form", clear_on_submit=True):
                        nome_n = st.text_input("Nome Completo")
                        email_n = st.text_input("E-mail Corporativo").lower()
                        senha_n = st.text_input("Senha Temporária")
                        tipo_n = st.selectbox("Cargo/Perfil", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("CADASTRAR"):
                            supabase.table('usuarios').insert({'nome':nome_n,'email':email_n,'senha':senha_n,'tipo':tipo_n,'primeiro_acesso':True}).execute()
                            enviar_email_boas_vindas(nome_n, email_n, senha_n)
                            st.success("Funcionário cadastrado e e-mail enviado!")
                            st.rerun()
                with tab_del:
                    remover = st.selectbox("Escolha quem remover:", list(usuarios_db.keys()))
                    if st.button("REMOVER DEFINITIVAMENTE"):
                        supabase.table('usuarios').delete().eq('id', usuarios_db[remover]['id']).execute()
                        st.success("Usuário excluído."); st.rerun()

            elif menu == "Correções":
                st.subheader("⚠️ Destravar Status de Funcionário")
                esc = supabase.table('escalas').select('*').execute()
                if esc.data:
                    travado = st.selectbox("Funcionário Travado:", [f"{x['nome']} ({x['email']})" for x in esc.data])
                    cod = st.text_input("Digite o Código Mestre", type="password")
                    if st.button("FORÇAR DESTRAVAMENTO") and cod == CODIGO_MESTRE_GESTAO:
                        id_e = esc.data[[f"{x['nome']} ({x['email']})" for x in esc.data].index(travado)]['id']
                        supabase.table('escalas').delete().eq('id', id_e).execute()
                        st.success("Status resetado com sucesso!"); st.rerun()
                else: st.write("Não há funcionários travados no momento.")

        else: # INTERFACE DO ATENDENTE
            st.subheader("⏱️ Painel de Pausa")
            if 'pausa_ativa' not in st.session_state or not st.session_state.pausa_ativa:
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO"):
                    res = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()
                    if res.data:
                        st.session_state.update({"t_pausa": res.data[0]['duracao'], "p_id": res.data[0]['id'], "liberado": True})
                        st.success(f"Sua pausa de {st.session_state.t_pausa} min foi liberada!"); st.balloons()
                    else: st.info("Aguardando autorização da gestão...")
                if st.session_state.get('liberado') and st.button("🚀 INICIAR AGORA"):
                    supabase.table('escalas').update({'status': 'Em Pausa'}).eq('id', st.session_state.p_id).execute()
                    st.session_state.update({"pausa_ativa": True, "fim": (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000, "saida": get_now().strftime("%H:%M:%S")})
                    enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** iniciou a pausa."); st.rerun()
            else:
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px;">--:--</div>
                    <script>
                        var endTime = {st.session_state.fim};
                        function playBeep() {{
                            var ctx = new (window.AudioContext || window.webkitAudioContext)();
                            var osc = ctx.createOscillator(); var g = ctx.createGain();
                            osc.connect(g); g.connect(ctx.destination);
                            osc.type = 'square'; osc.frequency.value = 1000;
                            g.gain.setValueAtTime(1, ctx.currentTime);
                            osc.start(); osc.stop(ctx.currentTime + 2);
                        }}
                        var x = setInterval(function() {{
                            var diff = endTime - new Date().getTime();
                            if (diff <= 0) {{
                                document.getElementById('timer').innerHTML = "00:00";
                                playBeep(); alert("🔴 TEMPO ESGOTADO! BATA O PONTO NO VR AGORA!"); clearInterval(x);
                            }} else {{
                                var m = Math.floor(diff / 60000); var s = Math.floor((diff % 60000) / 1000);
                                document.getElementById('timer').innerHTML = (m<10?"0":"")+m+":"+(s<10?"0":"")+s;
                            }}
                        }}, 1000);
                    </script>""", height=220)
                if st.button("✅ FINALIZAR PAUSA (Bati o Ponto no VR)"):
                    supabase.table('historico').insert({'email': st.session_state.user_atual, 'nome': u_info['nome'], 'data': get_now().date().isoformat(), 'h_saida': st.session_state.saida, 'h_retorno': get_now().strftime("%H:%M:%S"), 'duracao': st.session_state.t_pausa}).execute()
                    supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()
                    enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** finalizou a pausa."); st.session_state.pausa_ativa = False; st.rerun()
else: st.error("Erro crítico de conexão com o banco de dados Supabase.")
