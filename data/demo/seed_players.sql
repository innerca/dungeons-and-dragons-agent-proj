-- SAO Progressive DND - Demo Seed Data
-- 测试账号和角色数据
-- 使用方法: psql $DATABASE_URL -f seed_players.sql

-- ============================================
-- 1. 测试账号
-- ============================================
-- 账号1: demo / demo123
-- 账号2: testplayer / test123

INSERT INTO players (id, username, display_name, password_hash, created_at, last_login_at, is_active) VALUES
  ('demo-player-001', 'demo', 'Demo玩家', '$2b$12$zwBHpbpPfpjVVC80IDoBeeHuf4aKwSLc5EGyTqoe3rxgf.E4BkVQW', now(), now(), true),
  ('demo-player-002', 'testplayer', 'TestPlayer', '$2b$12$0jvEnEGYOdNyxSeKRrWLIO1M2u5fiMMeO9Wj55uejAHidk.WGvS1u', now(), now(), true)
ON CONFLICT (username) DO NOTHING;

-- ============================================
-- 2. 角色数据
-- ============================================
-- demo 账号: Lv 3 的进阶角色（已完成新手阶段）
-- testplayer 账号: Lv 1 的新手角色

INSERT INTO player_characters (
  id, player_id, name, level, current_hp, max_hp, experience, exp_to_next,
  stat_str, stat_agi, stat_vit, stat_int, stat_dex, stat_luk,
  col, current_floor, current_area, current_location, stat_points_available,
  created_at, updated_at
) VALUES
  -- Demo角色: 等级3，有一定经验和装备基础
  ('demo-char-001', 'demo-player-001', '桐谷 demo', 3, 320, 320, 450, 550,
   12, 15, 11, 10, 13, 10,
   2850, 1, '托尔巴纳', '喷水池广场', 0,
   now(), now()),
  
  -- TestPlayer角色: 等级1，纯新手
  ('demo-char-002', 'demo-player-002', '新手勇者', 1, 250, 250, 0, 100,
   10, 10, 10, 10, 10, 10,
   500, 1, '起始之城', '中央广场', 0,
   now(), now())
ON CONFLICT (player_id) DO NOTHING;

-- ============================================
-- 3. 角色背包 - 初始装备和道具
-- ============================================

INSERT INTO character_inventory (
  id, character_id, item_def_id, quantity, current_durability,
  enhancement_level, enhancement_detail, is_equipped, equipped_slot, acquired_at
) VALUES
  -- Demo角色装备
  ('inv-demo-001', 'demo-char-001', 'rapier_wind_fleuret', 1, 145, 0, NULL, true, 'main_hand', now()),
  ('inv-demo-002', 'demo-char-001', 'armor_midnight_coat', 1, NULL, 0, NULL, true, 'body', now()),
  ('inv-demo-003', 'demo-char-001', 'potion_heal_low', 8, NULL, 0, NULL, false, NULL, now()),
  ('inv-demo-004', 'demo-char-001', 'potion_antidote', 3, NULL, 0, NULL, false, NULL, now()),
  ('inv-demo-005', 'demo-char-001', 'crystal_teleport', 2, NULL, 0, NULL, false, NULL, now()),
  
  -- TestPlayer角色装备（新手装）
  ('inv-test-001', 'demo-char-002', 'sword_anneal_blade', 1, 195, 0, NULL, true, 'main_hand', now()),
  ('inv-test-002', 'demo-char-002', 'potion_heal_low', 3, NULL, 0, NULL, false, NULL, now())
ON CONFLICT DO NOTHING;

-- ============================================
-- 4. 角色已解锁剑技
-- ============================================

INSERT INTO character_sword_skills (
  id, character_id, skill_def_id, proficiency, is_in_slot, slot_index, times_used
) VALUES
  -- Demo角色剑技（细剑使）
  ('skill-demo-001', 'demo-char-001', 'rapier_linear', 85, true, 1, 156),
  ('skill-demo-002', 'demo-char-001', 'rapier_oblique', 42, true, 2, 67),
  ('skill-demo-003', 'demo-char-001', 'rapier_parallel_sting', 12, false, NULL, 8),
  
  -- TestPlayer角色剑技（单手剑）
  ('skill-test-001', 'demo-char-002', 'sword_slant', 15, true, 1, 23),
  ('skill-test-002', 'demo-char-002', 'sword_vertical', 5, false, NULL, 3)
ON CONFLICT (character_id, skill_def_id) DO NOTHING;

-- ============================================
-- 5. 角色任务进度
-- ============================================

INSERT INTO character_quests (
  id, character_id, quest_def_id, status, progress_json, started_at, completed_at
) VALUES
  -- Demo角色: 正在进行情报贩子的委托
  ('quest-demo-001', 'demo-char-001', 'q_f1_argo_info', 'active',
   '{"map_data_collected": 2, "target": 3}'::jsonb, now() - interval '2 hours', NULL),
  
  -- Demo角色: 已完成韧炼之剑任务
  ('quest-demo-002', 'demo-char-001', 'q_f1_anneal_blade', 'completed',
   '{"wasp_queen_killed": true, "ovule_collected": true}'::jsonb, now() - interval '3 days', now() - interval '2 days'),
  
  -- TestPlayer角色: 刚接受情报贩子任务
  ('quest-test-001', 'demo-char-002', 'q_f1_argo_info', 'active',
   '{"map_data_collected": 0, "target": 3}'::jsonb, now() - interval '10 minutes', NULL)
ON CONFLICT DO NOTHING;

-- ============================================
-- 6. 角色与NPC关系
-- ============================================

INSERT INTO character_npc_relationships (
  id, character_id, npc_id, relationship_level, interaction_count, last_interaction_summary
) VALUES
  -- Demo角色与NPC关系
  ('rel-demo-001', 'demo-char-001', 'npc_argo', 25, 8, '亚鲁戈提供了第1层BOSS的攻略情报，收费1000珂尔'),
  ('rel-demo-002', 'demo-char-001', 'npc_agil', 18, 4, '在艾基尔的店铺购买了回复药水'),
  ('rel-demo-003', 'demo-char-001', 'npc_diabel', 5, 2, '参加了迪亚贝尔召集的BOSS攻略会议'),
  ('rel-demo-004', 'demo-char-001', 'npc_nezha', -5, 1, '对强化成功率表示怀疑，未进行交易'),
  
  -- TestPlayer角色与NPC关系（新手，关系较浅）
  ('rel-test-001', 'demo-char-002', 'npc_argo', 10, 1, '初次相遇，接受了收集地图数据的委托')
ON CONFLICT (character_id, npc_id) DO NOTHING;

-- ============================================
-- 7. 角色世界标记（剧情选择记录）
-- ============================================

INSERT INTO character_world_flags (
  id, character_id, flag_key, flag_value, set_at
) VALUES
  -- Demo角色标记
  ('flag-demo-001', 'demo-char-001', 'tutorial_completed', 'true', now() - interval '3 days'),
  ('flag-demo-002', 'demo-char-001', 'first_death', 'false', now() - interval '3 days'),
  ('flag-demo-003', 'demo-char-001', 'visited_horunka', 'true', now() - interval '2 days'),
  ('flag-demo-004', 'demo-char-001', 'anneal_blade_obtained', 'true', now() - interval '2 days'),
  
  -- TestPlayer角色标记
  ('flag-test-001', 'demo-char-002', 'tutorial_completed', 'true', now() - interval '30 minutes'),
  ('flag-test-002', 'demo-char-002', 'first_death', 'false', now())
ON CONFLICT (character_id, flag_key) DO NOTHING;

-- ============================================
-- 8. 非战斗技能
-- ============================================

INSERT INTO character_noncombat_skills (
  id, character_id, skill_name, level, experience, is_active
) VALUES
  -- Demo角色技能
  ('ncs-demo-001', 'demo-char-001', '采集', 2, 180, true),
  ('ncs-demo-002', 'demo-char-001', '锻造', 1, 45, false),
  ('ncs-demo-003', 'demo-char-001', '烹饪', 1, 80, true),
  
  -- TestPlayer角色技能
  ('ncs-test-001', 'demo-char-002', '采集', 1, 0, true)
ON CONFLICT (character_id, skill_name) DO NOTHING;

-- ============================================
-- Demo 数据插入完成
-- ============================================
-- 账号信息:
--   demo / demo123      -> 等级3角色，有基础装备和任务进度
--   testplayer / test123 -> 等级1新手角色
