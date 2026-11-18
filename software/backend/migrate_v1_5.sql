-- v1.4 -> v1.5 : 의견 보내기를 위한 feedback 테이블을 추가한다. (기존 데이터는 그대로)
-- 실행: mysql -u root -p moodnote < migrate_v1_5.sql    (두 번 실행해도 안전하다)
USE moodnote;
CREATE TABLE IF NOT EXISTS feedback (
  id         CHAR(36)    NOT NULL PRIMARY KEY,
  user_id    CHAR(36)    NOT NULL,
  category   VARCHAR(10) NOT NULL,
  rating     TINYINT     NULL,
  message    TEXT        NOT NULL,
  status     VARCHAR(10) NOT NULL DEFAULT 'new',
  created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_fbk_category CHECK (category IN ('bug','idea','praise','other')),
  CONSTRAINT chk_fbk_rating   CHECK (rating BETWEEN 1 AND 5),
  CONSTRAINT chk_fbk_status   CHECK (status IN ('new','done')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_feedback_user_date (user_id, created_at),
  INDEX idx_feedback_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
