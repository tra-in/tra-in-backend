from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LSTM/config.yaml 과 동일한 DB를 쓰면 됨
    DB_URL: str = "mysql+pymysql://train_root:train_root@localhost:3306/train?charset=utf8mb4"

    # 모델/아티팩트 경로 (LSTM 프로젝트 기준)
    LSTM_CONFIG_PATH: str = "../LSTM/config.yaml"

    # 추천 정책
    BUCKET_MINUTES: int = 10
    LOOKBACK_STEPS: int = 12
    DEFAULT_MIN_TRANSFER_MIN: int = 15
    DEADLINE_PLUS_MIN: int = 90
    MAX_TOTAL_HOURS: int = 12

    # route 확률 결합 방식: "min" or "product"
    ROUTE_AGG: str = "min"


settings = Settings()
