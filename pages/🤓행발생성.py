import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime    
import pytz
import google.generativeai as genai
import openai
import anthropic # Placeholder for Anthropic, actual library is 'anthropic'


# 구글 서비스 계정 인증 및 스프레드시트 열기 (app.py와 동일)
SERVICE_ACCOUNT_INFO = st.secrets["google_service_account"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
gc = gspread.authorize(credentials)
SHEET_ID = "1Bx4otXnVjpWONjlOMAecK4l-y3CAzxyNmH-O0mcQY0E"  # 실제 사용 중인 시트 ID로 맞추세요
sh = gc.open_by_key(SHEET_ID)

# 로그인/권한 정보 불러오기
user_role = st.session_state.get("user_role")
user_email = st.session_state.get("user_email")

# --- API Keys (Streamlit secrets) - 개선된 로딩 방식 ---
# Gemini API Key
GEMINI_API_KEY = None
try:
    # 여러 가능한 경로에서 시도
    if "gemini" in st.secrets and "API_KEY" in st.secrets["gemini"]:
        GEMINI_API_KEY = st.secrets["gemini"]["API_KEY"]
    elif "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass  # 조용히 실패

# OpenAI API Key
OPENAI_API_KEY = None
try:
    if "openai" in st.secrets and "API_KEY" in st.secrets["openai"]:
        OPENAI_API_KEY = st.secrets["openai"]["API_KEY"]
    elif "OPENAI_API_KEY" in st.secrets:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except Exception:
    pass  # 조용히 실패

# Anthropic API Key
ANTHROPIC_API_KEY = None
try:
    if "anthropic" in st.secrets and "API_KEY" in st.secrets["anthropic"]:
        ANTHROPIC_API_KEY = st.secrets["anthropic"]["API_KEY"]
    elif "ANTHROPIC_API_KEY" in st.secrets:
        ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass  # 조용히 실패

# 세션 상태 초기화 - 모델 캐싱용
if "cached_models" not in st.session_state:
    st.session_state.cached_models = {}

# --- Model Listing Functions with Caching ---
def list_gemini_models():
    # 캐시 확인
    if "gemini" in st.session_state.cached_models:
        return st.session_state.cached_models["gemini"]
    
    if not GEMINI_API_KEY:
        return ["Gemini API Key not configured"]
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Filter for more common/useful models if the list is too long or contains irrelevant ones
        filtered_models = [m for m in models if "gemini-1.5-pro" in m or "gemini-1.5-flash" in m or "gemini-1.0-pro" in m or "gemini-2.0" in m]
        result = filtered_models if filtered_models else models # Fallback to all if filter is too restrictive
        
        # 캐시에 저장
        st.session_state.cached_models["gemini"] = result
        return result
    except Exception as e:
        error_msg = f"Gemini 모델 목록 로드 실패: {str(e)}"
        return [error_msg]

def list_openai_models():
    # 캐시 확인
    if "openai" in st.session_state.cached_models:
        return st.session_state.cached_models["openai"]
    
    if not OPENAI_API_KEY:
        return ["OpenAI API Key not configured"]
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        models = client.models.list()
        # Revised filter: be less restrictive, initially include all, then sort
        # Common model prefixes: gpt-4, gpt-3.5. Users can visually filter.
        # Ensure model.id is accessed correctly from the model object in the list.
        model_ids = [model.id for model in models.data]
        
        # Prioritize newer models or those containing "gpt-4" or "gpt-3.5"
        priority_keywords = ["gpt-4o", "gpt-4", "gpt-3.5"]
        
        def sort_key(model_id):
            for i, keyword in enumerate(priority_keywords):
                if keyword in model_id:
                    return (i, model_id) # Prioritize by keyword, then alphabetically
            return (len(priority_keywords), model_id) # Others come after, then alphabetically

        sorted_model_ids = sorted(model_ids, key=sort_key)
        
        # 캐시에 저장
        st.session_state.cached_models["openai"] = sorted_model_ids
        return sorted_model_ids

    except Exception as e:
        error_msg = f"OpenAI 모델 목록 로드 실패: {str(e)}"
        return [error_msg]

def list_anthropic_models():
    # 캐시 확인
    if "anthropic" in st.session_state.cached_models:
        return st.session_state.cached_models["anthropic"]
    
    if not ANTHROPIC_API_KEY:
        return ["Anthropic API Key not configured"]
    
    # 기본 모델 목록 (fallback)
    default_models = [
        "claude-3-opus-20240229",
        "claude-3-5-sonnet-20241022",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-2.1",
        "claude-2.0",
        "claude-instant-1.2"
    ]
    
    try:
        # Dynamically fetch models as per documentation
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        models_page = client.models.list() # Returns a SyncPage[ModelInfo]
        
        # Extract model names/IDs from the ModelInfo objects
        model_ids = []
        
        # Try direct iteration first
        try:
            for model_info in models_page:
                if hasattr(model_info, 'id'):
                    model_ids.append(model_info.id)
                elif hasattr(model_info, 'name'):
                    model_ids.append(model_info.name)
        except:
            # If direct iteration fails, try .data attribute
            if hasattr(models_page, 'data'):
                for model_info in models_page.data:
                    if hasattr(model_info, 'id'):
                        model_ids.append(model_info.id)
                    elif hasattr(model_info, 'name'):
                        model_ids.append(model_info.name)

        # Use default list if dynamic fetching fails
        if not model_ids:
            model_ids = default_models
        else:
            # Sort to have newer/more capable models appear first
            model_ids = sorted(model_ids, reverse=True)
        
        # 캐시에 저장
        st.session_state.cached_models["anthropic"] = model_ids
        return model_ids

    except Exception as e:
        # Return default models on error
        st.session_state.cached_models["anthropic"] = default_models
        return default_models

# --- Unified LLM Generation Function ---
def generate_llm_text(provider, model_id, system_prompt, user_prompt, temperature, top_k=None, top_p=None):
    try:
        if provider == "Gemini":
            if not GEMINI_API_KEY: return "Gemini API Key not configured."
            genai.configure(api_key=GEMINI_API_KEY)
            model_name_only = model_id.split('/')[-1] # Extract "gemini-1.5-pro-latest" from "models/gemini-1.5-pro-latest"
            model = genai.GenerativeModel(
                model_name_only,
                system_instruction=system_prompt,
                generation_config={"temperature": temperature, "top_k": top_k}
            )
            response = model.generate_content(user_prompt)
            return response.text
        elif provider == "OpenAI":
            if not OPENAI_API_KEY: return "OpenAI API Key not configured."
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                top_p=top_p 
            )
            return completion.choices[0].message.content
        elif provider == "Anthropic":
            if not ANTHROPIC_API_KEY: return "Anthropic API Key not configured."
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) # Corrected instantiation
            response = client.messages.create(
                model=model_id,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=2000 # Anthropic requires max_tokens
            )
            return response.content[0].text
    except Exception as e:
        return f"{provider} API 호출 오류: {e}"

# --- 기본값 설정 (개발자가 코드에서 수정) ---
DEFAULT_SYSTEM_PROMPT = """당신은 고등학교 담임교사로서 학교생활기록부의 '행동특성 및 종합의견'을 작성하는 전문가입니다. 
다음 지침을 엄격히 준수하여 작성해주세요.

**작성 원칙:**
1. 수시로 관찰하여 누가 기록된 행동특성을 바탕으로 총체적으로 학생을 이해할 수 있는 종합의견 작성
2. 학생의 성장 정도, 특기사항, 발전 가능성을 구체적이고 객관적으로 서술
3. 학생에 대한 일종의 추천서 또는 지도 자료가 되도록 작성
4. 각 학교생활기록부 항목에 기록된 자료를 종합하여 균형 있게 기술
5. 우수행동특성발달사항 예시로 부터 문자의 구조와 스타일 형태를 분석하여 작성. 우수행동특성발달사항의 사람이 작성한 스타일처럼 글을 작성

** 우수행동특성발달사항 문장 예시: 
    - 혼자 종이접기 하는 것을 좋아하며 매사에 적극적으로 질문하고 참여하는 자세가 돋보임. 새로 바뀌는 환경에 민감하여 주변 친구들과 관계 맺는 일에 조금 어려움을 느끼지만 끊임없이 자신을 성찰하며 나아지려는 모습을 보임. 비교적 학업성취도는 낮으나 긍정적이고 적극적인 생활태도로 인하여 진로에 대한 진지한 자기성찰과 탐색을 통해 분명하고 구체적인 방향을 정하여 꾸준하게 노력한다면 무엇이든지 발전가능성이 있을 것으로 기대됨.
    - 다정하고 부드러운 면이 있어 사교성이 좋으며 자기 방식대로 일하는 것을 좋아하나 비교적 의지력이 약하여 추진력이 떨어짐. 스스로 공부하는 방법을 터득하고 자신이 세운 학습계획에 따라 자기주도적으로 열심히 공부하고 있어 발전가능성이 엿보임. 음악을 좋아하고 노래 부르는데도 재능이 있음. 친구들을 대할 때 항상 친절하고 다정하게 대함으로써 상대방을 배려하고 존중하는 마음을 실천함. 낯선 사람에게 선뜻 잘 다가서지 못하지만 한번 사귀면 지속적으로 좋은 친구관계를 잘 유지함.
    - 심성이 바르고 온순하여 대인관계에서 다소 수동적이고 순응적인 편이며 매우 신중하고 조심스러우며 비교적 소심한 성격임. 예의가 바르고 주변 친구들과 사이가 매우 원만하여 누가와도 잘 지냄. 교내 외 공동도덕과 규칙을 잘 지키고 남에게 피해를 주는 일이 없도록 항상 노력함. 학업에 흥미를 느끼고 있으므로 꾸준히 노력한다면 좋은 성취를 이룰 것으로 기대됨.
    - 다정다감하고 다른 사람들과 관계 맺는 것을 좋아하지만 비교적 자기중심적으로 생각하여 판단하는 경향이 있음. 공부의 필요성은 느끼고 있으나 기초학력이 부족하고 집중력과 의지력이 약하여 학업성취도가 다소 낮음. 요리에 대한 관심을 가지고 여러 가지 체험활동을 통해 진로를 모색하고 있어 자신의 노력이 더해진다면 발전가능성이 있을 것으로 보임. 체육에 대한 흥미가 많아 피구를 잘하며 승부욕도 강하여 학급대항 리그전에서 실력을 발휘함.
    - 매사에 긍정적이고 침착하며 마음의 변화가 적은 장점을 가진 학생으로 친구들에게 매우 온순하고 수용적인 편이라 자기주장과 표현이 다소 부족함. 어린이들을 좋아하고 아이들의 눈높이에 맞게 잘 놀아주고 가르치기를 즐거워하며 유아교육과 관련된 일에 남다른 관심과 흥미가 많음. 자신의 의견을 피력하기 전에 항상 주변 여건과 상황을 고려하여 합리적이고 올곧은 자세로 의견을 제시하는 등 긍정적이고 고운 심성을 가짐.
    - 정이 많고 온순하고 온순하며 타인에 대한 이해심이 많아 교우 관계가 원만함. 상대방의 말을 잘 경청하고 상대방의 입장에서 먼저 이해하려고 노력함. 친구들과의 관계를 주도하지는 못하지만 같이 어울리기를 좋아하며 즐겁게 잘 지내는 편임. 수업태도가 좋고 성실하게 과제를 수행하는 편이지만, 보다 구체적으로 목표를 설정하고 실천이 뒷받침 된다면 더욱 진전된 학습 성과가 있을 것으로 기대됨. 진로에 대한 보다 구체적인 탐색을 통해 관련된 정보와 지식을 획득하고 구체적인 실천 계획과 지속적인 노력이 필요함.
    - 밝고 긍정적인 사고방식을 가지고 있어 사교적이며 교우관계가 원만함. 친구의 고민사항을 잘 들어주고 공감하면서 격려하고 챙겨줌. 학업에 대한 욕심은 다소 미흡하지만 성실하게 과제를 수행하며 자신과 생각을 스스럼없이 잘 표현함. 춤에 대한 열정이 넘치고 꾸준히 호흡을 맞추면서 노력하는 모습을 보이며, 반가 발표회에서 주도적으로 안무를 짬. 교내 피구리그전에 참가하여 공격을 주도적으로 이끌어 학급이 좋은 성적을 올리는 데 크게 기여함은 물론 팀원들을 독려하면서 열정적인 모습으로 적극 참여함.

**문장 스타일 및 어미 형태:**
1. 어미 형태: 반드시 명사형 어미('-함', '-음', '-됨', '-임')로 종결
   - 올바른 예: '~을 보임', '~이 뛰어남', '~을 실천함', '~에 관심이 많음', '~을 도모함'
   - 잘못된 예: '~을 보인다', '~이 뛰어나다', '~을 실천한다'

2. 서술 구조:
   - [구체적 관찰 사실] + [행동 특성] + [평가/전망]
   - [학습/활동 상황] + [보인 태도/능력] + [성장/발전 가능성]
   - [성격/특성] + [구체적 사례] + [긍정적 영향/결과]

3. 내용 포함 영역:
   - 학업역량: 자기주도적 학습태도, 학업성취도, 탐구심, 문제해결력 등
   - 인성: 성실성, 책임감, 정직성, 예의바름, 배려심 등
   - 사회성: 교우관계, 리더십, 협력, 의사소통능력, 갈등해결능력 등
   - 특기·적성: 예체능, 진로관련 활동, 특별한 재능이나 관심분야 등
   - 봉사정신: 나눔, 배려, 공동체 의식, 사회참여 등

4. 서술 방식:
   - 관찰 가능한 구체적 사실과 행동 중심으로 기술
   - 정성적 평가와 정량적 사실을 조화롭게 결합
   - 긍정적 변화와 성장 과정을 강조
   - 학생의 개별적 특성과 장점이 드러나도록 개별화하여 작성

5. 'ooo 학생은'과 같은 주어는 쓰지 않을 것. 기본적으로 해당 학생에 대한 세특이므로 쓰지 않는다.

**특수 상황 처리:**
1. 부정적 행동특성 포함 시: 반드시 변화 가능성과 개선 노력을 함께 기술
2. 학교폭력 조치사항: 「학교폭력예방 및 대책에 관한 법률」 제17조에 따른 조치사항을 정확한 일자와 함께 기재
3. 직접 관찰이 불가능한 경우: 그 사유를 명시하여 입력

**기재 시 유의사항:**
- 300-340자 내외의 충분한 분량으로 작성
- 단순한 나열이 아닌 종합적이고 균형잡힌 평가
- 학생의 전인적 성장을 위한 건설적 관점 유지
- 객관적 사실에 기반한 따뜻하고 격려적인 어조"""

DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_K = 40 # For Gemini and Anthropic
DEFAULT_TOP_P = 0.9 # For OpenAI and Anthropic (if top_k is not used)

# Helper: 한글 접미사 제거
def extract_number(value, suffix):
    if value and value.endswith(suffix):
        return value.replace(suffix, "")
    return value

# ------------------- 행발생성 기능 -------------------
st.header("행동특성 및 발달사항")
counseling_allowed_roles = st.session_state.get('board_roles', {}).get("행발생성", []) # Safer access
if user_role not in counseling_allowed_roles:
    st.info("행발생성 기능은 허용된 사용자만 접근할 수 있습니다. 필요 및 오류 시 관리자(혁쌤, complete860127@gmail.com)에게 문의하세요.")
else:
    # 행발생성 시트 열기
    try:
        character_ws = sh.worksheet("character")
        # 기존 시트의 헤더를 확인하고 필요시 업데이트
        try:
            headers = character_ws.row_values(1)
            expected_headers = ["학년", "반", "번호", "이름", "발달사항", "기록시간", "입력자"]
            if headers != expected_headers:
                # 헤더가 다른 경우 새 시트를 만들거나 경고
                st.warning("기존 시트의 구조가 변경되었습니다. 관리자에게 문의하세요.")
        except:
            pass
    except Exception:
        character_ws = sh.add_worksheet(title="character", rows=1000, cols=10)
        character_ws.append_row(["학년", "반", "번호", "이름", "발달사항", "기록시간", "입력자"])
    
    # students 시트 열기
    try:
        students_ws = sh.worksheet("students")
    except Exception:
        st.warning("students 시트를 찾을 수 없습니다. 학생 정보를 자동으로 불러올 수 없습니다.")
        students_ws = None

    # Initialize session state for form fields if not present
    if "llm_dev_text" not in st.session_state:
        st.session_state.llm_dev_text = ""
    
    # students 시트에서 학생 이름 조회하는 함수
    def get_student_name(grade, class_num, student_num):
        if not students_ws:
            return ""
        try:
            all_students = students_ws.get_all_records()
            # 학년, 반, 번호로 학생 찾기
            for student in all_students:
                if (student.get('학년') == grade and 
                    student.get('반') == class_num and 
                    student.get('번호') == student_num):
                    return student.get('이름', '')
            return ""
        except Exception as e:
            st.error(f"학생 정보 조회 중 오류: {e}")
            return ""
    
    # 학생 정보로 기존 발달사항 조회하는 함수
    def get_existing_development(grade, class_num, student_num, user_email):
        try:
            all_records = character_ws.get_all_records()
            # 해당 학생의 기록 중 입력자가 본인인 것만 필터링
            student_records = [
                record for record in all_records
                if record.get('학년') == grade and 
                   record.get('반') == class_num and 
                   record.get('번호') == student_num and 
                   record.get('입력자') == user_email
            ]
            
            if student_records:
                # 기록시간 기준으로 정렬하여 가장 최근 것 반환
                # 기록시간이 문자열로 저장되어 있으므로 datetime으로 변환 시도
                try:
                    sorted_records = sorted(
                        student_records, 
                        key=lambda x: datetime.datetime.strptime(x.get('기록시간', ''), '%Y-%m-%d %H:%M:%S'),
                        reverse=True
                    )
                    return sorted_records[0].get('발달사항', '')
                except:
                    # 시간 파싱 실패시 첫 번째 기록 반환
                    return student_records[0].get('발달사항', '')
            return ""
        except Exception as e:
            st.error(f"기존 발달사항 조회 중 오류: {e}")
            return ""
    
    import re

    def extract_number(value):
        if value:
            m = re.search(r'\d+', value)
            if m:
                return int(m.group())
        return None

    # --- LLM 기반 발달사항 생성 섹션 ---
    st.sidebar.subheader("✨ LLM 기반 발달사항 생성 도우미 ✨")
    
    # API 키 상태 표시
    api_status = {
        "Gemini": "✅ 설정됨" if GEMINI_API_KEY else "❌ 미설정",
        "OpenAI": "✅ 설정됨" if OPENAI_API_KEY else "❌ 미설정", 
        "Anthropic": "✅ 설정됨" if ANTHROPIC_API_KEY else "❌ 미설정"
    }
    
    # st.sidebar.caption("API 키 상태:")
    # for provider, status in api_status.items():
    #     st.sidebar.caption(f"- {provider}: {status}")
    
    # 이전 선택된 공급자 추적
    if "prev_provider" not in st.session_state:
        st.session_state.prev_provider = None
    
    selected_provider = st.sidebar.selectbox(
        "LLM 공급자 선택",
        ["Gemini", "OpenAI", "Anthropic"],
        index=0, # Default to Gemini
        key="llm_provider"
    )
    
    # 공급자가 변경되었을 때만 모델 목록 로드
    if selected_provider != st.session_state.prev_provider:
        st.session_state.prev_provider = selected_provider
        # 캐시 무효화 (선택적)
        # if selected_provider.lower() in st.session_state.cached_models:
        #     del st.session_state.cached_models[selected_provider.lower()]
    
    # 모델 목록 로드 (캐싱됨)
    with st.spinner(f"{selected_provider} 모델 목록 로딩 중..."):
        if selected_provider == "Gemini":
            models_list = list_gemini_models()
        elif selected_provider == "OpenAI":
            models_list = list_openai_models()
        elif selected_provider == "Anthropic":
            models_list = list_anthropic_models()
    
    # 모델 선택
    if models_list and not any("API Key not configured" in str(m) for m in models_list):
        selected_model = st.sidebar.selectbox(
            f"{selected_provider} 모델 선택",
            models_list,
            key="llm_model_id"
        )
    else:
        st.sidebar.error(f"{selected_provider} API 키가 설정되지 않았거나 모델 목록을 가져올 수 없습니다.")
        selected_model = None

    with st.sidebar.expander("System Prompt (LLM 지시사항)", expanded=False):
        llm_system_prompt = st.text_area(
            "System Prompt (LLM 지시사항)",
            value=st.session_state.get("llm_system_prompt", DEFAULT_SYSTEM_PROMPT),
            key="llm_system_prompt",
            height=200
        )

    llm_temperature = st.sidebar.slider(
        "Temperature (창의성)", 
        min_value=0.0, max_value=1.0, 
        value=st.session_state.get("llm_temperature", DEFAULT_TEMPERATURE), 
        step=0.05, 
        key="llm_temperature"
    )

    llm_top_k = None
    llm_top_p = None

    if selected_provider in ["Gemini", "Anthropic"]:
        llm_top_k = st.sidebar.slider(
            "Top-K (다음 단어 선택 후보군)", 
            min_value=1, max_value=100, 
            value=st.session_state.get("llm_top_k", DEFAULT_TOP_K), 
            step=1, 
            key="llm_top_k"
        )
    if selected_provider in ["OpenAI", "Anthropic"]: # Anthropic supports both
        llm_top_p = st.sidebar.slider(
            "Top-P (다음 단어 선택 확률 임계값)", 
            min_value=0.0, max_value=1.0, 
            value=st.session_state.get("llm_top_p", DEFAULT_TOP_P), 
            step=0.01, 
            key="llm_top_p"
        )

    st.markdown("---") # Separator before the form

    # Form for submitting student data
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        grade_raw = st.selectbox("학년", options=["", "1학년", "2학년", "3학년"], key="grade_select")
    with col2:
        class_num_raw = st.selectbox("반", options=["", "1반", "2반", "3반", "4반", "5반", "6반"], key="class_select")
    with col3:
        student_num_raw = st.selectbox("번호", options=[""] + [f"{i}번" for i in range(1, 31)], key="student_num_select")
    
    # 숫자만 추출
    grade = extract_number(grade_raw)
    class_num = extract_number(class_num_raw)
    student_num = extract_number(student_num_raw)

    # 학년, 반, 번호가 모두 선택되면 학생 이름과 발달사항 자동 조회
    if grade and class_num and student_num:
        # 세션 상태에 이전 선택 정보 저장
        current_selection = f"{grade}_{class_num}_{student_num}"
        if "prev_student_selection" not in st.session_state:
            st.session_state.prev_student_selection = ""
        
        # 학생이 변경되었을 때만 조회
        if current_selection != st.session_state.prev_student_selection:
            st.session_state.prev_student_selection = current_selection
            
            # 학생 이름 조회
            student_name = get_student_name(grade, class_num, student_num)
            if student_name:
                st.session_state.student_name = student_name
            else:
                st.session_state.student_name = ""
            
            # 발달사항 조회
            existing_dev = get_existing_development(grade, class_num, student_num, user_email)
            if existing_dev:
                st.session_state.form_development_text = existing_dev
            else:
                st.session_state.form_development_text = ""
    
    # 이름 입력 필드 - 자동으로 채워지거나 수동 입력 가능
    with col4:
        name = st.text_input(
            "이름", 
            value=st.session_state.get("student_name", ""),
            key="name"
        )
    
    # User Prompt를 메인 영역으로 이동 (제목 아래)
    llm_user_prompt = st.text_area(
        "User Prompt (학생 특성 요약)",
        value=st.session_state.get("llm_user_prompt", ""),
        key="llm_user_prompt",
        placeholder="예: 김철수, 1학년. 수학에 재능이 있으나 자신감 부족. 친구관계 원만. 미술 대회 수상.",
        height=100
    )
    
    # LLM 생성 버튼 (메인 영역으로 이동)
    col_gen1, col_gen2, col_gen3 = st.columns([1, 3, 1])
    with col_gen3:
        if st.button("🤖 AI 생성", key="generate_llm_dev", disabled=not selected_model):
            if not selected_model:
                st.error(f"{selected_provider} API 키를 설정해주세요.")
            elif not llm_user_prompt.strip():
                st.warning("User Prompt에 학생 특성을 입력해주세요.")
            else:
                with st.spinner(f"{selected_provider} ({selected_model}) 모델로 생성 중..."):
                    generated_text = generate_llm_text(
                        selected_provider,
                        selected_model,
                        llm_system_prompt,
                        llm_user_prompt,
                        llm_temperature,
                        top_k=llm_top_k if selected_provider in ["Gemini", "Anthropic"] else None,
                        top_p=llm_top_p if selected_provider in ["OpenAI", "Anthropic"] else None
                    )
                    # 생성된 텍스트를 바로 발달사항 필드에 입력
                    st.session_state.form_development_text = generated_text
                    st.success("AI가 발달사항을 생성했습니다.")
                    st.rerun()
    
    # Use session state to allow updating from LLM generation
    if "form_development_text" not in st.session_state:
        st.session_state.form_development_text = ""
    
    # 발달사항 입력 필드
    development = st.text_area(
        "발달사항: AI가 생성한 내용을 수정할 수 있습니다.", 
        value=st.session_state.form_development_text if st.session_state.form_development_text else "기록된 내용이 없음",
        key="form_development_input",
        height=200
    )
    
    with col_gen1:
        if st.button("📥 불러오기", key="load_existing"):
            if grade and class_num and student_num:
                # 학생 이름 다시 조회
                student_name = get_student_name(grade, class_num, student_num)
                if student_name:
                    st.session_state.student_name = student_name
                
                # 발달사항 다시 조회
                existing_dev = get_existing_development(grade, class_num, student_num, user_email)
                if existing_dev:
                    st.session_state.form_development_text = existing_dev
                    st.info("기존 발달사항을 불러왔습니다.")
                else:
                    st.session_state.form_development_text = ""
                    st.info("저장된 발달사항이 없습니다.")
                st.rerun()
            else:
                st.warning("학년, 반, 번호를 모두 선택해주세요.")
    
    # 저장 버튼
    if st.button("💾 저장", type="primary", use_container_width=True):
        # 폼 입력값 가져오기
        development_text = st.session_state.get("form_development_input", "")
        final_name = st.session_state.get("student_name", "")  # 사용자가 수정했을 수 있으므로 입력 필드 값 사용
        
        # "기록된 내용이 없음"인 경우 빈 문자열로 처리
        if development_text == "기록된 내용이 없음":
            development_text = ""
        
        if not grade or not class_num or not student_num:
            st.error("학년, 반, 번호를 모두 선택해주세요.")
        elif not final_name.strip():
            st.error("이름을 입력해주세요.")
        elif not development_text.strip():
            st.error("발달사항 내용을 입력해주세요.")
        else:
            # 현재 시간 (시분초 포함)
            current_time = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
            time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 입력자 이메일
            input_email = user_email if user_email else "Unknown"
            
            # 스프레드시트에 저장
            character_ws.append_row([grade, class_num, student_num, final_name, development_text, time_str, input_email])
            st.success(f"행발생성 정보가 저장되었습니다. (저장시간: {time_str})")
            
            # Clear the form fields after successful submission
            for k in ["llm_dev_text", "form_development_text", "llm_user_prompt", "prev_student_selection", "student_name"]:
                st.session_state.pop(k, None)
            st.rerun()


