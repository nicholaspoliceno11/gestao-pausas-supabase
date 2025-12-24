import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, date, time
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
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSC_PJtSD91ZkrvUi" # Webhook para notificações da equipe (ex: 10 min antes da pausa)
DISCORD_WEBHOOK_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI" # Webhook para notificações da gestão (ex: agendamento, início/fim de pausa)
SUPABASE_URL = "https://gzozqxrlgdzjrqfvdxzw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6b3pxeHJsZ2R6anJxZnZkeHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0OTg1MjIsImV4cCI6MjA4MjA3NDUyMn0.dLEjBPESUz5KnVwxqEMaMxoy65gsLqG2QdjK2xFTUhU"

CODIGO_MESTRE_GESTAO = "QP2025"
TIMEZONE_SP = pytz.timezone('America/Sao_Paulo')

def get_now():
    return datetime.now(TIMEZONE_SP)

def enviar_discord(webhook_url, mensagem):
    try: requests.post(webhook_url, json={"content": mensagem}, timeout=5)
    except: pass

def gerar_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

# --- UI E ESTILO ---
st.set_page_config(page_title="Gestão de Pausas - QP", layout="centered")

st.markdown("""
<style>
    :root { color-scheme: light !important; }
    body, .stApp { background-color: #f5f7fa !important; color: #262730 !important; }
    .logo-qp { font-family: 'Arial Black', sans-serif; font-size: 35pt; color: #004a99; text-align: center; margin-bottom: 5px; }
    .subtitulo-qp { font-size: 16pt; color: #666; text-align: center; margin-bottom: 30px; }

    /* Sidebar */
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

    /* Selectbox Visibility */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        color: #262730 !important;
        -webkit-text-fill-color: #262730 !important;
        background-color: white !important;
    }
    [data-baseweb="popover"] li { color: #262730 !important; }

    /* Tables */
    [data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span { color: #262730 !important; }

    /* Primary Buttons */
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
        st.error(f"❌ Erro ao conectar com banco de dados ou carregar usuários: {e}")
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
            menu = st.radio("Ações:", ["Agendar Pausa", "Histórico de Pausas", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Agendar Pausa":
                st.markdown("### 🗓️ Agendar Pausa para Atendente")

                todos_atendentes_resp = supabase.table('usuarios').select('email, nome, tipo').execute()
                todos_atendentes_filtrados = {u['email'].lower(): u for u in todos_atendentes_resp.data if 'atendente' in u['tipo'].lower()}

                hoje_iso = get_now().date().isoformat()
                historico_hoje_resp = supabase.table('historico').select('email').eq('data', hoje_iso).execute()
                emails_com_pausa_finalizada_hoje = {h['email'] for h in historico_hoje_resp.data}

                escalas_ativas_ou_agendadas_resp = supabase.table('escalas').select('email').in_('status', ['Agendada', 'Notificada', 'Em Pausa']).execute()
                emails_com_pausa_ativa_ou_agendada = {e['email'] for e in escalas_ativas_ou_agendadas_resp.data}

                at_list_pendentes = [
                    e for e, i in todos_atendentes_filtrados.items() 
                    if e not in emails_com_pausa_finalizada_hoje and e not in emails_com_pausa_ativa_ou_agendada
                ]

                if not at_list_pendentes:
                    st.info("🎉 Todos os atendentes já tiraram ou têm pausas agendadas/ativas para hoje!")
                else:
                    st.write("Selecione os atendentes e agende suas pausas:")
                    agendamentos = []
                    with st.form("form_agendar_pausas"):
                        for atendente_email in at_list_pendentes:
                            atendente_nome = todos_atendentes_filtrados[atendente_email]['nome']
                            st.subheader(f"Para: {atendente_nome}")

                            duracao = st.number_input(f"Duração da pausa (minutos) para {atendente_nome}:", min_value=5, max_value=60, value=15, key=f"duracao_{atendente_email}")

                            horario_agendado_str = st.text_input(f"Horário de início (HH:MM) para {atendente_nome}:", value="00:00", key=f"horario_{atendente_email}")

                            agendamentos.append({
                                'email': atendente_email,
                                'nome': atendente_nome,
                                'duracao': duracao,
                                'horario_agendado_str': horario_agendado_str
                            })
                            st.markdown("---")

                        submitted = st.form_submit_button("Agendar Pausas Selecionadas", type="primary")

                        if submitted:
                            for agendamento in agendamentos:
                                try:
                                    horario_agendado_time_obj = datetime.strptime(agendamento['horario_agendado_str'], '%H:%M').time()
                                except ValueError:
                                    st.error(f"❌ Formato de horário inválido para {agendamento['nome']}. Use HH:MM (ex: 21:30).")
                                    continue

                                data_hora_agendada_para_calculo = datetime.combine(get_now().date(), horario_agendado_time_obj, tzinfo=TIMEZONE_SP)

                                supabase.table('escalas').insert({
                                    'email': agendamento['email'],
                                    'nome': agendamento['nome'],
                                    'duracao': agendamento['duracao'],
                                    'status': 'Agendada',
                                    'horario_agendado': agendamento['horario_agendado_str'],
                                    'horario_agendado_dt_utc': data_hora_agendada_para_calculo.astimezone(pytz.utc).isoformat(),
                                    'notificacao_enviada': False
                                }).execute()

                                st.success(f"✅ Pausa agendada para {agendamento['nome']} às {agendamento['horario_agendado_str']} por {agendamento['duracao']} minutos.")

                                enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🗓️ **{agendamento['nome']}** teve a pausa agendada para **{agendamento['horario_agendado_str']}**.")
                                enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🗓️ Supervisor **{u_info['nome']}** agendou a pausa de **{agendamento['nome']}** para **{agendamento['horario_agendado_str']}**.")

                            st.rerun()

            elif menu == "Histórico de Pausas":
                st.markdown("### 📊 Histórico de Pausas")
                data_selecionada = st.date_input("Selecione a data:", get_now().date())

                if data_selecionada:
                    historico_resp = supabase.table('historico').select('*').eq('data', data_selecionada.isoformat()).order('h_saida', desc=False).execute()
                    historico_data = historico_resp.data

                    if historico_data:
                        df_historico = pd.DataFrame(historico_data)
                        df_historico['h_saida'] = pd.to_datetime(df_historico['h_saida'], format='%H:%M:%S').dt.time
                        df_historico['h_retorno'] = pd.to_datetime(df_historico['h_retorno'], format='%H:%M:%S').dt.time

                        st.dataframe(df_historico[['nome', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)

                        csv = gerar_csv(df_historico)
                        st.download_button(
                            label="Download Histórico CSV",
                            data=csv,
                            file_name=f"historico_pausas_{data_selecionada.isoformat()}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("Nenhuma pausa registrada para esta data.")

            elif menu == "Gestão de Equipe":
                st.markdown("### 👥 Gestão de Equipe")
                tab_add, tab_del = st.tabs(["➕ Adicionar Usuário", "🗑️ Remover Usuário"])
                with tab_add:
                    with st.form("add_user"):
                        n_f = st.text_input("Nome*"); e_f = st.text_input("E-mail*").lower().strip(); s_f = st.text_input("Senha Temporária*")
                        t_f = st.selectbox("Perfil de Acesso*", ["atendente sac", "supervisor", "administrador"])
                        if st.form_submit_button("💾 SALVAR"):
                            if n_f and e_f and s_f:
                                supabase.table('usuarios').insert({'nome': n_f, 'email': e_f, 'senha': s_f, 'tipo': t_f, 'primeiro_acesso': True}).execute()
                                st.success("✅ Cadastrado!")
                                st.rerun()
                            else:
                                st.error("Por favor, preencha todos os campos obrigatórios.")
                with tab_del:
                    lista_del = [f"{u['nome']} ({u['email']})" for u in usuarios_resp.data if u['email'] != st.session_state.user_atual]
                    if lista_del:
                        sel_del = st.selectbox("Selecione quem remover:", lista_del)
                        email_final = sel_del.split('(')[-1].replace(')', '')
                        cod_del = st.text_input("Código Mestre p/ Deletar:", type="password", key="del_cod")
                        if st.button("🗑️ REMOVER"):
                            if cod_del == CODIGO_MESTRE_GESTAO:
                                supabase.table('usuarios').delete().eq('email', email_final).execute()
                                st.success("✅ Usuário removido!")
                                st.rerun()
                            else: st.error("❌ Código incorreto.")
                    else:
                        st.info("Nenhum usuário para remover (exceto você mesmo).")

            elif menu == "Correções":
                st.markdown("### 🛠️ Correções e Destravamento")
                st.warning("Use esta seção com cautela. Ações aqui podem afetar o registro de pausas.")

                pausas_pendentes_resp = supabase.table('escalas').select('*').in_('status', ['Agendada', 'Notificada', 'Em Pausa']).execute()
                pausas_pendentes = pausas_pendentes_resp.data

                if pausas_pendentes:
                    st.write("Pausas pendentes (Agendadas, Notificadas ou Em Pausa):")
                    df_pendentes = pd.DataFrame(pausas_pendentes)
                    st.dataframe(df_pendentes[['nome', 'status', 'horario_agendado', 'duracao']], use_container_width=True)

                    st.markdown("---")
                    st.write("Selecione uma pausa para destravar:")
                    opcoes_destravar = {f"{p['nome']} - {p['horario_agendado']} ({p['status']})": p['id'] for p in pausas_pendentes}
                    selecao_destravar = st.selectbox("Pausa a destravar:", ["Selecione..."] + list(opcoes_destravar.keys()))

                    if selecao_destravar != "Selecione...":
                        pausa_id_destravar = opcoes_destravar[selecao_destravar]
                        if st.button("🔓 Destravar Pausa", type="secondary"):
                            supabase.table('escalas').delete().eq('id', pausa_id_destravar).execute()
                            st.success(f"Pausa {selecao_destravar} destravada com sucesso!")
                            st.rerun()
                else:
                    st.info("Nenhuma pausa pendente para destravar.")

        else: # --- INTERFACE DO ATENDENTE ---
            st.markdown(f"### Olá, {u_info.get('nome')}!")
            st.markdown("---")

            pausa_ativa_resp = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).in_('status', ['Agendada', 'Notificada', 'Em Pausa']).limit(1).execute()
            pausa_data = pausa_ativa_resp.data[0] if pausa_ativa_resp.data else None

            if pausa_data:
                st.session_state.pausa_ativa = True
                st.session_state.p_id = pausa_data['id']
                st.session_state.t_pausa = pausa_data['duracao']

                st.session_state.horario_agendado_str = pausa_data['horario_agendado']

                try:
                    horario_agendado_dt_utc = datetime.fromisoformat(pausa_data['horario_agendado_dt_utc'])
                    horario_agendado_dt_sp = horario_agendado_dt_utc.astimezone(TIMEZONE_SP)
                    st.session_state.horario_agendado_dt = horario_agendado_dt_sp
                except (ValueError, TypeError):
                    st.error("❌ Erro: Horário agendado para cálculo inválido no banco de dados. Contate a gestão.")
                    st.stop()

                if pausa_data['status'] in ['Agendada', 'Notificada']:
                    agora = get_now()
                    tempo_para_pausa = st.session_state.horario_agendado_dt - agora

                    if timedelta(minutes=0) <= tempo_para_pausa <= timedelta(minutes=10) and not pausa_data['notificacao_enviada']:
                        enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 **{u_info['nome']}**, sua pausa foi liberada! Início agendado para **{st.session_state.horario_agendado_str}**.")
                        supabase.table('escalas').update({'status': 'Notificada', 'notificacao_enviada': True}).eq('id', st.session_state.p_id).execute()
                        st.success(f"🔔 Notificação enviada! Sua pausa está agendada para **{st.session_state.horario_agendado_str}**.")
                        st.rerun()

                    st.info(f"🗓️ Sua pausa está agendada para **{st.session_state.horario_agendado_str}** por {st.session_state.t_pausa} minutos.")

                    if tempo_para_pausa > timedelta(minutes=0):
                        minutos_restantes = int(tempo_para_pausa.total_seconds() // 60)
                        segundos_restantes = int(tempo_para_pausa.total_seconds() % 60)
                        st.markdown(f"**Início em:** {minutos_restantes:02d}:{segundos_restantes:02d}")
                    else:
                        st.markdown("**Aguardando início...**")

                    if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True, type="primary"):
                        st.session_state.saida = get_now().strftime("%H:%M:%S")
                        st.session_state.fim = (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000
                        supabase.table('escalas').update({'status': 'Em Pausa', 'inicio': st.session_state.saida}).eq('id', st.session_state.p_id).execute()
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** INICIOU a pausa.")
                        st.rerun()

                elif pausa_data['status'] == 'Em Pausa':
                    st.warning(f"⏳ Pausa ativa! Retorno previsto em {st.session_state.t_pausa} minutos.")
                    st.markdown(f'<div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px; font-family: sans-serif;">--:--</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                        <script>
                            var endTime = {st.session_state.get('fim', 0)};
                            var audioContext = new (window.AudioContext || window.webkitAudioContext)();
                            var beepCount = 0;
                            var beepInterval;

                            function playBeep(frequency, duration, volume, delay) {{
                                setTimeout(() => {{
                                    var oscillator = audioContext.createOscillator();
                                    var gainNode = audioContext.createGain();

                                    oscillator.connect(gainNode);
                                    gainNode.connect(audioContext.destination);

                                    oscillator.type = 'sine';
                                    oscillator.frequency.value = frequency;
                                    gainNode.gain.value = volume;

                                    oscillator.start(audioContext.currentTime);
                                    oscillator.stop(audioContext.currentTime + duration);
                                }}, delay);
                            }}

                            function startBeeping() {{
                                beepCount = 0;
                                beepInterval = setInterval(() => {{
                                    if (beepCount < 3) {{
                                        playBeep(880, 0.3, 0.8, 0);
                                        beepCount++;
                                    }} else {{
                                        clearInterval(beepInterval);
                                    }}
                                }}, 500);
                            }}

                            var x = setInterval(function() {{
                                var now = new Date().getTime();
                                var diff = endTime - now;

                                if (diff <= 0) {{
                                    clearInterval(x);
                                    document.getElementById('timer').innerHTML = "00:00";
                                    document.getElementById('timer').style.backgroundColor = "#ff4b4b";
                                    document.getElementById('timer').style.color = "white";
                                    startBeeping();
                                    alert("🚨 ATENÇÃO! Sua pausa finalizou!\\n\\nPRIMEIRO, bata o ponto principal no VR e SÓ DEPOIS finalize aqui no site de gestão de pausas.");
                                }} else {{
                                    var m = Math.floor(diff / 60000);
                                    var s = Math.floor((diff % 60000) / 1000);
                                    document.getElementById('timer').innerHTML = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
                                }}
                            }}, 1000);
                        </script>""", height=220)

                    if st.button("✅ FINALIZAR E VOLTAR", use_container_width=True, type="primary"):
                        saida_pausa = st.session_state.get('saida', 'N/A') 
                        supabase.table('historico').insert({
                            'email': st.session_state.user_atual,
                            'nome': u_info['nome'],
                            'data': get_now().date().isoformat(),
                            'h_saida': saida_pausa,
                            'h_retorno': get_now().strftime("%H:%M:%S"),
                            'duracao': st.session_state.t_pausa
                        }).execute()
                        supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** FINALIZOU a pausa.")
                        st.session_state.pausa_ativa = False
                        st.rerun()
            else:
                st.info("⏳ Aguardando liberação da gestão ou agendamento de pausa...")

else: st.error("Erro de conexão.")
