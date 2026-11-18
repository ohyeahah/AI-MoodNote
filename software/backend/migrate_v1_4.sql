-- v1.3 -> v1.4 : 감정을 최대 3개 고를 수 있게 칸 1개를 추가한다. (데이터는 지워지지 않는다)
-- 실행: mysql -u root -p moodnote < migrate_v1_4.sql    (한 번만. 두 번 실행하면 "Duplicate column" 오류가 나는데, 이미 올라갔다는 뜻이라 괜찮다)
USE moodnote;
ALTER TABLE diary_entries ADD COLUMN picked_word_ids VARCHAR(20) NULL AFTER ai_suggested_word_ids;
UPDATE diary_entries SET picked_word_ids = CAST(mood_word_id AS CHAR) WHERE mood_word_id IS NOT NULL AND picked_word_ids IS NULL;
