from __future__ import annotations

import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests
import mysql.connector
from dotenv import load_dotenv


BASE = "https://apis.data.go.kr/1613000/TrainInfoService"
URL_CITY_CODES = f"{BASE}/getCtyCodeList"
URL_STATIONS_BY_CITY = f"{BASE}/getCtyAcctoTrainSttnList"


def normalize_service_key(key: str) -> str:
    # 인코딩 키(%2F 등)면 requests가 %를 다시 인코딩(%25)해서 깨질 수 있으니 unquote
    # 디코딩 키면 그대로 유지
    if "%" in key:
        return urllib.parse.unquote(key)
    return key


def request_json(url: str, params: Dict[str, Any], timeout: float = 10.0) -> dict:
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "train-loader/1.0",
    }
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def safe_items(data: dict) -> List[dict]:
    """
    응답 형태:
    response.body.items.item 이 list 또는 dict 또는 ""(빈 문자열)로 올 수 있어서 방어.
    """
    resp = data.get("response") or {}
    body = resp.get("body") or {}
    items = body.get("items")

    if not items or isinstance(items, str):
        return []

    item = items.get("item", [])
    if item is None:
        return []
    if isinstance(item, list):
        return item
    if isinstance(item, dict):
        return [item]
    return []


def fetch_city_codes(service_key: str) -> List[Tuple[int, str]]:
    params = {
        "serviceKey": service_key,
        "_type": "json",
        "pageNo": 1,
        "numOfRows": 200,
    }
    data = request_json(URL_CITY_CODES, params)
    items = safe_items(data)
    out: List[Tuple[int, str]] = []
    for it in items:
        code = it.get("citycode")
        name = it.get("cityname")
        if code is None or name is None:
            continue
        out.append((int(code), str(name)))
    return out


def fetch_stations_for_city(service_key: str, city_code: int, num_of_rows: int = 1000) -> List[dict]:
    params = {
        "serviceKey": service_key,
        "_type": "json",
        "cityCode": city_code,
        "pageNo": 1,
        "numOfRows": num_of_rows,
    }
    first = request_json(URL_STATIONS_BY_CITY, params)
    results = safe_items(first)

    # totalCount 기반 추가 페이지 호출(필요 시)
    resp = first.get("response") or {}
    body = resp.get("body") or {}
    total = int(body.get("totalCount") or len(results) or 0)
    page_size = int(body.get("numOfRows") or num_of_rows)

    if total > len(results) and page_size > 0:
        pages = (total + page_size - 1) // page_size
        for p in range(2, pages + 1):
            params["pageNo"] = p
            data = request_json(URL_STATIONS_BY_CITY, params)
            results.extend(safe_items(data))

    return results


def upsert_stations_mysql(
    rows: List[Tuple[str, Optional[str], Optional[int], Optional[str]]],
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
) -> int:
    conn = mysql.connector.connect(
        host=host, port=port, user=user, password=password, database=database, autocommit=False
    )
    try:
        cur = conn.cursor()
        sql = """
        INSERT INTO train.stations (name, station_code, city_code, city_name)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          station_code = VALUES(station_code),
          city_code = VALUES(city_code),
          city_name = VALUES(city_name),
          updated_at = CURRENT_TIMESTAMP
        """
        cur.executemany(sql, rows)
        affected = cur.rowcount
        conn.commit()
        return affected
    finally:
        conn.close()


def main():
    load_dotenv()

    service_key = normalize_service_key(os.environ["TAGO_SERVICE_KEY"])

    mysql_host = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.environ["MYSQL_PASSWORD"]
    mysql_db = os.getenv("MYSQL_DB", "train")

    city_codes = fetch_city_codes(service_key)
    print(f"cityCodes={len(city_codes)}")

    all_rows: List[Tuple[str, Optional[str],
                         Optional[int], Optional[str]]] = []

    for code, cname in city_codes:
        items = fetch_stations_for_city(service_key, code, num_of_rows=1000)
        print(f"cityCode={code} {cname}: items={len(items)}")

        for it in items:
            nodeid = it.get("nodeid")
            nodename = it.get("nodename")
            if not nodename:
                continue
            all_rows.append((str(nodename), str(nodeid)
                            if nodeid else None, int(code), str(cname)))

        time.sleep(0.05)  # 너무 공격적으로 때리지 않게 아주 짧게만

    affected = upsert_stations_mysql(
        rows=all_rows,
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_db,
    )
    print(f"stations: rows={len(all_rows)} affected={affected}")


if __name__ == "__main__":
    main()
