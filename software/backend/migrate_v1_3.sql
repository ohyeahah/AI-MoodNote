-- v1.2 -> v1.3 : 이미 만든 moodnote DB에 새 칸 2개를 추가한다. (데이터는 지워지지 않는다)
-- 실행: mysql -u root -p moodnote < migrate_v1_3.sql    (한 번만. 두 번 실행하면 "Duplicate column" 오류가 나는데, 이미 올라갔다는 뜻이라 괜찮다)
USE moodnote;
ALTER TABLE daily_condition ADD COLUMN water_cups TINYINT NULL AFTER caffeine_cups;
ALTER TABLE daily_condition ADD CONSTRAINT chk_dc_water CHECK (water_cups BETWEEN 0 AND 30);
ALTER TABLE diary_entries ADD COLUMN ai_suggested_word_ids VARCHAR(20) NULL AFTER automatic_thought;
