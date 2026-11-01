-- 개발용 합성(가짜) 데이터. 실제 사용자 기록은 절대 넣지 않는다.
-- 실행 순서: schema_mysql.sql -> mood_words 가져오기 -> 이 파일 (MySQL용)
-- mood_words id = (grid_row - 1) * 10 + grid_col
--   34 = (4,4) 짜증나는, 66 = (7,6) 평온한, 82 = (9,2) 우울한

USE moodnote;

INSERT INTO users (id, nickname, login_id, password_hash) VALUES
  ('u-test-1', '테스트1', 'test1', 'DUMMY_HASH'),
  ('u-test-2', '테스트2', 'test2', 'DUMMY_HASH');

INSERT INTO consents (id, user_id, consent_type, version) VALUES
  ('c1', 'u-test-1', 'diary_storage', 'v1'),
  ('c2', 'u-test-1', 'ai_counseling', 'v1'),
  ('c3', 'u-test-2', 'diary_storage', 'v1'),
  ('c4', 'u-test-1', 'cycle_tracking', 'v1');

INSERT INTO diary_entries (id, user_id, mood_word_id, entry_date, content, source) VALUES
  ('d1', 'u-test-1', 34,   '2026-10-01', '(합성) 약속에 친구가 늦어서 짜증이 났다.', 'text'),
  ('d2', 'u-test-1', 66,   '2026-10-02', '(합성) 차를 마시며 쉬었다.',               'text'),
  ('d3', 'u-test-1', NULL, '2026-10-03', '(합성) 음성으로 남긴 메모.',               'voice'),
  ('d4', 'u-test-2', 82,   '2026-10-01', '(합성) 하루 종일 의욕이 없었다.',           'text');

INSERT INTO ai_feedback (id, entry_id, feedback_type, feedback_text, user_reaction) VALUES
  ('f1', 'd1', 'empathy', '(합성) 약속이 어긋나서 속상했겠어요. 어떤 점이 가장 신경 쓰였나요?', 'helpful');

INSERT INTO daily_condition
  (id, user_id, log_date, sleep_hours, sleep_score, meal_count, appetite_score, bowel_score, exercise_minutes, caffeine_cups) VALUES
  ('dc1', 'u-test-1', '2026-10-01', 5.5, 2, 2, 3, 4, 20, 3);

-- 월경 주기(선택 기능): cycle_tracking 동의가 있는 합성 사용자만
INSERT INTO menstrual_cycles (id, user_id, start_date, end_date) VALUES
  ('mc1', 'u-test-1', '2026-08-23', '2026-08-28'),
  ('mc2', 'u-test-1', '2026-09-20', '2026-09-25');

INSERT INTO self_model (id, user_id, hypotheses) VALUES
  ('sm1', 'u-test-1', '(합성) 수면이 짧은 날 짜증이 늘 수 있다는 가설');

INSERT INTO safety_events (id, user_id, entry_id, level, trigger_type) VALUES
  ('s1', 'u-test-1', NULL, 3, 'pattern');

-- ---------------------------------------------------------------
-- 삭제 검증: test1을 지운 뒤 흔적이 모두 0이어야 한다.
-- DELETE FROM users WHERE id = 'u-test-1';
--
-- SELECT 'users' AS t, COUNT(*) AS n FROM users WHERE id = 'u-test-1'
-- UNION ALL SELECT 'user_profile', COUNT(*) FROM user_profile WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'relationships', COUNT(*) FROM relationships WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'diary_entries', COUNT(*) FROM diary_entries WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'ai_feedback', COUNT(*) FROM ai_feedback WHERE entry_id IN ('d1','d2','d3')
-- UNION ALL SELECT 'daily_condition', COUNT(*) FROM daily_condition WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'self_model', COUNT(*) FROM self_model WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'safety_events', COUNT(*) FROM safety_events WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'menstrual_cycles', COUNT(*) FROM menstrual_cycles WHERE user_id = 'u-test-1'
-- UNION ALL SELECT 'consents', COUNT(*) FROM consents WHERE user_id = 'u-test-1';
-- (test2의 데이터는 그대로 남아 있어야 한다)
