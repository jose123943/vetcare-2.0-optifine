CREATE TABLE IF NOT EXISTS vc_session (
 token_hash CHAR(64) PRIMARY KEY,
 user_id INT NULL,
 csrf_hash CHAR(64) NOT NULL,
 owner_hash CHAR(64) NOT NULL,
 expires DATETIME(6) NOT NULL,
 created DATETIME(6) NOT NULL,
 INDEX vc_session_expiry (expires),
 FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS vc_login_bucket (
 bucket CHAR(64) PRIMARY KEY,
 attempts INT UNSIGNED NOT NULL DEFAULT 0,
 window_start DATETIME(6) NOT NULL,
 blocked_until DATETIME(6) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
