CREATE TABLE IF NOT EXISTS segment_delay_buckets (
  segment VARCHAR(80) NOT NULL,
  ts DATETIME NOT NULL,     -- bucketed timestamp (e.g. 10min)
  y FLOAT NOT NULL,         -- avg delay minutes
  PRIMARY KEY(segment, ts),
  KEY idx_ts(ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;