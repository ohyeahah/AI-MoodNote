-- v1.6 -> v1.7 : 일기별 '연구 활용' 선택을 위한 열 2개를 추가한다. 기존 일기는 모두 0(연구에 쓰지 않음)으로 시작한다.
-- 실행: sudo mysql moodnote < migrate_v1_7.sql    (두 번 실행해도 안전하다: 이미 있으면 건너뛴다)
USE moodnote;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE diary_entries ADD COLUMN research_use TINYINT(1) NOT NULL DEFAULT 0 AFTER picked_word_ids',
  'SELECT 1') FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'diary_entries' AND column_name = 'research_use');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;

SET @s = (SELECT IF(COUNT(*) = 0,
  'ALTER TABLE users ADD COLUMN research_default TINYINT(1) NOT NULL DEFAULT 0 AFTER password_hash',
  'SELECT 1') FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'users' AND column_name = 'research_default');
PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
