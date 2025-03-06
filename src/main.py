import streamlit as st
import json
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import requests
from datetime import datetime

def apply_custom_css():
    # Cores para tema claro
    light_primary = "#4361ee"
    light_secondary = "#3a0ca3"
    light_accent = "#f72585"
    light_bg = "#ffffff"
    light_text = "#1f2937"
    light_card_bg = "#f9fafb"
    
    # Cores para tema escuro
    dark_primary = "#4cc9f0"
    dark_secondary = "#4895ef"
    dark_accent = "#f72585"
    dark_bg = "#111827"
    dark_text = "#f9fafb"
    dark_card_bg = "#1f2937"
    
    # Selecionar cores com base no tema
    primary = dark_primary
    secondary = dark_secondary
    accent = dark_accent
    bg = dark_bg
    text = dark_text
    card_bg = dark_card_bg
    
    # CSS personalizado (simplificado para melhor performance)
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {bg};
            color: {text};
        }}
        
        h1, h2, h3 {{
            color: {primary};
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, {primary}, {secondary});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }}
        
        .card {{
            background-color: {card_bg};
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .stButton > button {{
            background-color: {primary};
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            border: none;
        }}
        
        .stButton > button:hover {{
            background-color: {secondary};
        }}
        
        .success-box {{
            background-color: #d1fae5;
            border-left: 4px solid #10b981;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 1rem 0;
        }}
        
        .error-box {{
            background-color: #fee2e2;
            border-left: 4px solid #ef4444;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 1rem 0;
        }}
        
        .info-box {{
            background-color: #dbeafe;
            border-left: 4px solid #3b82f6;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 1rem 0;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 1rem;
            font-size: 0.875rem;
            color: {text}99;
            border-top: 1px solid {text}22;
        }}
    </style>
    """, unsafe_allow_html=True)


# Inicializar o estado da sessão se necessário
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'has_generated' not in st.session_state:
    st.session_state.has_generated = False
if 'question_type' not in st.session_state:
    st.session_state.question_type = "dissertativa"

def extract_video_id(youtube_url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    youtube_match = re.search(youtube_regex, youtube_url)
    if youtube_match:
        return youtube_match.group(6)
    return None

def check_video_availability(video_id):
    """Verifica se o vídeo está disponível no YouTube"""
    try:
        # Usando a API pública do YouTube para verificar o status do vídeo
        url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url)
        
        # Se a resposta for bem-sucedida, o vídeo está disponível
        return response.status_code == 200
    except:
        # Em caso de erro, assumimos que o vídeo não está disponível
        return False

def get_transcript_via_proxy(video_id):
    """Tenta obter a transcrição usando serviços proxy alternativos"""
    try:
        # Lista de serviços proxy para tentar
        proxy_services = [
            f"https://invidious.snopyta.org/api/v1/videos/{video_id}/captions",
            f"https://vid.puffyan.us/api/v1/videos/{video_id}/captions",
            f"https://yewtu.be/api/v1/videos/{video_id}/captions"
        ]
        
        for service_url in proxy_services:
            try:
                response = requests.get(service_url, timeout=5)
                if response.status_code == 200:
                    captions_data = response.json()
                    # Processar os dados de legendas
                    if captions_data and len(captions_data) > 0:
                        # Tentar encontrar legendas em português
                        pt_captions = next((c for c in captions_data if c.get('languageCode') == 'pt'), None)
                        if pt_captions:
                            caption_url = pt_captions.get('url')
                            if caption_url:
                                caption_response = requests.get(caption_url)
                                if caption_response.status_code == 200:
                                    # Processar o conteúdo das legendas
                                    return caption_response.text
                        
                        # Se não encontrou legendas em português, tenta em inglês
                        en_captions = next((c for c in captions_data if c.get('languageCode') == 'en'), None)
                        if en_captions:
                            caption_url = en_captions.get('url')
                            if caption_url:
                                caption_response = requests.get(caption_url)
                                if caption_response.status_code == 200:
                                    # Processar o conteúdo das legendas
                                    return caption_response.text
            except:
                continue
    except:
        pass
    
    return None

def get_transcript_via_api(video_id):
    """Tenta obter a transcrição usando APIs alternativas"""
    try:
        # Tentar API alternativa 1
        url = f"https://youtubetranscript.com/?server_vid={video_id}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            # Extrair o texto da transcrição da resposta
            transcript_text = response.text
            # Processar o texto para extrair apenas a transcrição
            transcript_match = re.search(r'"text":"(.*?)"', transcript_text)
            if transcript_match:
                return transcript_match.group(1)
    except:
        pass
    
    try:
        # Tentar API alternativa 2
        url = f"https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            captions_data = response.json()
            if 'items' in captions_data and len(captions_data['items']) > 0:
                # Processar os dados de legendas
                return "Transcrição obtida via API alternativa"
    except:
        pass
    
    return None

def get_youtube_transcript_with_fallback(video_id):
    """Tenta obter a transcrição do YouTube com múltiplos métodos"""
    # Verificar se o vídeo está disponível
    if not check_video_availability(video_id):
        st.error("Este vídeo não está mais disponível no YouTube.")
        return None
    
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
        
        # Método 3: Tentar com proxy
        st.info("Tentando obter transcrição através de serviços alternativos...")
        proxy_transcript = get_transcript_via_proxy(video_id)
        if proxy_transcript:
            st.success("✅ Transcrição obtida via serviço alternativo!")
            return proxy_transcript
        
        # Método 4: Tentar com API alternativa
        api_transcript = get_transcript_via_api(video_id)
        if api_transcript:
            st.success("✅ Transcrição obtida via API alternativa!")
            return api_transcript
        
        # Se todos os métodos falharem
        st.error("Não foi possível obter a transcrição automaticamente.")
        
        # Permitir entrada manual como último recurso
        manual_transcript = st.text_area(
            "Como último recurso, você pode colar a transcrição manualmente:",
            height=200,
            placeholder="Cole aqui a transcrição do vídeo..."
        )
        
        if manual_transcript:
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
    
    # # Mostrar opções de deploy alternativas
    # render_deployment_options()
    
    # Formulário de entrada
    with st.form("input_form"):
        youtube_url = st.text_input("URL do YouTube", placeholder="https://www.youtube.com/watch?v=...")
        api_key = st.text_input("Chave da API Google (AI/Gemini)", type="password")
        # Guardar a API key na sessão para uso posterior
        if api_key:
            st.session_state['api_key'] = api_key
            
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
        
        if not api_key:
            st.error("Por favor, insira sua chave de API do Google (AI/Gemini).")
            return
        
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("URL do YouTube inválida. Por favor, insira uma URL válida.")
            return
        
        with st.spinner("Verificando disponibilidade do vídeo e buscando transcrição..."):
            # Usar o método com fallback
            transcript = get_youtube_transcript_with_fallback(video_id)
            if not transcript:
                return
            
            with st.spinner("Gerando perguntas com IA..."):
                questions = generate_questions(transcript, api_key, num_questions, question_type)
                
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
        
        # Botão para baixar as perguntas
        questions_json = json.dumps(st.session_state.questions, indent=2, ensure_ascii=False)
        st.download_button(
            label="Baixar Perguntas como JSON",
            data=questions_json,
            file_name=f"perguntas_youtube_{st.session_state.question_type}.json",
            mime="application/json"
        )
    
    # Renderizar footer
    render_footer()

if __name__ == "__main__":
    main()