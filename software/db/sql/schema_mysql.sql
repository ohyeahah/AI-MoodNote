-- MoodNote 스키마 v1.2 (MySQL 8.0.16 이상 기준)
-- 변경 기록: v1.1 최초(테이블 10개) / v1.2 daily_condition 숫자화 + caffeine_cups, menstrual_cycles, cycle_tracking 동의 추가(11개). 회의 확정 필요
-- schema.sql(SQLite)의 MySQL 변환본. 구조와 제약은 같고, 문법만 다르다.
-- 검증: MariaDB 10.11(MySQL 호환)에서 실행해 테이블 생성, 제약 차단, CASCADE 삭제를 확인했다.
--       MySQL 8.0 자체에서는 아직 돌려보지 않았다. 처음 실행할 때 오류가 나면 팀에 알린다.
--
-- SQLite와 달라진 점
-- 1) id: TEXT 대신 CHAR(36) (UUID 문자열). PRIMARY KEY에는 길이가 있는 타입이 필요하다.
-- 2) 날짜: TEXT 대신 DATE / DATETIME. 현재 시각 기본값은 CURRENT_TIMESTAMP.
-- 3) PRAGMA foreign_keys 줄이 없다. InnoDB는 외래키가 항상 켜져 있다.
-- 4) CHECK 제약은 MySQL 8.0.16 이상에서만 실제로 적용된다. (그 아래 버전은 무시됨)
-- 5) 문자셋은 utf8mb4 (한글, 이모지 저장).
-- 민감 필드(일기 본문, 트라우마 등)는 앱 레이어에서 암호화해 저장한다. 음성 원본은 DB에 저장하지 않는다.

CREATE DATABASE IF NOT EXISTS moodnote DEFAULT CHARACTER SET utf8mb4;
USE moodnote;

CREATE TABLE users (
  id            CHAR(36)     NOT NULL PRIMARY KEY,
  nickname      VARCHAR(50)  NOT NULL,
  login_id      VARCHAR(64)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_profile (
  id                CHAR(36) NOT NULL PRIMARY KEY,
  user_id           CHAR(36) NOT NULL UNIQUE,
  characteristics   TEXT,
  dreams_goals      TEXT,
  occupation        TEXT,
  childhood_trauma  TEXT,   -- 민감: 선택 입력, 암호화 대상
  thinking_patterns TEXT,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE relationships (
  id                CHAR(36)     NOT NULL PRIMARY KEY,
  user_id           CHAR(36)     NOT NULL,
  person_name       VARCHAR(100) NOT NULL,
  relationship_type VARCHAR(50),
  notes             TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 무드미터 100단어 고정 좌표표 (참조 데이터)
-- id = (grid_row - 1) * 10 + grid_col, energy = 11 - grid_row, pleasantness = grid_col
-- 한국어 단어는 중복될 수 있으므로 (grid_row, grid_col)이 기준 키다.
CREATE TABLE mood_words (
  id           INT         NOT NULL PRIMARY KEY,
  word_ko      VARCHAR(30) NOT NULL,
  word_en      VARCHAR(30),
  grid_row     TINYINT     NOT NULL,
  grid_col     TINYINT     NOT NULL,
  energy       TINYINT     NOT NULL,
  pleasantness TINYINT     NOT NULL,
  zone         VARCHAR(10) NOT NULL,
  UNIQUE KEY uq_mood_grid (grid_row, grid_col),
  CONSTRAINT chk_mw_row  CHECK (grid_row BETWEEN 1 AND 10),
  CONSTRAINT chk_mw_col  CHECK (grid_col BETWEEN 1 AND 10),
  CONSTRAINT chk_mw_id   CHECK (id = (grid_row - 1) * 10 + grid_col),
  CONSTRAINT chk_mw_en   CHECK (energy = 11 - grid_row),
  CONSTRAINT chk_mw_pl   CHECK (pleasantness = grid_col),
  CONSTRAINT chk_mw_zone CHECK (zone IN ('red','yellow','blue','green'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE diary_entries (
  id                CHAR(36)    NOT NULL PRIMARY KEY,
  user_id           CHAR(36)    NOT NULL,
  mood_word_id      INT         NULL,        -- 음성 일기는 나중에 선택하므로 NULL 허용
  entry_date        DATE        NOT NULL,
  content           TEXT        NOT NULL,    -- 민감: 암호화 대상
  source            VARCHAR(10) NOT NULL DEFAULT 'text',
  trigger_event     TEXT,                    -- 선택 입력 (회의 결정 반영)
  automatic_thought TEXT,                    -- 선택 입력 (화면에서는 "그때 든 생각")
  created_at        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_diary_source CHECK (source IN ('text','voice')),
  FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE,
  FOREIGN KEY (mood_word_id) REFERENCES mood_words(id),
  INDEX idx_diary_user_date (user_id, entry_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ai_feedback (
  id               CHAR(36)    NOT NULL PRIMARY KEY,
  entry_id         CHAR(36)    NOT NULL,
  feedback_type    VARCHAR(20) NOT NULL,
  feedback_text    TEXT        NOT NULL,
  perceived_desire TEXT,       -- AI의 추정(가설). 사용자가 확인한 것만 self_model로 올린다.
  user_reaction    VARCHAR(20),
  user_note        TEXT,
  created_at       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_fb_type     CHECK (feedback_type IN ('empathy','reframe','body_care')),
  CONSTRAINT chk_fb_reaction CHECK (user_reaction IN ('helpful','not_helpful','neutral')),
  FOREIGN KEY (entry_id) REFERENCES diary_entries(id) ON DELETE CASCADE,
  INDEX idx_feedback_entry (entry_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 하루 상태: 모든 칸은 비워둘 수 있다(선택 입력). 텍스트 대신 숫자로 저장한다.
-- 1~5 척도의 뜻(팀 확정 필요): sleep_score 1=매우 나쁨 ~ 5=매우 좋음 / appetite_score 1=거의 없음 ~ 5=아주 좋음 /
--                              bowel_score 1=매우 불편 ~ 5=매우 편안
CREATE TABLE daily_condition (
  id               CHAR(36)      NOT NULL PRIMARY KEY,
  user_id          CHAR(36)      NOT NULL,
  log_date         DATE          NOT NULL,
  sleep_hours      DECIMAL(4,2),               -- 객관 값(웨어러블 연동 가능)
  sleep_score      TINYINT,                    -- 주관 값 1~5
  meal_count       TINYINT,                    -- 끼니 수
  appetite_score   TINYINT,                    -- 식욕 1~5
  bowel_score      TINYINT,                    -- 배변 상태 1~5
  exercise_minutes SMALLINT,                   -- 운동 시간(분)
  caffeine_cups    TINYINT,                    -- 카페인 음료(잔), 선택
  source           VARCHAR(10)   NOT NULL DEFAULT 'self',
  UNIQUE KEY uq_condition (user_id, log_date, source),
  CONSTRAINT chk_dc_hours    CHECK (sleep_hours BETWEEN 0 AND 24),
  CONSTRAINT chk_dc_score    CHECK (sleep_score BETWEEN 1 AND 5),
  CONSTRAINT chk_dc_meals    CHECK (meal_count BETWEEN 0 AND 10),
  CONSTRAINT chk_dc_appetite CHECK (appetite_score BETWEEN 1 AND 5),
  CONSTRAINT chk_dc_bowel    CHECK (bowel_score BETWEEN 1 AND 5),
  CONSTRAINT chk_dc_exercise CHECK (exercise_minutes BETWEEN 0 AND 1440),
  CONSTRAINT chk_dc_caffeine CHECK (caffeine_cups BETWEEN 0 AND 20),
  CONSTRAINT chk_dc_source   CHECK (source IN ('self','wearable')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_condition_user_date (user_id, log_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 월경 주기 기록(선택 기능, 별도 동의 cycle_tracking). 시작일과 종료일만 저장한다.
-- 주기 길이와 "주기 몇 일째인지"는 저장하지 않고 조회할 때 계산한다. 기본적으로 AI 프롬프트에 넣지 않는다.
CREATE TABLE menstrual_cycles (
  id         CHAR(36) NOT NULL PRIMARY KEY,
  user_id    CHAR(36) NOT NULL,
  start_date DATE     NOT NULL,
  end_date   DATE     NULL,                          -- 아직 진행 중이면 NULL
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cycle_start (user_id, start_date),
  CONSTRAINT chk_cycle_dates CHECK (end_date IS NULL OR end_date >= start_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_cycles_user (user_id, start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11/18에는 테이블만 만들고 자동 갱신은 하지 않는다.
CREATE TABLE self_model (
  id                 CHAR(36) NOT NULL PRIMARY KEY,
  user_id            CHAR(36) NOT NULL UNIQUE,
  confirmed_patterns TEXT,
  probable_patterns  TEXT,
  hypotheses         TEXT,
  unknown_areas      TEXT,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 안전장치 기록. 일기 본문은 복사해 저장하지 않는다. 접근은 시스템만.
CREATE TABLE safety_events (
  id           CHAR(36)    NOT NULL PRIMARY KEY,
  user_id      CHAR(36)    NOT NULL,
  entry_id     CHAR(36)    NULL,               -- 패턴(L3)은 NULL
  `level`      TINYINT     NOT NULL,
  trigger_type VARCHAR(10) NOT NULL,
  created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_se_level CHECK (`level` IN (1,2,3)),
  CONSTRAINT chk_se_type  CHECK (trigger_type IN ('keyword','llm','pattern')),
  FOREIGN KEY (user_id)  REFERENCES users(id)         ON DELETE CASCADE,
  FOREIGN KEY (entry_id) REFERENCES diary_entries(id) ON DELETE CASCADE,
  INDEX idx_safety_user (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 동의 기록. 동의 행이 없으면 "동의 안 함"이다(기본 off).
CREATE TABLE consents (
  id           CHAR(36)    NOT NULL PRIMARY KEY,
  user_id      CHAR(36)    NOT NULL,
  consent_type VARCHAR(30) NOT NULL,
  version      VARCHAR(20) NOT NULL,           -- 동의 문구 버전
  granted_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  revoked_at   DATETIME    NULL,               -- 철회하면 시각을 채운다
  CONSTRAINT chk_consent_type CHECK (consent_type IN
    ('diary_storage','voice_processing','ai_counseling','expert_export','ai_training','cycle_tracking')),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_consents_user (user_id, consent_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- AI 학습 동의 여부는 consents에서 계산한다(같은 값을 두 곳에 저장하지 않기 위해 별도 컬럼을 두지 않는다).
CREATE VIEW v_ai_training_opt_in AS
SELECT u.id AS user_id,
       EXISTS (
         SELECT 1 FROM consents c
         WHERE c.user_id = u.id AND c.consent_type = 'ai_training' AND c.revoked_at IS NULL
       ) AS opted_in
FROM users u;
