import os
import datetime
import streamlit as st
from openai import OpenAI, APIError
from docx import Document
import tempfile

# ───── 환경 설정 ─────
# Streamlit secrets에서 API 키 가져오기
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
        "article1": "", "article2": "",
        "summary1": "", "summary2": "",
        "draft": "", "feedback": "",
        "final_text": "",
        "stage": "input"
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
            value=st.session_state.article1,
            height=300,
            key="article1_input"
        )
    
    with col2:
        st.markdown("**기사 2 본문**")
        article2 = st.text_area(
            "두 번째 기사의 본문을 입력하세요",
            value=st.session_state.article2,
            height=300,
            key="article2_input"
        )
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        if st.button("다음 단계 → (요약 생성)", type="primary", use_container_width=True):
            if not article1.strip() or not article2.strip():
                st.error("두 기사 본문을 모두 입력해주세요.")
            else:
                st.session_state.article1 = article1
                st.session_state.article2 = article2
                
                # 요약 생성
                with st.spinner("기사 요약을 생성하고 있습니다..."):
                    st.session_state.summary1 = summarize_text(article1)
                    st.session_state.summary2 = summarize_text(article2)
                
                st.session_state.stage = "draft"
                st.rerun()

# 2단계: 초안 작성
elif st.session_state.stage == "draft":
    st.subheader("② 비교 설명문 초안 작성")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**초안 작성 영역**")
        draft = st.text_area(
            "두 기사를 비교하여 설명문을 작성하세요 (한국어)",
            value=st.session_state.draft,
            height=400,
            key="draft_input"
        )
    
    with col2:
        st.markdown("**기사 요약**")
        st.info(f"**[기사 1 요약]**\n{st.session_state.summary1}\n\n**[기사 2 요약]**\n{st.session_state.summary2}")
        
        st.markdown("**Expressions for Comparative Analysis**")
        with st.expander("유용한 표현들 보기"):
            st.markdown("""
**[Similarities]**
- Both A and B show / indicate / suggest ...
- A is similar to B in terms of ...
- In both cases, ...
- A and B share the characteristic of ...
- A, like B, ...

**[Differences]**
- Unlike A, B ...
- A, on the other hand, ...
- In contrast to A, B ...
- While A focuses on ..., B emphasizes ...
- A differs from B in that ...

**[Degree and Extent]**
- A is more/less [adjective] than B.
- B shows a greater tendency to ...
- A is considerably / slightly / significantly different from B.

**[Logical Connection]**
- This suggests that ..., whereas ...
- Although A ..., B ...
- The difference may be attributed to ...

**[Synthesis]**
- Taken together, the articles illustrate ...
- The comparison reveals that ...
- Overall, both texts contribute to ...
            """)
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "input"
            st.rerun()
    
    with col_btn2:
        if st.button("AI 피드백 받기 →", type="primary", use_container_width=True):
            if not draft.strip():
                st.error("초안을 작성해주세요.")
            else:
                st.session_state.draft = draft
                st.session_state.stage = "feedback"
                st.rerun()

# 3단계: AI 피드백
elif st.session_state.stage == "feedback":
    st.subheader("③ GPT-4o 피드백")
    
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
        st.markdown("**AI 피드백 (영어)**")
        
        if not st.session_state.feedback:
            if OPENAI_OK:
                with st.spinner("AI 피드백을 생성하고 있습니다..."):
                    feedback = gpt_feedback(st.session_state.draft)
                    st.session_state.feedback = feedback
            else:
                st.session_state.feedback = "⚠️ GPT 피드백 기능이 비활성화되어 있습니다."
        
        st.text_area(
            "GPT-4o 피드백",
            value=st.session_state.feedback,
            height=400,
            disabled=True,
            key="feedback_display"
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
        final_text = st.text_area(
            "피드백을 반영하여 최종 수정하세요",
            value=st.session_state.final_text or st.session_state.draft,
            height=400,
            key="final_input"
        )
        
        st.session_state.final_text = final_text
    
    with col2:
        st.markdown("**AI 피드백 참고**")
        st.info(st.session_state.feedback)
    
    st.markdown("---")
    
    # 버튼들
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        if st.button("← 이전 단계", use_container_width=True):
            st.session_state.stage = "feedback"
            st.rerun()
    
    with col_btn2:
        if st.button("DOCX 다운로드", use_container_width=True):
            if final_text.strip():
                try:
                    docx_data = create_docx_content(final_text)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"news_comparison_{timestamp}.docx"
                    
                    st.download_button(
                        label="📥 DOCX 파일 다운로드",
                        data=docx_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"파일 생성 중 오류: {e}")
            else:
                st.error("저장할 내용이 없습니다.")
    
    with col_btn3:
        if st.button("처음부터 다시", use_container_width=True):
            # 세션 상태 초기화
            for key in ["article1", "article2", "summary1", "summary2", "draft", "feedback", "final_text"]:
                st.session_state[key] = ""
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
    2. **초안 작성**: AI가 생성한 요약을 참고하여 비교 설명문 작성
    3. **AI 피드백**: GPT-4o가 작문에 대한 상세한 피드백 제공
    4. **최종 완성**: 피드백을 반영하여 수정 후 DOCX 파일로 다운로드
    """)
    
    st.markdown("### ⚙️ 설정 상태")
    if OPENAI_OK:
        st.success("✅ OpenAI API 연결됨")
    else:
        st.error("❌ OpenAI API 연결 실패")
    
    st.markdown("### 📊 진행 상황")
    st.markdown(f"현재 단계: **{stage_names[current_stage_idx]}**")
    
    if st.session_state.article1:
        st.markdown("✅ 기사 1 입력 완료")
    if st.session_state.article2:
        st.markdown("✅ 기사 2 입력 완료")
    if st.session_state.draft:
        st.markdown("✅ 초안 작성 완료")
    if st.session_state.feedback:
        st.markdown("✅ AI 피드백 완료")
    if st.session_state.final_text:
        st.markdown("✅ 최종 수정 완료")