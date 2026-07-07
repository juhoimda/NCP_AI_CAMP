import json
import time
import hmac
import hashlib
import base64
import requests
import streamlit as st
import os
# ==========================================
# ⚙️ [백엔드] CLOVA Chatbot 연동 정보
# ==========================================
NCP_CHATBOT_URL = os.environ.get("NCP_CHATBOT_URL", "https://ewzgmo6gyf.apigw.ntruss.com/custom/v1/19241/09e0ce15be9461a29cc72ff3ad60f47b80ec411176a2fd244219c364a6175d89")
NCP_CHATBOT_SECRET = os.environ.get("NCP_CHATBOT_SECRET", "c3JMZkZHV2FRTkVUcUZEclhjdXJCSm1wWkR5WWFvUUE=")


def render_fixed_logo(image_path: str = "logo.png", size_px: int = 48):
    """스크립트와 같은 폴더의 logo.png를 화면 좌상단에 고정 표시 (app_ui.py와 동일한 방식)"""
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
        st.sidebar.warning(f"⚠️ 로고 파일을 찾지 못했습니다: {image_path}")

def make_signature(secret_key: str, request_body: str) -> str:
    """요청 바디를 Secret Key로 HMAC-SHA256 서명 후 Base64 인코딩"""
    signature = hmac.new(
        secret_key.encode("UTF-8"),
        request_body.encode("UTF-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature).decode("UTF-8")
def ask_kb_custom_chatbot(user_query: str) -> str:
    """NCP CLOVA Chatbot Custom API 규격에 맞춘 요청"""
    timestamp = int(time.time() * 1000)
    request_body = {
        "version": "v2",
        "userId": "kb_dash_employee_test",
        "timestamp": timestamp,
        "bubbles": [
            {"type": "text", "data": {"description": user_query}}
        ],
        "event": "send",
    }
    body_str = json.dumps(request_body, ensure_ascii=False)
    signature = make_signature(NCP_CHATBOT_SECRET, body_str)
    headers = {
        "Content-Type": "application/json;UTF-8",
        "X-NCP-CHATBOT_SIGNATURE": signature,
    }
    try:
        response = requests.post(
            NCP_CHATBOT_URL,
            headers=headers,
            data=body_str.encode("UTF-8"),
        )
        response.raise_for_status()
        res_json = response.json()
        if "bubbles" in res_json and len(res_json["bubbles"]) > 0:
            bubble = res_json["bubbles"][0]
            # 응답 구조는 콘솔에서 실제 응답 예시로 한 번 확인해보세요
            return bubble.get("data", {}).get("description", str(bubble))
        return f"⚠️ 응답 구조 확인 필요: {res_json}"
    except Exception as e:
        return f"🚨 [NCP 챗봇 통신 에러]: {e}"
# ==========================================
# 🖥️ Streamlit UI
# ==========================================
st.set_page_config(page_title="Bank Pilot 서류 가이드 챗봇", layout="centered")
render_fixed_logo()
st.title("💚 Bank Pilot 금융 서류 가이드 챗봇")
st.caption("NCP CLOVA Chatbot 연동 화면입니다.")
st.write("---")
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "안녕하세요. 무엇이든 물어보세요!"}
    ]
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
if user_q := st.chat_input("질문을 던져보세요."):
    with st.chat_message("user"):
        st.write(user_q)
    st.session_state["messages"].append({"role": "user", "content": user_q})
    with st.spinner("답변 생성 중..."):
        chatbot_reply = ask_kb_custom_chatbot(user_q)
    with st.chat_message("assistant"):
        st.write(chatbot_reply)
    st.session_state["messages"].append({"role": "assistant", "content": chatbot_reply})