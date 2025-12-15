from __future__ import annotations
import pandas as pd

RISKY_CODES = {"NAT013271", "NAT040257"}  # 동대구/전주


def _to_dt(x) -> pd.Timestamp:
    return pd.to_datetime(x)


def _mins(a: pd.Timestamp, b: pd.Timestamp) -> float:
    return (b - a).total_seconds() / 60.0


def risk_level(has_risky: bool, min_transfer_wait: float, p_on_time: float) -> str:
    if has_risky and (min_transfer_wait < 20 or p_on_time < 0.7):
        return "HIGH"
    if has_risky:
        return "MED"
    return "LOW"


def present_recommendation_v2(
    raw: dict,
    *,
    query: dict,
    topk: int,
    station_code_to_name: dict[str, str] | None = None,
) -> dict:
    # ✅ deadline은 raw가 아니라 query에서 가져오는 게 맞음
    deadline = _to_dt(query["deadline"])
    min_transfer_min = float(query.get("min_transfer_min", 0))

    routes = []
    for i, r in enumerate(raw.get("results", [])):
        legs = r["legs"]
        dep_time = _to_dt(legs[0]["dep_time"])
        arr_time = _to_dt(legs[-1]["arr_time"])

        total_duration = _mins(dep_time, arr_time)
        arrival_slack = max(0.0, _mins(arr_time, deadline)
                            )  # deadline - arrival

        # transfer summary
        transfer_summary = []
        min_transfer_wait = 10**9

        if int(r.get("transfers", 0)) == 1:
            wait = float(r["transfer"]["min_transfer"])
            min_transfer_wait = min(min_transfer_wait, wait)
            transfer_summary.append(
                {
                    "station": r["transfer"]["station"],
                    "transfer_wait_min": wait,
                    "ok": wait >= min_transfer_min,
                }
            )

        elif int(r.get("transfers", 0)) == 2:
            stations = r["transfer"]["stations"]
            waits = r["transfer"]["mins"]
            for st, w in zip(stations, waits):
                w = float(w)
                min_transfer_wait = min(min_transfer_wait, w)
                transfer_summary.append(
                    {
                        "station": st,
                        "transfer_wait_min": w,
                        "ok": w >= min_transfer_min,
                    }
                )

        # risky stations list (segment 기반)
        risky_stations = []
        for lg in legs:
            seg = lg.get("explain", {}).get("segment", "")
            if "->" in seg:
                a, b = seg.split("->", 1)
                if a in RISKY_CODES and a not in risky_stations:
                    risky_stations.append(a)
                if b in RISKY_CODES and b not in risky_stations:
                    risky_stations.append(b)

        has_risky = bool(r.get("has_risky", False))
        effective_min_wait = float(
            min_transfer_wait if min_transfer_wait != 10**9 else 9999)
        rl = risk_level(has_risky, effective_min_wait, float(r["p_on_time"]))

        # user messages
        msgs = []
        msgs.append(
            f"{deadline.strftime('%H:%M')}까지 도착 여유 {int(arrival_slack)}분")
        if int(r.get("transfers", 0)) == 0:
            msgs.append("직행")
        elif int(r.get("transfers", 0)) == 1:
            msgs.append(
                f"환승 1회 ({transfer_summary[0]['station']}), 환승 여유 {int(transfer_summary[0]['transfer_wait_min'])}분"
            )
        else:
            msgs.append(f"환승 2회, 최소 환승 여유 {int(effective_min_wait)}분")

        if has_risky:
            msgs.append("동대구/전주 경유 구간 포함 → 지연 리스크")

        # legs pretty
        out_legs = []
        for lg in legs:
            d = _to_dt(lg["dep_time"])
            a = _to_dt(lg["arr_time"])
            dur = _mins(d, a)
            seg = lg.get("explain", {}).get("segment")

            out_legs.append(
                {
                    "train_id": lg["train_id"],
                    "train_no": lg["train_no"],
                    "from_code": lg["dep"],
                    "to_code": lg["arr"],
                    "dep_time": d.isoformat(sep="T", timespec="seconds"),
                    "arr_time": a.isoformat(sep="T", timespec="seconds"),
                    "leg_duration_min": float(dur),
                    "leg_on_time_probability": float(lg["p_leg"]),
                    "segment": seg,
                    "segment_is_risky": bool(lg.get("explain", {}).get("is_risky_segment", False)),
                }
            )

        routes.append(
            {
                "route_id": f"r_{i}",
                "rank": i + 1,
                "transfers": int(r["transfers"]),
                "departure_time": dep_time.isoformat(sep="T", timespec="seconds"),
                "arrival_time": arr_time.isoformat(sep="T", timespec="seconds"),
                "total_duration_min": float(total_duration),
                "arrival_slack_min": float(arrival_slack),
                "on_time_probability": float(r["p_on_time"]),
                "risk": {
                    "has_risky_station": has_risky,
                    "risky_stations": risky_stations,
                    "risk_level": rl,
                },
                "transfer_summary": transfer_summary,
                "user_messages": msgs,
                "legs": out_legs,
                "debug": {
                    "agg": raw.get("route_agg"),
                    "explain": [lg.get("explain", {}) for lg in legs],
                },
            }
        )

    return {
        "query": query,
        "meta": {
            "candidate_count": int(raw.get("count", 0)),
            "returned": min(int(topk), len(routes)),
        },
        "routes": routes[: int(topk)],
    }
