SELECT
  t1.id AS leg1_train_id, t1.train_no AS leg1_train_no,
  sA.station_code AS leg1_dep_code, sX.station_code AS leg1_arr_code,
  t1.departure_time AS leg1_dep_time, t1.arrival_time AS leg1_arr_time,

  CASE
    WHEN sA.station_code IN ('NAT013271','NAT040257')
      OR sX.station_code IN ('NAT013271','NAT040257')
    THEN 1 ELSE 0
  END AS is_risky_segment_1,

  t2.id AS leg2_train_id, t2.train_no AS leg2_train_no,
  sX.station_code AS leg2_dep_code, sB.station_code AS leg2_arr_code,
  t2.departure_time AS leg2_dep_time, t2.arrival_time AS leg2_arr_time,

  CASE
    WHEN sX.station_code IN ('NAT013271','NAT040257')
      OR sB.station_code IN ('NAT013271','NAT040257')
    THEN 1 ELSE 0
  END AS is_risky_segment_2,

  sX.name AS transfer_station
FROM trains t1
JOIN trains t2 ON t2.origin_station_id = t1.dest_station_id

JOIN stations sA ON sA.id = t1.origin_station_id
JOIN stations sX ON sX.id = t1.dest_station_id
JOIN stations sB ON sB.id = t2.dest_station_id

WHERE sA.name = :from_name
  AND sB.name = :to_name
  AND t1.departure_time >= :now
  AND t2.arrival_time <= :deadline_plus
  AND t2.departure_time >= DATE_ADD(t1.arrival_time, INTERVAL :min_transfer_min MINUTE)
  AND t2.arrival_time <= DATE_ADD(t1.departure_time, INTERVAL :max_total_hours HOUR)
ORDER BY t1.departure_time
LIMIT :limit;
