else: # --- INTERFACE DO ATENDENTE (CRONÔMETRO COM ALERTA SONORO) ---
            st.markdown("### ⏱️ Minha Pausa")
            
            if 'pausa_ativa' not in st.session_state or not st.session_state.pausa_ativa:
                if st.button("🔄 VERIFICAR MINHA LIBERAÇÃO", use_container_width=True, type="primary"):
                    res = supabase.table('escalas').select('*').eq('email', st.session_state.user_atual).eq('status', 'Pendente').execute()
                    if res.data:
                        st.session_state.update({"t_pausa": res.data[0]['duracao'], "p_id": res.data[0]['id'], "liberado": True})
                        st.success(f"✅ Pausa autorizada: {st.session_state.t_pausa} minutos!")
                    else: st.info("⏳ Aguardando liberação da gestão...")
                
                if st.session_state.get('liberado'):
                    if st.button("🚀 INICIAR PAUSA AGORA", use_container_width=True):
                        supabase.table('escalas').update({'status': 'Em Pausa'}).eq('id', st.session_state.p_id).execute()
                        st.session_state.update({"pausa_ativa": True, "fim": (get_now() + timedelta(minutes=st.session_state.t_pausa)).timestamp() * 1000, "saida": get_now().strftime("%H:%M:%S")})
                        enviar_discord(DISCORD_WEBHOOK_GESTAO, f"🚀 **{u_info['nome']}** iniciou pausa.")
                        st.rerun()
            else:
                # CRONÔMETRO COM SOM E MENSAGEM PERSONALIZADA
                st.components.v1.html(f"""
                    <div id="timer" style="font-size: 80px; font-weight: bold; text-align: center; color: #ff4b4b; padding: 20px; border: 4px solid #ff4b4b; border-radius: 15px; font-family: sans-serif;">--:--</div>
                    <script>
                        var endTime = {st.session_state.fim};
                        
                        function tocarAlerta() {{
                            var context = new (window.AudioContext || window.webkitAudioContext)();
                            
                            function beep(delay) {{
                                setTimeout(() => {{
                                    var osc = context.createOscillator();
                                    var gain = context.createGain();
                                    osc.connect(gain);
                                    gain.connect(context.destination);
                                    osc.type = "sine";
                                    osc.frequency.value = 880;
                                    gain.gain.setValueAtTime(0.5, context.currentTime);
                                    gain.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.5);
                                    osc.start();
                                    osc.stop(context.currentTime + 0.5);
                                }}, delay);
                            }}
                            
                            beep(0);    // Primeiro toque
                            beep(600);  // Segundo toque
                        }}

                        var x = setInterval(function() {{
                            var now = new Date().getTime();
                            var diff = endTime - now;
                            
                            if (diff <= 0) {{
                                clearInterval(x);
                                document.getElementById('timer').innerHTML = "00:00";
                                document.getElementById('timer').style.backgroundColor = "#ff4b4b";
                                document.getElementById('timer').style.color = "white";
                                
                                tocarAlerta();
                                
                                alert("🚨 ATENÇÃO!\\n\\nSua pausa finalizou, abra seu VR e bata o ponto e depois finalize aqui no site gestão de pausas");
                            }} else {{
                                var m = Math.floor(diff / 60000);
                                var s = Math.floor((diff % 60000) / 1000);
                                document.getElementById('timer').innerHTML = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
                            }}
                        }}, 1000);
                    </script>
                """, height=220)
                
                st.warning("⚠️ **Atenção:** Não feche esta aba até finalizar a pausa.")
                
                if st.button("✅ FINALIZAR E VOLTAR", use_container_width=True, type="primary"):
                    try:
                        supabase.table('historico').insert({
                            'email': st.session_state.user_atual, 
                            'nome': u_info['nome'], 
                            'data': get_now().date().isoformat(), 
                            'h_saida': st.session_state.saida, 
                            'h_retorno': get_now().strftime("%H:%M:%S"), 
                            'duracao': st.session_state.t_pausa
                        }).execute()
                        supabase.table('escalas').delete().eq('id', st.session_state.p_id).execute()
                        st.session_state.pausa_ativa = False
                        st.session_state.liberado = False
                        st.rerun()
                    except:
                        st.error("Erro ao salvar histórico. Tente novamente.")
