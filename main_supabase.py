import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, date
import pandas as pd
import pytz, requests, io, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES ---
GMAIL_USER, GMAIL_PW = "gestao.queropassagem@gmail.com", "pakiujauoxbmihyy"
DISCORD_GESTAO = "https://discord.com/api/webhooks/1452088104616722475/mIVeSKVD0mtLErmlTt5QqnQvYpDBEw7TpH7CdZB0A0H1Ms5iFWZqZdGmcRY78EpsJ_pI"
DISCORD_EQUIPE = "https://discord.com/api/webhooks/1452314030357348353/-ty01Mp6tabaM4U9eICtKHJiitsNUoEa9CFs04ivKmvg2FjEBRQ8CSjPJtSD91ZkrvUi"
URL, KEY = "https://gzozqxrlgdzjrqfvdxzw.supabase.co", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6b3pxeHJsZ2R6anJxZnZkeHp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0OTg1MjIsImV4cCI6MjA4MjA3NDUyMn0.dLEjBPESUz5KnVwxqEMaMxoy65gsLqG2QdjK2xFTUhU"
COD_MESTRE = "QP2025" # Defina sua senha de supervisor aqui
TZ = pytz.timezone('America/Sao_Paulo')

def get_now(): return datetime.now(TZ)
def disc(url, m): requests.post(url, json={"content": m})

def mail(nome, dest, senha):
    try:
        msg = MIMEMultipart(); msg['Subject'] = "Acesso Gestão de Pausas - QP"
        msg.attach(MIMEText(f"Olá {nome},\nLogin: {dest}\nSenha: {senha}\nLink: https://gestao-pausas-supabase-rytpzdbzurqiuf53rgnusb.streamlit.app/", 'plain'))
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(GMAIL_USER, GMAIL_PW)
        s.send_message(msg); s.quit(); return True
    except: return False

st.set_page_config(page_title="Gestão de Pausas - QP")
st.markdown("<style>.logo-qp{font-size:35pt;color:#004a99;text-align:center;font-weight:bold;}</style>", unsafe_allow_html=True)

@st.cache_resource
def conn(): return create_client(URL, KEY)
supabase = conn()

if supabase:
    st.markdown('<div class="logo-qp">Quero Passagem</div>', unsafe_allow_html=True)
    if 'logado' not in st.session_state: st.session_state.logado = False

    if not st.session_state.logado:
        u, p = st.text_input("E-mail").lower(), st.text_input("Senha", type="password")
        if st.button("ACESSAR"):
            res = supabase.table('usuarios').select('*').execute()
            db = {x['email'].lower(): x for x in res.data}
            if u in db and db[u]['senha'] == p:
                st.session_state.update({"logado":True, "user":u, "u_info":db[u], "db":db, "trocar":db[u].get('primeiro_acesso',True)})
                st.rerun()
            else: st.error("Erro no login")
    
    elif st.session_state.get('trocar'):
        nova = st.text_input("Nova Senha", type="password")
        if st.button("ALTERAR") and len(nova)>=6:
            supabase.table('usuarios').update({'senha':nova,'primeiro_acesso':False}).eq('email',st.session_state.user).execute()
            st.session_state.trocar = False; st.rerun()

    else:
        info = st.session_state.u_info
        st.sidebar.write(f"👤 {info['nome']}")
        if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

        if any(x in info['tipo'].lower() for x in ['admin','supervisor','gestão']):
            menu = st.tabs(["Liberar", "Histórico", "Relatórios", "Equipe", "Correções"])
            
            with menu[0]: # Liberar
                at = [e for e,i in st.session_state.db.items() if 'atendente' in i['tipo'].lower()]
                alvo = st.selectbox("Atendente:", at)
                t = st.number_input("Minutos:", 1, 120, 15)
                if st.button("AUTORIZAR"):
                    supabase.table('escalas').insert({'email':alvo,'nome':st.session_state.db[alvo]['nome'],'duracao':t,'status':'Pendente'}).execute()
                    disc(DISCORD_EQUIPE, f"🔔 {st.session_state.db[alvo]['nome']}, pausa liberada!")
                    st.success("Liberado!")

            with menu[1]: # Histórico
                h = supabase.table('historico').select('*').order('created_at',desc=True).limit(20).execute()
                st.table(pd.DataFrame(h.data)[['nome','data','h_saida','h_retorno']] if h.data else [])

            with menu[2]: # Relatórios
                d1, d2 = st.date_input("Início", date.today()-timedelta(7)), st.date_input("Fim", date.today())
                if st.button("GERAR"):
                    r = supabase.table('historico').select('*').gte('data',d1.isoformat()).lte('data',d2.isoformat()).execute()
                    st.write(pd.DataFrame(r.data) if r.data else "Sem dados")

            with menu[3]: # Equipe
                with st.form("cad"):
                    n, e, s, tp = st.text_input("Nome"), st.text_input("Email"), st.text_input("Senha"), st.selectbox("Perfil",["atendente sac","supervisor"])
                    if st.form_submit_button("SALVAR"):
                        supabase.table('usuarios').insert({'nome':n,'email':e,'senha':s,'tipo':tp,'primeiro_acesso':True}).execute()
                        mail(n,e,s); st.success("Criado!"); st.cache_resource.clear(); st.rerun()

            with menu[4]: # Correções (NOVO)
                st.subheader("⚠️ Destravar Pausa")
                esc = supabase.table('escalas').select('*').execute()
                if esc.data:
                    trav = st.selectbox("Funcionário:", [f"{x['nome']} ({x['status']})" for x in esc.data])
                    id_c = esc.data[[f"{x['nome']} ({x['status']})" for x in esc.data].index(trav)]['id']
                    cod = st.text_input("Código Mestre", type="password")
                    if st.button("DESTRAVAR") and cod == COD_MESTRE:
                        supabase.table('escalas').delete().eq('id', id_c).execute()
                        disc(DISCORD_GESTAO, f"⚠️ {info['nome']} destravou {trav}")
                        st.success("Resetado!"); st.rerun()
                else: st.write("Ninguém travado.")

        else: # Atendente
            st.subheader("⏱️ Minha Pausa")
            if not st.session_state.get('ativa'):
                if st.button("🔄 VERIFICAR LIBERAÇÃO"):
                    res = supabase.table('escalas').select('*').eq('email',st.session_state.user).eq('status','Pendente').execute()
                    if res.data:
                        st.session_state.update({"pausa_id":res.data[0]['id'], "tempo":res.data[0]['duracao'], "liberado":True})
                        st.success("Liberado!"); st.balloons()
                if st.session_state.get('liberado') and st.button("🚀 INICIAR"):
                    supabase.table('escalas').update({'status':'Em Pausa'}).eq('id',st.session_state.pausa_id).execute()
                    st.session_state.update({"ativa":True, "fim":(get_now()+timedelta(minutes=st.session_state.tempo)).timestamp()*1000, "saida":get_now().strftime("%H:%M")})
                    disc(DISCORD_GESTAO, f"🚀 {info['nome']} Iniciou"); st.rerun()
            else:
                st.components.v1.html(f"<div id='t' style='font-size:50px;text-align:center;'>00:00</div><script>var f={st.session_state.fim};setInterval(function(){{var d=f-new Date().getTime();if(d<=0){{document.getElementById('t').innerHTML='FIM';}}else{{var m=Math.floor(d/60000),s=Math.floor((d%60000)/1000);document.getElementById('t').innerHTML=m+':'+(s<10?'0':'')+s;}}}},1000)</script>")
                if st.button("✅ FINALIZAR"):
                    supabase.table('historico').insert({'email':st.session_state.user,'nome':info['nome'],'data':date.today().isoformat(),'h_saida':st.session_state.saida,'h_retorno':get_now().strftime("%H:%M"),'duracao':st.session_state.tempo}).execute()
                    supabase.table('escalas').delete().eq('id',st.session_state.pausa_id).execute()
                    disc(DISCORD_GESTAO, f"✅ {info['nome']} Voltou"); st.session_state.ativa=False; st.rerun()
