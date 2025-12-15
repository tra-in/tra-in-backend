INSERT INTO segment_delay_buckets(segment, ts, y)
SELECT
  CONCAT(dep_station_code,'->',arr_station_code) AS segment,
  -- 10분 버킷으로 내림(floor)
  DATE_SUB(
    DATE_FORMAT(arr_planned, '%Y-%m-%d %H:%i:00'),
    INTERVAL (MINUTE(arr_planned) % 10) MINUTE
  ) AS ts,
  AVG((TIMESTAMPDIFF(SECOND, arr_planned, arr_actual) / 60.0)) AS y
FROM actual_trains
GROUP BY segment, ts
ON DUPLICATE KEY UPDATE y = VALUES(y);