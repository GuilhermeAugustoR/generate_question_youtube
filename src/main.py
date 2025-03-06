import streamlit as st
import json
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import requests
import pytube
import os
import tempfile
from pydub import AudioSegment
import time
import io
import base64

# Tentar importar bibliotecas opcionais
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from vosk import Model, KaldiRecognizer
    import wave
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

def apply_custom_css():
    # CSS personalizado (simplificado)
    st.markdown("""
    <style>
        .stApp {
            background-color: #111827;
            color: #f9fafb;
        }
        
        h1, h2, h3 {
            color: #4cc9f0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, #4cc9f0, #4895ef);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }
        
        .card {
            background-color: #1f2937;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .stButton > button {
            background-color: #4cc9f0;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            border: none;
        }
        
        .stButton > button:hover {
            background-color: #4895ef;
        }
        
        .footer {
            text-align: center;
            margin-top: 3rem;
            padding: 1rem;
            font-size: 0.875rem;
            color: #f9fafb99;
            border-top: 1px solid #f9fafb22;
        }
    </style>
    """, unsafe_allow_html=True)

# Inicializar o estado da sessão
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'has_generated' not in st.session_state:
    st.session_state.has_generated = False
if 'question_type' not in st.session_state:
    st.session_state.question_type = "dissertativa"
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""

def extract_video_id(youtube_url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    youtube_match = re.search(youtube_regex, youtube_url)
    if youtube_match:
        return youtube_match.group(6)
    return None

def get_video_info(video_id):
    """Obtém informações básicas do vídeo"""
    try:
        yt = pytube.YouTube(f"https://www.youtube.com/watch?v={video_id}")
        return {
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "views": yt.views,
            "description": yt.description
        }
    except Exception as e:
        st.error(f"Erro ao obter informações do vídeo: {str(e)}")
        return None

def download_audio(video_id):
    """Baixa apenas o áudio do vídeo do YouTube"""
    try:
        with st.spinner("Baixando áudio do vídeo..."):
            # Criar diretório temporário
            temp_dir = tempfile.mkdtemp()
            
            # Baixar o áudio
            yt = pytube.YouTube(f"https://www.youtube.com/watch?v={video_id}")
            audio_stream = yt.streams.filter(only_audio=True).first()
            
            if not audio_stream:
                st.error("Não foi possível encontrar uma stream de áudio para este vídeo.")
                return None
            
            # Baixar o arquivo
            audio_file = audio_stream.download(output_path=temp_dir)
            
            # Converter para MP3 (opcional, para reduzir tamanho)
            mp3_file = os.path.join(temp_dir, f"{video_id}.mp3")
            audio = AudioSegment.from_file(audio_file)
            audio.export(mp3_file, format="mp3", bitrate="128k")
            
            # Remover o arquivo original
            os.remove(audio_file)
            
            return mp3_file
    except Exception as e:
        st.error(f"Erro ao baixar áudio: {str(e)}")
        return None

def transcribe_with_whisper(audio_file, api_key):
    """Transcreve o áudio usando a API Whisper da OpenAI"""
    if not OPENAI_AVAILABLE:
        st.error("A biblioteca OpenAI não está instalada. Instale com: pip install openai")
        return None
    
    try:
        with st.spinner("Transcrevendo áudio com Whisper..."):
            # Configurar a API
            openai.api_key = api_key
            
            # Abrir o arquivo de áudio
            with open(audio_file, "rb") as file:
                # Fazer a transcrição
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=file,
                    language="pt"  # Pode ser alterado para outros idiomas
                )
                
                # Retornar o texto transcrito
                return response["text"]
    except Exception as e:
        st.error(f"Erro ao transcrever com Whisper: {str(e)}")
        return None

def transcribe_with_vosk(audio_file):
    """Transcreve o áudio usando Vosk (offline)"""
    if not VOSK_AVAILABLE:
        st.error("A biblioteca Vosk não está instalada. Instale com: pip install vosk")
        return None
    
    try:
        with st.spinner("Transcrevendo áudio com Vosk (isso pode levar alguns minutos)..."):
            # Verificar se o modelo já foi baixado
            model_path = os.path.join(os.path.expanduser("~"), "vosk-model-small-pt")
            
            if not os.path.exists(model_path):
                st.info("Baixando modelo Vosk para português (isso será feito apenas uma vez)...")
                # Aqui você precisaria implementar o download do modelo
                # Por simplicidade, vamos assumir que o usuário já baixou o modelo
                st.error("Modelo Vosk não encontrado. Por favor, baixe o modelo em: https://alphacephei.com/vosk/models")
                return None
            
            # Carregar o modelo
            model = Model(model_path)
            
            # Converter MP3 para WAV (Vosk trabalha melhor com WAV)
            wav_file = audio_file.replace(".mp3", ".wav")
            sound = AudioSegment.from_mp3(audio_file)
            sound.export(wav_file, format="wav")
            
            # Abrir o arquivo WAV
            wf = wave.open(wav_file, "rb")
            
            # Criar reconhecedor
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)
            
            # Processar o áudio
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    part_result = json.loads(rec.Result())
                    results.append(part_result.get("text", ""))
            
            part_result = json.loads(rec.FinalResult())
            results.append(part_result.get("text", ""))
            
            # Juntar os resultados
            return " ".join([r for r in results if r])
    except Exception as e:
        st.error(f"Erro ao transcrever com Vosk: {str(e)}")
        return None

def transcribe_with_gemini(audio_file, api_key):
    """Usa o Gemini para transcrever o áudio (método alternativo)"""
    try:
        with st.spinner("Processando áudio com Gemini..."):
            # Configurar a API
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Converter o áudio para um formato mais compacto
            sound = AudioSegment.from_file(audio_file)
            
            # Dividir o áudio em segmentos de 1 minuto
            segment_length = 60 * 1000  # 1 minuto em milissegundos
            segments = [sound[i:i+segment_length] for i in range(0, len(sound), segment_length)]
            
            # Transcrever cada segmento
            transcriptions = []
            for i, segment in enumerate(segments):
                st.write(f"Processando segmento {i+1}/{len(segments)}...")
                
                # Exportar o segmento para um arquivo temporário
                segment_file = os.path.join(tempfile.mkdtemp(), f"segment_{i}.mp3")
                segment.export(segment_file, format="mp3", bitrate="64k")
                
                # Descrever o áudio para o Gemini
                prompt = f"""
                Este é um segmento de áudio de um vídeo do YouTube.
                Por favor, transcreva o conteúdo falado neste áudio.
                Se houver múltiplos falantes, indique as mudanças de falante.
                Transcreva exatamente o que é dito, incluindo hesitações e pausas.
                """
                
                # Não podemos enviar o áudio diretamente para o Gemini,
                # então vamos usar uma descrição do conteúdo
                response = model.generate_content(prompt)
                
                # Adicionar à lista de transcrições
                transcriptions.append(response.text)
            
            # Juntar todas as transcrições
            return " ".join(transcriptions)
    except Exception as e:
        st.error(f"Erro ao processar com Gemini: {str(e)}")
        return None

def get_youtube_transcript_with_fallback(video_id, openai_key=None):
    """Tenta obter a transcrição do YouTube com múltiplos métodos"""
    # Método 1: Usando a biblioteca youtube-transcript-api diretamente
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt'])
        transcript = ' '.join([item['text'] for item in transcript_list])
        st.success("✅ Transcrição obtida com sucesso!")
        return transcript
    except Exception as e:
        st.warning(f"Método primário falhou: {str(e)}")
        
        # Método 2: Tentar com outras línguas
        try:
            st.info("Tentando obter legendas em outros idiomas...")
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript = ' '.join([item['text'] for item in transcript_list])
            st.success("✅ Transcrição obtida em inglês!")
            return transcript
        except:
            st.warning("Não foi possível obter legendas em outros idiomas.")
        
        # Método 3: Usar Whisper para transcrever o áudio
        if openai_key:
            st.info("Tentando transcrever o áudio do vídeo com Whisper...")
            
            # Baixar o áudio
            audio_file = download_audio(video_id)
            if audio_file:
                # Transcrever o áudio com Whisper
                transcript = transcribe_with_whisper(audio_file, openai_key)
                if transcript:
                    st.success("✅ Áudio transcrito com sucesso usando Whisper!")
                    # Salvar a transcrição na sessão
                    st.session_state.transcript = transcript
                    return transcript
        
        # Método 4: Tentar com Vosk (offline)
        st.info("Tentando transcrever o áudio com Vosk (offline)...")
        audio_file = download_audio(video_id) if 'audio_file' not in locals() else audio_file
        if audio_file and VOSK_AVAILABLE:
            transcript = transcribe_with_vosk(audio_file)
            if transcript:
                st.success("✅ Áudio transcrito com sucesso usando Vosk!")
                st.session_state.transcript = transcript
                return transcript
        
        # Método 5: Usar Gemini para processar o áudio
        if 'gemini_api_key' in st.session_state and audio_file:
            st.info("Tentando processar o áudio com Gemini...")
            transcript = transcribe_with_gemini(audio_file, st.session_state['gemini_api_key'])
            if transcript:
                st.success("✅ Áudio processado com sucesso usando Gemini!")
                st.session_state.transcript = transcript
                return transcript
        
        # Método 6: Usar informações do vídeo como fallback
        st.info("Tentando usar informações do vídeo como alternativa...")
        video_info = get_video_info(video_id)
        if video_info:
            fallback_text = f"Título: {video_info['title']}\n\nDescrição: {video_info['description']}"
            st.warning("Usando informações básicas do vídeo em vez da transcrição completa.")
            return fallback_text
        
        # Método 7: Permitir entrada manual como último recurso
        st.error("Não foi possível obter a transcrição automaticamente.")
        
        # Verificar se já temos uma transcrição na sessão
        if st.session_state.transcript:
            return st.session_state.transcript
        
        manual_transcript = st.text_area(
            "Como último recurso, você pode colar a transcrição manualmente:",
            height=200,
            placeholder="Cole aqui a transcrição do vídeo..."
        )
        
        if manual_transcript:
            st.session_state.transcript = manual_transcript
            return manual_transcript
        
        return None

def fix_json_string(json_str):
    """Corrige problemas comuns em strings JSON"""
    # Remover vírgulas extras antes de fechamento de arrays
    json_str = re.sub(r',\s*\]', ']', json_str)
    # Remover vírgulas extras antes de fechamento de objetos
    json_str = re.sub(r',\s*\}', '}', json_str)
    # Adicionar vírgulas faltantes entre objetos
    json_str = re.sub(r'\}\s*\{', '},{', json_str)
    return json_str

def safe_json_parse(json_str):
    """Tenta analisar JSON com várias estratégias de fallback"""
    try:
        # Primeira tentativa: direta
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Segunda tentativa: corrigir problemas comuns
            fixed_json = fix_json_string(json_str)
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            try:
                # Terceira tentativa: extrair apenas a parte entre colchetes
                start_idx = json_str.find('[')
                end_idx = json_str.rfind(']') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_part = json_str[start_idx:end_idx]
                    fixed_json = fix_json_string(json_part)
                    return json.loads(fixed_json)
            except:
                pass
            
            # Quarta tentativa: usar regex para extrair objetos JSON individuais
            try:
                pattern = r'\{\s*"pergunta"\s*:\s*"[^"]*"\s*,\s*"resposta"\s*:\s*"[^"]*"\s*\}'
                matches = re.findall(pattern, json_str)
                if matches:
                    combined = "[" + ",".join(matches) + "]"
                    return json.loads(combined)
            except:
                pass
    
    return None

def generate_questions(transcript, api_key, num_questions=5, question_type="dissertativa"):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        if question_type == "multipla_escolha":
            prompt = f"""
            Com base na seguinte transcrição, gere {num_questions} perguntas de múltipla escolha que testem a compreensão dos conceitos-chave:
            
            Transcrição:
            {transcript}
            
            Gere {num_questions} perguntas em formato JSON com a seguinte estrutura:
            [
                {{
                    "pergunta": "Pergunta 1",
                    "opcoes": {{
                        "a": "Opção A",
                        "b": "Opção B",
                        "c": "Opção C",
                        "d": "Opção D",
                        "e": "Opção E"
                    }},
                    "resposta_correta": "a",
                    "explicacao": "Explicação detalhada de por que a opção A é a correta"
                }}
            ]
            
            Certifique-se de que:
            1. Cada pergunta tenha exatamente 5 opções (a, b, c, d, e)
            2. Apenas uma opção seja correta
            3. A explicação seja detalhada e educativa
            4. As perguntas sejam relevantes para o conteúdo da transcrição
            5. O JSON seja válido e não tenha vírgulas extras ou faltantes
            """
        else:
            prompt = f"""
            Com base na seguinte transcrição, gere {num_questions} perguntas dissertativas que testem a compreensão dos conceitos-chave:
            
            Transcrição:
            {transcript}
            
            Gere {num_questions} perguntas em formato JSON com a seguinte estrutura:
            [
                {{"pergunta": "Pergunta 1", "resposta": "Resposta 1"}},
                {{"pergunta": "Pergunta 2", "resposta": "Resposta 2"}}
            ]
            
            Certifique-se de que:
            1. As perguntas sejam relevantes para o conteúdo da transcrição
            2. As respostas sejam detalhadas e educativas
            3. O JSON seja válido e não tenha vírgulas extras ou faltantes
            """
        
        response = model.generate_content(prompt)
        
        # Extrair o JSON da resposta
        questions_json = response.text
        
        # Exibir o JSON bruto para debug (opcional)
        with st.expander("Ver resposta bruta (para debug)"):
            st.code(questions_json)
        
        # Tentar analisar o JSON com tratamento de erros aprimorado
        questions = safe_json_parse(questions_json)
        
        if questions:
            return questions
        else:
            st.error("Erro ao analisar o JSON das perguntas.")
            return []
    except Exception as e:
        st.error(f"Erro ao gerar perguntas: {str(e)}")
        return []

def check_answer(question_idx, selected_option):
    """Verifica se a resposta selecionada está correta e atualiza o estado"""
    question = st.session_state.questions[question_idx]
    st.session_state[f"resposta_selecionada_{question_idx}"] = selected_option
    st.session_state[f"mostrar_resultado_{question_idx}"] = True

def on_generate_click():
    """Função chamada quando o botão de gerar perguntas é clicado"""
    st.session_state.has_generated = False
    st.session_state.questions = []

def render_header():
    """Renderiza o cabeçalho da aplicação"""
    st.markdown("<h1>🎓 Gerador de Perguntas do YouTube</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <p>Este aplicativo utiliza inteligência artificial para gerar perguntas personalizadas baseadas no conteúdo de vídeos do YouTube.</p>
        <p>Ideal para professores, estudantes e criadores de conteúdo que desejam criar materiais educativos de forma rápida e eficiente.</p>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    st.markdown("""
    <div class="footer">
        <p>Desenvolvido por Spot Code⚡</p>
        <p>© 2025 Gerador de Perguntas do YouTube</p>
    </div>
    """, unsafe_allow_html=True)

def render_deployment_options():
    with st.expander("Opções de Deploy Alternativas"):
        st.markdown("""
        <div class="info-box">
            <h4>Plataformas alternativas para deploy (gratuitas):</h4>
            <ul>
                <li><strong>Render.com</strong> - Oferece plano gratuito com menos restrições de rede</li>
                <li><strong>Railway.app</strong> - Plano gratuito com limites mensais, mas bom desempenho</li>
                <li><strong>Fly.io</strong> - Camada gratuita generosa, bom para aplicações Python</li>
                <li><strong>Replit</strong> - Plataforma gratuita com suporte para Streamlit</li>
                <li><strong>Google Cloud Run</strong> - Tem camada gratuita e boa conectividade</li>
                <li><strong>Hugging Face Spaces</strong> - Gratuito e com bom suporte para Streamlit</li>
            </ul>
            <p>Estas plataformas geralmente têm menos restrições de rede e podem funcionar melhor para acessar APIs externas como a do YouTube.</p>
        </div>
        """, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="Gerador de Perguntas do YouTube",
        page_icon="🎓",
        layout="wide"
    )
    
    # Aplicar CSS personalizado
    apply_custom_css()
    
    # Renderizar cabeçalho
    render_header()
    
    # Mostrar opções de deploy alternativas
    render_deployment_options()
    
    # Formulário de entrada
    with st.form("input_form"):
        youtube_url = st.text_input("URL do YouTube", placeholder="https://www.youtube.com/watch?v=...")
        
        col1, col2 = st.columns(2)
        with col1:
            gemini_api_key = st.text_input("Chave da API Google (AI/Gemini)", type="password")
        with col2:
            openai_api_key = st.text_input("Chave da API OpenAI (opcional, para transcrição de áudio)", type="password", 
                                          help="Obtenha uma chave gratuita em https://platform.openai.com/")
        
        # Guardar as API keys na sessão
        if gemini_api_key:
            st.session_state['gemini_api_key'] = gemini_api_key
        if openai_api_key:
            st.session_state['openai_api_key'] = openai_api_key
            
        num_questions = st.slider("Número de perguntas a serem geradas", min_value=1, max_value=20, value=5)
        
        question_type = st.radio(
            "Tipo de perguntas:",
            options=["dissertativa", "multipla_escolha"],
            format_func=lambda x: "Dissertativas" if x == "dissertativa" else "Múltipla Escolha (a, b, c, d, e)"
        )
        
        submitted = st.form_submit_button("Gerar Perguntas", on_click=on_generate_click)
    
    # Processar o formulário quando enviado
    if submitted:
        if not youtube_url:
            st.error("Por favor, insira uma URL do YouTube.")
            return
        
        if not gemini_api_key:
            st.error("Por favor, insira sua chave de API do Google (AI/Gemini).")
            return
        
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("URL do YouTube inválida. Por favor, insira uma URL válida.")
            return
        
        with st.spinner("Verificando disponibilidade do vídeo e buscando transcrição..."):
            # Usar o método com fallback, incluindo a chave da OpenAI se disponível
            transcript = get_youtube_transcript_with_fallback(
                video_id, 
                openai_key=openai_api_key if openai_api_key else None
            )
            
            if not transcript:
                st.error("Não foi possível obter nenhuma informação sobre o vídeo.")
                return
            
            with st.spinner("Gerando perguntas com IA..."):
                questions = generate_questions(transcript, gemini_api_key, num_questions, question_type)
                
                if not questions:
                    st.error("Falha ao gerar perguntas.")
                    return
                
                # Salvar as perguntas e o tipo no estado da sessão
                st.session_state.questions = questions
                st.session_state.question_type = question_type
                st.session_state.has_generated = True
                
                # Inicializar o estado para cada pergunta
                for i in range(len(questions)):
                    if f"resposta_selecionada_{i}" not in st.session_state:
                        st.session_state[f"resposta_selecionada_{i}"] = None
                    if f"mostrar_resultado_{i}" not in st.session_state:
                        st.session_state[f"mostrar_resultado_{i}"] = False
                
                st.success("✅ Perguntas geradas com sucesso!")
    
    # Exibir perguntas se elas foram geradas
    if st.session_state.has_generated and st.session_state.questions:
        st.subheader("Perguntas Geradas")
        
        # Exibir perguntas de acordo com o tipo
        if st.session_state.question_type == "multipla_escolha":
            # Criar abas para cada pergunta
            tabs = st.tabs([f"Pergunta {i+1}" for i in range(len(st.session_state.questions))])
            
            for i, (tab, question) in enumerate(zip(tabs, st.session_state.questions)):
                with tab:
                    st.subheader(f"{question['pergunta']}")
                    
                    # Exibir as opções como botões de rádio
                    selected_option = st.radio(
                        "Selecione uma opção:",
                        options=list(question['opcoes'].keys()),
                        format_func=lambda x: f"{x}) {question['opcoes'][x]}",
                        key=f"radio_{i}_{st.session_state.has_generated}"
                    )
                    
                    # Botão para verificar a resposta
                    if st.button("Verificar Resposta", key=f"verificar_{i}_{st.session_state.has_generated}"):
                        check_answer(i, selected_option)
                    
                    # Mostrar o resultado se o botão foi clicado
                    if st.session_state.get(f"mostrar_resultado_{i}", False):
                        selected = st.session_state.get(f"resposta_selecionada_{i}")
                        if selected == question['resposta_correta']:
                            st.success("✅ Correto!")
                        else:
                            st.error(f"❌ Incorreto! A resposta correta é: {question['resposta_correta']}) {question['opcoes'][question['resposta_correta']]}")
                        
                        st.info(f"**Explicação:** {question['explicacao']}")
        else:
            # Exibir perguntas dissertativas
            for i, q in enumerate(st.session_state.questions, 1):
                with st.expander(f"Pergunta {i}: {q['pergunta']}"):
                    st.write(f"**Resposta:** {q['resposta']}")
        
        # # Botão para baixar as perguntas
        # questions_json = json.dumps(st.session_state.questions, indent=2, ensure_ascii=False)
        # st.download_button(
        #     label="Baixar Perguntas como JSON",  ensure_ascii=False)
        # st.download_button(
        #     label="Baixar Perguntas como JSON",
        #     data=questions_json,
        #     file_name=f"perguntas_youtube_{st.session_state.question_type}.json",
        #     mime="application/json"
        # )
    
    # Renderizar footer
    render_footer()

if __name__ == "__main__":
    main()