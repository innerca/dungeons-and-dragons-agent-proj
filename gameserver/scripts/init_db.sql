-- SAO Progressive DND Game - Database Schema
-- PostgreSQL 16

-- 1. 玩家账号
CREATE TABLE IF NOT EXISTS players (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(32) UNIQUE NOT NULL,
    display_name    VARCHAR(64) NOT NULL,
    password_hash   VARCHAR(128) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    last_login_at   TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT true
);

-- 2. 角色核心属性
CREATE TABLE IF NOT EXISTS player_characters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id       UUID REFERENCES players(id) UNIQUE,
    name            VARCHAR(64) NOT NULL,
    level           INTEGER DEFAULT 1,
    current_hp      INTEGER DEFAULT 250,
    max_hp          INTEGER DEFAULT 250,
    experience      BIGINT DEFAULT 0,
    exp_to_next     BIGINT DEFAULT 100,
    stat_str        INTEGER DEFAULT 10,
    stat_agi        INTEGER DEFAULT 10,
    stat_vit        INTEGER DEFAULT 10,
    stat_int        INTEGER DEFAULT 10,
    stat_dex        INTEGER DEFAULT 10,
    stat_luk        INTEGER DEFAULT 10,
    col             BIGINT DEFAULT 500,
    current_floor   INTEGER DEFAULT 1,
    current_area    VARCHAR(128) DEFAULT '起始之城',
    current_location VARCHAR(256) DEFAULT '中央广场',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 3. 物品定义（全服共享元数据）
CREATE TABLE IF NOT EXISTS item_definitions (
    id              VARCHAR(64) PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    item_type       VARCHAR(32) NOT NULL,
    rarity          VARCHAR(16) DEFAULT 'common',
    description     TEXT,
    is_stackable    BOOLEAN DEFAULT false,
    max_stack       INTEGER DEFAULT 1,
    base_price      INTEGER DEFAULT 0,
    weapon_atk      INTEGER,
    weapon_sharpness INTEGER,
    weapon_speed    INTEGER,
    weapon_accuracy INTEGER,
    weapon_weight   INTEGER,
    weapon_durability INTEGER,
    armor_defense   INTEGER,
    effect_json     JSONB
);

-- 4. 玩家背包
CREATE TABLE IF NOT EXISTS character_inventory (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id        UUID REFERENCES player_characters(id),
    item_def_id         VARCHAR(64) REFERENCES item_definitions(id),
    quantity            INTEGER DEFAULT 1,
    current_durability  INTEGER,
    enhancement_level   INTEGER DEFAULT 0,
    enhancement_detail  VARCHAR(32),
    is_equipped         BOOLEAN DEFAULT false,
    equipped_slot       VARCHAR(32),
    acquired_at         TIMESTAMPTZ DEFAULT now()
);

-- 5. 剑技定义（全服共享）
CREATE TABLE IF NOT EXISTS sword_skill_definitions (
    id                      VARCHAR(64) PRIMARY KEY,
    name                    VARCHAR(128) NOT NULL,
    weapon_type             VARCHAR(32) NOT NULL,
    hit_count               INTEGER DEFAULT 1,
    damage_multiplier       FLOAT DEFAULT 1.0,
    cooldown_seconds        FLOAT DEFAULT 2.0,
    required_level          INTEGER DEFAULT 1,
    description             TEXT,
    motion_description      TEXT
);

-- 6. 玩家已解锁剑技
CREATE TABLE IF NOT EXISTS character_sword_skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    skill_def_id    VARCHAR(64) REFERENCES sword_skill_definitions(id),
    proficiency     INTEGER DEFAULT 0,
    is_in_slot      BOOLEAN DEFAULT false,
    slot_index      INTEGER,
    times_used      INTEGER DEFAULT 0,
    UNIQUE(character_id, skill_def_id)
);

-- 7. 非战斗技能
CREATE TABLE IF NOT EXISTS character_noncombat_skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    skill_name      VARCHAR(64) NOT NULL,
    level           INTEGER DEFAULT 1,
    experience      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT true,
    UNIQUE(character_id, skill_name)
);

-- 8. 任务进度
CREATE TABLE IF NOT EXISTS character_quests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    quest_def_id    VARCHAR(64) NOT NULL,
    status          VARCHAR(16) DEFAULT 'active',
    progress_json   JSONB DEFAULT '{}',
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- 9. 世界标记（剧情分支/选择记录）
CREATE TABLE IF NOT EXISTS character_world_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    flag_key        VARCHAR(128) NOT NULL,
    flag_value      TEXT NOT NULL,
    set_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(character_id, flag_key)
);

-- 10. NPC 关系
CREATE TABLE IF NOT EXISTS character_npc_relationships (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id            UUID REFERENCES player_characters(id),
    npc_id                  VARCHAR(64) NOT NULL,
    relationship_level      INTEGER DEFAULT 0,
    interaction_count       INTEGER DEFAULT 0,
    last_interaction_summary TEXT,
    UNIQUE(character_id, npc_id)
);

-- 11. 对话历史
CREATE TABLE IF NOT EXISTS conversation_messages (
    id              BIGSERIAL PRIMARY KEY,
    player_id       UUID REFERENCES players(id) NOT NULL,
    role            VARCHAR(16) NOT NULL,
    content         TEXT NOT NULL,
    token_count     INTEGER,
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conv_player_time ON conversation_messages(player_id, created_at DESC);

-- 12. 对话摘要
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id              BIGSERIAL PRIMARY KEY,
    player_id       UUID REFERENCES players(id),
    summary         TEXT NOT NULL,
    covers_from_id  BIGINT,
    covers_to_id    BIGINT,
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Seed: 初始剑技定义
INSERT INTO sword_skill_definitions (id, name, weapon_type, hit_count, damage_multiplier, cooldown_seconds, required_level, description, motion_description) VALUES
('rapier_linear', 'Linear', 'rapier', 1, 1.0, 1.5, 1, '基础突刺', '剑摆身体中央，旋转往前笔直刺出。纯白光芒'),
('rapier_oblique', 'Oblique', 'rapier', 1, 1.1, 1.5, 2, '下段刺击', '下段刺击，银色光芒。最快的剑技之一'),
('rapier_parallel_sting', 'Parallel Sting', 'rapier', 2, 1.6, 2.5, 4, '连续突刺', '快到肉眼几乎看不见的连续突刺'),
('rapier_shooting_star', 'Shooting Star', 'rapier', 1, 1.8, 3.0, 8, '最大射程突进技', '最大射程突进技，准备动作复杂出招慢'),
('rapier_lightning_thrust', 'Lightning Thrust', 'rapier', 4, 3.2, 5.0, 15, '高速四连突刺', '高速四连突刺，闪电般光芒'),
('sword_slant', 'Slant', 'one_hand_sword', 1, 1.0, 1.5, 1, '基本斜向斩击', '基本斜向斩击，淡蓝色光芒。可弹开敌人武器'),
('sword_vertical', 'Vertical', 'one_hand_sword', 1, 1.1, 1.5, 2, '上段斩击', '上段斩击'),
('sword_horizontal', 'Horizontal', 'one_hand_sword', 1, 1.0, 1.5, 2, '水平横扫', '水平横扫'),
('sword_rage_spike', 'Rage Spike', 'one_hand_sword', 1, 1.4, 2.0, 3, '突进技', '剑摆左腰，极低姿势冲刺，淡蓝色光芒'),
('sword_sonic_leap', 'Sonic Leap', 'one_hand_sword', 1, 1.6, 2.5, 5, '突进技', '扛右肩姿势，可朝空中发动。黄绿色光芒'),
('sword_horizontal_arc', 'Horizontal Arc', 'one_hand_sword', 2, 1.8, 3.0, 6, 'V字轨迹二连击', 'V字轨迹二连击'),
('sword_sharp_nail', 'Sharp Nail', 'one_hand_sword', 3, 2.4, 3.5, 8, '三连爪击', '右胸→左胸→胸口中央，如野兽爪痕'),
('sword_cyclone', 'Cyclone', 'one_hand_sword', 3, 2.8, 4.0, 12, '旋转三连斩', '旋转三连斩'),
('axe_whirlpool', 'Whirlpool', 'one_hand_axe', 1, 1.3, 2.0, 1, '龙卷风般回转攻击', '龙卷风般回转攻击'),
('axe_double_cleave', 'Double Cleave', 'one_hand_axe', 2, 2.0, 3.0, 4, '红色特效光连砍两次', '红色特效光，陀螺旋转连砍两次'),
('martial_flash_hit', 'Flash Hit', 'martial_arts', 1, 0.8, 1.0, 1, '最快单发拳击', '最快单发拳击，红色光芒。可武装解除'),
('martial_crescent_moon', 'Crescent Moon', 'martial_arts', 1, 1.2, 2.0, 3, '后空翻上踢', '后空翻上踢，红色光芒')
ON CONFLICT (id) DO NOTHING;

-- Seed: 初始物品定义
INSERT INTO item_definitions (id, name, item_type, rarity, description, is_stackable, max_stack, base_price, weapon_atk, weapon_durability, armor_defense) VALUES
('sword_anneal_blade', '韧炼之剑', 'weapon', 'uncommon', '准稀有单手剑，可用到第4层', false, 1, 15000, 45, 200, NULL),
('rapier_wind_fleuret', '风花剑', 'weapon', 'uncommon', '掉宝道具细剑', false, 1, 8000, 35, 150, NULL),
('rapier_chivalric_rapier', '骑士刺剑', 'weapon', 'rare', '精灵铁匠制，锤打40下', false, 1, 30000, 55, 250, NULL),
('sword_dusk_blade', '日暮之剑', 'weapon', 'rare', 'AGI+7，准度自动瞄准弱点', false, 1, 50000, 68, 200, NULL),
('armor_midnight_coat', '午夜大衣', 'armor_body', 'uncommon', '第1层LA奖励，桐人标志', false, 1, 0, NULL, NULL, 20),
('potion_heal_low', '低级回复药水', 'consumable', 'common', '时间持续回复HP', true, 99, 100, NULL, NULL, NULL),
('potion_antidote', '解毒药水', 'consumable', 'common', '解除中毒/麻痹状态', true, 99, 150, NULL, NULL, NULL),
('crystal_teleport', '转移水晶', 'crystal', 'rare', '瞬间移动至任意已开通转移门', true, 10, 5000, NULL, NULL, NULL),
('crystal_heal', '回复水晶', 'crystal', 'legendary', '瞬间回满HP，掉率0.1%', true, 5, 100000, NULL, NULL, NULL)
ON CONFLICT (id) DO NOTHING;
