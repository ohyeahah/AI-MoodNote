-- v1.5 -> v1.6 : 소셜 로그인(카카오/네이버/구글)을 위한 user_identities 테이블을 추가한다. (기존 데이터는 그대로)
-- 실행: mysql -u root -p moodnote < migrate_v1_6.sql    (두 번 실행해도 안전하다)
USE moodnote;
CREATE TABLE IF NOT EXISTS user_identities (
  id               CHAR(36)     NOT NULL PRIMARY KEY,
  user_id          CHAR(36)     NOT NULL,
  provider         VARCHAR(10)  NOT NULL,
  provider_user_id VARCHAR(100) NOT NULL,
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_ident_provider CHECK (provider IN ('kakao','naver','google')),
  UNIQUE KEY uq_ident_provider_user (provider, provider_user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_ident_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
