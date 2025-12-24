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
# ATENÇÃO: Verifique se esses links estão corretos no seu Discord!
# Webhook para notificações da equipe (SAC-QP)
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSC_PJtSD91ZkrvUi"
# Webhook para notificações da gestão (gestão-de-pausa-supervisao-qp)
DISCORD_WEBHOOK_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI"

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
        st.markdown("### ⚠️ Primeiro Acesso: Troque sua Senha")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password")
        if st.button("TROCAR SENHA", type="primary"):
            if nova_senha and nova_senha == confirma_senha:
                try:
                    supabase.table('usuarios').update({'senha': nova_senha, 'primeiro_acesso': False}).eq('email', st.session_state.user_atual).execute()
                    st.success("✅ Senha alterada com sucesso! Faça login novamente.")
                    st.session_state.logado = False
                    st.session_state.precisa_trocar = False
                    st.rerun()
                except Exception as e: st.error(f"❌ Erro ao trocar senha: {e}")
            else: st.error("❌ As senhas não coincidem ou estão vazias.")
    else:
        u_info = usuarios_db.get(st.session_state.user_atual)
        if not u_info:
            st.error("❌ Informações do usuário não encontradas. Faça login novamente.")
            st.session_state.logado = False
            st.rerun()

        st.sidebar.markdown(f"**Usuário:** {u_info['nome']}")
        st.sidebar.markdown(f"**Tipo:** {u_info['tipo']}")
        if st.sidebar.button("SAIR", type="secondary"):
            st.session_state.logado = False
            st.session_state.user_atual = None
            st.session_state.pausa_ativa = False # Garante que o estado de pausa seja resetado
            st.rerun()

        if u_info['tipo'] == 'Supervisor':
            st.markdown(f"### Olá, {u_info['nome']}! 👋")
            menu = st.radio("Ações:", ["Agendar Pausa", "Histórico de Pausas", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Agendar Pausa":
                st.markdown("#### 🗓️ Agendar Pausa para Atendente")

                # Buscar todos os atendentes
                todos_atendentes_resp = supabase.table('usuarios').select('email, nome').eq('tipo', 'Atendente').execute()
                todos_atendentes = {u['email']: u['nome'] for u in todos_atendentes_resp.data}

                # Buscar pausas agendadas/ativas/finalizadas para hoje
                hoje_iso = get_now().date().isoformat()
                escalas_hoje_resp = supabase.table('escalas').select('email, status').eq('data', hoje_iso).execute()
                escalas_hoje = escalas_hoje_resp.data

                emails_com_pausa_finalizada_hoje = {e['email'] for e in escalas_hoje if e['status'] == 'Finalizada'}
                emails_com_pausa_ativa_ou_agendada = {e['email'] for e in escalas_hoje if e['status'] in ['Agendada', 'Notificada', 'Em Pausa']}

                # Atendentes que ainda precisam tirar pausa (não finalizaram e não têm ativa/agendada)
                at_list_pendentes = [
                    email for email, nome in todos_atendentes.items() 
                    if email not in emails_com_pausa_finalizada_hoje and email not in emails_com_pausa_ativa_ou_agendada
                ]

                if at_list_pendentes:
                    atendentes_para_selecionar = {email: todos_atendentes[email] for email in at_list_pendentes}

                    with st.form("form_agendar_pausa"):
                        st.subheader("Dados da Pausa")
                        selected_email = st.selectbox("Selecione o Atendente", options=list(atendentes_para_selecionar.keys()), format_func=lambda x: atendentes_para_selecionar[x])

                        # Horário como texto
                        horario_agendado_str = st.text_input("Horário da Pausa (HH:MM)", value="12:00")

                        duracao_pausa = st.number_input("Duração da Pausa (minutos)", min_value=5, max_value=60, value=15)

                        submitted = st.form_submit_button("AGENDAR PAUSA", type="primary")

                        if submitted:
                            # Validação do formato HH:MM
                            try:
                                hora, minuto = map(int, horario_agendado_str.split(':'))
                                if not (0 <= hora <= 23 and 0 <= minuto <= 59):
                                    raise ValueError("Formato de hora inválido.")
                                # Criar um objeto time para combinar com a data
                                horario_obj = time(hora, minuto)
                            except ValueError:
                                st.error("❌ Formato de horário inválido. Use HH:MM (ex: 21:30).")
                                st.stop()

                            # Criar datetime com fuso horário para cálculos internos
                            data_hora_agendada_com_tz = datetime.combine(get_now().date(), horario_obj, tzinfo=TIMEZONE_SP)

                            try:
                                supabase.table('escalas').insert({
                                    'email': selected_email,
                                    'nome': atendentes_para_selecionar[selected_email],
                                    'data': get_now().date().isoformat(), # Coluna 'data' para filtro do atendente
                                    'horario_agendado': horario_agendado_str, # Salva a string digitada
                                    'horario_agendado_dt_utc': data_hora_agendada_com_tz.astimezone(pytz.utc).isoformat(), # Salva o datetime em UTC para cálculos
                                    'duracao': duracao_pausa,
                                    'status': 'Agendada',
                                    'notificacao_enviada': False,
                                    'inicio': None
                                }).execute()
                                st.success(f"✅ Pausa agendada para {atendentes_para_selecionar[selected_email]} às {horario_agendado_str} por {duracao_pausa} minutos.")

                                # --- CORREÇÃO AQUI: Notificação de agendamento para o grupo SAC-QP (EQUIPE) ---
                                enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🗓️ Supervisor **{u_info['nome']}** agendou a pausa de **{atendentes_para_selecionar[selected_email]}** para **{horario_agendado_str}**.")

                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao agendar pausa: {e}")
                else:
                    st.info("🎉 Todos os atendentes já tiraram ou têm pausas agendadas/ativas para hoje!")

            elif menu == "Histórico de Pausas":
                st.markdown("#### 📊 Histórico de Pausas")
                try:
                    historico_resp = supabase.table('historico').select('*').order('data', desc=True).order('h_saida', desc=True).execute()
                    historico_df = pd.DataFrame(historico_resp.data)
                    if not historico_df.empty:
                        historico_df['data'] = pd.to_datetime(historico_df['data']).dt.strftime('%d/%m/%Y')
                        st.dataframe(historico_df[['data', 'nome', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                        st.download_button(
                            label="Baixar Histórico (CSV)",
                            data=gerar_csv(historico_df),
                            file_name=f"historico_pausas_{get_now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else: st.info("Nenhum histórico de pausas encontrado.")
                except Exception as e: st.error(f"❌ Erro ao carregar histórico: {e}")

            elif menu == "Gestão de Equipe":
                st.markdown("#### 👥 Gestão de Equipe")
                tab1, tab2 = st.tabs(["Adicionar Usuário", "Remover Usuário"])

                with tab1:
                    st.subheader("Adicionar Novo Usuário")
                    with st.form("form_add_user"):
                        add_email = st.text_input("E-mail do Novo Usuário").strip().lower()
                        add_nome = st.text_input("Nome Completo").strip()
                        add_tipo = st.selectbox("Tipo de Usuário", ["Atendente", "Supervisor"])
                        add_senha_temp = st.text_input("Senha Temporária (primeiro acesso)", type="password")
                        add_submitted = st.form_submit_button("ADICIONAR USUÁRIO", type="primary")

                        if add_submitted:
                            if add_email and add_nome and add_tipo and add_senha_temp:
                                if add_email in usuarios_db:
                                    st.error("❌ E-mail já cadastrado.")
                                else:
                                    try:
                                        supabase.table('usuarios').insert({
                                            'email': add_email,
                                            'nome': add_nome,
                                            'tipo': add_tipo,
                                            'senha': add_senha_temp,
                                            'primeiro_acesso': True
                                        }).execute()
                                        st.success(f"✅ Usuário {add_nome} ({add_email}) adicionado com sucesso! Ele precisará trocar a senha no primeiro acesso.")
                                        st.rerun()
                                    except Exception as e: st.error(f"❌ Erro ao adicionar usuário: {e}")
                            else: st.error("❌ Preencha todos os campos.")

                with tab2:
                    st.subheader("Remover Usuário Existente")
                    with st.form("form_remove_user"):
                        remove_email = st.selectbox("Selecione o Usuário para Remover", options=list(usuarios_db.keys()), format_func=lambda x: f"{usuarios_db[x]['nome']} ({x})")
                        remove_submitted = st.form_submit_button("REMOVER USUÁRIO", type="secondary")

                        if remove_submitted:
                            if remove_email:
                                try:
                                    supabase.table('usuarios').delete().eq('email', remove_email).execute()
                                    st.success(f"✅ Usuário {remove_email} removido com sucesso.")
                                    st.rerun()
                                except Exception as e: st.error(f"❌ Erro ao remover usuário: {e}")
                            else: st.error("❌ Selecione um usuário para remover.")

            elif menu == "Correções":
                st.markdown("#### 🛠️ Ferramentas de Correção")
                st.warning("Use estas ferramentas com cautela. Elas podem alterar o estado das pausas.")

                st.subheader("Resetar Pausas Agendadas/Ativas de um Atendente")
                st.info("Isso irá remover qualquer pausa com status 'Agendada', 'Notificada' ou 'Em Pausa' para o atendente selecionado.")

                todos_atendentes_emails = [u['email'] for u in usuarios_db.values() if u['tipo'] == 'Atendente']
                atendente_reset = st.selectbox("Selecione o Atendente para Resetar Pausas", options=todos_atendentes_emails)

                if st.button(f"Resetar Pausas de {atendente_reset}", type="secondary"):
                    try:
                        # Primeiro, buscar IDs das pausas a serem resetadas
                        pausas_para_reset_resp = supabase.table('escalas').select('id').eq('email', atendente_reset).in_('status', ['Agendada', 'Notificada', 'Em Pausa']).execute()
                        pausas_ids = [p['id'] for p in pausas_para_reset_resp.data]

                        if pausas_ids:
                            # Excluir as pausas encontradas
                            supabase.table('escalas').delete().in_('id', pausas_ids).execute()
                            st.success(f"✅ Pausas agendadas/ativas de {atendente_reset} resetadas com sucesso.")
                        else:
                            st.info(f"Nenhuma pausa agendada/ativa encontrada para {atendente_reset}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao resetar pausas: {e}")

        else: # --- INTERFACE DO ATENDENTE ---
            st.markdown(f"### Olá, {u_info['nome']}! 👋")
            st.markdown("#### ⏰ Sua Pausa")

            hoje_iso = get_now().date().isoformat()
            # --- CORREÇÃO AQUI: Consulta do atendente para incluir 'data' ---
            pausa_resp = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('data', hoje_iso).in_('status', ['Agendada', 'Notificada', 'Em Pausa']).limit(1).execute()
            pausa_data = pausa_resp.data[0] if pausa_resp.data else None

            if pausa_data:
                # Carregar dados da pausa para o session_state
                st.session_state.p_id = pausa_data['id']
                st.session_state.t_pausa = pausa_data['duracao']
                st.session_state.horario_agendado_str = pausa_data['horario_agendado'] # String para exibição

                # Tentar converter horario_agendado_dt_utc para datetime com fuso horário
                try:
                    horario_agendado_dt_utc = datetime.fromisoformat(pausa_data['horario_agendado_dt_utc'])
                    # Se o datetime não tiver informações de fuso horário, assume UTC e converte para TIMEZONE_SP
                    if horario_agendado_dt_utc.tzinfo is None:
                        horario_agendado_dt_utc = pytz.utc.localize(horario_agendado_dt_utc).astimezone(TIMEZONE_SP)
                    else: # Se já tem fuso horário, apenas converte para TIMEZONE_SP
                        horario_agendado_dt_utc = horario_agendado_dt_utc.astimezone(TIMEZONE_SP)
                    st.session_state.horario_agendado_dt = horario_agendado_dt_utc # Datetime para cálculos
                except Exception as e:
                    st.error(f"❌ Erro ao carregar horário agendado para cálculos: {e}. Por favor, contate a gestão.")
                    st.stop() # Interrompe para evitar erros maiores

                if pausa_data['status'] == 'Agendada':
                    st.info(f"Sua pausa está agendada para as **{st.session_state.horario_agendado_str}** por {st.session_state.t_pausa} minutos.")

                    tempo_para_pausa = st.session_state.horario_agendado_dt - get_now()

                    if tempo_para_pausa <= timedelta(minutes=10) and not pausa_data['notificacao_enviada']:
                        enviar_discord(DISCORD_WEBHOOK_EQUIPE, f"🔔 **{u_info['nome']}**, sua pausa de {st.session_state.t_pausa} minutos está agendada para **{st.session_state.horario_agendado_str}** e começa em menos de 10 minutos!")
                        supabase.table('escalas').update({'notificacao_enviada': True, 'status': 'Notificada'}).eq('id', st.session_state.p_id).execute()
                        st.rerun()

                    if tempo_para_pausa > timedelta(0):
                        minutos_restantes = int(tempo_para_pausa.total_seconds() // 60)
                        segundos_restantes = int(tempo_para_pausa.total_seconds() % 60)
                        st.markdown(f"**Início em:** {minutos_restantes:02d}:{segundos_restantes:02d}")
                    else:
                        st.markdown("**Aguardando início...**")

                    if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True, type="primary'):
                        st.session_state.saida = get_now().strftime("%H:%M:%S")
                        # --- CORREÇÃO AQUI: Definir st.session_state.fim ANTES do rerun ---
                        st.session_state.fim = (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000
                        supabase.table('escalas').update({'status': 'Em Pausa', 'inicio': st.session_state.saida}).eq('id', st.session_state.p_id).execute()
                        # Notificação de início de pausa para o grupo de Gestão
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** INICIOU a pausa às {get_now().strftime('%H:%M')}.")
                        st.rerun()

                elif pausa_data['status'] == 'Em Pausa':
                    st.warning(f"⏳ Pausa ativa! Retorno previsto em {st.session_state.t_pausa} minutos.")
                    # --- CORREÇÃO AQUI: Recalcular 'fim' se não estiver no session_state (após um rerun, por exemplo) ---
                    if 'fim' not in st.session_state or st.session_state.fim == 0:
                        # Se a pausa já está 'Em Pausa' e 'fim' não está definido, tenta calcular a partir do 'inicio'
                        if pausa_data.get('inicio'):
                            inicio_pausa_dt = datetime.strptime(pausa_data['inicio'], "%H:%M:%S").replace(year=get_now().year, month=get_now().month, day=get_now().day, tzinfo=TIMEZONE_SP)
                            st.session_state.fim = (inicio_pausa_dt + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000
                        else:
                            # Fallback: se 'inicio' também não estiver, usa o tempo atual + duração
                            st.session_state.fim = (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000
                            st.warning("⚠️ Não foi possível recuperar o horário de início da pausa. O cronômetro pode não ser preciso.")

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
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** FINALIZOU a pausa às {get_now().strftime('%H:%M')}.")
                        st.session_state.pausa_ativa = False
                        st.rerun()
            else:
                st.info("⏳ Aguardando liberação da gestão ou agendamento de pausa...")

else: st.error("Erro de conexão.")
