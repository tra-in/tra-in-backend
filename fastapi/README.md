# 🌏 AI Travel Recommendation API

FastAPI, OpenAI, ChromaDB를 활용한 **지능형 여행 추천 시스템**입니다. 위치 기반 추천부터 자연어 검색, RAG 기반 AI 추천까지 제공합니다.

## ✨ 주요 기능

- 🤖 **AI 기반 맞춤 추천**: OpenAI GPT를 활용한 개인화된 여행지 추천
- 🔍 **의미 기반 검색**: 47,543개 한국 관광지 데이터를 Vector DB로 빠르게 검색
- 📍 **위치 기반 추천**: 사용자 위치와 선호도를 고려한 주변 여행지 추천
- 🧠 **RAG 기술**: 실제 관광 데이터와 AI를 결합한 정확한 추천

---

## 🚀 빠른 시작 (5분 설정)

### **사전 요구사항**

- **Python**: 3.11.9 (필수 - NumPy 호환성)
- **API 키**: OpenAI API Key
- **선택사항**: 한국관광공사 API Key

### **즉시 시작**

```bash
# 1. 저장소 클론
git clone <repository-url>
cd fastapi

# 2. Python 환경 설정 (asdf 사용자)
asdf install python 3.11.9
asdf set python 3.11.9

# 3. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 5. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 입력

# 6. Vector DB 검증 (사전 임베딩된 데이터 사용)
python verify_vector_db.py

# 7. 서버 실행
uvicorn app.main:app --reload

또는

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**✅ 성공!** → http://localhost:8000/docs 에서 API 문서 확인

---

## 📁 프로젝트 구조

```
fastapi/
├── app/
│   ├── api/
│   │   └── travel.py              # 모든 API 엔드포인트
│   ├── core/
│   │   ├── config.py              # 환경 설정 관리
│   │   └── vector_db.py           # Vector DB 싱글톤 관리자
│   ├── schemas/
│   │   ├── travel.py              # 여행 추천 데이터 모델
│   │   └── search.py              # 검색 관련 데이터 모델
│   ├── services/
│   │   ├── recommendation.py      # AI 추천 로직 (RAG)
│   │   ├── tourism_search.py      # Vector 검색 서비스
│   │   └── kto_ingestion.py       # 관광 데이터 수집/임베딩
│   ├── scripts/
│   │   └── embed_kto_data.py      # 데이터 임베딩 실행 스크립트
│   └── main.py                    # FastAPI 앱 진입점
├── data/
│   └── kto_tourism_db/            # Vector DB 저장소 (사전 임베딩)
├── venv/                          # Python 가상환경
├── .env                           # 환경변수 (Git 제외)
├── requirements.txt               # Python 의존성
└── README.md
```

---

## 🔧 환경 설정

### **1. .env 파일 설정**

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
# ==================== 필수 설정 ====================
OPENAI_API_KEY=sk-your-openai-key-here
KTO_SERVICE_KEY=your-kto-service-key-here

# ==================== 기본 설정 ====================
DEBUG=True

# ==================== OpenAI 설정 ====================
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

# ==================== Vector DB 설정 ====================
VECTOR_DB_PATH=./data/kto_tourism_db
VECTOR_DB_COLLECTION=kto_tourism
EMBEDDING_TYPE=korean

# ==================== 성능 설정 ====================
BATCH_SIZE=50
MAX_RETRIES=3
REQUEST_TIMEOUT=30

# ==================== 검색 설정 ====================
DEFAULT_SEARCH_RESULTS=10
MAX_SEARCH_RESULTS=50
```

### **2. Vector DB 설정**

#### **방법 A: 사전 임베딩된 데이터 사용 (권장 ⭐)**

구글드라이브에 포함된 Vector DB를 바로 사용합니다.

```bash
# 검증만 수행
python verify_vector_db.py

# 예상 출력:
# ✅ Vector DB 디렉토리 존재: data/kto_tourism_db
# 📦 Vector DB 크기: 413.8 MB
...
# ✅ 저장된 데이터: 47,543개
...
# ✅ 검색 기능 정상
# 🎉 Vector DB 검증 완료!
```

**장점:**

- ⚡ 즉시 사용 가능 (설정 시간: 5분)
- 💰 KTO API 키 불필요
- 🔒 API 트래픽 소모 없음

#### **방법 B: 직접 임베딩 (최신 데이터 필요시)**

```bash
# KTO API 키가 .env에 설정되어 있어야 함
python -m app.scripts.embed_kto_data

# 소요 시간: 약 2-3시간
# API 호출: 약 48회 (트래픽의 4.8%)
```

---

## 📡 API 사용법

### **API 문서**

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### **주요 엔드포인트**

#### **1. 위치 기반 여행지 추천 (기존 API)**

```bash
curl -X POST http://localhost:8000/travel/recommend-travel \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 37.5665,
    "longitude": 126.9780,
    "travel_type": "culture"
  }'
```

**travel_type 옵션:**

- `nature`: 자연 관광지
- `culture`: 문화/역사 시설
- `food`: 맛집/카페
- `shopping`: 쇼핑 장소
- `activity`: 액티비티/레저
- `relaxation`: 휴양/힐링

-> 하지만 "카페나 맛집이 있었으면 합니다" 등의 자연어를 입력해도 작동

#### **2. 자연어 검색 (Vector DB)**

```bash
# 간단한 검색
curl "http://localhost:8000/travel/search/simple?q=서울 맛집&limit=5"

# 상세 검색 (필터 포함)
curl -X POST http://localhost:8000/travel/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "제주도 해변 카페",
    "n_results": 10,
    "area_code": "39",
    "include_similarity": true
  }'
```

#### **3. AI 기반 자연어 추천 (RAG)**

```bash
curl "http://localhost:8000/travel/recommend/query?query=가족과 함께 갈만한 서울 관광지"
```

#### **4. 유사 장소 검색**

```bash
curl "http://localhost:8000/travel/similar?query=경복궁&limit=5"
```

### **참조 정보 API**

```bash
# 지역 코드 목록 (1:서울, 6:부산, 39:제주 등)
curl http://localhost:8000/travel/area-codes

# 콘텐츠 타입 목록 (12:관광지, 39:음식점 등)
curl http://localhost:8000/travel/content-types

# 여행 타입 목록
curl http://localhost:8000/travel/travel-types
```

### **시스템 정보**

```bash
# 서비스 상태 및 활성화된 기능
curl http://localhost:8000/travel/status

# Vector DB 통계
curl http://localhost:8000/travel/stats

# 헬스체크 (로드밸런서용)
curl http://localhost:8000/travel/health
```

---

## 🚨 트러블슈팅

### **🔥 자주 발생하는 문제**

#### **1. ModuleNotFoundError: No module named 'app'**

**원인:** Python이 프로젝트 패키지 구조를 인식하지 못함

**해결방법:**

```bash
# ✅ 권장: 모듈 방식으로 실행
python -m app.scripts.embed_kto_data

# ✅ 프로젝트 루트에서 실행 확인
pwd  # /path/to/fastapi 여야 함
cd /path/to/fastapi

# ✅ __init__.py 파일 확인 및 생성
find app -name "__init__.py" -type f
# 없다면 생성
touch app/__init__.py app/core/__init__.py app/services/__init__.py app/schemas/__init__.py app/scripts/__init__.py app/api/__init__.py
```

#### **2. NumPy 호환성 오류 (np.float\_ was removed)**

**원인:** NumPy 2.x와 AI 라이브러리 간 호환성 문제

**해결방법:**
chromadb 최신 버전이 requirements.txt에 설정되어 있습니다. 버전 확인해 주세요.

#### **3. ChromaDB 텔레메트리 오류**

**증상:**

```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**해결방법:**

이미 `app/core/vector_db.py`에 해결책이 적용되어 있습니다. 추가로:

```bash
# .env 파일에 추가
echo "ANONYMIZED_TELEMETRY=False" >> .env
echo "CHROMA_ANONYMIZED_TELEMETRY=False" >> .env
```

#### **4. OpenAI API 키 오류**

**증상:**

```
ValueError: OpenAI API 키가 설정되지 않았습니다.
```

**해결방법:**

```bash
# 1. .env 파일 확인
cat .env | grep OPENAI_API_KEY

# 2. API 키 형식 확인 (sk-로 시작해야 함)
# 올바른 예: OPENAI_API_KEY=sk-proj-abc123...

# 3. 환경변수 로드 확인
python -c "from app.core.config import settings; print('키 확인:', settings.OPENAI_API_KEY[:10] + '...')"
```

#### **5. Vector DB 로딩 실패**

**증상:**

```
❌ Vector DB 디렉토리가 없습니다!
```

**해결방법:**

```bash
# 방법 A: 구글 드라이브에서 다운로드 (큰 파일인 경우)
{유성구해바라기반 구글 드라이브 tra:in에 data.zip}

# 방법 B: 디렉토리 및 권한 확인
ls -la data/kto_tourism_db/
sudo chown -R $USER:$USER data/kto_tourism_db/
chmod -R 755 data/kto_tourism_db/

# 방법 C: 직접 임베딩
python -m app.scripts.embed_kto_data
```

### **💻 플랫폼별 문제**

#### **macOS (Apple Silicon M1/M2/M3)**

**문제:** ARM 아키텍처 호환성

```bash
# Homebrew로 Python 3.11 설치
brew install python@3.11

# ARM 네이티브 설치
arch -arm64 pip install -r requirements.txt

# 문제 지속시 Intel 호환 모드
arch -x86_64 pip install -r requirements.txt
```

#### **Windows**

**문제:** PowerShell 실행 정책

```powershell
# PowerShell 실행 정책 변경
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 가상환경 활성화
.\venv\Scripts\Activate.ps1
```

#### **Linux (Ubuntu/Debian)**

**문제:** Python 개발 헤더 누락

```bash
# 필수 패키지 설치
sudo apt update
sudo apt install -y python3.11-dev build-essential gcc g++

# pip 업그레이드
pip install --upgrade pip setuptools wheel
```

### **🔧 성능 관련 문제**

#### **메모리 부족 오류**

**증상:**

```
Killed
MemoryError
```

**해결방법:**

```bash
# 1. 배치 크기 감소 (.env 파일)
BATCH_SIZE=25  # 기본값: 50

# 2. 스왑 메모리 추가 (Linux/Mac)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 3. 시스템 리소스 확인
htop
```

#### **API 트래픽 초과 방지**

**현재 최적화 상태:**

- 페이지당 데이터: 1,000개
- 총 API 호출: 약 48회
- 트래픽 사용률: 4.8% (1,000회 제한 기준)

```bash
# .env 설정 확인
grep KTO_ITEMS_PER_PAGE .env
# 출력: KTO_ITEMS_PER_PAGE=1000

# 트래픽 증설 신청: https://www.data.go.kr/
# 마이페이지 → 활용신청 현황 → 트래픽 변경신청
```

### **🔍 디버깅 및 로깅**

#### **로그 파일 확인**

```bash
# 애플리케이션 로그
tail -f app.log

# 디버그 모드 활성화 (.env)
DEBUG=True
LOG_LEVEL=DEBUG

# 디버그 모드로 서버 실행
uvicorn app.main:app --reload --log-level debug
```

#### **Vector DB 무결성 검증**

```bash
# 상세 검증 스크립트 실행
python verify_vector_db.py

# Vector DB 재생성 (문제 지속시)
rm -rf data/kto_tourism_db
python -m app.scripts.embed_kto_data
```

---

## ⚡ 성능 최적화

### **검색 응답 속도 개선**

```python
# app/services/tourism_search.py에 캐싱 추가
from functools import lru_cache

class TourismSearchService:
    @lru_cache(maxsize=200)
    def cached_search(self, query: str, n_results: int = 10):
        """자주 사용되는 검색어 캐싱"""
        return self.search(query, n_results)
```

### **메모리 사용량 최적화**

```env
# .env 파일 최적화 설정
BATCH_SIZE=25                # 메모리 부족시 감소
MAX_SEARCH_RESULTS=30        # 기본값 50에서 감소
REQUEST_TIMEOUT=30           # 타임아웃 조정
```

---

## FAQ

**Q1. Vector DB 없이 실행할 수 있나요?**

네, 가능합니다. KTO API 키를 설정하지 않으면 기본 OpenAI 추천만 사용됩니다.

---

**Made with ❤️ for Better Travel Experience**
