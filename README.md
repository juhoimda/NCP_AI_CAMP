# 🏦 BANK PILOT

> AI 기반 스마트 금융 혁신 심사 자동화 가이드 솔루션

---


BANK PILOT은 금융 현장에서 반복적으로 수행되는
**서류 확인, 규정 검색, 누락 판단 및 고객 안내 업무를 AI로 지원하는 서비스**입니다.



금융 서류를 업로드하면 **OCR → RAG → AI Chatbot** 과정을 통해 문서를 분석하고,
금융기관의 내부 지침을 기반으로 필요한 서류와 누락 사항을 확인합니다.


<img width="1470" height="956" alt="스크린샷 2026-08-13 오후 4 22 26" src="https://github.com/user-attachments/assets/9a12356c-0d98-4cdb-8527-ac07b0e89c30" />
<img width="1470" height="956" alt="스크린샷 2026-08-13 오후 4 28 36" src="https://github.com/user-attachments/assets/8c87efd4-7189-461f-8753-24e4d3cf1d0f" />


---

## 💡 주요 기능

### 1. 금융 서류 OCR 인식
- 업로드된 금융 서류의 텍스트 자동 추출
- 서류명 및 주요 정보 인식
- NAVER Cloud OCR 활용

### 2. 필요 서류 충족 여부 판단
- 제출된 서류와 금융 내부 지침 비교
- RAG 기반 관련 규정 검색
- 제출 완료 / 누락 / 보완 필요 여부 판단
- 추가 제출 서류 및 보완 사항 안내

### 3. 내부 지침 기반 AI 챗봇
- 금융 업무 관련 자연어 질의
- 내부 금융 지침 및 Q&A 기반 답변
- NAVER HyperCLOVA X 활용

---

## ⚙️ 서비스 흐름

사용자가 금융 서류를 업로드하면 다음 과정으로 분석합니다.

```text
금융 서류 업로드
        ↓
NAVER Cloud OCR
        ↓
텍스트 및 주요 정보 추출
        ↓
금융 내부 지침 RAG 검색
        ↓
HyperCLOVA X
        ↓
서류 충족 여부 및 AI 답변 제공
````

---

## 🛠 Tech Stack

**AI**

* NAVER HyperCLOVA X
* CLOVA Studio
* RAG (Retrieval-Augmented Generation)

**OCR**

* NAVER Cloud Platform OCR

**Application**

* Python
* Streamlit

**Data**

* 금융 내부 업무 지침
* 금융 Q&A 데이터
* Vector DB

---

## 📂 프로젝트 구조

```text
finance-ai/
├── 계좌개설/
├── 기업계좌개설/
├── 신용대출심사/
├── kb_knowledge_db/
├── app.py
├── app_ui.py
├── chat.py
├── ingest.py
├── ocr_helper.py
└── kb_master_knowledge.txt
```

---

## 👥 Team

**경북대학교 CHEM.COM**

| 이름  | 소속    |
| --- | ----- |
| 강주호 | 컴퓨터학부 |
| 조해민 | 컴퓨터학부 |
| 조민혁 | 화학과   |


---

## 🚀 실행 방법

### 1. 저장소 내려받기

```bash
git clone https://github.com/juhoimda/NCP_AI_CAMP.git
cd NCP_AI_CAMP
```

### 2. 가상환경 생성 및 패키지 설치

macOS/Linux 기준입니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install fastapi uvicorn python-multipart streamlit requests pillow chromadb
```

Windows PowerShell에서는 가상환경을 다음 명령으로 활성화합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

그다음 위와 동일하게 `pip install` 명령을 실행합니다.

### 3. 환경변수 설정

프로젝트 루트의 `.env.example`을 복사해 `.env` 파일을 만듭니다.

```bash
cp .env.example .env
```

`.env`에 실제 NCP API 정보를 입력합니다.

```dotenv
CLOVA_STUDIO_API_KEY=발급받은_Clova_Studio_API_Key
RAG_API_URL=https://clovastudio.stream.ntruss.com/v1/api-tools/rag-reasoning
REAL_OCR_INVOKE_URL=발급받은_OCR_Invoke_URL
OCR_SECRET_KEY=발급받은_OCR_Secret_Key
NCP_CHATBOT_URL=발급받은_Chatbot_Invoke_URL
NCP_CHATBOT_SECRET=발급받은_Chatbot_Secret_Key
```

> 실제 인증 정보가 담긴 `.env` 파일은 GitHub에 올리지 마세요.

## 프로젝트 실행

프로젝트 루트에서 터미널을 3개 열고 아래 프로그램을 각각 실행합니다. 각 터미널에서 가상환경이 활성화되어 있어야 합니다.

### 터미널 1: FastAPI 백엔드

```bash
source .venv/bin/activate
python app.py
```

- API 주소: <http://127.0.0.1:8000>
- API 문서: <http://127.0.0.1:8000/docs>

### 터미널 2: 메인 심사 UI

```bash
source .venv/bin/activate
streamlit run app_ui.py --server.port 8501
```

- 메인 화면: <http://127.0.0.1:8501>

### 터미널 3: 챗봇 UI

```bash
source .venv/bin/activate
streamlit run chat.py --server.port 8502
```

- 챗봇 화면: <http://127.0.0.1:8502>

메인 심사 UI 오른쪽 아래의 챗봇 버튼도 `8502` 포트로 연결됩니다.

## 실행 순서 요약

1. `python app.py`
2. `streamlit run app_ui.py --server.port 8501`
3. `streamlit run chat.py --server.port 8502`
4. 브라우저에서 <http://127.0.0.1:8501> 접속

서버를 종료하려면 각 터미널에서 `Ctrl+C`를 누릅니다.

## 문제 해결

- `Missing required environment variables` 오류가 발생하면 프로젝트 루트에 `.env`가 있는지, 값이 정확한지 확인합니다.
- `Address already in use` 오류가 발생하면 해당 포트를 사용 중인 기존 프로세스를 종료한 뒤 다시 실행합니다.
- 메인 UI에서 API 연결 오류가 발생하면 터미널 1의 FastAPI 서버가 `8000` 포트에서 실행 중인지 확인합니다.
- 챗봇 버튼이 열리지 않으면 터미널 3의 Streamlit 서버가 `8502` 포트에서 실행 중인지 확인합니다.
