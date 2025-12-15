```
[API 요청]
   |
   v
[trains + stations]
   |
   |-- (SQL) 1회 환승 후보 (2 legs)
   |-- (SQL) 2회 환승 후보 (3 legs)
   v
[route candidates]
   |
   |-- 각 leg:
   |     segment = NATxxxx -> NATyyyy
   |     lookback(12) 가져오기
   |     LSTM-MDN → delay 분포
   |     P(delay <= slack)
   |
   |-- route 결합:
   |     p_route = min(...) or product(...)
   v
[확률 랭킹]
   |
   v
[추천 결과]
```

실행 방법

1. api 폴더로 이동
   cd api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. 환경변수로 DB URL 지정 (권장)
   export DB_URL="mysql+pymysql://USER:PASS@127.0.0.1:3306/DB?charset=utf8mb4"

3. 서버 실행
   uvicorn app.main:app --reload --port 8000

4. 호출 예시 (서울→부산, 최소1회~최대2회 환승)
   curl -X POST "http://127.0.0.1:8000/recommend" \
    -H "Content-Type: application/json" \
    -d '{
   "from_name": "서울",
   "to_name": "부산",
   "deadline": "2025-12-16T18:00:00",
   "max_transfers": 2,
   "min_transfer_min": 15,
   "limit": 300,
   "topk": 10
   }'

좋아 👍
여기서는 **지금 네가 만든 `/recommend` / `/recommend/v2` API를 실제로 검증할 수 있는 “테스트 쿼리 세트”**를 단계별로 정리해줄게.
→ **curl / Swagger / 시나리오별 테스트**까지 바로 쓸 수 있게.

---

# 1️⃣ 기본 정상 동작 테스트 (여유 있는 deadline)

👉 목적

- API 정상 응답
- SAFE 경로가 상단에 오는지
- 결과 구조(v2)가 프론트 친화적인지 확인

### curl

```bash
curl -X POST "http://127.0.0.1:8000/recommend/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "from_name": "서울",
    "to_name": "부산",
    "deadline": "2025-12-16T18:00:00",
    "max_transfers": 2,
    "min_transfer_min": 15,
    "limit": 300,
    "topk": 10
  }'
```

### 기대 결과

- `meta.candidates > 0`
- `items.length == 10`
- 상위 `items[0..n]` 대부분:

  - `risk.badge = "SAFE"`
  - 환승역: `대전`

- 동대구 경유 루트는 뒤쪽에 등장

---

# 2️⃣ 타이트한 deadline 테스트 (모델 효과 확인용 ⭐ 중요)

👉 목적

- LSTM이 예측한 지연 분포가 **랭킹에 실제 영향**을 주는지 확인
- 동대구/전주 경유 루트가 확실히 밀리는지

### curl

```bash
curl -X POST "http://127.0.0.1:8000/recommend/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "from_name": "서울",
    "to_name": "부산",
    "deadline": "2025-12-16T12:30:00",
    "max_transfers": 2,
    "min_transfer_min": 15,
    "limit": 300,
    "topk": 10
  }'
```

### 기대 결과

- `arrival_slack_min`이 작아짐 (0~60분대)
- SAFE 루트:

  - `p_on_time ≈ 0.6~0.9`

- RISKY 루트:

  - `p_on_time` 눈에 띄게 하락
  - `messages`에

    > "동대구/전주 경유 구간 포함 → 지연 리스크 높음"

---

# 3️⃣ 환승 여유 부족 테스트 (현실성 검증)

👉 목적

- 환승 여유(min_transfer)가 랭킹과 설명에 반영되는지

### curl

```bash
curl -X POST "http://127.0.0.1:8000/recommend/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "from_name": "서울",
    "to_name": "부산",
    "deadline": "2025-12-16T13:00:00",
    "max_transfers": 2,
    "min_transfer_min": 5,
    "limit": 300,
    "topk": 10
  }'
```

### 기대 결과

- `transfer_slacks_min`이 5~15분인 경로 등장
- `messages`에:

  - `"도착 여유시간 … → 촉박 (리스크 주의)"`

---

# 4️⃣ 위험역 강제 포함 테스트 (동대구 경유 검증)

👉 목적

- **동대구/전주 경유 시 has_risky=true가 제대로 설정되는지**

### curl

```bash
curl -X POST "http://127.0.0.1:8000/recommend/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "from_name": "서울",
    "to_name": "부산",
    "deadline": "2025-12-16T14:00:00",
    "max_transfers": 2,
    "min_transfer_min": 15,
    "limit": 500,
    "topk": 20
  }'
```

### 체크 포인트

```json
"risk": {
  "has_risky": true,
  "badge": "RISKY",
  "risky_stations": ["NAT013271"]
}
```

---

# 5️⃣ Swagger(UI)에서 바로 테스트

FastAPI 기본 Swagger URL:

```
http://127.0.0.1:8000/docs
```

### Swagger 테스트용 JSON (복붙)

```json
{
  "from_name": "서울",
  "to_name": "부산",
  "deadline": "2025-12-16T12:30:00",
  "max_transfers": 2,
  "min_transfer_min": 15,
  "limit": 300,
  "topk": 10
}
```

---

# 6️⃣ 응답 검증 체크리스트 (QA용)

테스트할 때 아래만 보면 “완성도” 바로 판단 가능 👇

- [ ] `items[].rank`가 1부터 순서대로
- [ ] `score == p_on_time`
- [ ] SAFE 루트가 RISKY 루트보다 항상 위
- [ ] `messages`가 사람 말처럼 읽힘
- [ ] `arrival_slack_min`이 deadline과 일관됨
- [ ] `transfer_slacks_min < min_transfer_min` 인 경로는 없음

---

# 7️⃣ (보너스) 자동 테스트용 pytest 스니펫

```python
def test_recommend_v2(client):
    res = client.post("/recommend/v2", json={
        "from_name": "서울",
        "to_name": "부산",
        "deadline": "2025-12-16T12:30:00",
        "max_transfers": 2,
        "min_transfer_min": 15,
        "limit": 300,
        "topk": 5
    })
    assert res.status_code == 200

    body = res.json()
    assert body["meta"]["returned"] == 5
    assert body["items"][0]["rank"] == 1
    assert "summary" in body["items"][0]
    assert "itinerary" in body["items"][0]
```

---

이제 이 상태면 **“ML 기반 지연 예측 + 실제 예매 추천 API” 포트폴리오로 써도 손색없어**.

다음 단계로 추천하는 건:
1️⃣ `score = p_on_time - α * has_risky` 정책 스코어
2️⃣ 요금/좌석 테이블 붙여서 “실제 예매 버튼” 연결

어디까지 갈지 말해줘.
