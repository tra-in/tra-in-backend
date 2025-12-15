from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, date
from itertools import product
from typing import Any, Dict, Iterable, List, Optional, Tuple

import mysql.connector
import requests
from dotenv import load_dotenv


# -----------------------
# TAGO endpoints
# -----------------------
BASE_SERVICE_URL = "http://apis.data.go.kr/1613000/TrainInfoService"
# 공식 문서 :contentReference[oaicite:1]{index=1}
URL_TIMETABLE = f"{BASE_SERVICE_URL}/getStrtpntAlocFndTrainInfo"
URL_CITY_CODES = f"{BASE_SERVICE_URL}/getCtyCodeList"
URL_STATIONS_BY_CITY = f"{BASE_SERVICE_URL}/getCtyAcctoTrainSttnList"


# -----------------------
# Config
# -----------------------
HUB_NAMES = ["서울", "부산", "대전", "동대구", "경주", "전주"]

# 필요 날짜(원하면 늘리세요)
DATES = [date(2025, 12, 16), date(2025, 12, 17), date(2025, 12, 18)]

# 도시 이름 매칭(도시코드 목록 조회의 cityname 기준)
# - 공공데이터의 cityname 표기가 "전라북도/전북특별자치도"처럼 바뀔 수 있어 후보를 여러 개 둠
CITYNAME_CANDIDATES = [
    "서울", "서울특별시",
    "부산", "부산광역시",
    "대전", "대전광역시",
    "대구", "대구광역시",
    "경상북도", "경북",
    "전라북도", "전북", "전북특별자치도",
]

# "역 이름"이 어느 시/도에 속하는지 힌트(도시코드 목록을 좁혀서 API 호출 수를 줄이기 위함)
STATION_TO_CITYNAME_HINTS: Dict[str, List[str]] = {
    "서울": ["서울", "서울특별시"],
    "부산": ["부산", "부산광역시"],
    "대전": ["대전", "대전광역시"],
    "동대구": ["대구", "대구광역시"],
    "경주": ["경상북도", "경북"],
    "전주": ["전라북도", "전북", "전북특별자치도"],
}


# -----------------------
# Utilities
# -----------------------
def yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def parse_dt_yyyymmddhhmmss(s: Any) -> Optional[datetime]:
    if s is None:
        return None
    s = str(s)
    try:
        return datetime.strptime(s, "%Y%m%d%H%M%S")
    except Exception:
        return None


def safe_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


# -----------------------
# SQLite cache for HTTP (minimize traffic)
# -----------------------
class SqliteCache:
    def __init__(self, path: str = "tago_http_cache.sqlite3") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
              key TEXT PRIMARY KEY,
              created_at INTEGER NOT NULL,
              payload TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def get(self, key: str) -> Optional[dict]:
        cur = self.conn.execute(
            "SELECT payload FROM cache WHERE key=?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def set(self, key: str, payload: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO cache(key, created_at, payload) VALUES(?,?,?)",
            (key, int(time.time()), json.dumps(payload, ensure_ascii=False)),
        )
        self.conn.commit()


def stable_key(url: str, params: Dict[str, Any]) -> str:
    raw = url + "?" + \
        "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# -----------------------
# TAGO client
# -----------------------
class TagoClient:
    def __init__(
        self,
        service_key: str,
        cache: Optional[SqliteCache] = None,
        timeout_sec: float = 15.0,
        max_retries: int = 4,
    ) -> None:
        self.service_key = service_key
        self.cache = cache or SqliteCache()
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "User-Agent": "tago-train-loader/1.0",
            }
        )

    def _get_json(self, url: str, params: Dict[str, Any]) -> dict:
        key = stable_key(url, params)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                r = self.session.get(url, params=params,
                                     timeout=self.timeout_sec)
                r.raise_for_status()
                data = r.json()
                self.cache.set(key, data)
                return data
            except Exception as e:
                last_err = e
                time.sleep(0.4 * (2 ** attempt))
        raise RuntimeError(f"TAGO request failed: {last_err}")

    @staticmethod
    def _body(data: dict) -> dict:
        return (data.get("response") or {}).get("body") or {}

    @staticmethod
    def _items_list(data: dict) -> List[dict]:
        """
        방어 포인트:
        - body/items/items.item 이 dict/list가 아니라 ""(str) 또는 None인 경우가 있음
        """
        body = TagoClient._body(data)
        items = body.get("items")

        if items is None:
            return []
        if isinstance(items, str):
            # 예: items: ""  (이 케이스 때문에 'str has no attribute get' 터짐)
            return []
        if not isinstance(items, dict):
            return []

        item = items.get("item", [])
        if item is None:
            return []
        if isinstance(item, str):
            return []
        if isinstance(item, list):
            return item
        if isinstance(item, dict):
            return [item]
        return []

    # --------
    # City codes
    # --------
    def fetch_city_codes(self, num_of_rows: int = 1000) -> List[dict]:
        params = {
            "serviceKey": self.service_key,
            "_type": "json",
            "pageNo": 1,
            "numOfRows": num_of_rows,
        }
        data = self._get_json(URL_CITY_CODES, params)
        rows = self._items_list(data)

        # 페이징 필요 시 (보통 1회로 충분)
        total = safe_int(self._body(data).get("totalCount")) or len(rows)
        if total > len(rows):
            page_size = safe_int(self._body(
                data).get("numOfRows")) or num_of_rows
            pages = (total + page_size - 1) // page_size
            for p in range(2, pages + 1):
                params["pageNo"] = p
                data2 = self._get_json(URL_CITY_CODES, params)
                rows.extend(self._items_list(data2))
        return rows

    # --------
    # Stations by cityCode
    # --------
    def fetch_stations_by_city(self, city_code: str, num_of_rows: int = 1000) -> List[dict]:
        params = {
            "serviceKey": self.service_key,
            "_type": "json",
            "pageNo": 1,
            "numOfRows": num_of_rows,
            "cityCode": city_code,
        }
        data = self._get_json(URL_STATIONS_BY_CITY, params)
        rows = self._items_list(data)

        total = safe_int(self._body(data).get("totalCount")) or len(rows)
        if total > len(rows):
            page_size = safe_int(self._body(
                data).get("numOfRows")) or num_of_rows
            pages = (total + page_size - 1) // page_size
            for p in range(2, pages + 1):
                params["pageNo"] = p
                data2 = self._get_json(URL_STATIONS_BY_CITY, params)
                rows.extend(self._items_list(data2))
        return rows

    # --------
    # Timetable (min traffic)
    # --------
    def fetch_timetable_min_traffic(
        self,
        dep_place_id: str,
        arr_place_id: str,
        dep_pland_date_yyyymmdd: str,
        num_of_rows: int = 1000,
    ) -> List[dict]:
        # trainGradeCode는 옵션이므로 생략(=한 번에 전체 차량종류 포함) -> 트래픽 최소화 :contentReference[oaicite:2]{index=2}
        params = {
            "serviceKey": self.service_key,
            "_type": "json",
            "pageNo": 1,
            "numOfRows": num_of_rows,
            "depPlaceId": dep_place_id,
            "arrPlaceId": arr_place_id,
            "depPlandTime": dep_pland_date_yyyymmdd,
        }
        data = self._get_json(URL_TIMETABLE, params)
        rows = self._items_list(data)

        total = safe_int(self._body(data).get("totalCount")) or len(rows)
        if total > len(rows):
            page_size = safe_int(self._body(
                data).get("numOfRows")) or num_of_rows
            pages = (total + page_size - 1) // page_size
            for p in range(2, pages + 1):
                params["pageNo"] = p
                data2 = self._get_json(URL_TIMETABLE, params)
                rows.extend(self._items_list(data2))
        return rows


# -----------------------
# MySQL helpers
# -----------------------
def mysql_connect_from_env() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "train"),
        autocommit=False,
    )


def ensure_tables(conn: mysql.connector.MySQLConnection) -> None:
    cur = conn.cursor()
    cur.execute(
        "CREATE DATABASE IF NOT EXISTS train DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_0900_ai_ci;")
    cur.execute("USE train;")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stations (
          id BIGINT NOT NULL AUTO_INCREMENT,
          name VARCHAR(100) NOT NULL,
          station_code VARCHAR(30) NULL,
          city_code VARCHAR(10) NULL,
          city_name VARCHAR(100) NULL,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uq_stations_name (name),
          KEY idx_stations_station_code (station_code)
        ) ENGINE=InnoDB;
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS train_timetables (
          id BIGINT NOT NULL AUTO_INCREMENT,
          service_date DATE NOT NULL,
          dep_station_name VARCHAR(100) NOT NULL,
          arr_station_name VARCHAR(100) NOT NULL,
          dep_station_code VARCHAR(30) NOT NULL,
          arr_station_code VARCHAR(30) NOT NULL,
          train_type VARCHAR(50) NULL,
          train_no VARCHAR(20) NOT NULL,
          dep_planned DATETIME NOT NULL,
          arr_planned DATETIME NOT NULL,
          duration_min INT NULL,
          adult_charge INT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uq_timetable (
            service_date, dep_station_code, arr_station_code, train_no, dep_planned, arr_planned
          ),
          KEY idx_route_date (dep_station_code, arr_station_code, service_date)
        ) ENGINE=InnoDB;
        """
    )
    conn.commit()


def upsert_station_by_name(
    conn: mysql.connector.MySQLConnection,
    name: str,
    station_code: Optional[str],
    city_code: Optional[str],
    city_name: Optional[str],
) -> int:
    """
    name UNIQUE를 기준으로 UPSERT 하므로, 기존 row의 id는 유지됩니다.
    """
    sql = """
    INSERT INTO stations (name, station_code, city_code, city_name)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      station_code = VALUES(station_code),
      city_code = VALUES(city_code),
      city_name = VALUES(city_name);
    """
    cur = conn.cursor()
    cur.execute(sql, (name, station_code, city_code, city_name))
    return cur.rowcount


def fetch_station_code_map(conn: mysql.connector.MySQLConnection, names: List[str]) -> Dict[str, Optional[str]]:
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(names))
    cur.execute(
        f"SELECT name, station_code FROM stations WHERE name IN ({placeholders})", names)
    res: Dict[str, Optional[str]] = {n: None for n in names}
    for n, code in cur.fetchall():
        res[n] = code
    return res


def write_timetables(
    conn: mysql.connector.MySQLConnection,
    rows: List[Tuple],
) -> int:
    sql = """
    INSERT INTO train_timetables (
      service_date,
      dep_station_name, arr_station_name,
      dep_station_code, arr_station_code,
      train_type, train_no,
      dep_planned, arr_planned,
      duration_min, adult_charge
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
      train_type = VALUES(train_type),
      duration_min = VALUES(duration_min),
      adult_charge = VALUES(adult_charge);
    """
    cur = conn.cursor()
    cur.executemany(sql, rows)
    return cur.rowcount


# -----------------------
# Station sync (cityCode list -> station list -> update train.stations)
# -----------------------
def sync_hub_station_codes(
    client: TagoClient,
    conn: mysql.connector.MySQLConnection,
    hub_names: List[str],
) -> None:
    city_rows = client.fetch_city_codes(num_of_rows=1000)

    # cityname -> citycode 매핑 만들기
    cityname_to_code: Dict[str, str] = {}
    for r in city_rows:
        # API 응답 필드명은 보통 cityname, citycode 형태(공공데이터 샘플 기준)
        cn = str(r.get("cityname") or "").strip()
        cc = str(r.get("citycode") or "").strip()
        if cn and cc:
            cityname_to_code[cn] = cc

    # 필요한 city만 골라서 호출 수 최소화
    needed_city_codes: Dict[str, str] = {}
    for station_name in hub_names:
        hints = STATION_TO_CITYNAME_HINTS.get(station_name, [])
        for h in hints:
            # 정확히 일치 없으면 포함 검색도 허용
            if h in cityname_to_code:
                needed_city_codes[h] = cityname_to_code[h]
            else:
                for k, v in cityname_to_code.items():
                    if h and h in k:
                        needed_city_codes[k] = v

    # cityCode 별 역목록 조회 -> hub_names에 해당하는 nodename만 반영
    updated = 0
    for city_name, city_code in needed_city_codes.items():
        stations = client.fetch_stations_by_city(
            city_code=city_code, num_of_rows=1000)

        by_name: Dict[str, str] = {}
        for s in stations:
            nodename = str(s.get("nodename") or "").strip()
            nodeid = str(s.get("nodeid") or "").strip()
            if nodename and nodeid:
                by_name[nodename] = nodeid

        for hub in hub_names:
            if hub in by_name:
                updated += upsert_station_by_name(
                    conn,
                    name=hub,
                    station_code=by_name[hub],
                    city_code=city_code,
                    city_name=city_name,
                )

    conn.commit()
    print(f"[stations] upsert affected={updated}")


# -----------------------
# Timetable loading for all ordered hub pairs and dates
# -----------------------
def iter_ordered_pairs(names: List[str]) -> Iterable[Tuple[str, str]]:
    for a, b in product(names, names):
        if a != b:
            yield a, b


def load_all_hub_timetables(
    client: TagoClient,
    conn: mysql.connector.MySQLConnection,
    hub_names: List[str],
    dates: List[date],
) -> None:
    # station_code 확보
    code_map = fetch_station_code_map(conn, hub_names)
    missing = [n for n, c in code_map.items() if not c]
    if missing:
        raise RuntimeError(
            f"stations.station_code 가 비어있는 허브가 있어요: {missing} (먼저 stations 동기화를 성공시켜야 함)")

    total_queries = 0
    total_items = 0
    total_rows_written = 0

    for d in dates:
        d_str = yyyymmdd(d)

        for dep_name, arr_name in iter_ordered_pairs(hub_names):
            dep_code = code_map[dep_name]
            arr_code = code_map[arr_name]
            assert dep_code and arr_code

            items = client.fetch_timetable_min_traffic(
                dep_code, arr_code, d_str, num_of_rows=1000)
            total_queries += 1
            total_items += len(items)

            rows: List[Tuple] = []
            for it in items:
                dep_dt = parse_dt_yyyymmddhhmmss(it.get("depplandtime"))
                arr_dt = parse_dt_yyyymmddhhmmss(it.get("arrplandtime"))
                if not dep_dt or not arr_dt:
                    continue

                duration_min = int((arr_dt - dep_dt).total_seconds() // 60)
                rows.append(
                    (
                        d,                         # service_date
                        dep_name, arr_name,
                        dep_code, arr_code,
                        (it.get("traingradename") or None),
                        str(it.get("trainno") or ""),
                        dep_dt,
                        arr_dt,
                        duration_min,
                        safe_int(it.get("adultcharge")),
                    )
                )

            affected = write_timetables(conn, rows)
            conn.commit()
            total_rows_written += affected

            print(f"[{d_str}] {dep_name}({dep_code}) -> {arr_name}({arr_code}) : items={len(items)} rows={len(rows)} affected={affected}")

    print(
        f"[done] queries={total_queries} items={total_items} mysql_affected={total_rows_written}")


# -----------------------
# Main
# -----------------------
def main() -> None:
    load_dotenv()

    service_key = os.getenv("TAGO_SERVICE_KEY")
    if not service_key:
        raise RuntimeError("TAGO_SERVICE_KEY 가 필요합니다 (.env 또는 환경변수)")

    client = TagoClient(service_key=service_key)

    conn = mysql_connect_from_env()
    try:
        ensure_tables(conn)

        # 1) stations를 name 기준으로 nodeid(station_code) / city_code / city_name 채우기
        sync_hub_station_codes(client, conn, HUB_NAMES)

        # 2) 거점 간 (모든 방향) + 날짜별 시간표 적재
        load_all_hub_timetables(client, conn, HUB_NAMES, DATES)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
