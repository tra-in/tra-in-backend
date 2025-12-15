# 버킷 만들기

```
mysql -u train_root -p -h 127.0.0.1 train < scripts/init_buckets.sql
mysql -u train_root -p -h 127.0.0.1 train < scripts/refresh_buckets.sql
```

또는

수동으로 sql executes

# 예시

POST 요청

```
curl -X 'POST' \
  'http://127.0.0.1:8000/recommend' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
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

### JSON 결과값

```
{
  "from": "서울",
  "to": "부산",
  "deadline": "2025-12-16 18:00:00",
  "route_agg": "min",
  "count": 455,
  "results": [
    {
      "transfers": 1,
      "p_on_time": 0.9999999292194843,
      "legs": [
        {
          "train_id": 270,
          "train_no": "KTX366",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 06:30:00",
          "arr_time": "2025-12-16 07:25:00",
          "p_leg": 0.9999999292194843,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 635,
            "target_ts": "2025-12-16 07:20:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 3318,
          "train_no": "D1008161",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 09:40:00",
          "arr_time": "2025-12-16 11:40:00",
          "p_leg": 1,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 380,
            "target_ts": "2025-12-16 11:40:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 135
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.9999989098733274,
      "legs": [
        {
          "train_id": 270,
          "train_no": "KTX366",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 06:30:00",
          "arr_time": "2025-12-16 07:25:00",
          "p_leg": 0.9999999292194843,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 635,
            "target_ts": "2025-12-16 07:20:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 83,
          "train_no": "KTX179",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 10:40:00",
          "arr_time": "2025-12-16 12:40:00",
          "p_leg": 0.9999989098733274,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 320,
            "target_ts": "2025-12-16 12:40:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 195
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.99999868754871,
      "legs": [
        {
          "train_id": 270,
          "train_no": "KTX366",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 06:30:00",
          "arr_time": "2025-12-16 07:25:00",
          "p_leg": 0.9999999292194843,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 635,
            "target_ts": "2025-12-16 07:20:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 3321,
          "train_no": "D1008162",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 12:00:00",
          "arr_time": "2025-12-16 12:42:00",
          "p_leg": 0.99999868754871,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 318,
            "target_ts": "2025-12-16 12:40:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 275
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.99999868754871,
      "legs": [
        {
          "train_id": 2418,
          "train_no": "D0910161",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 10:00:00",
          "arr_time": "2025-12-16 10:44:00",
          "p_leg": 0.9999999389003686,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 436,
            "target_ts": "2025-12-16 10:40:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 3321,
          "train_no": "D1008162",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 12:00:00",
          "arr_time": "2025-12-16 12:42:00",
          "p_leg": 0.99999868754871,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 318,
            "target_ts": "2025-12-16 12:40:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 76
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.99999868754871,
      "legs": [
        {
          "train_id": 281,
          "train_no": "KTX377",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 10:40:00",
          "arr_time": "2025-12-16 11:35:00",
          "p_leg": 1,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 385,
            "target_ts": "2025-12-16 11:30:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 3321,
          "train_no": "D1008162",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 12:00:00",
          "arr_time": "2025-12-16 12:42:00",
          "p_leg": 0.99999868754871,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 318,
            "target_ts": "2025-12-16 12:40:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 25
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.9999986108565104,
      "legs": [
        {
          "train_id": 270,
          "train_no": "KTX366",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 06:30:00",
          "arr_time": "2025-12-16 07:25:00",
          "p_leg": 0.9999999292194843,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 635,
            "target_ts": "2025-12-16 07:20:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 76,
          "train_no": "KTX172",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 11:00:00",
          "arr_time": "2025-12-16 13:00:00",
          "p_leg": 0.9999986108565104,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 300,
            "target_ts": "2025-12-16 13:00:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 215
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.9999986108565104,
      "legs": [
        {
          "train_id": 2418,
          "train_no": "D0910161",
          "dep": "NAT010000",
          "arr": "NAT011668",
          "dep_time": "2025-12-16 10:00:00",
          "arr_time": "2025-12-16 10:44:00",
          "p_leg": 0.9999999389003686,
          "explain": {
            "segment": "NAT010000->NAT011668",
            "slack_min": 436,
            "target_ts": "2025-12-16 10:40:00",
            "is_risky_segment": false
          }
        },
        {
          "train_id": 76,
          "train_no": "KTX172",
          "dep": "NAT011668",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 11:00:00",
          "arr_time": "2025-12-16 13:00:00",
          "p_leg": 0.9999986108565104,
          "explain": {
            "segment": "NAT011668->NAT014445",
            "slack_min": 300,
            "target_ts": "2025-12-16 13:00:00",
            "is_risky_segment": false
          }
        }
      ],
      "transfer": {
        "station": "대전",
        "min_transfer": 16
      },
      "has_risky": false
    },
    {
      "transfers": 1,
      "p_on_time": 0.9999984267621291,
      "legs": [
        {
          "train_id": 2715,
          "train_no": "D0912165",
          "dep": "NAT010000",
          "arr": "NAT013271",
          "dep_time": "2025-12-16 06:48:00",
          "arr_time": "2025-12-16 08:46:00",
          "p_leg": 1,
          "explain": {
            "segment": "NAT010000->NAT013271",
            "slack_min": 554,
            "target_ts": "2025-12-16 08:40:00",
            "is_risky_segment": true
          }
        },
        {
          "train_id": 3303,
          "train_no": "D1208161",
          "dep": "NAT013271",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 11:12:00",
          "arr_time": "2025-12-16 11:55:00",
          "p_leg": 0.9999984267621291,
          "explain": {
            "segment": "NAT013271->NAT014445",
            "slack_min": 365,
            "target_ts": "2025-12-16 11:50:00",
            "is_risky_segment": true
          }
        }
      ],
      "transfer": {
        "station": "동대구",
        "min_transfer": 146
      },
      "has_risky": true
    },
    {
      "transfers": 1,
      "p_on_time": 0.9999977156109922,
      "legs": [
        {
          "train_id": 2715,
          "train_no": "D0912165",
          "dep": "NAT010000",
          "arr": "NAT013271",
          "dep_time": "2025-12-16 06:48:00",
          "arr_time": "2025-12-16 08:46:00",
          "p_leg": 1,
          "explain": {
            "segment": "NAT010000->NAT013271",
            "slack_min": 554,
            "target_ts": "2025-12-16 08:40:00",
            "is_risky_segment": true
          }
        },
        {
          "train_id": 215,
          "train_no": "KTX311",
          "dep": "NAT013271",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 10:40:00",
          "arr_time": "2025-12-16 12:00:00",
          "p_leg": 0.9999977156109922,
          "explain": {
            "segment": "NAT013271->NAT014445",
            "slack_min": 360,
            "target_ts": "2025-12-16 12:00:00",
            "is_risky_segment": true
          }
        }
      ],
      "transfer": {
        "station": "동대구",
        "min_transfer": 114
      },
      "has_risky": true
    },
    {
      "transfers": 1,
      "p_on_time": 0.9999940188299324,
      "legs": [
        {
          "train_id": 2715,
          "train_no": "D0912165",
          "dep": "NAT010000",
          "arr": "NAT013271",
          "dep_time": "2025-12-16 06:48:00",
          "arr_time": "2025-12-16 08:46:00",
          "p_leg": 1,
          "explain": {
            "segment": "NAT010000->NAT013271",
            "slack_min": 554,
            "target_ts": "2025-12-16 08:40:00",
            "is_risky_segment": true
          }
        },
        {
          "train_id": 208,
          "train_no": "KTX304",
          "dep": "NAT013271",
          "arr": "NAT014445",
          "dep_time": "2025-12-16 11:00:00",
          "arr_time": "2025-12-16 12:20:00",
          "p_leg": 0.9999940188299324,
          "explain": {
            "segment": "NAT013271->NAT014445",
            "slack_min": 340,
            "target_ts": "2025-12-16 12:20:00",
            "is_risky_segment": true
          }
        }
      ],
      "transfer": {
        "station": "동대구",
        "min_transfer": 134
      },
      "has_risky": true
    }
  ]
}
```

### 해석

아래 응답은 **“서울 → 부산, 18:00까지 도착”** 조건에서, DB에서 찾은 환승 후보들을 **LSTM(MDN)으로 지연 분포를 예측해 ‘제시간 도착 확률’로 정렬**한 결과야.

---

## 최상위 필드 설명

- **from / to**: 사용자가 입력한 출발/도착 역 이름
- **deadline**: 사용자가 “이 시간까지 도착했으면” 하는 목표 도착 시각
  → 각 leg(구간)가 이 deadline을 만족할 확률을 계산할 때 기준으로 사용됨
- **route_agg**: 구간 확률을 “한 경로(route)” 확률로 합치는 방식

  - `"min"`이면 **route의 p_on_time = 각 leg p_leg 중 최솟값**
    (즉, 한 구간이라도 위험하면 전체 경로는 위험하게 봄)

- **count**: DB에서 조건에 맞게 찾은 후보 경로 수 (여기선 455개)
- **results**: 그 후보들 중 상위 `topk=10`개를 확률 기준으로 정렬한 목록

---

## results[n] (한 개 추천 경로) 필드 설명

### 1) transfers

- 환승 횟수
- 예: `1`이면 **2개의 열차(2 legs) + 환승 1회**

### 2) p_on_time

- **이 경로를 선택했을 때, deadline 이전에 “문제 없이” 도착할 확률**
- `route_agg="min"`이므로:

  - `p_on_time = min(p_leg1, p_leg2)` (2 legs일 때)
  - 3 legs면 `min(p_leg1, p_leg2, p_leg3)`

### 3) legs (구간 목록)

각 leg는 “한 번의 열차 탑승(한 구간)”을 의미해.

각 leg의 필드:

- **train_id / train_no**: DB trains 테이블의 id와 열차 번호
- **dep / arr**: 출발/도착 역의 `station_code` (예: NAT010000)
- **dep_time / arr_time**: DB상 계획된 출발/도착 시간(시간표)
- **p_leg**: 이 leg가 **deadline을 맞출 확률**
  (엄밀히는 “해당 leg의 도착이 deadline까지 허용되는 slack 안에서 끝날 확률”)
- **explain**: 모델이 확률을 계산할 때 사용한 핵심 메타정보

### 4) transfer

- 환승 정보
- `station`: 환승역 이름
- `min_transfer`: 실제 환승 가능한 시간(분)
  = `(다음 열차 dep_time) - (이전 열차 arr_time)` 분
  예: 135면 “대전에서 135분 환승 대기시간”이 있다는 뜻

### 5) has_risky

- 너의 시나리오에서 **위험역(동대구 NAT013271, 전주 NAT040257)을 경유하는지**
- `true`면 추천에서 밀리도록(하단 배치) 사용할 수 있는 플래그

---

## explain 안의 필드 설명 (각 leg별)

- **segment**: 모델이 예측하는 구간 키
  예: `"NAT010000->NAT011668"`
- **slack_min**: “deadline까지 남아있는 여유 시간(분)”
  = `deadline - planned_arrival_time`
  예: `slack_min=635`면, 이 구간이 예정대로 도착하면 deadline까지 635분 여유가 있다는 뜻
  → 여유가 크면 p_leg가 거의 1에 가까워짐
- **target_ts**: 과거 지연 히스토리를 조회할 때 사용한 **버킷 기준 시간**
  (예: 10분 버킷이면 07:25 도착을 07:20 버킷으로 내림)
- **is_risky_segment**: segment 출발/도착 코드 중 하나라도 (동대구/전주)면 true
  → 모델 설명용(“이 구간 자체가 위험역 포함”) 플래그

---

## 네 결과를 해석하면 (지금 출력의 특징)

- 상위 추천들은 대부분 **대전 환승(transfer_station="대전")**이고 `has_risky=false`
- 뒤쪽에 **동대구 경유** 루트가 나오기 시작하면서:

  - explain의 `is_risky_segment=true`
  - `has_risky=true`
  - p_on_time이 아주 미세하게 낮아짐

- 근데 지금은 deadline이 18:00이라 slack이 엄청 커서(300~600분대)
  대부분 확률이 0.99999…로 거의 1에 가까워 보여.

> 실제로 “위험역 회피 효과”가 더 확실히 보이게 하려면
> deadline을 더 타이트하게(예: 12:30~13:00) 주면 risky 루트 확률이 확 떨어지고 랭킹이 더 아래로 내려갈 거야.

---

원하면 내가 이 응답 JSON을 기준으로 **프론트에서 바로 쓰기 좋은 형태(예: “총 소요시간/도착예정/환승여유/리스크 경고 메시지”)로 변환하는 응답 스키마**도 같이 설계해줄게.
