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
DISCORD_WEBHOOK_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSnPJtSD91ZkrvUi" # Webhook para alertas gerais da equipe
DISCORD_WEBHOOK_SAC_QP = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnVpYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI" # Webhook para alertas de início/fim de pausa (gestão)
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
            menu = st.radio("Ações:", ["Agendar Pausa", "Histórico", "Gestão de Equipe", "Correções"], horizontal=True) # Renomeado "Liberar Pausa" para "Agendar Pausa"
            st.divider()

            if menu == "Agendar Pausa":
                st.markdown("### 🗓️ Agendar Pausa para Atendente")

                # 1. Identificar atendentes sem pausa agendada/ativa para o dia
                atendentes_sac = {e: i for e, i in usuarios_db.items() if 'atendente' in i['tipo'].lower()}

                # Buscar pausas ativas ou pendentes para o dia atual
                hoje_iso = get_now().date().isoformat()
                escalas_hoje_resp = supabase.table('escalas').select('email').execute()
                escalas_hoje_emails = {item['email'] for item in escalas_hoje_resp.data}

                atendentes_sem_pausa = []
                for email, info in atendentes_sac.items():
                    if email not in escalas_hoje_emails:
                        atendentes_sem_pausa.append(f"{info['nome']} ({email})")

                if not atendentes_sac:
                    st.warning("⚠️ Não há atendentes SAC cadastrados.")
                elif not atendentes_sem_pausa:
                    st.info("🎉 Todos os atendentes SAC já têm uma pausa agendada ou estão em pausa para hoje.")
                else:
                    st.markdown("#### Atendentes sem pausa agendada para hoje:")
                    for atendente_str in atendentes_sem_pausa:
                        st.write(f"- {atendente_str.split('(')[0].strip()} falta agendar pausa")

                    st.markdown("---")
                    st.markdown("#### Programar Pausa:")

                    alvo_str = st.selectbox("Selecione o Atendente SAC para agendar:", atendentes_sem_pausa)
                    alvo_email = alvo_str.split('(')[-1].replace(')', '')

                    minutos = st.number_input("Duração da Pausa (Minutos):", 1, 120, 15)

                    # Campo para o supervisor definir o horário agendado
                    horario_agendado_input = st.text_input("Horário Agendado (HH:MM):", value=get_now().strftime("%H:%M"))

                    if st.button("✅ AGENDAR PAUSA", type="primary"):
                        try:
                            # Validação simples do formato HH:MM
                            datetime.strptime(horario_agendado_input, "%H:%M")

                            # Inserir na tabela de escalas com status 'Pendente' e o horário agendado
                            supabase.table('escalas').insert({
                                'email': alvo_email,
                                'nome': usuarios_db[alvo_email]['nome'],
                                'duracao': minutos,
                                'status': 'Pendente',
                                'horario_agendado': horario_agendado_input # Salva o horário agendado
                            }).execute()

                            # Notificação para o Discord (DISCORD_WEBHOOK_EQUIPE)
                            mensagem_agendamento = (
                                f"Supervisor {u_info['nome']} programou a pausa do Atendente "
                                f"{usuarios_db[alvo_email]['nome']} para as {horario_agendado_input} "
                                f"com duração de {minutos} minutos."
                            )
                            enviar_discord(DISCORD_WEBHOOK_EQUIPE, mensagem_agendamento)

                            st.success(f"✅ Pausa agendada para {usuarios_db[alvo_email]['nome']} às {horario_agendado_input}!")
                            st.rerun()
                        except ValueError:
                            st.error("❌ Formato de horário inválido. Use HH:MM (ex: 14:30).")
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
                        n_f = st.text_input("Nome Completo*")
                        e_f = st.text_input("E-mail (será o login)*").lower().strip()
                        s_f = st.text_input("Senha Temporária (mínimo 6 caracteres)*", type="password")
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
                    lista_del = [f"{u['nome']} ({u['email']})" for u in usuarios_resp.data if u['email'] != st.session_state.user_atual]
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
                esc_resp = supabase.table('escalas').select('*').execute()
                if esc_resp.data:
                    sel_un = st.selectbox("Pausa ativa:", [f"{x['nome']} ({x['email']})" for x in esc_resp.data])
                    cod_un = st.text_input("Código Mestre:", type="password", key="un_cod")
                    if st.button("🔓 DESTRAVAR"):
                        if cod_un == CODIGO_MESTRE_GESTAO:
                            try:
                                supabase.table('escalas').delete().eq('email', sel_un.split('(')[-1].replace(')','')).execute()
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

            # Verifica se já existe uma pausa "Em Pausa" para o usuário (restauração de estado)
            if not st.session_state.pausa_ativa:
                res_em_pausa = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Em Pausa').execute()
                if res_em_pausa.data:
                    st.session_state.update({
                        "t_pausa": res_em_pausa.data[0]['duracao'],
                        "p_id": res_em_pausa.data[0]['id'],
                        "pausa_ativa": True,
                        "saida": res_em_pausa.data[0].get('h_saida', get_now().strftime("%H:%M:%S")),
                        "fim": (get_now() + timedelta(minutes=res_em_pausa.data[0]['duracao'])).timestamp() * 1000
                    })
                    st.warning("⚠️ Sua pausa estava ativa e foi restaurada. Por favor, finalize-a se já retornou.")
                    st.rerun()

            if not st.session_state.pausa_ativa:
                st.markdown("#### Verifique sua pausa agendada:")
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO", use_container_width=True, type="primary"):
                    # Busca pausas pendentes com horário agendado
                    res = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()

                    if res.data:
                        pausa_agendada = res.data[0]
                        horario_agendado_str = pausa_agendada.get('horario_agendado')

                        if horario_agendado_str:
                            # Converte o horário agendado para um objeto datetime para comparação
                            hoje = get_now().date()
                            horario_agendado_dt = datetime.strptime(f"{hoje} {horario_agendado_str}", "%Y-%m-%d %H:%M").replace(tzinfo=TIMEZONE_SP)

                            if get_now() >= horario_agendado_dt:
                                st.session_state.update({
                                    "t_pausa": pausa_agendada['duracao'],
                                    "p_id": pausa_agendada['id'],
                                    "liberado": True,
                                    "horario_agendado": horario_agendado_str # Armazena o horário agendado na sessão
                                })
                                st.success(f"✅ Pausa autorizada: {st.session_state.t_pausa} minutos! Horário agendado: {horario_agendado_str}.")
                            else:
                                st.info(f"⏳ Sua pausa está agendada para as {horario_agendado_str}. Aguarde o horário para iniciar.")
                        else:
                            st.warning("⚠️ Sua pausa foi liberada, mas sem horário agendado. Por favor, contate seu supervisor.")
                            st.session_state.update({
                                "t_pausa": pausa_agendada['duracao'],
                                "p_id": pausa_agendada['id'],
                                "liberado": True,
                                "horario_agendado": None # Indica que não há horário agendado
                            })
                    else: 
                        st.info("⏳ Nenhuma pausa agendada ou liberada para você no momento.")

                if st.session_state.get('liberado') and not st.session_state.pausa_ativa:
                    # Só mostra o botão de iniciar se estiver liberado E o horário agendado já passou (ou não há horário agendado)
                    pode_iniciar = False
                    if st.session_state.get('horario_agendado'):
                        hoje = get_now().date()
                        horario_agendado_dt = datetime.strptime(f"{hoje} {st.session_state.horario_agendado}", "%Y-%m-%d %H:%M").replace(tzinfo=TIMEZONE_SP)
                        if get_now() >= horario_agendado_dt:
                            pode_iniciar = True
                    else: # Se não há horário agendado, pode iniciar imediatamente após a liberação
                        pode_iniciar = True

                    if pode_iniciar:
                        if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True):
                            hora_saida = get_now().strftime("%H:%M:%S")
                            supabase.table('escalas').update({'status': 'Em Pausa', 'h_saida': hora_saida}).eq('id', st.session_state.p_id).execute()
                            st.session_state.update({
                                "pausa_ativa": True,
                                "fim": (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000,
                                "saida": hora_saida
                            })

                            # Alerta de início de pausa para o Discord (DISCORD_WEBHOOK_SAC_QP)
                            mensagem_inicio = f"Atendente {u_info['nome']} iniciou a pausa."
                            enviar_discord(DISCORD_WEBHOOK_SAC_QP, mensagem_inicio)
                            st.rerun()
                    else:
                        st.info(f"Aguardando o horário agendado ({st.session_state.get('horario_agendado')}) para iniciar a pausa.")
            else:
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

                    # Alerta de finalização de pausa para o Discord (DISCORD_WEBHOOK_SAC_QP)
                    mensagem_fim = f"Atendente {u_info['nome']} finalizou a pausa."
                    enviar_discord(DISCORD_WEBHOOK_SAC_QP, mensagem_fim)

                    st.session_state.pausa_ativa = False
                    st.session_state.liberado = False
                    st.session_state.pop('horario_agendado', None) # Limpa o horário agendado da sessão
                    st.rerun()

else: st.error("Erro de conexão com o Supabase. Por favor, verifique as configurações ou sua conexão com a internet.")

