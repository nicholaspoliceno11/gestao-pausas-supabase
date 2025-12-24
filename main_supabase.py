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
import time # Importar o módulo time para usar sleep

# --- CONFIGURAÇÕES ---
GMAIL_USER = "gestao.queropassagem@gmail.com"
GMAIL_PASSWORD = "pakiujauoxbmihyy"
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSC_PJtSD91ZkrvUi" # Verifique se este webhook é para a equipe
DISCORD_WEBHOOK_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI" # Verifique se este webhook é para a gestão
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
    except Exception as e: # Captura o erro para depuração
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
            menu = st.radio("Ações:", ["Agendar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True) # Renomeado "Liberar Pausa" para "Agendar Pausa"
            st.divider()

            if menu == "Agendar Pausa": # Nova lógica para agendamento
                st.markdown("### 🚀 Agendar Pausa para Atendente")

                # 1. Obter atendentes que ainda não tiraram pausa hoje ou não têm pausa agendada/em andamento
                hoje = get_now().date().isoformat()

                # Atendentes que já finalizaram pausa hoje
                historico_hoje_resp = supabase.table('historico').select('email').eq('data', hoje).execute()
                emails_com_pausa_finalizada_hoje = {item['email'] for item in historico_hoje_resp.data}

                # Pausas ativas ou agendadas (não finalizadas)
                escalas_ativas_resp = supabase.table('escalas').select('email').neq('status', 'Finalizada').execute()
                emails_com_pausa_ativa_ou_agendada = {item['email'] for item in escalas_ativas_resp.data}

                # Lista de todos os atendentes
                todos_atendentes = {e: i for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()}

                # Atendentes que ainda precisam tirar pausa (não finalizaram e não têm ativa/agendada)
                at_list_pendentes = [
                    e for e, i in todos_atendentes.items() 
                    if e not in emails_com_pausa_finalizada_hoje and e not in emails_com_pausa_ativa_ou_agendada
                ]

                if not at_list_pendentes:
                    st.info("🎉 Todos os atendentes já tiraram ou têm pausas agendadas/ativas para hoje!")
                else:
                    st.write("Atendentes que ainda precisam de pausa:")

                    # Usar um formulário para agendar múltiplas pausas
                    with st.form("agendar_pausas_form"):
                        agendamentos = []
                        for atendente_email in at_list_pendentes:
                            atendente_nome = usuarios_db[atendente_email]['nome']
                            st.subheader(f"Agendar para: {atendente_nome}")

                            col1, col2 = st.columns(2)
                            with col1:
                                duracao = st.number_input(f"Duração (minutos) para {atendente_nome}:", 1, 120, 15, key=f"duracao_{atendente_email}")
                            with col2:
                                # Define um horário padrão razoável, como 15 minutos a partir de agora
                                hora_sugestao = (get_now() + timedelta(minutes=15)).time()
                                horario_agendado_input = st.time_input(f"Horário de início para {atendente_nome}:", value=hora_sugestao, key=f"horario_{atendente_email}")

                            # Armazena os dados para processamento
                            agendamentos.append({
                                'email': atendente_email,
                                'nome': atendente_nome,
                                'duracao': duracao,
                                'horario_agendado': horario_agendado_input
                            })

                        submitted = st.form_submit_button("✅ AGENDAR PAUSAS SELECIONADAS", type="primary")

                        if submitted:
                            for agendamento in agendamentos:
                                # Combina a data de hoje com o horário agendado
                                data_hora_agendada = datetime.combine(get_now().date(), agendamento['horario_agendado'], tzinfo=TIMEZONE_SP)

                                # Insere a pausa com status 'Agendada' e 'notificacao_enviada' como False
                                supabase.table('escalas').insert({
                                    'email': agendamento['email'],
                                    'nome': agendamento['nome'],
                                    'duracao': agendamento['duracao'],
                                    'status': 'Agendada', # Novo status
                                    'horario_agendado': data_hora_agendada.isoformat(), # Salva como ISO formatado
                                    'notificacao_enviada': False # Novo campo
                                }).execute()
                                st.success(f"✅ Pausa agendada para {agendamento['nome']} às {agendamento['horario_agendado'].strftime('%H:%M')} por {agendamento['duracao']} minutos.")
                            st.rerun() # Recarrega para atualizar a lista de atendentes pendentes

            elif menu == "Histórico":
                st.markdown("### 📊 Histórico de Pausas")
                h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                if h_resp.data:
                    df = pd.DataFrame(h_resp.data)
                    # Converter 'data' para datetime e formatar para exibição
                    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
                    st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                    st.download_button("📥 Baixar CSV", data=gerar_csv(df), file_name="historico.csv", mime="text/csv")
                else:
                    st.info("Nenhum histórico de pausas encontrado.")

            elif menu == "Gestão de Equipe":
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
                        cod_del = st.text_input("Código Mestre p/ Deletar:", type="password", key="del_secure")
                        if st.button("🗑️ EXCLUIR DEFINITIVAMENTE", type="primary"):
                            if cod_del == CODIGO_MESTRE_GESTAO:
                                supabase.table('usuarios').delete().eq('email', email_final).execute()
                                st.success("✅ Usuário removido.")
                                st.rerun()
                            else: st.error("❌ Código incorreto.")
                    else:
                        st.info("Nenhum usuário para remover (exceto você mesmo).")

            elif menu == "Correções":
                st.markdown("### ⚠️ Destravar Funcionário")
                # Mostrar pausas com status 'Agendada' ou 'Em Pausa'
                esc_resp = supabase.table('escalas').select('*').or_('status.eq.Agendada,status.eq.Em Pausa,status.eq.Notificada').execute() # Adicionado 'Notificada'
                if esc_resp.data:
                    sel_un = st.selectbox("Pausa ativa ou agendada:", [f"{x['nome']} ({x['email']}) - Status: {x['status']}" for x in esc_resp.data])
                    email_para_destravar = sel_un.split('(')[-1].split(')')[0].strip() # Extrai o email corretamente
                    cod_un = st.text_input("Código Mestre:", type="password", key="un_cod")
                    if st.button("🔓 DESTRAVAR"):
                        if cod_un == CODIGO_MESTRE_GESTAO:
                            supabase.table('escalas').delete().eq('email', email_para_destravar).execute()
                            st.success("✅ Destravado!")
                            st.rerun()
                        else: st.error("❌ Código incorreto.")
                else:
                    st.info("Nenhuma pausa ativa ou agendada para destravar.")

        else: # --- INTERFACE DO ATENDENTE ---
            st.markdown("### ⏱️ Minha Pausa")

            # 1. Verificar se há uma pausa AGENDADA, NOTIFICADA ou EM PAUSA para o atendente
            pausa_agendada_ou_ativa_resp = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).or_('status.eq.Agendada,status.eq.Em Pausa,status.eq.Notificada').execute()
            pausa_data = pausa_agendada_ou_ativa_resp.data[0] if pausa_agendada_ou_ativa_resp.data else None

            if pausa_data:
                # Se houver uma pausa agendada ou ativa, atualiza o session_state
                st.session_state.update({
                    "t_pausa": pausa_data['duracao'],
                    "p_id": pausa_data['id'],
                    "liberado": True, # Considera liberado se já está agendada ou em pausa
                    "pausa_ativa": pausa_data['status'] == 'Em Pausa',
                    "horario_agendado": datetime.fromisoformat(pausa_data['horario_agendado']) if pausa_data['horario_agendado'] else None
                })

                # Lógica para notificação de 10 minutos antes
                if st.session_state.get('horario_agendado') and not pausa_data['notificacao_enviada'] and pausa_data['status'] == 'Agendada':
                    agora = get_now()
                    tempo_para_pausa = st.session_state.horario_agendado - agora

                    # Se faltam 10 minutos ou menos para a pausa agendada
                    if timedelta(minutes=0) <= tempo_para_pausa <= timedelta(minutes=10):
                        # Envia notificação para o Discord
                        mensagem_discord = f"🔔 **{u_info['nome']}**, sua pausa foi liberada para iniciar às {st.session_state.horario_agendado.strftime('%H:%M')}! Por favor, prepare-se para iniciar a pausa em breve."
                        enviar_discord(DISCORD_WEBHOOK_EQUIPE, mensagem_discord) # Envia para o webhook da equipe

                        # Atualiza o status no Supabase para 'Notificada' e marca como enviada
                        supabase.table('escalas').update({'status': 'Notificada', 'notificacao_enviada': True}).eq('id', st.session_state.p_id).execute()
                        st.success(f"✅ Sua pausa foi liberada para iniciar às {st.session_state.horario_agendado.strftime('%H:%M')}! Prepare-se!")
                        st.rerun() # Recarrega para refletir o novo status e evitar reenvio

                # Exibe informações da pausa agendada/ativa
                if pausa_data['status'] == 'Agendada' or pausa_data['status'] == 'Notificada':
                    st.info(f"⏳ Sua pausa está agendada para iniciar às **{st.session_state.horario_agendado.strftime('%H:%M')}** e terá duração de **{st.session_state.t_pausa} minutos**.")

                    # Calcula e exibe o tempo restante para o início da pausa
                    agora = get_now()
                    tempo_restante_inicio = st.session_state.horario_agendado - agora
                    if tempo_restante_inicio.total_seconds() > 0:
                        minutos_restantes = int(tempo_restante_inicio.total_seconds() / 60)
                        segundos_restantes = int(tempo_restante_inicio.total_seconds() % 60)
                        st.write(f"Faltam **{minutos_restantes} minutos e {segundos_restantes} segundos** para o início agendado.")
                    else:
                        st.write("O horário agendado para sua pausa já chegou ou passou. Você pode iniciar agora.")

                    # Botão para iniciar a pausa, visível quando a pausa está agendada ou notificada
                    if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True, type="primary"):
                        # Atualiza o status para 'Em Pausa'
                        supabase.table('escalas').update({'status': 'Em Pausa'}).eq('id', st.session_state.p_id).execute()
                        st.session_state.update({
                            "pausa_ativa": True,
                            "fim": (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000,
                            "saida": get_now().strftime("%H:%M:%S")
                        })
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** iniciou pausa às {get_now().strftime('%H:%M')}.")
                        st.rerun()

                elif pausa_data['status'] == 'Em Pausa':
                    # Lógica do timer existente
                    st.components.v1.html(f"""
                        <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px; font-family: sans-serif;">--:--</div>
                        <script>
                            var endTime = {st.session_state.fim};
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
                                        playBeep(880, 0.3, 0.8, 0); // Frequência, duração, volume, delay
                                        beepCount++;
                                    }} else {{
                                        clearInterval(beepInterval);
                                    }}
                                }}, 500); // Intervalo de 500ms entre os bips
                            }}

                            var x = setInterval(function() {{
                                var now = new Date().getTime();
                                var diff = endTime - now;

                                if (diff <= 0) {{
                                    clearInterval(x);
                                    document.getElementById('timer').innerHTML = "00:00";
                                    document.getElementById('timer').style.backgroundColor = "#ff4b4b";
                                    document.getElementById('timer').style.color = "white";
                                    startBeeping(); // Inicia os bips
                                    alert("🚨 ATENÇÃO! Sua pausa finalizou!\\n\\nPRIMEIRO, bata o ponto principal no VR e SÓ DEPOIS finalize aqui no site de gestão de pausas.");
                                }} else {{
                                    var m = Math.floor(diff / 60000);
                                    var s = Math.floor((diff % 60000) / 1000);
                                    document.getElementById('timer').innerHTML = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
                                }}
                            }}, 1000);
                        </script>""", height=220)

                    if st.button("✅ FINALIZAR E VOLTAR", use_container_width=True, type="primary"):
                        # Garante que 'saida' está no session_state antes de usar
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
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"✅ **{u_info['nome']}** finalizou a pausa e retornou às {get_now().strftime('%H:%M')}.")
                        st.session_state.pausa_ativa = False
                        st.rerun()
            else:
                # Se não há pausa agendada nem ativa, mostra a mensagem de aguardo
                st.info("⏳ Aguardando liberação da gestão ou agendamento de pausa...")

else: st.error("Erro de conexão.")
