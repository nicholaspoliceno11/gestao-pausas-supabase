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
    try: requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except: pass

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

Atenciosamente,
Gestão de Pausas - Quero Passagem"""
        msg.attach(MIMEText(corpo, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg); server.quit()
        return True
    except: return False

def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- UI E ESTILO ---
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
                st.session_state.update({"logado": True, "user_atual": u_input, "precisa_trocar": usuarios_db[u_input].get('primeiro_acesso', True)})
                st.rerun()
            else: st.error("Login ou senha inválidos.")
    
    elif st.session_state.get('precisa_trocar'):
        nova = st.text_input("Nova Senha", type="password")
        if st.button("ALTERAR") and len(nova) >= 6:
            supabase.table('usuarios').update({'senha': nova, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
            st.session_state.precisa_trocar = False; st.rerun()

    else:
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        st.sidebar.write(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Liberar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Liberar Pausa":
                at = [e for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()]
                alvo = st.selectbox("Atendente SAC:", at)
                minutos = st.number_input("Duração (minutos):", 1, 120, 15)
                if st.button("AUTORIZAR PAUSA"):
                    supabase.table('escalas').insert({'email':alvo,'nome':usuarios_db[alvo]['nome'],'duracao':minutos,'status':'Pendente','inicio':get_now().isoformat()}).execute()
                    enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 {usuarios_db[alvo]['nome']}, sua pausa foi liberada!")
                    st.success("✅ Liberado!")

            elif menu == "Histórico":
                st.subheader("📊 Histórico de Pausas")
                h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                if h_resp.data:
                    df = pd.DataFrame(h_resp.data)
                    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
                    st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                    st.download_button("📥 Baixar para Google Planilhas (CSV)", data=gerar_csv(df), file_name=f"historico_{date.today()}.csv", mime="text/csv")
                else: st.info("Histórico vazio.")

            elif menu == "Gestão de Equipe":
                tab_add, tab_del = st.tabs(["➕ Adicionar", "🗑️ Excluir"])
                with tab_add:
                    with st.form("add_user", clear_on_submit=True):
                        n, e, s = st.text_input("Nome"), st.text_input("Email").lower(), st.text_input("Senha Temp")
                        t = st.selectbox("Perfil", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("SALVAR"):
                            supabase.table('usuarios').insert({'nome':n,'email':e,'senha':s,'tipo':t,'primeiro_acesso':True}).execute()
                            enviar_email_boas_vindas(n, e, s)
                            st.success("✅ Usuário criado e e-mail enviado!"); st.rerun()
                with tab_del:
                    remover = st.selectbox("Selecione para remover:", list(usuarios_db.keys()))
                    if st.button("REMOVER PERMANENTEMENTE"):
                        supabase.table('usuarios').delete().eq('id', usuarios_db[remover]['id']).execute()
                        st.success("🗑️ Usuário removido!"); st.rerun()

            elif menu == "Correções":
                st.subheader("⚠️ Destravar Funcionário")
                esc = supabase.table('escalas').select('*').execute()
                if esc.data:
                    sel = st.selectbox("Funcionário:", [f"{x['nome']} ({x['email']})" for x in esc.data])
                    cod = st.text_input("Código Mestre", type="password")
                    if st.button("DESTRAVAR AGORA") and cod == CODIGO_MESTRE_GESTAO:
                        id_e = esc.data[[f"{x['nome']} ({x['email']})" for x in esc.data].index(sel)]['id']
                        supabase.table('escalas').delete().eq('id', id_e).execute()
                        st.success("✅ Resetado!"); st.rerun()
                else: st.write("Ninguém travado.")

        else: # --- LÓGICA DO ATENDENTE (COM RECUPERAÇÃO DE QUEDA) ---
            st.subheader("⏱️ Minha Pausa")
            
            # Recuperação automática se o site travar/atualizar
            res_recupera = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Em Pausa').execute()
            
            if res_recupera.data and 'pausa_ativa' not in st.session_state:
                pausa_salva = res_recupera.data[0]
                inicio_dt = datetime.fromisoformat(pausa_salva['inicio'].replace('Z', '+00:00')).astimezone(TIMEZONE_SP)
                fim_dt = inicio_dt + timedelta(minutes=pausa_salva['duracao'])
                
                if get_now() < fim_dt:
                    st.session_state.update({
                        "pausa_ativa": True, 
                        "p_id": pausa_salva['id'], 
                        "t_pausa": pausa_salva['duracao'],
                        "fim": fim_dt.timestamp() * 1000,
                        "saida": inicio_dt.strftime("%H:%M:%S")
                    })
                    st.warning("⚠️ Sua pausa foi recuperada após uma queda de conexão!")
                else:
                    st.error("🚨 Seu tempo de pausa expirou durante a queda de conexão. Finalize agora!")
                    st.session_state.update({
                        "pausa_ativa": True, "p_id": pausa_salva['id'], "t_pausa": pausa_salva['duracao'],
                        "fim": get_now().timestamp() * 1000, "saida": inicio_dt.strftime("%H:%M:%S")
                    })

            if not st.session_state.get('pausa_ativa'):
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO"):
                    res = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()
                    if res.data:
                        st.session_state.update({"t_pausa": res.data[0]['duracao'], "p_id": res.data[0]['id'], "liberado": True})
                        st.success(f"✅ Autorizado: {st.session_state.t_pausa} min!"); st.balloons()
                    else: st.info("⏳ Aguardando liberação...")
                
                if st.session_state.get('liberado') and st.button("🚀 INICIAR"):
                    # Registramos o 'inicio' exato no banco para poder recuperar depois
                    hora_inicio = get_now()
                    supabase.table('escalas').update({
                        'status': 'Em Pausa', 
                        'inicio': hora_inicio.isoformat()
                    }).eq('id', st.session_state.p_id).execute()
                    
                    st.session_state.update({
                        "pausa_ativa": True, 
                        "fim": (hora_inicio + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000, 
                        "saida": hora_inicio.strftime("%H:%M:%S")
                    })
                    enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** iniciou."); st.rerun()
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
                                playBeep(); alert("🔴 TEMPO ESGOTADO! BATA O PONTO NO VR!"); clearInterval(x);
                            }} else {{
                                var m = Math.floor(diff / 60000); var s = Math.floor((diff % 60000) / 1000);
                                document.getElementById('timer').innerHTML = (m<10?"0":"")+m+":"+(s<10?"0":"")+s;
                            }}
                        }}, 1000);
                    </script>""", height=220)
                if st.button("✅ FINALIZAR E VOLTAR"):
                    supabase.table('historico').insert({'email': st.session_state.user_atual, 'nome': u_info['nome'], 'data': get_now().date().isoformat(), 'h_saida': st.session_state.saida, 'h_retorno': get_now().strftime("%H:%M:%S"), 'duracao': st.session_state.t_pausa}).execute()
                    supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()
                    enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** finalizou."); st.session_state.pausa_ativa = False; st.rerun()
else: st.error("Erro de conexão.")
