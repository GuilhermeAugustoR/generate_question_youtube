import streamlit as st
import json
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import requests
from datetime import datetime
import base64
import time

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
    
    # CSS personalizado
    st.markdown(f"""
    <style>
        /* Estilos gerais */
        .stApp {{
            background-color: {bg};
            color: {text};
        }}
        
        /* Cabeçalhos */
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
        
        h2 {{
            font-size: 1.8rem;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        /* Cards */
        .card {{
            background-color: {card_bg};
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }}
        
        .card:hover {{
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
            transform: translateY(-5px);
        }}
        
        /* Formulário */
        .form-container {{
            background-color: {card_bg};
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        /* Botões */
        .stButton > button {{
            background-color: {primary};
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            border: none;
            transition: all 0.3s;
        }}
        
        .stButton > button:hover {{
            background-color: {secondary};
            transform: translateY(-2px);
        }}
        
        /* Mensagens */
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
        
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background-color: {primary}33;
            color: {primary};
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-right: 0.5rem;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: {card_bg};
            border-radius: 8px 8px 0 0;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {primary};
            color: white;
        }}
        
        /* Animações */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .animate-fade-in {{
            animation: fadeIn 0.5s ease-out forwards;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 1rem;
            font-size: 0.875rem;
            color: {text}99;
            border-top: 1px solid {text}22;
        }}
        
        /* Tema toggle */
        .theme-toggle {{
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 1000;
        }}
        
        /* Responsividade */
        @media (max-width: 768px) {{
            h1 {{ font-size: 2rem; }}
            .card {{ padding: 1rem; }}
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
if 'manual_transcript' not in st.session_state:
    st.session_state.manual_transcript = ""

def extract_video_id(youtube_url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    youtube_match = re.search(youtube_regex, youtube_url)
    if youtube_match:
        return youtube_match.group(6)
    return None

def get_transcript_from_local_file():
    """Permite ao usuário fazer upload de um arquivo de transcrição"""
    uploaded_file = st.file_uploader("Faça upload de um arquivo de transcrição (TXT)", type="txt")
    if uploaded_file is not None:
        # Ler o conteúdo do arquivo
        transcript = uploaded_file.getvalue().decode("utf-8")
        return transcript
    return None

def get_youtube_transcript_with_proxy(video_id):
    """Tenta obter a transcrição do YouTube usando um proxy ou serviço alternativo"""
    # Lista de serviços proxy para tentar
    proxy_services = [
        f"https://invidious.snopyta.org/api/v1/videos/{video_id}/captions",
        f"https://vid.puffyan.us/api/v1/videos/{video_id}/captions",
        f"https://yewtu.be/api/v1/videos/{video_id}/captions"
    ]
    
    for service_url in proxy_services:
        try:
            response = requests.get(service_url)
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
    
    return None

def get_youtube_transcript_with_fallback(video_id):
    """Tenta obter a transcrição do YouTube com múltiplos métodos"""
    # Método 1: Usando a biblioteca youtube-transcript-api diretamente
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt'])
        transcript = ' '.join([item['text'] for item in transcript_list])
        return transcript
    except Exception as e:
        st.warning(f"Método primário falhou: {str(e)}")
        
        # Método 2: Tentar com outras línguas
        try:
            st.info("Tentando obter legendas em outros idiomas...")
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript = ' '.join([item['text'] for item in transcript_list])
            return transcript
        except:
            st.warning("Não foi possível obter legendas em outros idiomas.")
        
        # Método 3: Tentar com proxy
        try:
            st.info("Tentando obter transcrição através de serviços alternativos...")
            proxy_transcript = get_youtube_transcript_with_proxy(video_id)
            if proxy_transcript:
                return proxy_transcript
        except:
            st.warning("Não foi possível obter transcrição através de serviços alternativos.")
        
        # Método 4: Permitir upload de arquivo
        st.info("Você pode fazer upload de um arquivo de transcrição:")
        file_transcript = get_transcript_from_local_file()
        if file_transcript:
            return file_transcript
        
        # Método 5: Entrada manual
        st.warning("Não foi possível obter a transcrição automaticamente.")
        
        # Verificar se já temos uma transcrição manual na sessão
        if st.session_state.manual_transcript:
            return st.session_state.manual_transcript
        
        # Opção para inserir transcrição manualmente
        manual_transcript = st.text_area(
            "Insira manualmente a transcrição ou o conteúdo do vídeo:",
            height=300,
            placeholder="Cole aqui a transcrição do vídeo ou um texto relacionado ao tema..."
        )
        
        if manual_transcript:
            # Salvar na sessão para não perder se o usuário recarregar
            st.session_state.manual_transcript = manual_transcript
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
    col1, col2 = st.columns([6, 1])
    
    with col1:
        st.markdown("<h1>🎓 Gerador de Perguntas do YouTube</h1>", unsafe_allow_html=True)
    
    
    st.markdown("""
    <div class="card animate-fade-in">
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

def render_video_tips():
    """Renderiza dicas para escolher vídeos compatíveis"""
    with st.expander("Dicas para escolher vídeos compatíveis"):
        st.markdown("""
        <div class="info-box">
            <h4>Como escolher vídeos compatíveis:</h4>
            <ul>
                <li>Escolha vídeos que tenham legendas disponíveis (ícone CC na barra de controle do YouTube)</li>
                <li>Vídeos em português do Brasil geralmente funcionam melhor</li>
                <li>Vídeos educacionais, palestras e tutoriais costumam ter legendas de qualidade</li>
                <li>Verifique se o vídeo está disponível publicamente (não é privado ou restrito)</li>
                <li>Vídeos muito recentes podem ainda não ter legendas processadas</li>
            </ul>
            <h4>Solução para problemas de acesso:</h4>
            <p>Se um vídeo funciona localmente mas não funciona no deploy, você pode:</p>
            <ul>
                <li>Fazer upload de um arquivo de transcrição (TXT) que você obteve localmente</li>
                <li>Colar manualmente a transcrição no campo de texto</li>
                <li>Tentar outro vídeo com legendas disponíveis</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

def render_local_transcript_uploader():
    """Renderiza um uploader para transcrições locais"""
    st.markdown("<h3>Transcrição Local</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
        <p>Se você já tem a transcrição do vídeo, pode fazer upload dela aqui ou colar diretamente no campo abaixo.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Opção 1: Upload de arquivo
    uploaded_file = st.file_uploader("Faça upload de um arquivo de transcrição (TXT)", type="txt")
    if uploaded_file is not None:
        # Ler o conteúdo do arquivo
        transcript = uploaded_file.getvalue().decode("utf-8")
        st.session_state.manual_transcript = transcript
        st.success("✅ Transcrição carregada com sucesso!")
        return True
    
    # Opção 2: Entrada manual
    manual_transcript = st.text_area(
        "Ou cole a transcrição aqui:",
        value=st.session_state.manual_transcript,
        height=200,
        placeholder="Cole aqui a transcrição do vídeo ou um texto relacionado ao tema..."
    )
    
    if manual_transcript and manual_transcript != st.session_state.manual_transcript:
        st.session_state.manual_transcript = manual_transcript
        st.success("✅ Transcrição salva!")
        return True
    
    return False

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
    
    # Renderizar dicas para escolher vídeos
    render_video_tips()
    
    # Criar abas para diferentes métodos de entrada
    tab1, tab2 = st.tabs(["Vídeo do YouTube", "Transcrição Manual"])
    
    with tab1:
        # Formulário de entrada para vídeo do YouTube
        with st.form("youtube_form"):
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
            
            submitted_youtube = st.form_submit_button("Gerar Perguntas", on_click=on_generate_click)
    
    with tab2:
        # Uploader para transcrição local
        has_local_transcript = render_local_transcript_uploader()
        
        # Formulário para gerar perguntas a partir da transcrição manual
        with st.form("manual_form"):
            api_key_manual = st.text_input("Chave da API Google (AI/Gemini)", type="password", key="api_key_manual")
            # Guardar a API key na sessão para uso posterior
            if api_key_manual:
                st.session_state['api_key'] = api_key_manual
                
            num_questions_manual = st.slider("Número de perguntas a serem geradas", min_value=1, max_value=20, value=5, key="num_questions_manual")
            
            question_type_manual = st.radio(
                "Tipo de perguntas:",
                options=["dissertativa", "multipla_escolha"],
                format_func=lambda x: "Dissertativas" if x == "dissertativa" else "Múltipla Escolha (a, b, c, d, e)",
                key="question_type_manual"
            )
            
            submitted_manual = st.form_submit_button("Gerar Perguntas", on_click=on_generate_click)
    
    # Processar o formulário do YouTube quando enviado
    if submitted_youtube:
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
        
        with st.spinner("Buscando transcrição..."):
            # Usar o método com fallback
            transcript = get_youtube_transcript_with_fallback(video_id)
            if not transcript:
                st.error("Não foi possível obter a transcrição. Por favor, tente a opção de transcrição manual.")
                return
            
            st.success("✅ Transcrição obtida com sucesso!")
            
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
    
    # Processar o formulário manual quando enviado
    if submitted_manual:
        if not st.session_state.manual_transcript:
            st.error("Por favor, insira ou faça upload de uma transcrição.")
            return
        
        if not api_key_manual:
            st.error("Por favor, insira sua chave de API do Google (AI/Gemini).")
            return
        
        with st.spinner("Gerando perguntas com IA..."):
            questions = generate_questions(st.session_state.manual_transcript, api_key_manual, num_questions_manual, question_type_manual)
            
            if not questions:
                st.error("Falha ao gerar perguntas.")
                return
            
            # Salvar as perguntas e o tipo no estado da sessão
            st.session_state.questions = questions
            st.session_state.question_type = question_type_manual
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
        st.markdown("<h2>📋 Perguntas Geradas</h2>", unsafe_allow_html=True)
        
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