import os
import datetime
import streamlit as st
from openai import OpenAI, APIError
from docx import Document
import tempfile
import json
import pandas as pd

# ───── 환경 설정 ─────
try:
    OPENAI_KEY = st.secrets["openai"]["api_key"]
except KeyError:
    OPENAI_KEY = ""

OPENAI_OK = bool(OPENAI_KEY)

client = None
if OPENAI_OK:
    try:
        client = OpenAI(api_key=OPENAI_KEY)
    except Exception as e:
        st.error(f"OpenAI 초기화 실패: {e}")
        OPENAI_OK = False

# ───── 유틸리티 함수들 ─────
def summarize_text(text: str) -> str:
    """기사 내용을 영어로 5-10문장으로 요약"""
    if not OPENAI_OK or client is None:
        return "요약 불가: API 오류"
    if not text.strip():
        return "요약 불가: 입력된 텍스트가 없습니다."
    
    prompt = f"다음 기사 내용을 영어로 다섯 문장 이상, 열문장 이하로 요약해줘:\n\n{text}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"요약 실패: {e}"

def analyze_tone_and_stance(text: str) -> dict:
    """논조 및 입장 분석 - 점수화된 논조 포함"""
    if not OPENAI_OK or client is None:
        return {"error": "API 오류"}
    
    prompt = f"""
    다음 기사의 논조와 입장을 분석해주세요:
    
    1. 논조 분류: positive/neutral/negative 중 하나 선택
    2. 논조 점수: -3(매우 부정적) ~ +3(매우 긍정적) 사이의 정수
    3. 주요 논점 3가지
    4. 사용된 감정적 언어나 편향된 표현 (최대 5개)
    5. 신뢰도 점수 (1-10점)
    6. 객관성 점수 (1-10점)
    
    JSON 형식으로 응답해주세요:
    {{
        "논조분류": "positive/neutral/negative",
        "논조점수": 정수값,
        "주요논점": ["논점1", "논점2", "논점3"],
        "감정적언어": ["예시1", "예시2", "예시3"],
        "신뢰도점수": 정수값,
        "객관성점수": 정수값
    }}
    
    기사: {text}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600
        )
        
        result = response.choices[0].message.content.strip()
        try:
            return json.loads(result)
        except:
            return {"analysis": result}
    except Exception as e:
        return {"error": f"분석 실패: {e}"}

def display_emotional_words(analysis1: dict, analysis2: dict) -> None:
    """감정적 언어 시각화"""
    st.markdown("#### 🔤 감정적 표현 비교")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**기사 1**")
        if "감정적언어" in analysis1 and analysis1["감정적언어"]:
            words = analysis1["감정적언어"]
            word_html = ""
            for i, word in enumerate(words):
                size = 20 - i*2
                color = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57"][i % 5]
                word_html += f'<span style="font-size:{size}px; color:{color}; margin:5px; font-weight:bold;">{word}</span> '
            
            st.markdown(f'<div style="line-height:2;">{word_html}</div>', unsafe_allow_html=True)
        else:
            st.info("감정적 표현이 감지되지 않았습니다.")
    
    with col2:
        st.markdown("**기사 2**")
        if "감정적언어" in analysis2 and analysis2["감정적언어"]:
            words = analysis2["감정적언어"]
            word_html = ""
            for i, word in enumerate(words):
                size = 20 - i*2
                color = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57"][i % 5]
                word_html += f'<span style="font-size:{size}px; color:{color}; margin:5px; font-weight:bold;">{word}</span> '
            
            st.markdown(f'<div style="line-height:2;">{word_html}</div>', unsafe_allow_html=True)
        else:
            st.info("감정적 표현이 감지되지 않았습니다.")

def create_simple_gauge(value: int, title: str) -> None:
    """간단한 게이지 시각화"""
    percentage = ((value + 3) / 6) * 100
    
    if value <= -2:
        color = "#ff4757"
        emoji = "😞"
    elif value <= -1:
        color = "#ffa502"
        emoji = "😕"
    elif value == 0:
        color = "#747d8c"
        emoji = "😐"
    elif value <= 1:
        color = "#2ed573"
        emoji = "🙂"
    else:
        color = "#5352ed"
        emoji = "😊"
    
    gauge_html = f"""
    <div style="text-align: center; margin: 20px; padding: 20px; border-radius: 10px; background-color: #f8f9fa;">
        <h4 style="margin-bottom: 15px;">{title}</h4>
        <div style="font-size: 30px; margin-bottom: 10px;">{emoji}</div>
        <div style="width: 200px; height: 20px; background-color: #e1e8ed; border-radius: 10px; margin: 0 auto; position: relative;">
            <div style="width: {percentage}%; height: 100%; background-color: {color}; border-radius: 10px;"></div>
        </div>
        <p style="margin-top: 10px; font-weight: bold; color: {color}; font-size: 18px;">{value}점</p>
    </div>
    """
    st.markdown(gauge_html, unsafe_allow_html=True)

def create_enhanced_comparison_chart(analysis1: dict, analysis2: dict) -> None:
    """개선된 논조 비교 차트"""
    if "error" in analysis1 or "error" in analysis2:
        st.error("논조 분석 데이터가 부족하여 차트를 생성할 수 없습니다.")
        return
    
    st.markdown("#### 📊 논조 점수 비교")
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_simple_gauge(analysis1.get('논조점수', 0), "기사 1 논조")
    with col2:
        create_simple_gauge(analysis2.get('논조점수', 0), "기사 2 논조")
    
    # 신뢰도 & 객관성 차트
    st.markdown("#### 📈 신뢰도 & 객관성")
    
    trust1 = analysis1.get('신뢰도점수', 5)
    trust2 = analysis2.get('신뢰도점수', 5)
    obj1 = analysis1.get('객관성점수', 5)
    obj2 = analysis2.get('객관성점수', 5)
    
    metrics_df = pd.DataFrame({
        '지표': ['신뢰도', '객관성'],
        '기사1': [trust1, obj1],
        '기사2': [trust2, obj2]
    })
    st.bar_chart(metrics_df.set_index('지표'))

def gpt_feedback(korean_text: str) -> str:
    """한국어 작문에 대한 한국어 피드백 제공"""
    if not OPENAI_OK or client is None:
        return "⚠️ GPT 사용을 위한 OpenAI API 키가 설정되지 않았거나 문제가 있습니다."
    if not korean_text.strip():
        return "⚠️ 피드백할 텍스트가 없습니다."

    prompt = f"""
    당신은 한국인 학습자를 위한 글쓰기 지도교사입니다. 다음 비교 설명문을 평가하고 건설적인 피드백을 한국어로 제공하세요.

    다음 루브릭 기준으로 평가해주세요:

    **1. 내용 논리성 (Content Logic)** 
    - 주장의 명확성, 근거 제시 충분성, 논리적 연결, 문제 상황 분석 깊이

    **2. 구성 체계성 (Organization)**
    - 서론-본론-결론 구조, 문단 간 연결과 흐름, 응집성과 일관성

    **3. 문법·어휘 정확성 (Language Accuracy)**
    - 문법적 정확성, 문장 구조의 다양성, 어휘 선택의 적절성

    각 영역별로 구체적인 피드백과 3-5개의 개선 제안을 제공해주세요.

    평가 대상 글:
    {korean_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 글쓰기 지도교사입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        return response.choices[0].message.content.strip()
    except APIError as e:
        return f"⚠️ OpenAI API 오류: {e}"
    except Exception as e:
        return f"⚠️ GPT 호출 오류: {e}"

def evaluate_writing_rubric(text: str) -> dict:
    """영어 표현 능력 루브릭 평가 - 구체적 기준 적용"""
    if not OPENAI_OK or client is None:
        return {"error": "API 오류"}
    
    prompt = f"""
    다음 영어 텍스트를 구체적인 루브릭 기준으로 평가해주세요.

    **평가 영역 및 기준:**

    **1. 내용 논리성 (Content Logic) - 1~4점**
    - 4점: 주장이 명확하고 일관성 있으며, 근거 제시가 충분하고 논리적 연결이 자연스러움. 다양한 관점을 균형적으로 고려하여 문제 상황에 대한 깊이 있는 분석을 보여줌
    - 3점: 주장이 대체로 명확하고 근거가 적절하나, 일부 논리적 연결에서 미흡한 부분이 있음. 문제 상황에 대한 이해는 있으나 분석의 깊이가 부족함
    - 2점: 주장은 있으나 명확성이 부족하고, 근거 제시가 미흡하며 논리적 흐름에 문제가 있음. 문제 상황에 대한 기본적 이해만 보여줌
    - 1점: 주장이 불분명하고 근거가 부족하며, 논리적 구조가 혼란스러움. 문제 상황에 대한 이해가 부족함

    **2. 구성 체계성 (Organization) - 1~4점**
    - 4점: 서론-본론-결론의 구조가 명확하고, 문단 간 자연스러운 연결과 흐름을 보임. 응집성과 일관성이 뛰어나며 주제문과 뒷받침 문장이 효과적으로 배치됨
    - 3점: 전체적 구조는 적절하나 일부 문단에서 연결이 어색하거나 흐름이 끊어지는 부분이 있음. 응집성과 일관성이 대체로 유지됨
    - 2점: 기본적인 구조는 있으나 문단 구성이 미흡하고 연결어 사용이 부적절함. 일관성이 부족하여 읽기에 어려움이 있음
    - 1점: 구조가 불분명하고 문단 구성이 혼란스러우며, 응집성과 일관성이 현저히 부족함

    **3. 문법·어휘 정확성 (Language Accuracy) - 1~4점**
    - 4점: 문법적 오류가 거의 없고 문장 구조가 다양하며 복잡함. 어휘 선택이 적절하고 다양하며, 학술적 글쓰기에 적합한 어휘를 효과적으로 사용함. 철자법과 구두점 사용이 정확함
    - 3점: 문법적 오류가 적고 문장 구조가 대체로 적절함. 어휘 사용이 적절하나 다양성이 부족하거나 일부 부적절한 선택이 있음. 철자법과 구두점에 경미한 오류가 있음
    - 2점: 문법적 오류가 있으나 의미 전달에 큰 지장은 없음. 어휘 선택이 단조롭고 일부 부적절한 사용이 있음. 철자법과 구두점 오류가 눈에 띔
    - 1점: 문법적 오류가 빈번하여 의미 전달에 지장을 줌. 어휘 사용이 부적절하고 제한적임. 철자법과 구두점 오류가 많아 읽기에 어려움

    JSON 형식으로 응답해주세요:
    {{
        "내용논리성": {{
            "점수": 정수값,
            "근거": "구체적 평가 근거"
        }},
        "구성체계성": {{
            "점수": 정수값, 
            "근거": "구체적 평가 근거"
        }},
        "문법어휘정확성": {{
            "점수": 정수값,
            "근거": "구체적 평가 근거"
        }},
        "총점": "12점 만점 중 X점",
        "종합평가": "전체적인 평가 및 개선 제안"
    }}

    평가 대상 텍스트: {text}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800
        )
        
        result = response.choices[0].message.content.strip()
        try:
            return json.loads(result)
        except:
            return {"evaluation": result}
    except Exception as e:
        return {"error": f"평가 실패: {e}"}

def assess_problem_solving(reflection_text: str) -> dict:
    """문제해결 역량 평가"""
    if not OPENAI_OK or client is None:
        return {"error": "API 오류"}
    
    prompt = f"""
    다음 학습자의 성찰 내용을 바탕으로 문제해결 역량을 평가해주세요:
    
    평가 영역:
    1. 문제이해: 핵심 문제 파악, 요소 분석 능력 (1-5점)
    2. 분석적 사고: 정보 비교, 논리적 판단 능력 (1-5점)
    3. 대안발견 및 기획: 창의적 해결방안, 실행계획 수립 (1-5점)
    4. 의사소통: 명확한 표현, 건설적 토론 능력 (1-5점)
    
    각 영역별 점수와 개선 제안을 JSON 형식으로 제공해주세요.
    
    성찰 내용: {reflection_text}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800
        )
        
        result = response.choices[0].message.content.strip()
        try:
            return json.loads(result)
        except:
            return {"assessment": result}
    except Exception as e:
        return {"error": f"평가 실패: {e}"}

def translate_to_korean(text: str) -> str:
    """영문 텍스트를 한국어로 번역"""
    if not OPENAI_OK or client is None:
        return "번역 불가: API 오류"
    if "요약 실패" in text or "요약 불가" in text:
        return "원본 요약이 없어 번역할 수 없습니다."
    if not text.strip():
        return "번역 불가: 입력된 텍스트가 없습니다."

    prompt = f"다음 영문 텍스트를 자연스러운 한국어로 번역해줘:\n\n{text}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"번역 실패: {e}"

def translate_to_english(text: str) -> str:
    """한국어 텍스트를 영어로 번역"""
    if not OPENAI_OK or client is None:
        return "번역 불가: API 오류"
    if not text.strip():
        return "번역 불가: 입력된 텍스트가 없습니다."

    prompt = f"다음 한국어 텍스트를 자연스러운 영어로 번역해줘:\n\n{text}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"번역 실패: {e}"

def create_docx_content(text: str, analysis_data: dict = None) -> bytes:
    """텍스트를 DOCX 파일로 변환하여 바이트 데이터 반환"""
    doc = Document()
    doc.add_heading('News Comparison Analysis', 0)
    doc.add_paragraph(f"작성일: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}")
    doc.add_paragraph("")
    
    if analysis_data:
        doc.add_heading('분석 요약', level=1)
        for key, value in analysis_data.items():
            doc.add_paragraph(f"{key}: {value}")
        doc.add_paragraph("")
    
    doc.add_heading('작성된 설명문', level=1)
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    
    with tempfile.NamedTemporaryFile() as tmp:
        doc.save(tmp.name)
        tmp.seek(0)
        return tmp.read()

# ───── Streamlit 앱 설정 ─────
st.set_page_config(
    page_title="News Comparison Assistant", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ───── 세션 상태 초기화 ─────
if "stage" not in st.session_state:
    st.session_state.update({
        "stage": "input",
        "article1": "", "article2": "",
        "summary1": "", "summary2": "",
        "summary1_kr": "", "summary2_kr": "",
        "tone_analysis1": {}, "tone_analysis2": {},
        "draft": "", "feedback": "",
        "writing_evaluation": {},
        "problem_solving_score": {},
        "reflection_log": [],
        "final_text": ""
    })

# ───── 메인 타이틀과 경고 메시지 ─────
st.title("📰 News Comparison and Writing Assistant")

if not OPENAI_OK:
    st.warning("⚠️ OpenAI API 키가 설정되지 않았거나 문제가 있습니다. 요약 및 피드백 기능이 비활성화됩니다.")

# ───── 진행 상태 표시 ─────
progress_stages = ["input", "analysis", "draft", "feedback", "final"]
current_stage_idx = progress_stages.index(st.session_state.stage)
progress = (current_stage_idx + 1) / len(progress_stages)

st.progress(progress)
stage_names = ["기사 입력", "논조 분석", "초안 작성", "AI 피드백", "최종 완성"]
st.caption(f"현재 단계: {stage_names[current_stage_idx]} ({current_stage_idx + 1}/{len(progress_stages)})")

# ───── 단계별 화면 구성 ─────

# 1단계: 기사 입력
if st.session_state.stage == "input":
    st.subheader("① 기사 본문 입력")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**기사 1 본문**")
        error_placeholder1 = st.empty()
        article1 = st.text_area(
            "첫 번째 기사의 본문을 입력하세요",
            value=st.session_state.get("article1", ""),
            height=300,
            key="article1_input"
        )
    
    with col2:
        st.markdown("**기사 2 본문**")
        error_placeholder2 = st.empty()
        article2 = st.text_area(
            "두 번째 기사의 본문을 입력하세요",
            value=st.session_state.get("article2", ""),
            height=300,
            key="article2_input"
        )
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        overall_error_placeholder = st.empty()
        if st.button("다음 단계 → (분석 시작)", type="primary", use_container_width=True):
            is_valid = True
            if not article1.strip():
                error_placeholder1.error("기사 1 본문을 입력해주세요.")
                is_valid = False
            else:
                error_placeholder1.empty()

            if not article2.strip():
                error_placeholder2.error("기사 2 본문을 입력해주세요.")
                is_valid = False
            else:
                error_placeholder2.empty()

            if is_valid:
                overall_error_placeholder.empty()
                st.session_state.article1 = article1
                st.session_state.article2 = article2
                st.session_state.stage = "analysis"
                st.rerun()
            else:
                overall_error_placeholder.error("모든 필수 입력 필드를 채워주세요.")

# 2단계: 논조 분석 및 시각화
elif st.session_state.stage == "analysis":
    st.subheader("② 논조 분석 및 요약")
    
    if not st.session_state.get("summary1"):
        with st.spinner("기사 분석 및 요약을 생성하고 있습니다... 잠시만 기다려주세요."):
            st.session_state.summary1 = summarize_text(st.session_state.article1)
            st.session_state.summary2 = summarize_text(st.session_state.article2)
            
            st.session_state.tone_analysis1 = analyze_tone_and_stance(st.session_state.article1)
            st.session_state.tone_analysis2 = analyze_tone_and_stance(st.session_state.article2)
            
            st.session_state.summary1_kr = translate_to_korean(st.session_state.summary1)
            st.session_state.summary2_kr = translate_to_korean(st.session_state.summary2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🗞️ 기사 1 분석")
        with st.expander("요약 (영어/한국어)", expanded=True):
            st.info(f"**[English]**\n{st.session_state.summary1}")
            st.success(f"**[한국어]**\n{st.session_state.summary1_kr}")
        
        with st.expander("논조 분석", expanded=True):
            if "error" not in st.session_state.tone_analysis1:
                analysis = st.session_state.tone_analysis1
                st.markdown(f"**논조**: {analysis.get('논조분류', 'N/A')} ({analysis.get('논조점수', 0)}점)")
                st.markdown(f"**신뢰도**: {analysis.get('신뢰도점수', 0)}/10점")
                st.markdown(f"**객관성**: {analysis.get('객관성점수', 0)}/10점")
                
                if analysis.get('주요논점'):
                    st.markdown("**주요 논점**:")
                    for i, point in enumerate(analysis.get('주요논점', []), 1):
                        st.markdown(f"  {i}. {point}")
            else:
                st.error(st.session_state.tone_analysis1["error"])
    
    with col2:
        st.markdown("#### 🗞️ 기사 2 분석")
        with st.expander("요약 (영어/한국어)", expanded=True):
            st.info(f"**[English]**\n{st.session_state.summary2}")
            st.success(f"**[한국어]**\n{st.session_state.summary2_kr}")
        
        with st.expander("논조 분석", expanded=True):
            if "error" not in st.session_state.tone_analysis2:
                analysis = st.session_state.tone_analysis2
                st.markdown(f"**논조**: {analysis.get('논조분류', 'N/A')} ({analysis.get('논조점수', 0)}점)")
                st.markdown(f"**신뢰도**: {analysis.get('신뢰도점수', 0)}/10점")
                st.markdown(f"**객관성**: {analysis.get('객관성점수', 0)}/10점")
                
                if analysis.get('주요논점'):
                    st.markdown("**주요 논점**:")
                    for i, point in enumerate(analysis.get('주요논점', []), 1):
                        st.markdown(f"  {i}. {point}")
            else:
                st.error(st.session_state.tone_analysis2["error"])
    
    # 논조 시각화
    st.markdown("---")
    create_enhanced_comparison_chart(st.session_state.tone_analysis1, st.session_state.tone_analysis2)
    
    # 감정적 언어 시각화
    st.markdown("---")
    display_emotional_words(st.session_state.tone_analysis1, st.session_state.tone_analysis2)
    
    # 성찰 질문
    st.markdown("---")
    st.markdown("#### 🤔 분석 성찰")
    reflection_error_placeholder = st.empty()
    reflection = st.text_area(
        "두 기사의 차이점과 공통점, 그리고 각각의 논조에 대한 당신의 생각을 적어보세요:",
        height=100,
        key="analysis_reflection"
    )
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "input"
            st.rerun()
    
    with col_btn2:
        if st.button("초안 작성 단계로 →", type="primary", use_container_width=True):
            if not reflection.strip():
                reflection_error_placeholder.error("분석 성찰 내용을 입력해주세요.")
            else:
                reflection_error_placeholder.empty()
                st.session_state.reflection_log.append({
                    "stage": "analysis",
                    "content": reflection,
                    "timestamp": datetime.datetime.now()
                })
                st.session_state.stage = "draft"
                st.rerun()

# 3단계: 초안 작성
elif st.session_state.stage == "draft":
    st.subheader("③ 비교 설명문 초안 작성")

    def paragraph_input_with_guide(title, key, guide_title, guide_lines, summary_text=None, hint_key=None, hint_prompt=None):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(title)
            if key not in st.session_state:
                st.session_state[key] = ""
            
            error_key = f"{key}_error_placeholder"
            if error_key not in st.session_state:
                st.session_state[error_key] = st.empty()
            
            user_input = st.text_area("", key=key, height=160)
        
        with col2:
            st.markdown(f"#### 🧭 {guide_title}")
            for line in guide_lines:
                st.markdown(f"- {line}")
            
            if summary_text:
                st.markdown("#### 🗞️ 관련 기사 요약")
                summary_en = summary_text
                summary_kr_key = "summary1_kr" if summary_en == st.session_state.get("summary1") else "summary2_kr"
                summary_kr = st.session_state.get(summary_kr_key, "번역 없음")
                
                with st.expander("요약문 보기", expanded=True):
                    st.info(f"**[English]**\n{summary_en}")
                    st.success(f"**[한국어]**\n{summary_kr}")

            if hint_key and hint_prompt and OPENAI_OK:
                if f"{hint_key}_hint" not in st.session_state:
                    st.session_state[f"{hint_key}_hint"] = ""
                if st.button(f"✏️ AI 힌트 받기", key=f"{hint_key}_btn"):
                    with st.spinner("AI 힌트를 생성하는 중입니다..."):
                        try:
                            hint_response = client.chat.completions.create(
                                model="gpt-4o",
                                messages=[{"role": "user", "content": hint_prompt}],
                                temperature=0.5,
                                max_tokens=300
                            )
                            st.session_state[f"{hint_key}_hint"] = hint_response.choices[0].message.content.strip()
                        except Exception as e:
                            st.session_state[f"{hint_key}_hint"] = f"❌ 힌트 생성 실패: {e}"
                if st.session_state[f"{hint_key}_hint"]:
                    st.markdown("#### 💡 AI 힌트")
                    st.success(st.session_state[f"{hint_key}_hint"])
        
        return user_input

    intro = paragraph_input_with_guide(
        "1️⃣ 서론", "intro_input", "비교 주제 소개", [
            "비교할 두 기사 간단히 소개",
            "글의 목적, 문제 제기",
            "두 관점 간 차이에 대한 암시"
        ],
        hint_key="intro", hint_prompt="비교 설명문의 서론을 쓰기 위한 문장 구성 힌트를 3개 제시해줘. (한국어)"
    )

    body1 = paragraph_input_with_guide(
        "2️⃣ 본론 - 기사 1 설명", "body1_input", "기사 1 요약", [
            "기사 1의 주장과 근거 요약",
            "자료, 사례, 강조점 기술"
        ],
        summary_text=st.session_state.get("summary1"),
        hint_key="body1", hint_prompt="첫 번째 기사 내용을 요약하는 문단 작성에 쓸 수 있는 문장 예시 3개를 제시해줘. (한국어)"
    )

    body2 = paragraph_input_with_guide(
        "3️⃣ 본론 - 기사 2 설명", "body2_input", "기사 2 요약", [
            "기사 2의 주요 내용 요약",
            "기사 1과 비교했을 때의 특징 언급"
        ],
        summary_text=st.session_state.get("summary2"),
        hint_key="body2", hint_prompt="두 번째 기사 내용을 요약하며 비교하는 문단을 쓰기 위한 문장 예시 3개를 제시해줘. (한국어)"
    )

    compare = paragraph_input_with_guide(
        "4️⃣ 비교 분석", "compare_input", "공통점과 차이점", [
            "기준(관점, 목적 등)을 설정해 비교",
            "논리적으로 유사점·차이점 제시"
        ],
        hint_key="compare", hint_prompt="두 기사 간 공통점과 차이점을 비교하여 분석하는 문단을 위한 문장 구성 힌트를 제시해줘. (한국어)"
    )

    conclusion = paragraph_input_with_guide(
        "5️⃣ 결론", "conclusion_input", "요약 및 의견", [
            "전체 비교 내용 요약",
            "자신의 의견이나 평가 포함"
        ],
        hint_key="conclusion", hint_prompt="비교 설명문 결론에 사용할 수 있는 마무리 문장 3개를 제안해줘. (한국어)"
    )

    st.markdown("---")
    st.markdown("### 🧾 전체 초안 미리보기")

    full_draft = "\n\n".join([
        f"[서론]\n{intro}",
        f"[본론 1 - 기사 1]\n{body1}",
        f"[본론 2 - 기사 2]\n{body2}",
        f"[비교 분석]\n{compare}",
        f"[결론]\n{conclusion}"
    ])

    st.session_state.draft = full_draft

    st.markdown(f"""<div style="background-color:#f9f9f9; padding:15px; border-radius:10px; color:black; font-size:16px;">
<pre style="white-space: pre-wrap; word-wrap: break-word;">{full_draft}</pre>
</div>""", unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "analysis"
            st.rerun()

    with col_btn2:
        overall_draft_error = st.empty()
        if st.button("AI 피드백 받기 →", type="primary", use_container_width=True):
            paragraphs = [
                (intro, "intro_input", "서론"),
                (body1, "body1_input", "본론 1"),
                (body2, "body2_input", "본론 2"),
                (compare, "compare_input", "비교 분석"),
                (conclusion, "conclusion_input", "결론")
            ]
            
            is_valid = True
            for content, key, title in paragraphs:
                error_key = f"{key}_error_placeholder"
                if not content.strip():
                    if error_key in st.session_state:
                        st.session_state[error_key].error(f"{title} 부분을 작성해주세요.")
                    is_valid = False
                else:
                    if error_key in st.session_state:
                        st.session_state[error_key].empty()
            
            if is_valid:
                overall_draft_error.empty()
                st.session_state.stage = "feedback"
                st.rerun()
            else:
                overall_draft_error.error("모든 문단을 작성해주세요.")

# 4단계: AI 피드백 (한국어 전용)
elif st.session_state.stage == "feedback":
    st.subheader("④ AI 피드백 및 루브릭 평가")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**내 초안**")
        st.text_area(
            "작성한 초안",
            value=st.session_state.draft,
            height=400,
            disabled=True,
            key="draft_display"
        )
    
    with col2:
        st.markdown("**AI 피드백 및 평가**")
        
        if "feedback" not in st.session_state or not st.session_state.feedback:
            if OPENAI_OK:
                with st.spinner("AI 피드백 및 평가를 생성하고 있습니다..."):
                    # 한국어 피드백 생성
                    feedback = gpt_feedback(st.session_state.draft)
                    st.session_state.feedback = feedback
                    
                    # 영어 표현 능력 루브릭 평가
                    english_draft = translate_to_english(st.session_state.draft)
                    st.session_state.writing_evaluation = evaluate_writing_rubric(english_draft)
            else:
                st.session_state.feedback = "⚠️ AI 피드백 기능이 비활성화되어 있습니다."
        
        # 탭으로 구분하여 표시
        tab1, tab2 = st.tabs(["🇰🇷 한국어 피드백", "📊 루브릭 평가"])
        
        with tab1:
            st.text_area(
                "AI 피드백",
                value=st.session_state.feedback,
                height=350,
                disabled=True
            )
        
        with tab2:
            st.markdown("#### 📋 영어 표현 능력 평가")
            if st.session_state.writing_evaluation and "error" not in st.session_state.writing_evaluation:
                eval_data = st.session_state.writing_evaluation
                
                # 점수 카드 형태로 표시
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if "내용논리성" in eval_data:
                        logic = eval_data["내용논리성"]
                        st.metric("내용 논리성", f"{logic.get('점수', 0)}/4점")
                        st.caption(logic.get('근거', ''))
                
                with col2:
                    if "구성체계성" in eval_data:
                        org = eval_data["구성체계성"]
                        st.metric("구성 체계성", f"{org.get('점수', 0)}/4점")
                        st.caption(org.get('근거', ''))
                
                with col3:
                    if "문법어휘정확성" in eval_data:
                        lang = eval_data["문법어휘정확성"]
                        st.metric("문법·어휘", f"{lang.get('점수', 0)}/4점")
                        st.caption(lang.get('근거', ''))
                
                if eval_data.get('총점'):
                    st.markdown(f"**총점**: {eval_data['총점']}")
                
                if eval_data.get('종합평가'):
                    st.markdown("**종합 평가**")
                    st.info(eval_data['종합평가'])
            else:
                st.error(st.session_state.writing_evaluation.get("error", "평가 오류") if st.session_state.writing_evaluation else "평가 데이터 없음")
    
    st.markdown("---")
    st.markdown("#### 🤔 피드백 성찰")
    feedback_reflection_error = st.empty()
    feedback_reflection = st.text_area(
        "AI 피드백을 받은 후 느낀 점과 개선하고 싶은 부분을 적어보세요:",
        height=100,
        key="feedback_reflection"
    )
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "draft"
            st.rerun()
    
    with col_btn2:
        if st.button("최종 수정 단계로 →", type="primary", use_container_width=True):
            if not feedback_reflection.strip():
                feedback_reflection_error.error("피드백 성찰 내용을 입력해주세요.")
            else:
                feedback_reflection_error.empty()
                st.session_state.reflection_log.append({
                    "stage": "feedback",
                    "content": feedback_reflection,
                    "timestamp": datetime.datetime.now()
                })
                # 문제해결 역량 평가 수행
                st.session_state.problem_solving_score = assess_problem_solving(feedback_reflection)
                st.session_state.stage = "final"
                st.rerun()

# 5단계: 최종 완성
elif st.session_state.stage == "final":
    st.subheader("⑤ 최종 수정 및 완성")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**최종 수정**")
        if "final_text" not in st.session_state or not st.session_state.final_text:
             st.session_state.final_text = st.session_state.draft
             
        final_text = st.text_area(
            "피드백을 반영하여 최종 수정하세요",
            value=st.session_state.final_text,
            height=400,
            key="final_input"
        )
        
        st.session_state.final_text = final_text
    
    with col2:
        st.markdown("**종합 평가 결과**")
        
        # 문제해결 역량 평가 결과
        if st.session_state.problem_solving_score:
            with st.expander("🧠 문제해결 역량 평가", expanded=True):
                if "error" not in st.session_state.problem_solving_score:
                    eval_data = st.session_state.problem_solving_score
                    
                    # 4개 영역을 2x2 그리드로 배치
                    col1, col2 = st.columns(2)
                    
                    areas = ["문제이해", "분석적사고", "대안발견및기획", "의사소통"]
                    for i, area in enumerate(areas):
                        col = col1 if i % 2 == 0 else col2
                        with col:
                            if area in eval_data:
                                score = eval_data[area].get('점수', 0) if isinstance(eval_data[area], dict) else 0
                                st.metric(area.replace('및', ' & '), f"{score}/5점")
                else:
                    st.error(st.session_state.problem_solving_score["error"])
        
        # 영어 표현 능력 평가 결과
        if st.session_state.writing_evaluation:
            with st.expander("✍️ 영어 표현 능력 평가", expanded=True):
                if "error" not in st.session_state.writing_evaluation:
                    eval_data = st.session_state.writing_evaluation
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if "내용논리성" in eval_data:
                            logic = eval_data["내용논리성"]
                            score = logic.get('점수', 0) if isinstance(logic, dict) else 0
                            st.metric("내용 논리성", f"{score}/4점")
                    
                    with col2:
                        if "구성체계성" in eval_data:
                            org = eval_data["구성체계성"]
                            score = org.get('점수', 0) if isinstance(org, dict) else 0
                            st.metric("구성 체계성", f"{score}/4점")
                    
                    with col3:
                        if "문법어휘정확성" in eval_data:
                            lang = eval_data["문법어휘정확성"]
                            score = lang.get('점수', 0) if isinstance(lang, dict) else 0
                            st.metric("문법·어휘", f"{score}/4점")
                else:
                    st.error(st.session_state.writing_evaluation["error"])
    
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
    
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "feedback"
            st.rerun()

    with col_btn2:
        # 종합 보고서 다운로드
        analysis_summary = {
            "논조분석1": st.session_state.tone_analysis1,
            "논조분석2": st.session_state.tone_analysis2,
            "영어표현평가": st.session_state.writing_evaluation,
            "문제해결평가": st.session_state.problem_solving_score
        }
        docx_data = create_docx_content(final_text, analysis_summary)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_comparison_complete_{timestamp}.docx"
        st.download_button(
            label="📄 종합 보고서 다운로드",
            data=docx_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            disabled=not final_text.strip()
        )

    with col_btn4:
        if st.button("처음부터 다시", use_container_width=True):
            # 세션 상태 초기화
            for key in list(st.session_state.keys()):
                if key != 'stage':
                    st.session_state.pop(key)
            st.session_state.stage = "input"
            st.rerun()
    
    # 완성된 작문 미리보기
    if final_text.strip():
        st.markdown("### 📋 완성된 작문 미리보기")
        st.success(final_text)
        
        # 학습 성찰 로그 표시
        if st.session_state.reflection_log:
            with st.expander("📝 학습 성찰 기록", expanded=False):
                for idx, log in enumerate(st.session_state.reflection_log):
                    st.markdown(f"**{log['stage']} 단계 성찰:**")
                    st.write(log['content'])
                    st.caption(f"작성 시간: {log['timestamp']}")
                    st.markdown("---")

# ───── 사이드바 정보 ─────
with st.sidebar:
    st.markdown("### 📝 사용 방법")
    st.markdown("""
    1. **기사 입력**: 비교할 두 기사의 본문을 입력
    2. **논조 분석**: AI가 각 기사의 논조와 입장을 분석
    3. **초안 작성**: 분석 결과를 참고하여 비교 설명문 작성
    4. **AI 피드백**: 종합적인 피드백과 루브릭 평가 제공
    5. **최종 완성**: 피드백을 반영한 수정 후 종합 보고서 다운로드
    """)
    
    st.markdown("### ⚙️ 설정 상태")
    if OPENAI_OK:
        st.success("✅ OpenAI API 연결됨")
    else:
        st.error("❌ OpenAI API 연결 실패")
    
    st.markdown("### 📊 진행 상황")
    st.markdown(f"현재 단계: **{stage_names[current_stage_idx]}**")
    
    # 진행 상황 체크리스트
    checklist_items = [
        ("기사 입력", bool(st.session_state.get("article1") and st.session_state.get("article2"))),
        ("논조 분석", bool(st.session_state.get("tone_analysis1") and st.session_state.get("tone_analysis2"))),
        ("초안 작성", bool(st.session_state.get("draft"))),
        ("AI 피드백", bool(st.session_state.get("feedback"))),
        ("루브릭 평가", bool(st.session_state.get("writing_evaluation"))),
        ("최종 완성", bool(st.session_state.get("final_text")))
    ]
    
    for item, completed in checklist_items:
        icon = "✅" if completed else "⏳"
        st.markdown(f"{icon} {item}")