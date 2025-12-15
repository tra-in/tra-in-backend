### 1) 설치

pip install -r requirements.txt

### 2) config.yaml에서 DB URL 수정

### 3) 학습

python -m src.train

### 4) 랭킹(예시)

- src/ranker.py의 rank_routes_by_deadline_probability를 서비스 코드에서 호출
- routes 생성은 별도의 SQL/그래프 탐색 로직으로 준비
