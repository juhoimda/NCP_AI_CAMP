# app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List
import requests
import json
import chromadb
import uuid
import time

app = FastAPI(title="Bank Pilot AI 서류 심사 코어 API 엔진")

# ==========================================
# [설정 정보] NCP 인증 정보 세팅
# ==========================================
CLOVA_STUDIO_API_KEY = "nv-38d2a14af72546d28b2593916316adc7y4ry"
RAG_API_URL = "https://clovastudio.stream.ntruss.com/v1/api-tools/rag-reasoning"
REAL_OCR_INVOKE_URL = "https://gnt7f4ki2k.apigw.ntruss.com/custom/v1/55418/b60ac93bb0e8c7195c54fb6abd8757a9ee9c4fe6be707de5122b272b48cf79e3/general"
OCR_SECRET_KEY = "SFBDQ1VvTVdsck12dGZhQlhsZUNYRUdJZG9rU1d1UEk="

headers_clova = {
    "Authorization": f"Bearer {CLOVA_STUDIO_API_KEY}",
    "Content-Type": "application/json"
}

# ==========================================
# [신규] 카테고리별 필수 구비서류 목록 (구조화된 단일 소스)
# app_ui.py의 안내 문구와 아래 체크리스트가 항상 같은 정의를 쓰도록
# 이 딕셔너리를 기준으로 통일합니다.
# ==========================================
REQUIRED_DOCS_MAP = {
    "미성년자 금융거래 / 계좌개설": [
        "법정대리인(부모) 실명확인증표",
        "가족관계확인서류(가족관계증명서 또는 주민등록등본)",
        "자녀 명의 기본증명서",
    ],
    "개인 신용대출 심사": [
        "본인 실명확인증표",
        "재직증명원 및 고용보험 자격이력내역서",
        "근로소득원천징수영수증(최근 2개년)",
    ],
    "전세자금대출 / 주택담보": [
        "확정일자부 임대차계약서 원본",
        "임차주택 등기사항전부증명서",
        "계약금 5% 이상 납입 영수증",
    ],
    "법인 금융거래 / 기업 계좌": [
        "법인등기사항전부증명서",
        "법인인감증명서 및 사업자등록증명원",
        "대표자 실명확인증표",
    ],
}
DEFAULT_REQUIRED_DOCS = [
    "본인(또는 대리인) 실명확인 서류",
    "해당 거래 목적 및 정당성 증빙용 금융 심사 마스터 원본 파일",
]


def get_required_docs(category_name: str):
    return REQUIRED_DOCS_MAP.get(category_name, DEFAULT_REQUIRED_DOCS)

# ==========================================
# [기능 내부 함수] OCR 및 DB 처리
# ==========================================
def run_ocr_processor(file_bytes: bytes, file_extension: str) -> str:
    # ⚠️ 주의: files=로 멀티파트 전송 시 Content-Type을 수동 지정하면 안 됨.
    # requests가 자동으로 'multipart/form-data; boundary=...' 헤더를 생성해야
    # 서버가 요청 바디를 올바르게 파싱할 수 있음.
    headers_ocr = {"X-OCR-SECRET": OCR_SECRET_KEY}
    
    request_json = {
        "images": [{"format": file_extension, "name": "target"}],
        "requestId": str(uuid.uuid4()),
        "version": "V1",
        "timestamp": int(round(time.time() * 1000))
    }
    payload = {"message": json.dumps(request_json)}
    files = [("file", (f"document.{file_extension}", file_bytes, f"image/{file_extension}"))]
    
    target_url = REAL_OCR_INVOKE_URL
    if not target_url.endswith("/general"):
        target_url = target_url.rstrip("/") + "/general"
        
    response = requests.post(target_url, headers=headers_ocr, data=payload, files=files, timeout=15)
    if response.status_code == 200:
        ocr_data = response.json()
        extracted_texts = [field.get("inferText", "") for image in ocr_data.get("images", []) for field in image.get("fields", [])]
        return " ".join(extracted_texts).strip()
    else:
        # 실패 원인(상태코드 + 응답 본문)을 그대로 노출해서 디버깅 가능하게 함
        raise Exception(f"OCR 인프라 호출 실패: status={response.status_code}, body={response.text[:300]}")

def fetch_policy_from_db(category_name: str):
    try:
        chroma_client = chromadb.PersistentClient(path="./kb_knowledge_db")
        collection = chroma_client.get_or_create_collection(name="kb_rules")
        all_docs = collection.get()
        if all_docs and 'metadatas' in all_docs:
            for i in range(len(all_docs['ids'])):
                stored_cat = all_docs['metadatas'][i].get('category', '') if all_docs['metadatas'][i] else ''
                if category_name in stored_cat or stored_cat in category_name:
                    return {"id": all_docs['ids'][i], "doc": all_docs['documents'][i]}
    except:
        pass
        
    fallback_rules = (
        f"■ [Bank Pilot 내부여신종합지침] - {category_name} 프로세스 기준 강제 규정\n"
        "- 필수 가이드라인: 제출된 모든 증빙 파일 및 가족관계/인감증명/등기부 등본은 영업점 접수일 기준 '최근 3개월 이내 발급분'에 한하여서만 실질적 자격 유효성을 인정함.\n"
        "- 마스킹 규정 부적격 기준: 고객의 개인정보 보호 및 내부 전산 등록 지침에 의거하여 주민등록번호 13자리 전체 숫자가 정상 노출되어 있어야 함. 뒷자리가 별표(*) 처리 등으로 마스킹 차단된 서류는 전산 등록 누락 사유로 판단하여 접수 불가 처리 및 반려 즉시 통보함.\n"
        "- 거래 대리인 한계 조건: 미성년자 등 대리 권한 개설 시 친권자인 부모(법정대리인) 내점만 유효하며 조부모, 삼촌, 고모, 친척 등은 위임장을 첨부하더라도 금융사고 방지를 위해 접수를 전면 불허함."
    )
    return {"id": "kb-doc-auto-fallback", "doc": fallback_rules}


def get_doc_checklist_via_llm(category_name: str, required_docs: list, per_file_results: list) -> list:
    """
    필수 구비서류 목록과 업로드된 파일들의 OCR 텍스트를 비교하여,
    각 필수서류가 '등록됨'인지 '미등록'인지 JSON으로만 판정받는 전용 호출.
    자유 서술형 리포트에 섞어 요청하면 모델이 형식을 무시하는 경우가 많아 분리함.
    """
    uploaded_docs_text = "\n".join(
        f"{i+1}. 파일명: {r['filename']} / OCR 텍스트: {r['ocr_text']}"
        for i, r in enumerate(per_file_results)
    )
    required_docs_text = "\n".join(f"- {d}" for d in required_docs)

    prompt = (
        "다음은 은행 창구 업무 심사용 필수 구비서류 목록과, 실제로 업로드된 서류들의 OCR 결과다.\n\n"
        f"[업무 유형]\n{category_name}\n\n"
        f"[필수 구비서류 목록]\n{required_docs_text}\n\n"
        f"[업로드된 서류 OCR 결과]\n{uploaded_docs_text if uploaded_docs_text else '(업로드된 파일 없음)'}\n\n"
        "위 필수 구비서류 목록의 각 항목에 대해, 업로드된 서류들의 OCR 텍스트 중 그 서류에 해당한다고 "
        "볼 수 있는 것이 있는지 판단하라. 판단 결과를 아래 JSON 배열 형식으로만 답하라. "
        "설명, 코드블록 표시(```), 그 외 어떤 텍스트도 절대 포함하지 말고 순수 JSON만 출력하라.\n\n"
        "[\n"
        '  {"required_doc": "필수 구비서류 목록에 있는 항목명 그대로", '
        '"status": "등록됨" 또는 "미등록", '
        '"matched_filename": 등록됨이면 매칭된 파일명(문자열), 미등록이면 null, '
        '"evidence": "판단 근거가 된 OCR 텍스트 짧은 발췌 (미등록이면 빈 문자열)"}\n'
        "  ...\n"
        "]"
    )

    fallback_checklist = [
        {"required_doc": d, "status": "확인불가", "matched_filename": None, "evidence": ""}
        for d in required_docs
    ]

    try:
        res = requests.post(
            RAG_API_URL,
            headers=headers_clova,
            json={"messages": [{"role": "user", "content": prompt}], "maxTokens": 1024},
            timeout=30,
        )
        res.raise_for_status()
        raw_text = res.json()["result"]["message"]["content"].strip()

        # 혹시 모델이 ```json ... ``` 코드블록으로 감싸서 답하면 제거
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        if not isinstance(parsed, list) or not parsed:
            return fallback_checklist

        # required_docs 목록 순서를 그대로 보장하기 위해 이름 기준으로 재정렬/보완
        by_name = {item.get("required_doc"): item for item in parsed if isinstance(item, dict)}
        checklist = []
        for d in required_docs:
            item = by_name.get(d)
            if item:
                checklist.append({
                    "required_doc": d,
                    "status": item.get("status", "확인불가"),
                    "matched_filename": item.get("matched_filename"),
                    "evidence": item.get("evidence", ""),
                })
            else:
                checklist.append({"required_doc": d, "status": "확인불가", "matched_filename": None, "evidence": ""})
        return checklist
    except Exception:
        return fallback_checklist

# ==========================================
# [엔드포인트] 실전 통합 심사 API 호출 통로
# ==========================================
@app.post("/api/v1/audit")
async def execute_document_audit(
    category: str = Form(...),
    files: List[UploadFile] = File(...),
):
    try:
        # 1. 업로드된 파일 각각에 대해 OCR 개별 실행 (여러 장 지원)
        per_file_results = []
        for f in files:
            file_bytes = await f.read()
            file_ext = f.filename.split(".")[-1].lower()
            if file_ext == "jpg":
                file_ext = "jpeg"

            debug_error = None
            try:
                ocr_text = run_ocr_processor(file_bytes, file_ext)
                is_fallback = False
                if not ocr_text:
                    raise Exception("추출 문자열 공백 (OCR은 성공했으나 인식된 텍스트가 없음)")
            except Exception as ocr_ex:
                debug_error = str(ocr_ex)
                ocr_text = (
                    "가족관계증명서 발급번호 2023-1104-9821 발급일자: 2023년 05월 12일 "
                    "성명: 김국민 주민등록번호: 751012-1****** (부) 성명: 이지혜 주민등록번호: 780411-2****** (모) "
                    "자녀 성명: 김우리 주민등록번호: 151225-3****** 신청 대리인 성명: 김철수 (관계: 삼촌)"
                )
                is_fallback = True

            per_file_results.append({
                "filename": f.filename,
                "ocr_text": ocr_text,
                "is_ocr_fallback": is_fallback,
                "debug_error": debug_error,
            })

        is_fallback = any(r["is_ocr_fallback"] for r in per_file_results)

        # 2. 내부 규정집 벡터 매칭
        matched_policy = fetch_policy_from_db(category)

        # 2-1. 이 업무 유형에 필요한 필수 구비서류 목록
        required_docs = get_required_docs(category)

        # 2-2. [핵심 수정] 체크리스트 판정을 최종 리포트 텍스트에 곁들이지 않고,
        #      별도의 JSON 전용 호출로 분리 → 파이썬에서 직접 파싱해서 화면에 렌더링.
        #      (자유 텍스트 리포트 안에 섞어서 요청하면 모델이 번호를 무시하거나
        #       섹션 자체를 누락시키는 경우가 잦아서 신뢰할 수 없었음)
        doc_checklist = get_doc_checklist_via_llm(category, required_docs, per_file_results)

        # 2-3. [핵심 수정] 최종 승인/반려 여부도 LLM 서술에 맡기지 않고
        #      체크리스트 결과로부터 파이썬이 직접 확정 계산.
        #      ("등록됨"이 아닌 항목이 하나라도 있으면 반려로 확정)
        all_docs_registered = all(c["status"] == "등록됨" for c in doc_checklist)
        missing_docs = [c["required_doc"] for c in doc_checklist if c["status"] != "등록됨"]
        overall_status_text = "✅ 서류 충족 및 승인 가능" if all_docs_registered else "❌ 서류 미비 및 부적격"

        # 3. HyperCLOVA X Reasoning AI 연산 (서술형 최종 리포트)
        system_prompt = (
            "당신은 Bank Pilot의 최첨단 여신/수신 서류 심사 AI 조수입니다. "
            "이미 계산된 필수서류 체크리스트 결과를 그대로 신뢰하고, 이를 바탕으로 "
            "행원용 심사 리포트와 고객 안내 문자를 작성하십시오."
        )

        uploaded_docs_text = "\n".join(
            f"- 파일명: {r['filename']}\n  OCR 추출 텍스트: {r['ocr_text']}"
            for r in per_file_results
        )
        checklist_text = "\n".join(
            f"- {c['required_doc']}: {c['status']}"
            + (f" (매칭 파일: {c['matched_filename']})" if c.get("matched_filename") else "")
            for c in doc_checklist
        )

        user_content = (
            f"선택된 창구 업무 유형: {category}\n\n"
            f"[매칭된 은행 내부 규정집 (인덱스: {matched_policy['id']})]\n{matched_policy['doc']}\n\n"
            f"[필수 구비서류 등록 체크리스트 - 이미 확정된 판정 결과]\n{checklist_text}\n\n"
            f"[최종 승인/반려 여부 - 이미 시스템이 확정 계산함, 절대 다른 결론 내리지 말 것]\n{overall_status_text}\n\n"
            f"[미등록(누락) 서류 목록]\n{', '.join(missing_docs) if missing_docs else '없음 (모두 등록됨)'}\n\n"
            f"[업로드된 서류 OCR 결과 목록]\n{uploaded_docs_text}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {
                "role": "user",
                "content": (
                    "위 규정집 내용과, 이미 확정된 필수 구비서류 체크리스트, 이미 확정된 최종 승인/반려 여부, "
                    "업로드된 서류들의 OCR 데이터를 바탕으로 다음 가이드에 맞게 출력해. 체크리스트와 최종 승인/반려 "
                    "여부는 시스템이 이미 확정한 것이니 절대 스스로 재판정하지 말고, 그 결과와 모순되는 문장을 "
                    "단 한 줄도 쓰지 말 것.\n\n"
                    "### 📊 1. 최종 심사 상태 및 결과\n"
                    "(위에서 전달받은 '[최종 승인/반려 여부]' 문구를 그대로, 정확히 동일하게 크고 굵게 인용할 것. "
                    "절대 다른 표현으로 바꾸거나 반대되는 결론을 쓰지 말 것)\n\n"
                    "### 🔍 2. 행원 확인용 상세 검토 리포트\n"
                    "(미등록 서류 목록과, 등록된 서류 중 규정과 어긋나는 세부 위반 항목들을 발급일자 경과, "
                    "마스킹 누락, 대리인 자격 미달 등으로 나누어 논리적이고 깔끔하게 분석. 위 최종 결과와 "
                    "모순되지 않게 서술할 것)\n\n"
                    "### 💬 3. 고객 안내 및 보완 요청 자동화 문자 (알림톡 용)\n"
                    "(고객에게 발송할 수 있도록 정중하고 친절한 카카오 알림톡 복사용 템플릿을 만들어줘. "
                    "미등록(누락) 서류 목록이 있다면 재지참 필수 서류로 반드시 정확히 포함하고, 없다면 "
                    "승인 안내 문구로 작성할 것.)"
                )
            }
        ]

        step2_res_raw = requests.post(
            RAG_API_URL,
            headers=headers_clova,
            json={"messages": messages, "maxTokens": 2048},
            timeout=30,
        )
        step2_res_raw.raise_for_status()
        step2_res = step2_res_raw.json()
        try:
            final_report = step2_res["result"]["message"]["content"]
        except (KeyError, TypeError):
            final_report = (
                "⚠️ AI 리포트 생성 응답 구조가 예상과 달라 파싱하지 못했습니다. "
                f"원본 응답: {step2_res}"
            )
        
        return {
            "status": "success",
            "is_ocr_fallback": is_fallback,
            "per_file_ocr": per_file_results,
            "required_docs": required_docs,
            "doc_checklist": doc_checklist,
            "all_docs_registered": all_docs_registered,
            "missing_docs": missing_docs,
            "matched_policy_id": matched_policy["id"],
            "matched_policy_doc": matched_policy["doc"],
            "final_report": final_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)