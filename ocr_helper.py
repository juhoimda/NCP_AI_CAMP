import requests
import json
import uuid
import time

# ==========================================
# [설정] 유저가 제공한 NCP CLOVA OCR 정보 입력
# ==========================================
OCR_INVOKE_URL = "https://rqoqvwx6tp.apigw.ntruss.com/custom/v1/55358/e03d259238ac427308a9d53da9deeee47341b8071aca548bf950d0b12902576a/general"
OCR_SECRET_KEY = "Q3hkREZuYkVoSmJGdkp6QWRlaWpwQXlGenpKamVzZVU="

def analyze_document_ocr(image_path, file_extension="jpg"):
    """
    행원이 업로드한 서류 이미지를 NCP CLOVA OCR로 전송하여 
    텍스트를 하나의 문자열로 정제해 반환하는 함수입니다.
    """
    
    # 1. OCR API 호출을 위한 헤더 구성
    headers = {
        "X-OCR-SECRET": OCR_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    # 2. 이미지 파일을 바이너리로 읽기
    with open(image_path, "rb") as f:
        file_data = f.read()
        
    # 3. NCP OCR 스펙에 맞춘 유효 리퀘스트 바디 구성
    request_json = {
        "images": [
            {
                "format": file_extension,
                "name": "loan_document"
            }
        ],
        "requestId": str(uuid.uuid4()),
        "version": "V1",
        "timestamp": int(round(time.time() * 1000))
    }
    
    # multipart/form-data 형태로 보낼 데이터 구성
    payload = {
        "message": json.dumps(request_json)
    }
    files = [
        ("file", ("document_image." + file_extension, file_data, "image/" + file_extension))
    ]
    
    print(f"📸 [OCR] '{image_path}' 서류 분석 요청 중...")
    
    # 4. API 호출
    response = requests.post(OCR_INVOKE_URL, headers=headers, data=payload, files=files)
    
    if response.status_code == 200:
        ocr_data = response.json()
        
        # 5. 인식된 텍스트 조각들을 하나의 문장/문단으로 합치기
        extracted_texts = []
        for image_result in ocr_data.get("images", []):
            for field in image_result.get("fields", []):
                infer_text = field.get("inferText", "")
                extracted_texts.append(infer_text)
                
        full_text = " ".join(extracted_texts)
        print("✅ [OCR] 텍스트 추출 완료!")
        return full_text
    else:
        print(f"❌ [OCR] 실패: {response.status_code}, {response.text}")
        return None

# ==========================================
# 테스트 실행 구문
# ==========================================
if __name__ == "__main__":
    # 테스트용 이미지 파일이 있다면 아래 경로를 수정해서 실행해볼 수 있습니다.
    # 예: test_sample = "registration_document.jpg"
    # print(analyze_document_ocr(test_sample, "jpg"))
    pass