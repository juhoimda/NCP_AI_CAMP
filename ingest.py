import requests
import json
import chromadb
import re
import os
import shutil

# ==========================================
# [설정] 유저가 제공한 CLOVA Studio 정보 입력
# ==========================================
EMBEDDING_API_URL = "https://clovastudio.stream.ntruss.com/v1/api-tools/embedding/v2"
CLOVA_STUDIO_API_KEY = "nv-38d2a14af72546d28b2593916316adc7y4ry"

headers = {
    "Authorization": f"Bearer {CLOVA_STUDIO_API_KEY}",
    "Content-Type": "application/json"
}

def get_clova_embedding(text):
    """텍스트를 CLOVA Studio 임베딩 v2 API를 사용해 고차원 벡터로 변환합니다."""
    payload = {"text": text}
    try:
        response = requests.post(EMBEDDING_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["result"]["embedding"]
        else:
            print(f"❌ 임베딩 실패: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"❌ 임베딩 통신 오류: {e}")
        return None

def parse_knowledge_file(file_path):
    """
    텍스트 파일을 읽어 '■ 숫자. 업무명' 패턴을 기준으로 
    각 업무별 데이터를 쪼개고 카테고리를 분류하는 정밀 함수입니다.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 정규식 보정: 다양한 공백 문자 및 줄바꿈 대응 (\s*)
    sections = re.split(r'(■\s*\d+\.\s*)', content)
    
    documents = []
    doc_index = 1
    
    # 분할된 세션을 순회하며 타이틀과 본문을 안정적으로 매칭
    for i in range(1, len(sections), 2):
        prefix = sections[i].strip() # 예: "■ 5."
        body_part = sections[i+1] if i+1 < len(sections) else ""
        
        # 본문의 첫 줄에서 타이틀 명칭 추출
        body_lines = body_part.strip().split('\n')
        if not body_lines:
            continue
            
        raw_title = body_lines[0].strip() # 예: "미성년자 금융거래 및 계좌개설 가이드라인" 또는 "미성년자 금융거래"
        full_section_text = prefix + " " + body_part.strip()
        
        # 괄호 제거 및 깔끔한 키워드 추출 (예: "계좌개설 (기본 및 목적 증빙)" -> "계좌개설")
        clean_category = raw_title.split('(')[0].split('및')[0].strip()
        # 가이드라인, 지침 등의 서술어 제거하여 명사형 태그 추출
        clean_category = clean_category.replace("가이드라인", "").replace("지침", "").strip()

        if not clean_category:
            clean_category = "기타"

        documents.append({
            "id": f"kb-doc-{doc_index}",
            "category": clean_category,
            "text": full_section_text
        })
        doc_index += 1
        
    return documents

# ==========================================
# 메인 데이터 주입(Ingestion) 프로세스
# ==========================================
def main():
    source_file = "kb_master_knowledge.txt"
    db_path = "./kb_knowledge_db"
    
    # 🌟 [오류 차단] 기존 잘못 빌드된 '기타' 폴더 DB가 있다면 깨끗하게 밀어버립니다.
    if os.path.exists(db_path):
        print("🧹 기존에 잘못 생성된 로컬 데이터베이스 폴더를 초기화합니다...")
        shutil.rmtree(db_path)
        
    print(f"📖 1. '{source_file}' 원본 규정집 파일 읽는 중...")
    try:
        documents = parse_knowledge_file(source_file)
        print(f"✅ 규정집 파싱 완료: 총 {len(documents)}개의 금융 업무 카테고리를 식별했습니다.")
        for d in documents:
            print(f"   [분류 확인] ID: {d['id']} | 카테고리 태그: '{d['category']}'")
    except FileNotFoundError:
        print(f"❌ 오류: 프로젝트 폴더에 '{source_file}' 파일이 존재하지 않습니다.")
        return

    # Chroma 벡터 DB 신규 초기화
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="kb_rules")
    
    print("\n🚀 2. CLOVA Studio 임베딩 API 호출 및 DB 주입 시작...")
    for doc in documents:
        print(f"🔄 [{doc['category']}] 벡터 라이징 요청 중...")
        vector = get_clova_embedding(doc["text"])
        
        if vector:
            collection.add(
                embeddings=[vector],
                documents=[doc["text"]],
                ids=[doc["id"]],
                metadatas=[{"category": doc["category"]}]
            )
            print(f"   ✅ {doc['id']} 저장 완료!")
            
    print("\n🎉 모든 KB국민은행 금융 규정 DB 인덱싱이 정상적으로 완료되었습니다!")

if __name__ == "__main__":
    main()