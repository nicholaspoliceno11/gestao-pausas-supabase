import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, date
import pandas as pd
import pytz
import requests
import io

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

# --- FUNÇÕES DE RELATÓRIO ---
def gerar_relatorio_csv(df, nome_arquivo="relatorio"):
    """Gera CSV para download"""
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    return csv

def gerar_relatorio_excel(df, nome_arquivo="relatorio"):
    """Gera Excel para download"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
    return output.getvalue()

def formatar_dataframe_relatorio(df):
    """Formata o DataFrame para exibição"""
    if not df.empty:
        # Formata datas
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
    
    div[data-baseweb="select"] { background-color: white !important; }
    div[data-baseweb="select"] > div { background-color: white !important; color: black !important; }
    input[type="number"] { background-color: white !important; color: black !important; }
    button[kind="stepperButton"] { background-color: #f0f2f6 !important; color: #333 !important; }
    input[type="text"], input[type="email"], input[type="password"] { 
        background-color: white !important; 
        color: black !important; 
        border: 1px solid #ddd !important; 
    }
    
    button[kind="primary"], button[kind="secondary"] {
        background-color: #004a99 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        padding: 0.5rem 1rem !important;
    }
    
    button[kind="primary"]:hover, button[kind="secondary"]:hover {
        background-color: #003d7a !important;
    }
    
    label[data-baseweb="radio"] { color: black !important; }
    div[data-testid="stDataFrame"] { background-color: white !important; }
    div[data-testid="stDataFrame"] table { color: black !important; }
    
    .logo-qp { 
        font-family: 'Arial Black', sans-serif; 
        font-size: 35pt; 
        color: #004a99 !important; 
        text-align: center; 
    }
    .subtitulo-qp { 
        font-size: 16pt; 
        color: #666 !important; 
        text-align: center; 
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
@st.cache_resource
def conectar_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Testa a conexão fazendo uma query simples
        client.table('usuarios').select('id').limit(1).execute()
        return client
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o Supabase: {e}")
        return None

supabase: Client = conectar_supabase()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div><div class="subtitulo-qp">Gestão de Pausa</div>', unsafe_allow_html=True)
    st.divider()

    # Inicializar session_state
    if 'logado' not in st.session_state:
        st.session_state.logado = False
    if 'pausa_ativa' not in st.session_state:
        st.session_state.pausa_ativa = False

    if not st.session_state.logado:
        # TELA DE LOGIN
        st.markdown("### 🔐 Login")
        u_log_raw = st.text_input("E-mail", key="email_login")
        p_log = st.text_input("Senha", type="password", key="senha_login")
        
        if st.button("ACESSAR SISTEMA"):
            # Limpa e normaliza o email
            u_log = u_log_raw.strip().lower() if u_log_raw else ""
            
            if not u_log or not p_log:
                st.error("⚠️ Preencha todos os campos!")
            else:
                try:
                    # Carrega usuários apenas na hora do login
                    usuarios_response = supabase.table('usuarios').select('*').execute()
                    usuarios_db = {u['email'].strip().lower(): u for u in usuarios_response.data}
                    
                    if u_log in usuarios_db and usuarios_db[u_log]['senha'] == p_log:
                        st.session_state.logado = True
                        st.session_state.user_atual = u_log
                        st.session_state.usuarios_db = usuarios_db
                        
                        # Verifica primeiro acesso
                        if usuarios_db[u_log].get('primeiro_acesso', True):
                            st.session_state.precisa_trocar_senha = True
                        else:
                            st.session_state.precisa_trocar_senha = False
                        
                        st.rerun()
                    else:
                        st.error("❌ Login ou senha incorretos.")
                except Exception as e:
                    st.error(f"❌ Erro ao validar login: {e}")
    
    elif st.session_state.get('precisa_trocar_senha', False):
        # TELA DE TROCA DE SENHA
        st.markdown("### 🔐 Primeiro Acesso - Alterar Senha")
        st.warning("⚠️ Por segurança, você precisa criar uma nova senha.")
        st.info("💡 A senha deve ter pelo menos 6 caracteres.")
        
        nova_senha = st.text_input("Nova Senha", type="password", key="nova")
        confirma_senha = st.text_input("Confirme a Nova Senha", type="password", key="conf")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ ALTERAR SENHA"):
                if not nova_senha or not confirma_senha:
                    st.error("⚠️ Preencha todos os campos!")
                elif nova_senha != confirma_senha:
                    st.error("❌ As senhas não coincidem!")
                elif len(nova_senha) < 6:
                    st.error("❌ A senha deve ter pelo menos 6 caracteres!")
                else:
                    try:
                        # Atualiza senha e primeiro_acesso no Supabase
                        supabase.table('usuarios').update({
                            'senha': nova_senha,
                            'primeiro_acesso': False
                        }).eq('email', st.session_state.user_atual).execute()
                        
                        st.success("✅ Senha alterada com sucesso!")
                        st.session_state.precisa_trocar_senha = False
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar senha: {e}")
        
        with col2:
            if st.button("🚪 Cancelar e Sair"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    
    else:
        # SISTEMA PRINCIPAL
        usuarios_db = st.session_state.get('usuarios_db', {})
        
        # Se não tiver usuários no session_state, recarrega
        if not usuarios_db:
            try:
                usuarios_response = supabase.table('usuarios').select('*').execute()
                usuarios_db = {u['email'].lower(): u for u in usuarios_response.data}
                st.session_state.usuarios_db = usuarios_db
            except Exception as e:
                st.error(f"❌ Erro ao carregar usuários: {e}")
                st.stop()
        
        u_info = usuarios_db.get(st.session_state.user_atual, {})
        cargo = str(u_info.get('tipo', '')).lower()
        
        st.sidebar.markdown(f"## 👤 {u_info.get('nome')}")
        if st.sidebar.button("Sair"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # ADMIN/SUPERVISOR
        if any(x in cargo for x in ['admin', 'supervisor', 'gestão']):
            menu = st.radio("Ações:", ["Liberar Pausa", "Histórico", "Relatórios", "Gestão de Equipe"], 
                          horizontal=True, label_visibility="collapsed")
            st.divider()
            
            if menu == "Liberar Pausa":
                st.subheader("Autorizar Pausa")
                atendentes = [email for email, info in usuarios_db.items() 
                            if 'atendente' in info.get('tipo', '').lower()]
                
                if not atendentes:
                    st.warning("⚠️ Nenhum atendente cadastrado no sistema.")
                else:
                    alvo = st.selectbox("Atendente SAC:", atendentes)
                    tempo_alvo = st.number_input("Duração (minutos):", 1, 120, 15)
                    
                    if st.button("AUTORIZAR PAUSA"):
                        try:
                            supabase.table('escalas').insert({
                                'email': alvo,
                                'nome': usuarios_db[alvo]['nome'],
                                'duracao': tempo_alvo,
                                'status': 'Pendente',
                                'inicio': get_now().isoformat()
                            }).execute()
                            
                            enviar_discord(DISCORD_WEBHOOK_EQUIPE, 
                                         f"🔔 **{usuarios_db[alvo]['nome']}**, sua pausa foi liberada!")
                            st.success("✅ Pausa liberada com sucesso!")
                        except Exception as e:
                            st.error(f"❌ Erro ao autorizar pausa: {e}")

            elif menu == "Histórico":
                st.subheader("📊 Histórico de Pausas")
                try:
                    hist_response = supabase.table('historico').select('*').order('created_at', desc=True).limit(50).execute()
                    df = pd.DataFrame(hist_response.data)
                    if not df.empty:
                        df = formatar_dataframe_relatorio(df)
                        st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], 
                                   use_container_width=True)
                    else:
                        st.info("Nenhum histórico encontrado.")
                except Exception as e:
                    st.error(f"❌ Erro ao carregar histórico: {e}")

            elif menu == "Relatórios":
                st.subheader("📈 Relatórios e Exportação")
                
                # Filtros de período
                col1, col2 = st.columns(2)
                with col1:
                    data_inicio = st.date_input("Data Início:", value=date.today() - timedelta(days=30))
                with col2:
                    data_fim = st.date_input("Data Fim:", value=date.today())
                
                # Tipo de relatório
                tipo_relatorio = st.selectbox("Tipo de Relatório:", 
                    ["Histórico de Pausas", "Pausas por Usuário", "Estatísticas Gerais"])
                
                if st.button("🔍 GERAR RELATÓRIO"):
                    try:
                        if tipo_relatorio == "Histórico de Pausas":
                            # Busca histórico no período
                            hist_response = supabase.table('historico').select('*')\
                                .gte('data', data_inicio.isoformat())\
                                .lte('data', data_fim.isoformat())\
                                .order('data', desc=True).execute()
                            
                            df = pd.DataFrame(hist_response.data)
                            
                            if not df.empty:
                                df = formatar_dataframe_relatorio(df)
                                
                                # Métricas
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total de Pausas", len(df))
                                with col2:
                                    st.metric("Tempo Total (min)", df['duracao'].sum())
                                with col3:
                                    st.metric("Média por Pausa (min)", f"{df['duracao'].mean():.1f}")
                                
                                st.divider()
                                
                                # Tabela
                                st.dataframe(df[['nome', 'data', 'h_saida', 'h_retorno', 'duracao']], 
                                           use_container_width=True)
                                
                                # Botões de exportação
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv = gerar_relatorio_csv(df, "historico_pausas")
                                    st.download_button(
                                        label="📥 Baixar CSV",
                                        data=csv,
                                        file_name=f"historico_pausas_{data_inicio}_{data_fim}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    excel = gerar_relatorio_excel(df, "historico_pausas")
                                    st.download_button(
                                        label="📥 Baixar Excel",
                                        data=excel,
                                        file_name=f"historico_pausas_{data_inicio}_{data_fim}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                            else:
                                st.info("📭 Nenhum registro encontrado no período selecionado.")
                        
                        elif tipo_relatorio == "Pausas por Usuário":
                            # Relatório agrupado por usuário
                            hist_response = supabase.table('historico').select('*')\
                                .gte('data', data_inicio.isoformat())\
                                .lte('data', data_fim.isoformat()).execute()
                            
                            df = pd.DataFrame(hist_response.data)
                            
                            if not df.empty:
                                resumo = df.groupby('nome').agg({
                                    'duracao': ['count', 'sum', 'mean']
                                }).reset_index()
                                resumo.columns = ['Nome', 'Total de Pausas', 'Tempo Total (min)', 'Média (min)']
                                resumo['Média (min)'] = resumo['Média (min)'].round(1)
                                
                                st.dataframe(resumo, use_container_width=True)
                                
                                # Botões de exportação
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv = gerar_relatorio_csv(resumo, "pausas_por_usuario")
                                    st.download_button(
                                        label="📥 Baixar CSV",
                                        data=csv,
                                        file_name=f"pausas_por_usuario_{data_inicio}_{data_fim}.csv",
                                        mime="text/csv"
                                    )
                                with col2:
                                    excel = gerar_relatorio_excel(resumo, "pausas_por_usuario")
                                    st.download_button(
                                        label="📥 Baixar Excel",
                                        data=excel,
                                        file_name=f"pausas_por_usuario_{data_inicio}_{data_fim}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                            else:
                                st.info("📭 Nenhum registro encontrado no período selecionado.")
                        
                        elif tipo_relatorio == "Estatísticas Gerais":
                            # Dashboard com estatísticas
                            hist_response = supabase.table('historico').select('*')\
                                .gte('data', data_inicio.isoformat())\
                                .lte('data', data_fim.isoformat()).execute()
                            
                            df = pd.DataFrame(hist_response.data)
                            
                            if not df.empty:
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total de Pausas", len(df))
                                with col2:
                                    st.metric("Tempo Total", f"{df['duracao'].sum()} min")
                                with col3:
                                    st.metric("Média por Pausa", f"{df['duracao'].mean():.1f} min")
                                with col4:
                                    usuarios_unicos = df['nome'].nunique()
                                    st.metric("Usuários Ativos", usuarios_unicos)
                                
                                st.divider()
                                
                                # Top 5 usuários
                                st.markdown("### 🏆 Top 5 Usuários (Mais Pausas)")
                                top_users = df.groupby('nome')['duracao'].count().sort_values(ascending=False).head(5)
                                st.bar_chart(top_users)
                                
                            else:
                                st.info("📭 Nenhum registro encontrado no período selecionado.")
                                
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar relatório: {e}")

            elif menu == "Gestão de Equipe":
                st.subheader("👥 Gerenciamento de Usuários")
                t1, t2 = st.tabs(["➕ Adicionar", "🗑️ Excluir"])
                
                with t1:
                    with st.form("cad_user", clear_on_submit=True):
                        f_nome = st.text_input("Nome")
                        f_email = st.text_input("Email").strip().lower()
                        f_senha = st.text_input("Senha Temporária")
                        st.caption("⚠️ O usuário deverá trocar esta senha no primeiro acesso")
                        f_tipo = st.selectbox("Perfil", ["atendente sac", "supervisor", "administrador"])
                        
                        if st.form_submit_button("SALVAR"):
                            try:
                                supabase.table('usuarios').insert({
                                    'nome': f_nome,
                                    'email': f_email,
                                    'senha': f_senha,
                                    'tipo': f_tipo,
                                    'primeiro_acesso': True
                                }).execute()
                                
                                st.success(f"✅ Usuário {f_nome} criado com sucesso!")
                                st.info(f"🔑 Senha temporária: {f_senha}")
                                st.cache_resource.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao criar usuário: {e}")
                
                with t2:
                    remover = st.selectbox("Escolha para remover:", list(usuarios_db.keys()))
                    if st.button("REMOVER PERMANENTEMENTE"):
                        try:
                            user_id = usuarios_db[remover]['id']
                            supabase.table('usuarios').delete().eq('id', user_id).execute()
                            st.success("✅ Usuário removido!")
                            st.cache_resource.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao remover: {e}")

        # ATENDENTE
        else:
            st.subheader("⏱️ Minha Pausa")
            
            if not st.session_state.pausa_ativa:
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO"):
                    try:
                        pausa_response = supabase.table('escalas').select('*')\
                            .eq('email', st.session_state.user_atual)\
                            .eq('status', 'Pendente').execute()
                        
                        if pausa_response.data:
                            pausa = pausa_response.data[0]
                            st.session_state.tempo_pausa = pausa['duracao']
                            st.session_state.pausa_id = pausa['id']
                            st.session_state.pausa_liberada = True
                            st.success(f"✅ Autorizado: {pausa['duracao']} minutos!")
                            st.balloons()
                        else:
                            st.info("⏳ Aguardando autorização do supervisor...")
                    except Exception as e:
                        st.error(f"❌ Erro ao verificar liberação: {e}")
                
                if st.session_state.get('pausa_liberada'):
                    if st.button(f"🚀 INICIAR {st.session_state.tempo_pausa} MINUTOS"):
                        try:
                            # Atualiza status para "Em Pausa"
                            supabase.table('escalas').update({'status': 'Em Pausa'})\
                                .eq('id', st.session_state.pausa_id).execute()
                            
                            st.session_state.pausa_ativa = True
                            hora_final = get_now() + timedelta(minutes=st.session_state.tempo_pausa)
                            st.session_state.h_termino_ms = hora_final.timestamp() * 1000
                            st.session_state.h_saida = get_now().strftime("%H:%M:%S")
                            
                            enviar_discord(DISCORD_WEBHOOK_GESTAO, 
                                         f"🚀 **{u_info['nome']}** INICIOU a pausa.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao iniciar pausa: {e}")
            
            else:
                # CRONÔMETRO COM SOM DE ALERTA FORTE 3X
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; 
                         color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; 
                         border-radius: 15px; background-color: #fffafa;">--:--</div>
                    
                    <script>
                        var endTime = {st.session_state.h_termino_ms};
                        var timer = document.getElementById('timer');
                        var alerted = false;
                        
                        // Cria o contexto de áudio
                        var audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        
                        // Função para tocar beep forte
                        function playBeep() {{
                            var oscillator = audioContext.createOscillator();
                            var gainNode = audioContext.createGain();
                            
                            oscillator.connect(gainNode);
                            gainNode.connect(audioContext.destination);
                            
                            oscillator.frequency.value = 800; // Frequência alta (Hz)
                            oscillator.type = 'sine';
                            
                            gainNode.gain.setValueAtTime(1, audioContext.currentTime); // Volume máximo
                            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                            
                            oscillator.start(audioContext.currentTime);
                            oscillator.stop(audioContext.currentTime + 0.5);
                        }}
                        
                        // Função para tocar 3 beeps seguidos
                        function playAlertSound() {{
                            playBeep();
                            setTimeout(function() {{ playBeep(); }}, 600);
                            setTimeout(function() {{ playBeep(); }}, 1200);
                        }}
                        
                        function update() {{
                            var now = new Date().getTime();
                            var diff = endTime - now;
                            
                            if (diff <= 0) {{
                                timer.innerHTML = "00:00";
                                timer.style.backgroundColor = "#ff0000";
                                timer.style.animation = "blink 1s infinite";
                                
                                if (!alerted) {{
                                    alerted = true;
                                    playAlertSound();
                                    alert("🔴 TEMPO ESGOTADO!\\n\\nBata o ponto no VR AGORA!");
                                }}
                                
                                clearInterval(x);
                                return;
                            }}
                            
                            var m = Math.floor((diff % (1000*60*60)) / (1000*60));
                            var s = Math.floor((diff % (1000*60)) / 1000);
                            timer.innerHTML = (m<10?"0":"") + m + ":" + (s<10?"0":"") + s;
                            
                            // Alerta quando faltam 10 segundos
                            if (m === 0 && s === 10 && !alerted) {{
                                timer.style.backgroundColor = "#ffff00";
                            }}
                        }}
                        
                        var x = setInterval(update, 1000);
                        update();
                        
                        // Adiciona animação de piscar
                        var style = document.createElement('style');
                        style.innerHTML = `
                            @keyframes blink {{
                                0%, 50% {{ opacity: 1; }}
                                51%, 100% {{ opacity: 0.3; }}
                            }}
                        `;
                        document.head.appendChild(style);
                    </script>
                """, height=220)
                
                st.warning("🔴 Quando o tempo acabar, um ALARME vai tocar 3x! Bata o ponto no VR antes de finalizar!")
                
                if st.button("✅ FINALIZAR E VOLTAR"):
                    try:
                        # Registra no histórico
                        supabase.table('historico').insert({
                            'email': st.session_state.user_atual,
                            'nome': u_info['nome'],
                            'data': get_now().date().isoformat(),
                            'h_saida': st.session_state.h_saida,
                            'h_retorno': get_now().strftime("%H:%M:%S"),
                            'duracao': st.session_state.tempo_pausa
                        }).execute()
                        
                        # Remove da escala
                        supabase.table('escalas').delete()\
                            .eq('id', st.session_state.pausa_id).execute()
                        
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, 
                                     f"✅ **{u_info['nome']}** FINALIZOU a pausa.")
                        
                        st.session_state.pausa_ativa = False
                        st.session_state.pausa_liberada = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao finalizar pausa: {e}")

else:
    st.error("❌ Erro ao conectar com o banco de dados.")
    st.info("🔧 Verifique se as credenciais do Supabase estão corretas e se o serviço está disponível.")
    st.info("📝 Detalhes técnicos: Não foi possível estabelecer conexão com o Supabase.")
