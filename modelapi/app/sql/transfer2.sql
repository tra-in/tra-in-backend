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
  sX.station_code AS leg2_dep_code, sY.station_code AS leg2_arr_code,
  t2.departure_time AS leg2_dep_time, t2.arrival_time AS leg2_arr_time,

  CASE
    WHEN sX.station_code IN ('NAT013271','NAT040257')
      OR sY.station_code IN ('NAT013271','NAT040257')
    THEN 1 ELSE 0
  END AS is_risky_segment_2,

  t3.id AS leg3_train_id, t3.train_no AS leg3_train_no,
  sY.station_code AS leg3_dep_code, sB.station_code AS leg3_arr_code,
  t3.departure_time AS leg3_dep_time, t3.arrival_time AS leg3_arr_time,

  CASE
    WHEN sY.station_code IN ('NAT013271','NAT040257')
      OR sB.station_code IN ('NAT013271','NAT040257')
    THEN 1 ELSE 0
  END AS is_risky_segment_3,

  sX.name AS transfer1_name,
  sY.name AS transfer2_name
FROM trains t1
JOIN trains t2 ON t2.origin_station_id = t1.dest_station_id
JOIN trains t3 ON t3.origin_station_id = t2.dest_station_id

JOIN stations sA ON sA.id = t1.origin_station_id
JOIN stations sX ON sX.id = t1.dest_station_id
JOIN stations sY ON sY.id = t2.dest_station_id
JOIN stations sB ON sB.id = t3.dest_station_id

WHERE sA.name = :from_name
  AND sB.name = :to_name
  AND t1.departure_time >= :now
  AND t3.arrival_time <= :deadline_plus

  AND t2.departure_time >= DATE_ADD(t1.arrival_time, INTERVAL :min_transfer_min MINUTE)
  AND t3.departure_time >= DATE_ADD(t2.arrival_time, INTERVAL :min_transfer_min MINUTE)

  AND t3.arrival_time <= DATE_ADD(t1.departure_time, INTERVAL :max_total_hours HOUR)

  AND sX.id <> sY.id
  AND sA.id <> sY.id
  AND sX.id <> sB.id
ORDER BY t1.departure_time
LIMIT :limit;
