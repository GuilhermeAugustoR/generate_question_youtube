import streamlit as st
import json
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re

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

def extract_video_id(youtube_url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    youtube_match = re.search(youtube_regex, youtube_url)
    if youtube_match:
        return youtube_match.group(6)
    return None

def get_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt'])
        transcript = ' '.join([item['text'] for item in transcript_list])
        return transcript
    except Exception as e:
        st.error(f"Erro ao buscar a transcrição: {str(e)}")
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
    
    # Formulário de entrada
    with st.form("input_form"):
        youtube_url = st.text_input("URL do YouTube", placeholder="https://www.youtube.com/watch?v=...")
        api_key = st.text_input("Chave da API Google (AI/Gemini)", type="password")
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
        
        with st.spinner("Buscando transcrição e gerando perguntas..."):
            transcript = get_youtube_transcript(video_id)
            if not transcript:
                st.error("Não foi possível obter a transcrição. O vídeo pode não ter legendas ou legendas em português.")
                return
            
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