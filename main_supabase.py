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
# Webhook para a equipe (alertas de agendamento do supervisor)
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSjPJtSD91ZkrvUi"
# Webhook para o SAC-QP (alertas de início e fim de pausa do atendente)
DISCORD_WEBHOOK_SAC_QP = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnVpYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI"
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
            menu = st.radio("Ações:", ["Agendar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True)
            st.divider()

            if menu == "Agendar Pausa":
                st.markdown("### 🗓️ Agendar Pausa para Atendente")

                # Obter todas as pausas ativas (agendadas ou em pausa)
                escalas_ativas_resp = supabase.table('escalas').select('email, status').execute()
                escalas_ativas_emails = {x['email'] for x in escalas_ativas_resp.data if x['status'] in ['Agendada', 'Em Pausa']}

                # Filtrar atendentes que não têm pausa agendada/ativa
                at_list_disponiveis = []
                at_list_com_pausa = []
                for email, info in usuarios_db.items():
                    if 'atendente' in info['tipo'].lower():
                        if email not in escalas_ativas_emails:
                            at_list_disponiveis.append(email)
                        else:
                            at_list_com_pausa.append(info['nome'])

                if not at_list_disponiveis:
                    st.info("✅ Todos os atendentes SAC já têm uma pausa agendada ou estão em pausa.")
                    if at_list_com_pausa:
                        st.markdown("---")
                        st.write("Atendentes com pausa agendada/ativa:")
                        for nome_atendente in at_list_com_pausa:
                            st.write(f"- {nome_atendente}")
                else:
                    st.markdown("#### Atendentes sem pausa agendada:")
                    for email_atendente in at_list_disponiveis:
                        st.write(f"- {usuarios_db[email_atendente]['nome']} falta agendar pausa")
                    st.markdown("---")

                    st.markdown("#### Programar Pausa:")
                    alvo = st.selectbox("Selecione o Atendente SAC:", at_list_disponiveis, key="select_atendente_pausa")
                    minutos = st.number_input("Duração (Minutos):", 1, 120, 15, key="duracao_pausa")

                    # Campo para o supervisor definir o horário agendado
                    horario_agendado_str = st.text_input("Horário Agendado (HH:MM):", value=get_now().strftime("%H:%M"), key="horario_agendado_input")

                    if st.button("✅ AGENDAR PAUSA", type="primary"):
                        try:
                            # Validar formato do horário
                            datetime.strptime(horario_agendado_str, "%H:%M").time()

                            # Inserir na tabela de escalas com status 'Agendada' e o horário definido
                            supabase.table('escalas').insert({
                                'email': alvo,
                                'nome': usuarios_db[alvo]['nome'], # Usando 'nome'
                                'duracao': minutos,
                                'status': 'Agendada', # Novo status
                                'horario_agendado': horario_agendado_str, # Salva como string HH:MM
                                'supervisor_em': st.session_state.user_atual, # Usando 'supervisor_em'
                                'supervisor_noi': u_info['nome'] # Usando 'supervisor_noi'
                            }).execute()

                            # Alerta de agendamento de pausa para o Discord (formato específico)
                            mensagem_agendamento = f"Supervisor {u_info['nome']} programou a pausa do Atendente {usuarios_db[alvo]['nome']} para as {horario_agendado_str}."
                            enviar_discord(DISCORD_WEBHOOK_EQUIPE, mensagem_agendamento) # Enviando para o webhook EQUIPE

                            st.success(f"✅ Pausa agendada para {usuarios_db[alvo]['nome']} às {horario_agendado_str} com duração de {minutos} minutos!")
                            st.rerun() # Recarrega para atualizar a lista de atendentes disponíveis
                        except ValueError:
                            st.error("❌ Formato de horário inválido. Use HH:MM (ex: 09:30).")
                        except Exception as ex:
                            st.error(f"❌ Erro ao agendar pausa: {ex}")

            elif menu == "Histórico":
                st.markdown("### 📊 Histórico de Pausas")
                h_resp = supabase.table('historico').select('*').order('created_at', desc=True).execute()
                if h_resp.data:
                    df = pd.DataFrame(h_resp.data)
                    st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], use_container_width=True)
                    st.download_button("📥 Baixar CSV", data=gerar_csv(df), file_name="historico.csv", mime="text/csv")
                else:
                    st.info("Nenhum histórico de pausas encontrado.")

            elif menu == "Gestão de Equipe":
                st.markdown("### 👥 Gestão de Usuários")
                tab_add, tab_del = st.tabs(["➕ Adicionar Usuário", "🗑️ Remover Usuário"])
                with tab_add:
                    with st.form("add_user"):
                        n_f = st.text_input("Nome Completo*"); e_f = st.text_input("E-mail (será o login)*").lower().strip(); s_f = st.text_input("Senha Temporária (mínimo 6 caracteres)*", type="password")
                        t_f = st.selectbox("Perfil de Acesso*", ["atendente sac", "supervisor", "administrador"])

                        if st.form_submit_button("💾 SALVAR USUÁRIO"):
                            if n_f and e_f and s_f and len(s_f) >= 6:
                                if e_f in usuarios_db:
                                    st.error("❌ E-mail já cadastrado. Por favor, use outro e-mail.")
                                else:
                                    try:
                                        supabase.table('usuarios').insert({'nome': n_f, 'email': e_f, 'senha': s_f, 'tipo': t_f, 'primeiro_acesso': True}).execute()
                                        st.success(f"✅ Usuário '{n_f}' cadastrado com sucesso como '{t_f}'. Ele precisará trocar a senha no primeiro acesso.")
                                        st.rerun() # Recarrega para atualizar a lista de usuários
                                    except Exception as ex:
                                        st.error(f"❌ Erro ao cadastrar usuário: {ex}")
                            else:
                                st.error("❌ Por favor, preencha todos os campos e certifique-se de que a senha tenha pelo menos 6 caracteres.")
                with tab_del:
                    lista_del = [f"{u['nome']} ({u['email']})" for u in usuarios_resp.data if u['email'] != st.session_state.user_atual] # Usando 'nome'
                    if lista_del:
                        sel_del = st.selectbox("Selecione o usuário para remover:", lista_del)
                        email_final = sel_del.split('(')[-1].replace(')', '')
                        cod_del = st.text_input("Código Mestre para Deletar:", type="password", key="del_secure")
                        if st.button("🗑️ EXCLUIR DEFINITIVAMENTE", type="primary"):
                            if cod_del == CODIGO_MESTRE_GESTAO:
                                try:
                                    supabase.table('usuarios').delete().eq('email', email_final).execute()
                                    st.success(f"✅ Usuário '{sel_del.split('(')[0].strip()}' removido com sucesso.")
                                    st.rerun() # Recarrega para atualizar a lista de usuários
                                except Exception as ex:
                                    st.error(f"❌ Erro ao remover usuário: {ex}")
                            else: st.error("❌ Código mestre incorreto.")
                    else:
                        st.info("Não há outros usuários para remover ou você é o único usuário.")

            elif menu == "Correções":
                st.markdown("### ⚠️ Destravar Funcionário")
                # Busca todas as pausas ativas, independentemente do status
                esc_resp = supabase.table('escalas').select('*').execute()
                if esc_resp.data:
                    sel_un = st.selectbox("Pausa ativa:", [f"{x['nome']} ({x['email']}) - Status: {x['status']}" for x in esc_resp.data]) # Usando 'nome'
                    cod_un = st.text_input("Código Mestre:", type="password", key="un_cod")
                    if st.button("🔓 DESTRAVAR"):
                        if cod_un == CODIGO_MESTRE_GESTAO:
                            try:
                                # Deleta a pausa da tabela 'escalas'
                                supabase.table('escalas').delete().eq('email', sel_un.split('(')[-1].split(')')[0]).execute()
                                st.success(f"✅ Atendente '{sel_un.split('(')[0].strip()}' destravado com sucesso.")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"❌ Erro ao destravar atendente: {ex}")
                        else: st.error("❌ Código mestre incorreto.")
                else:
                    st.info("Nenhuma pausa ativa para destravar.")

        else: # --- INTERFACE DO ATENDENTE ---
            st.markdown("### ⏱️ Minha Pausa")

            if 'pausa_ativa' not in st.session_state:
                st.session_state.pausa_ativa = False
            if 'pausa_agendada_info' not in st.session_state: # Renomeado para evitar conflito e ser mais descritivo
                st.session_state.pausa_agendada_info = None

            # Verifica se já existe uma pausa "Em Pausa" para o usuário
            res_em_pausa = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Em Pausa').execute()
            if res_em_pausa.data and not st.session_state.pausa_ativa:
                # Se encontrou uma pausa "Em Pausa" que não foi finalizada, restaura o estado
                st.session_state.update({
                    "t_pausa": res_em_pausa.data[0]['duracao'],
                    "p_id": res_em_pausa.data[0]['id'],
                    "pausa_ativa": True,
                    "saida": res_em_pausa.data[0].get('h_saida', get_now().strftime("%H:%M:%S")), # Tenta pegar a hora de saída se existir
                    "fim": (get_now() + timedelta(minutes=res_em_pausa.data[0]['duracao'])).timestamp() * 1000
                })
                st.warning("⚠️ Sua pausa estava ativa e foi restaurada. Por favor, finalize-a se já retornou.")
                st.rerun() # Recarrega para exibir o timer

            # Se não há pausa ativa, verifica se há uma pausa agendada
            if not st.session_state.pausa_ativa:
                res_agendada = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Agendada').execute()
                if res_agendada.data:
                    pausa_agendada_info = res_agendada.data[0]
                    st.session_state.pausa_agendada_info = pausa_agendada_info # Armazena a info completa da pausa agendada

                    st.info(f"✅ Pausa autorizada: {pausa_agendada_info['duracao']} minutos. Agendada para as {pausa_agendada_info['horario_agendado']}.")

                    # O botão "VERIFICAR MINHA LIBERAÇÃO" agora apenas confirma a informação
                    if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO", use_container_width=True, type="primary"):
                        st.session_state.update({
                            "t_pausa": pausa_agendada_info['duracao'],
                            "p_id": pausa_agendada_info['id'],
                            "liberado": True # Marca como liberado para poder iniciar
                        })
                        st.success(f"✅ Pausa autorizada: {st.session_state.t_pausa} minutos, agendada para as {pausa_agendada_info['horario_agendado']}!")
                        # Não precisa de rerun aqui, pois a informação já foi exibida e o botão de iniciar aparecerá.

                else: # Nenhuma pausa agendada ou em pausa
                    st.info("⏳ Nenhuma pausa agendada para você no momento. Aguardando liberação da gestão...")
                    # Botão para verificar liberação (se não houver agendamento, apenas informa)
                    if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO", use_container_width=True, type="primary"):
                        st.info("⏳ Nenhuma pausa agendada para você no momento. Aguardando liberação da gestão...")


                # Botão para iniciar pausa, visível apenas se houver uma pausa agendada
                if st.session_state.get('liberado') and st.session_state.pausa_agendada_info:
                    agora_hora = get_now().time()
                    horario_agendado_obj = datetime.strptime(st.session_state.pausa_agendada_info['horario_agendado'], "%H:%M").time()

                    # Alerta se estiver iniciando antes do horário agendado
                    if agora_hora < horario_agendado_obj:
                        st.warning(f"⚠️ Você está iniciando a pausa **antes** do horário agendado ({st.session_state.pausa_agendada_info['horario_agendado']}).")

                    if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True):
                        hora_saida = get_now().strftime("%H:%M:%S")
                        # Atualiza o status e registra a hora de saída na tabela 'escalas'
                        supabase.table('escalas').update({'status': 'Em Pausa', 'h_saida': hora_saida}).eq('id', st.session_state.p_id).execute()
                        st.session_state.update({
                            "pausa_ativa": True,
                            "fim": (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000,
                            "saida": hora_saida
                        })

                        # Alerta de início de pausa para o Discord (formato específico)
                        mensagem_inicio = f"Atendente {u_info['nome']} iniciou a pausa."
                        enviar_discord(DISCORD_WEBHOOK_SAC_QP, mensagem_inicio) # Enviando para o webhook sac-qp
                        st.rerun()
            else: # Pausa está ativa (timer rodando)
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
                    hora_retorno = get_now().strftime("%H:%M:%S")
                    supabase.table('historico').insert({
                        'email': st.session_state.user_atual,
                        'nome': u_info['nome'],
                        'data': get_now().date().isoformat(),
                        'h_saida': st.session_state.saida,
                        'h_retorno': hora_retorno,
                        'duracao': st.session_state.t_pausa
                    }).execute()
                    supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()

                    # Alerta de finalização de pausa para o Discord (formato específico)
                    mensagem_fim = f"Atendente {u_info['nome']} finalizou a pausa."
                    enviar_discord(DISCORD_WEBHOOK_SAC_QP, mensagem_fim) # Enviando para o webhook sac-qp

                    st.session_state.pausa_ativa = False
                    st.session_state.liberado = False # Reseta o estado de liberação
                    st.session_state.pausa_agendada_info = None # Reseta a pausa agendada
                    st.rerun()

else: st.error("Erro de conexão com o Supabase. Por favor, verifique as configurações ou sua conexão com a internet.")

