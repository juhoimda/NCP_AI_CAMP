# app_ui.py
import streamlit as st
import requests
from PIL import Image
import os

BACKEND_API_URL = "http://127.0.0.1:8000/api/v1/audit"

# chat.py를 별도 Streamlit 앱으로 실행한 주소.
# 예: streamlit run chat.py --server.port 8502
# 실제 서버 IP/포트가 다르면 이 값만 바꿔주면 됩니다.
CHATBOT_APP_URL = os.environ.get("CHATBOT_APP_URL", "http://127.0.0.1:8502")

st.set_page_config(page_title="Bank Pilot | AI 서류 심사 지원 인프라", layout="wide")

# ==========================================
# 🖼️ 좌측 상단 고정 로고
# 스크립트와 같은 폴더에 있는 logo.png를 읽어 화면 좌상단에 고정 표시
# ==========================================
import base64


def render_fixed_logo(image_path: str = "logo.png", size_px: int = 48):
    # cwd(실행 위치)와 무관하게, 이 스크립트 파일과 같은 폴더를 기준으로 경로를 계산
    if not os.path.isabs(image_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, image_path)
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f"""
            <style>
            .kb-logo-fixed {{
                position: fixed;
                top: 14px;
                left: 18px;
                z-index: 9999;
            }}
            .kb-logo-fixed img {{
                height: {size_px}px;
                width: auto;
            }}
            </style>
            <div class="kb-logo-fixed">
                <img src="data:image/png;base64,{encoded}" alt="Bank Pilot logo">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        # 로고 파일을 못 찾은 경우, 화면은 안 깨지되 사이드바에 경로를 남겨 디버깅 가능하게 함
        st.sidebar.warning(f"⚠️ 로고 파일을 찾지 못했습니다: {image_path}")


render_fixed_logo()

# ==========================================
# 🎨 전역 스타일
# - primary 버튼(선택된 카테고리/현재 단계 등)을 연두색으로 강제 적용
#   (.streamlit/config.toml의 primaryColor가 적용 안 되는 환경에서도 항상 동작하도록
#    button[kind="primary"] 속성을 직접 타겟팅)
# - 오른쪽 하단 플로팅 챗봇 버튼
# ==========================================
st.markdown(
    f"""
    <style>
    button[kind="primary"] {{
        background-color: #8BC34A !important;
        border-color: #8BC34A !important;
        color: #FFFFFF !important;
    }}
    button[kind="primary"]:hover {{
        background-color: #7CB342 !important;
        border-color: #7CB342 !important;
        color: #FFFFFF !important;
    }}

    .kb-chatbot-fab {{
        position: fixed;
        bottom: 28px;
        right: 28px;
        z-index: 9999;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #8BC34A;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        text-decoration: none;
        font-size: 28px;
        transition: transform 0.15s ease;
    }}
    .kb-chatbot-fab:hover {{
        transform: scale(1.08);
        text-decoration: none;
    }}
    </style>
    <a href="{CHATBOT_APP_URL}" target="_blank" class="kb-chatbot-fab" title="Bank Pilot 내부 서류 가이드 챗봇 열기">
        💬
    </a>
    """,
    unsafe_allow_html=True,
)

# 헤더 영역
st.title("Bank Pilot AI 서류 심사 인프라 (실전 창구 모드)")
st.caption("독립형 FastAPI 백엔드 연동 심사 플랫폼 | Bank Pilot 전용 대시보드")
st.divider()

# 세션 상태 초기화 (현재 상태, 활성화된 카테고리, 진행 단계 저장)
if "active_category" not in st.session_state:
    st.session_state.active_category = "미성년자 금융거래 / 계좌개설"
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

# 실전 업무를 반영한 12대 핵심 금융 카테고리 정의
categories = [
    # [수신 및 가계금융 영역]
    "미성년자 금융거래 / 계좌개설", "개인 신용대출 심사", "전세자금대출 / 주택담보", "법인 금융거래 / 기업 계좌",
    # [기업 및 소상공인 영역]
    "소상공인 대환대출 / 보증서", "시설자금 / 운전자금 대출", "외환 거래 / 수출입 금융", "신용보증기금 연계 유동성",
    # [자산 관리 및 기타 영역]
    "상속 / 증여 금융거래 심사", "신파이낸스 소득증빙 검증", "부동산 담보 평가 연동", "가상자산 / 특정금융거래 확인"
]

# 상단에 진행 단계를 시각화하는 안내 바
step_names = [
    "🎯 1. 업무 카테고리 지정",
    "📂 2. 구비 서류 가이드 & 업로드",
    "🔍 3. 규정집 1:1 정밀 비교 대조",
    "📊 4. 최종 심사 결과 보고서"
]


def go_to_step(step_idx: int):
    st.session_state.current_step = step_idx
    st.rerun()


# ==========================================
# 상단 네비게이션 바 (st.tabs 대신 버튼 기반으로 구현)
# → 코드에서 직접 단계를 전환할 수 있어야 "다음 단계로 이동" 버튼이 동작함
# ==========================================
nav_cols = st.columns(4)
for idx, name in enumerate(step_names):
    with nav_cols[idx]:
        is_current = (st.session_state.current_step == idx)
        if st.button(name, use_container_width=True,
                     type="primary" if is_current else "secondary",
                     key=f"nav_btn_{idx}"):
            go_to_step(idx)
st.divider()

current_step = st.session_state.current_step
selected_category = st.session_state.active_category

# ==========================================
# [1단계 화면] 실전형 12대 금융 서비스 버튼 배치
# ==========================================
if current_step == 0:
    st.subheader("🏢 심사 대상 금융 서비스 업무 유형을 선택해 주세요.")
    st.write("은행 창구 및 비대면 채널에서 접수된 업무 카테고리를 터치하면 전용 RAG 심사 파이프라인이 매칭됩니다.")
    st.write("")

    # 12개 카테고리를 4열 x 3행의 조밀하고 전문적인 금융 단말기 형태로 배치
    cols = st.columns(4)

    for idx, cat_name in enumerate(categories):
        col_target = cols[idx % 4]
        with col_target:
            # 선택된 카테고리는 연두색(primary) 버튼으로 강조
            is_active = (st.session_state.active_category == cat_name)
            btn_type = "primary" if is_active else "secondary"

            if st.button(cat_name, use_container_width=True, type=btn_type, key=f"cat_btn_{idx}"):
                st.session_state.active_category = cat_name
                st.rerun()

    st.divider()
    st.info(f"🚀 **[엔진 활성화 수신]** 현재 창구 심사 모드가 **'{st.session_state.active_category}'** 라우팅 본선으로 지정되었습니다.")

    # ➔ 다음 단계 이동 버튼
    st.write("")
    col_space, col_next = st.columns([5, 1])
    with col_next:
        if st.button("다음 단계 →", use_container_width=True, type="primary", key="next_step_1"):
            go_to_step(1)

# ==========================================
# [2단계 화면] 필수 서류 체크리스트 및 업로드
# ==========================================
elif current_step == 1:
    st.subheader(f"📋 '{selected_category}' 업무 필수 구비 서류 마스터 지침")

    # 12개 업무 유형에 따른 맞춤형 서류 가이드 동적 분기
    if "미성년자" in selected_category:
        st.markdown("* 🪪 **법정대리인(부모) 실명확인증표** (주민등록증/운전면허증)  \n* 📜 **가족관계확인서류** (가족관계증명서 혹은 주민등록등본 - *발급 3개월 이내*)  \n* 📑 **자녀 명의 기본증명서** (*반드시 '상세' 또는 '특정' 지침 발급본만 유효*)")
    elif "신용대출" in selected_category:
        st.markdown("* 🪪 **본인 실명확인증표** \n* 🏢 **재직증명원** 및 고용보험 자격이력내역서  \n* 💰 **근로소득원천징수영수증** (최근 2개년 발급분)")
    elif "전세자금" in selected_category:
        st.markdown("* 🏠 **확정일자부 임대차계약서 원본** \n* 📜 **임차주택 등기사항전부증명서**(말소사항 포함)  \n* 💰 **계약금 5% 이상 납입 영수증**")
    elif "법인" in selected_category:
        st.markdown("* 🏢 **법인등기사항전부증명서** (발급 3개월 이내)  \n* 📜 **법인인감증명서 및 사업자등록증명원** \n* 🪪 **대표자 실명확인증표** (대리인 내점 시 위임장 및 인감날인 필수)")
    else:
        st.markdown("* 🪪 **본인(또는 대리인) 실명확인확인 서류** \n* 📂 **해당 거래 목적 및 정당성 증빙용 금융 심사 마스터 원본 파일**")

    st.divider()
    st.subheader("📤 고객 제출 이미지 스캔 및 업로드 인터페이스")
    uploaded_files = st.file_uploader(
        "가족관계증명서, 신분증, 계약서 등 검증 파일 로드 (*.png, *.jpg, *.jpeg) — 여러 장 동시 업로드 가능",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        file_names_key = tuple(f.name for f in uploaded_files)
        # 다른 단계(3, 4)에서도 업로드 여부를 확인할 수 있도록 세션에 저장
        st.session_state.uploaded_files_cache = uploaded_files

        st.success(f"✅ {len(uploaded_files)}개 파일이 정상적으로 금융 전산 캐시에 버퍼링되었습니다.")

        preview_cols = st.columns(min(len(uploaded_files), 4))
        for i, uf in enumerate(uploaded_files):
            with preview_cols[i % 4]:
                st.image(Image.open(uf), caption=uf.name, width=200)

        # 백엔드 FastAPI 서버와 API 실시간 동기화 호출 (다중 파일 전송)
        if "backend_response" not in st.session_state or st.session_state.get("last_uploaded") != file_names_key:
            with st.spinner("🚀 독립형 백엔드 심사 API 서버 통신 중... (다중 서류 OCR 및 체크리스트 추론 연산 가동)"):
                try:
                    files_payload = [
                        ("files", (uf.name, uf.getvalue(), uf.type)) for uf in uploaded_files
                    ]
                    data = {"category": selected_category}
                    res = requests.post(BACKEND_API_URL, data=data, files=files_payload, timeout=60)

                    if res.status_code == 200:
                        st.session_state.backend_response = res.json()
                        st.session_state.last_uploaded = file_names_key
                    else:
                        st.error(f"백엔드 코어 서버 에러 응답: {res.text}")
                except Exception as ex:
                    st.error(f"백엔드 서버와 통신할 수 없습니다. app.py 가동 상태를 확인하세요. 에러: {ex}")

        st.write("")
        col_space, col_next = st.columns([5, 1])
        with col_next:
            if "backend_response" in st.session_state:
                if st.button("다음 단계 →", use_container_width=True, type="primary", key="next_step_2"):
                    go_to_step(2)
            else:
                st.button("다음 단계 →", use_container_width=True, type="secondary", key="next_step_2_disabled", disabled=True)

# ==========================================
# [3단계 화면] 규정집 대조 모니터링
# ==========================================
elif current_step == 2:
    st.subheader("🔍 로컬 벡터 DB 금융 규정집과 추출 문자열 실시간 1:1 교차 대조")
    if st.session_state.get("uploaded_files_cache") and "backend_response" in st.session_state:
        res_data = st.session_state.backend_response

        st.markdown("#### ✅ [필수 구비서류 등록 체크리스트]")
        st.caption("업로드된 서류의 OCR 결과를 필수서류 목록과 대조한 확정 판정 결과입니다.")
        checklist = res_data.get("doc_checklist", [])
        if checklist:
            for item in checklist:
                status = item.get("status", "확인불가")
                if status == "등록됨":
                    icon = "✅"
                    detail = f" — 매칭 파일: `{item.get('matched_filename')}`" if item.get("matched_filename") else ""
                elif status == "미등록":
                    icon = "❌"
                    detail = ""
                else:
                    icon = "⚠️"
                    detail = " — AI 판정 실패, 행원 육안 확인 필요"
                st.markdown(f"{icon} **{item['required_doc']}** — {status}{detail}")
        else:
            st.warning("체크리스트 판정 결과를 불러오지 못했습니다.")

        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📝 [A] 업로드 파일별 OCR 추출 피드")
            if res_data.get("is_ocr_fallback"):
                st.warning("⚠️ 안내: 일부 파일은 시스템 우회 작동으로 시연용 가상 서류 데이터 셋이 마운트되었습니다.")
            for pf in res_data.get("per_file_ocr", []):
                with st.expander(f"📎 {pf['filename']}", expanded=True):
                    st.info(pf["ocr_text"])
                    if pf.get("is_ocr_fallback") and pf.get("debug_error"):
                        st.caption(f"🛠️ 디버그: 실제 OCR 실패 원인 → {pf['debug_error']}")

        with col2:
            st.markdown("#### 📖 [B] 매칭된 은행 내부 지침 마스터 북")
            st.caption(f"규정집 인덱스 번호: `{res_data['matched_policy_id']}`")
            st.code(res_data["matched_policy_doc"], language="text")

        st.write("")
        col_space, col_next = st.columns([5, 1])
        with col_next:
            if st.button("다음 단계 →", use_container_width=True, type="primary", key="next_step_3"):
                go_to_step(3)
    else:
        st.info("💡 2번 단계에서 서류 파일 업로드가 완료되면 실시간 1:1 대조 피드가 수신됩니다.")
        st.write("")
        if st.button("← 2단계로 돌아가기", key="back_to_step_2"):
            go_to_step(1)

# ==========================================
# [4단계 화면] AI 종합 심사 결과 보고서 출력
# ==========================================
elif current_step == 3:
    st.subheader("🎯 하이퍼클로바X Reasoning 엔진 기반 최종 심사 리포트")
    if st.session_state.get("uploaded_files_cache") and "backend_response" in st.session_state:
        res_data = st.session_state.backend_response
        final_report = res_data["final_report"]

        # 마크다운 리포트 출력
        st.markdown(final_report)

        # 체크리스트로부터 프로그램이 이미 확정 계산한 all_docs_registered를 그대로 사용
        if res_data.get("all_docs_registered"):
            st.success("🎉 심사 결과: 모든 필수서류 등록 확인 및 규정 조건 검증 통과. 정상 승인이 가능합니다.")
            st.balloons()
        else:
            missing = res_data.get("missing_docs", [])
            missing_text = ", ".join(missing) if missing else "확인 필요"
            st.error(f"🚨 심사 결과: 필수서류 미비로 접수 처리가 불가능합니다. (미등록: {missing_text}) 보완 문자를 발송하십시오.")

        st.write("")
        if st.button("🔄 새 심사 시작하기", type="secondary", key="restart_flow"):
            for k in ["backend_response", "last_uploaded", "uploaded_files_cache"]:
                st.session_state.pop(k, None)
            go_to_step(0)
    else:
        st.info("💡 이전 단계 서류 전처리가 완료되지 않았습니다. 2번 단계에서 서류 이미지를 접수해 주십시오.")
        st.write("")
        if st.button("← 2단계로 돌아가기", key="back_to_step_2_from_4"):
            go_to_step(1)