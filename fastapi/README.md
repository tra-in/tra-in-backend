# 여행 경로 추천 API

FastAPI와 OpenAI를 사용하여 구축된 간단한 여행 경로 추천 API 백엔드입니다.

## 사전 준비

- Python 3.8 이상 설치

## 프로젝트 설정

이 프로젝트는 `requirements.txt` 파일을 사용하여 필요한 파이썬 라이브러리를 관리합니다. 이 파일은 애플리케이션 실행에 필요한 모든 의존성을 명시하고 있습니다.

프로젝트를 설정하고 필요한 모든 라이브러리를 한 번에 설치하려면 아래 단계를 따르세요.

### 1. 가상 환경 생성 (권장)

프로젝트별로 독립된 환경을 구성하기 위해 가상 환경을 사용하는 것이 좋습니다. 프로젝트 폴더 내에서 터미널을 열고 다음 명령어를 실행하세요.

```bash
# 'venv'라는 이름의 가상 환경 생성
python -m venv venv
```

### 2. 가상 환경 활성화

생성한 가상 환경을 활성화합니다.

Windows:

```
.\venv\Scripts\activate
```

macOS / Linux:

```
source venv/bin/activate
```

(터미널 프롬프트 앞에 (venv)가 표시되면 가상 환경이 성공적으로 활성화된 것입니다.)

### 3. 의존성 라이브러리 설치

requirements.txt 파일을 사용하여 모든 라이브러리를 설치합니다. 다음 명령어를 실행하세요.

```
pip install -r requirements.txt
```

이 명령어는 pip(파이썬 패키지 설치 관리자)에게 requirements.txt 파일을 읽어 그 안에 명시된 모든 라이브러리를 자동으로 설치하라고 지시합니다.

### 애플리케이션 실행

1. 환경 변수 설정: 프로젝트의 루트 디렉토리에 .env 파일을 생성하고 OpenAI API 키를 추가합니다.

```
OPENAI*API_KEY="발급받은_API_키를_여기에_붙여넣으세요"
```

2. 서버 시작: 터미널에서 아래 명령어를 실행하여 FastAPI 개발 서버를 시작합니다.

```
uvicorn main:app --reload
```

3. API 문서 확인: 웹 브라우저를 열고 http://127.0.0.1:8000/docs 주소로 이동하면 API 문서를 확인하고 직접 테스트해볼 수 있습니다.

## Directory 구조

```
/fastapi
├── venv/                   # Python 가상 환경 폴더 (자동 생성)
│   ├── Include/
│   ├── Lib/
│   └── Scripts/
├── app/
│   ├── __init__.py             # 디렉토리를 패키지로 인식시킴
│   ├── api/
│   │   ├── __init__.py
│   │   └── travel.py           # 여행 추천 관련 API 엔드포인트를 정의
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # 환경 변수 및 설정을 관리
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── travel.py           # Pydantic 스키마(데이터 모델)를 정의
│   ├── services/
│   │   ├── __init__.py
│   │   └── recommendation.py   # OpenAI 호출 등 핵심 비즈니스 로직을 처리
│   └── main.py                 # FastAPI 앱을 생성하고 라우터를 등록하는 진입점
├── .env                    # 환경 변수 파일 (API 키 등 민감 정보 저장)
├── README.md               # 프로젝트 설명 및 사용법 안내 파일
└── requirements.txt        # 프로젝트 의존성(라이브러리) 목록
```
