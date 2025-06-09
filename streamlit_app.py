import os
import datetime
import streamlit as st
from openai import OpenAI, APIError
from docx import Document
import tempfile

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

def gpt_feedback(korean_text: str) -> str:
    """한국어 작문에 대한 영어 피드백 제공"""
    if not OPENAI_OK or client is None:
        return "⚠️ GPT 사용을 위한 OpenAI API 키가 설정되지 않았거나 문제가 있습니다."
    if not korean_text.strip():
        return "⚠️ 피드백할 텍스트가 없습니다."

    prompt = (
        "You are an academic writing coach. Evaluate the following comparative explanatory paragraph (in Korean) "
        "and provide constructive feedback in English. Focus on the following aspects:\n\n"
        "1. Content: Clarity of the main idea, richness of supporting details, and logical development.\n"
        "2. Organization: Coherence of structure, effectiveness of introductions and conclusions, and use of transitions.\n"
        "3. Vocabulary: Appropriateness and variety of word choice.\n"
        "4. Language Use: Grammatical accuracy and sentence structure.\n"
        "5. Mechanics: Correctness of spelling, punctuation, and capitalization.\n\n"
        "Provide 3–5 specific improvement suggestions.\n\n"
        "Here is the paragraph:\n" + korean_text
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an academic writing coach."},
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

def create_docx_content(text: str) -> bytes:
    """텍스트를 DOCX 파일로 변환하여 바이트 데이터 반환"""
    doc = Document()
    doc.add_heading('News Comparison Analysis', 0)
    doc.add_paragraph(f"작성일: {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}")
    doc.add_paragraph("")
    
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    
    # 임시 파일에 저장하고 바이트 데이터 반환
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
        "draft": "", "feedback": "", "feedback_kr": "",
        "final_text": ""
    })

# ───── 메인 타이틀과 경고 메시지 ─────
st.title("📰 News Comparison and Writing Assistant")

if not OPENAI_OK:
    st.warning("⚠️ OpenAI API 키가 설정되지 않았거나 문제가 있습니다. 요약 및 피드백 기능이 비활성화됩니다.")

# ───── 진행 상태 표시 ─────
progress_stages = ["input", "draft", "feedback", "final"]
current_stage_idx = progress_stages.index(st.session_state.stage)
progress = (current_stage_idx + 1) / len(progress_stages)

st.progress(progress)
stage_names = ["기사 입력", "초안 작성", "AI 피드백", "최종 완성"]
st.caption(f"현재 단계: {stage_names[current_stage_idx]} ({current_stage_idx + 1}/{len(progress_stages)})")

# ───── 단계별 화면 구성 ─────

# 1단계: 기사 입력
if st.session_state.stage == "input":
    st.subheader("① 기사 본문 입력")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**기사 1 본문**")
        article1 = st.text_area(
            "첫 번째 기사의 본문을 입력하세요",
            value=st.session_state.get("article1", ""),
            height=300,
            key="article1_input"
        )
    
    with col2:
        st.markdown("**기사 2 본문**")
        article2 = st.text_area(
            "두 번째 기사의 본문을 입력하세요",
            value=st.session_state.get("article2", ""),
            height=300,
            key="article2_input"
        )
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        if st.button("다음 단계 → (요약 및 번역 생성)", type="primary", use_container_width=True):
            if not article1.strip() or not article2.strip():
                st.error("두 기사 본문을 모두 입력해주세요.")
            else:
                st.session_state.article1 = article1
                st.session_state.article2 = article2
                
                # 요약 및 번역 생성
                with st.spinner("기사 요약 및 번역을 생성하고 있습니다... 잠시만 기다려주세요."):
                    # 영어 요약 생성
                    st.session_state.summary1 = summarize_text(article1)
                    st.session_state.summary2 = summarize_text(article2)
                    
                    # 한국어 번역 생성
                    st.session_state.summary1_kr = translate_to_korean(st.session_state.summary1)
                    st.session_state.summary2_kr = translate_to_korean(st.session_state.summary2)
                
                st.session_state.stage = "draft"
                st.rerun()

# 2단계: 초안 작성
elif st.session_state.stage == "draft":
    st.subheader("② 비교 설명문 초안 작성 (문단별 구성 + AI 힌트 지원)")

    def paragraph_input_with_guide(title, key, guide_title, guide_lines, summary_text=None, hint_key=None, hint_prompt=None):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(title)
            # st.session_state에 해당 키가 없으면 초기화
            if key not in st.session_state:
                st.session_state[key] = ""
            user_input = st.text_area("", key=key, height=160)
        
        with col2:
            st.markdown(f"#### 🧭 {guide_title}")
            for line in guide_lines:
                st.markdown(f"- {line}")
            
            # 관련 기사 요약 (영문/한글) 표시
            if summary_text:
                st.markdown("#### 🗞️ 관련 기사 요약 (영문/한글)")
                summary_en = summary_text
                # summary_text가 summary1인지 summary2인지 확인하여 해당하는 한글 번역본을 찾음
                summary_kr_key = "summary1_kr" if summary_en == st.session_state.get("summary1") else "summary2_kr"
                summary_kr = st.session_state.get(summary_kr_key, "번역 없음")
                
                with st.expander("요약문 보기", expanded=True):
                    st.info(f"**[English]**\n{summary_en}")
                    st.success(f"**[한국어]**\n{summary_kr}")

            # AI 힌트 버튼
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

    # 문단 구성
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
            st.session_state.stage = "input"
            st.rerun()

    with col_btn2:
        if st.button("AI 피드백 받기 →", type="primary", use_container_width=True):
            if not all([intro.strip(), body1.strip(), body2.strip(), compare.strip(), conclusion.strip()]):
                st.error("모든 문단을 작성해주세요.")
            else:
                st.session_state.stage = "feedback"
                st.rerun()

# 3단계: AI 피드백 (한국어 번역 추가)
elif st.session_state.stage == "feedback":
    st.subheader("③ GPT-4o 피드백 (영어 + 한국어 번역)")
    
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
        st.markdown("**AI 피드백**")
        
        # 영어 피드백 생성
        if "feedback" not in st.session_state or not st.session_state.feedback:
            if OPENAI_OK:
                with st.spinner("AI 피드백을 생성하고 있습니다..."):
                    feedback = gpt_feedback(st.session_state.draft)
                    st.session_state.feedback = feedback
                    
                    # 피드백 한국어 번역도 함께 생성
                    if feedback and "⚠️" not in feedback:
                        with st.spinner("피드백을 한국어로 번역하고 있습니다..."):
                            st.session_state.feedback_kr = translate_to_korean(feedback)
                    else:
                        st.session_state.feedback_kr = "번역 불가"
            else:
                st.session_state.feedback = "⚠️ GPT 피드백 기능이 비활성화되어 있습니다."
                st.session_state.feedback_kr = "⚠️ GPT 피드백 기능이 비활성화되어 있습니다."
        
        # 탭으로 영어/한국어 피드백 표시
        tab1, tab2 = st.tabs(["🇺🇸 English", "🇰🇷 한국어"])
        
        with tab1:
            st.text_area(
                "GPT-4o 피드백 (영어)",
                value=st.session_state.feedback,
                height=350,
                disabled=True,
                key="feedback_en_display"
            )
        
        with tab2:
            st.text_area(
                "GPT-4o 피드백 (한국어)",
                value=st.session_state.get("feedback_kr", "번역 중..."),
                height=350,
                disabled=True,
                key="feedback_kr_display"
            )
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "draft"
            st.rerun()
    
    with col_btn2:
        if st.button("최종 수정 단계로 →", type="primary", use_container_width=True):
            st.session_state.stage = "final"
            st.rerun()

# 4단계: 최종 완성
elif st.session_state.stage == "final":
    st.subheader("④ 최종 수정 및 완성")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**최종 수정**")
        # final_text가 비어있으면 draft 내용으로 초기화
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
        st.markdown("**AI 피드백 참고**")
        
        # 탭으로 영어/한국어 피드백 표시
        tab1, tab2 = st.tabs(["🇺🇸 English", "🇰🇷 한국어"])
        
        with tab1:
            st.info(st.session_state.feedback)
        
        with tab2:
            st.info(st.session_state.get("feedback_kr", "번역 없음"))
    
    st.markdown("---")
    
    # 버튼들
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 1])
    
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "feedback"
            st.rerun()

    with col_btn2:
        # 다운로드 버튼
        docx_data = create_docx_content(final_text)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_comparison_{timestamp}.docx"
        st.download_button(
            label="DOCX 다운로드",
            data=docx_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            disabled=not final_text.strip()
        )

    with col_btn4:
        if st.button("처음부터 다시", use_container_width=True):
            # 세션 상태 초기화
            keys_to_reset = [
                "article1", "article2", "summary1", "summary2", 
                "summary1_kr", "summary2_kr",
                "draft", "feedback", "feedback_kr", "final_text", "stage",
                "intro_input", "body1_input", "body2_input", 
                "compare_input", "conclusion_input",
                "intro_hint", "body1_hint", "body2_hint", 
                "compare_hint", "conclusion_hint"
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    st.session_state.pop(key)
            st.session_state.stage = "input"
            st.rerun()
    
    # 완성된 작문 미리보기
    if final_text.strip():
        st.markdown("### 📋 완성된 작문 미리보기")
        st.success(final_text)

# ───── 사이드바 정보 ─────
with st.sidebar:
    st.markdown("### 📝 사용 방법")
    st.markdown("""
    1. **기사 입력**: 비교할 두 기사의 본문을 입력
    2. **초안 작성**: AI가 생성한 요약/번역을 참고하여 문단별로 비교 설명문 작성 (AI 힌트 지원)
    3. **AI 피드백**: GPT-4o가 작문에 대한 상세한 피드백 제공 (영어 + 한국어 번역)
    4. **최종 완성**: 피드백을 반영하여 수정 후 DOCX 파일로 다운로드
    """)
    
    st.markdown("### ⚙️ 설정 상태")
    if OPENAI_OK:
        st.success("✅ OpenAI API 연결됨")
    else:
        st.error("❌ OpenAI API 연결 실패")
    
    st.markdown("### 📊 진행 상황")
    st.markdown(f"현재 단계: **{stage_names[current_stage_idx]}**")
    
    if st.session_state.get("article1") and st.session_state.get("article2"):
        st.markdown("✅ 기사 입력 완료")
    if st.session_state.get("summary1_kr") and st.session_state.get("summary2_kr"):
        st.markdown("✅ 요약/번역 완료")
    if st.session_state.get("draft"):
        st.markdown("✅ 초안 작성 완료")
    if st.session_state.get("feedback"):
        st.markdown("✅ AI 피드백 완료")
    if st.session_state.get("feedback_kr"):
        st.markdown("✅ 피드백 번역 완료")
    if st.session_state.get("final_text"):
        st.markdown("✅ 최종 수정 완료")