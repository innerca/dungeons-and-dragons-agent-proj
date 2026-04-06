-- v0.500 Migration: Definition Tables for Monsters, NPCs, Quests
-- Uses INSERT ... ON CONFLICT (id) DO UPDATE SET ... for incremental upsert.
-- NEVER drop/recreate these tables when adding data. Always use upsert.

-- ============================================================
-- 1. Monster Definitions (全服共享怪物元数据)
-- ============================================================
CREATE TABLE IF NOT EXISTS monster_definitions (
    id                  VARCHAR(64) PRIMARY KEY,
    name                VARCHAR(128) NOT NULL,
    name_en             VARCHAR(128),
    monster_type        VARCHAR(32) NOT NULL,       -- animal, insect, humanoid, plant, undead, spirit, boss, mini_boss
    floor               INTEGER NOT NULL,
    area                VARCHAR(128),               -- 出没区域
    level_min           INTEGER DEFAULT 1,
    level_max           INTEGER DEFAULT 1,
    hp                  INTEGER NOT NULL,
    atk                 INTEGER NOT NULL,
    defense             INTEGER NOT NULL,
    ac                  INTEGER NOT NULL DEFAULT 10,
    exp_reward          INTEGER NOT NULL DEFAULT 10,
    col_reward_min      INTEGER DEFAULT 0,
    col_reward_max      INTEGER DEFAULT 0,
    behavior_type       VARCHAR(32) DEFAULT 'aggressive',  -- aggressive, defensive, pack, ambush, phase, steal
    weaknesses          TEXT,
    abilities_json      JSONB DEFAULT '[]',
    loot_table_json     JSONB DEFAULT '[]',
    description         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 2. NPC Definitions (全服共享 NPC 元数据)
-- ============================================================
CREATE TABLE IF NOT EXISTS npc_definitions (
    id                  VARCHAR(64) PRIMARY KEY,
    name                VARCHAR(128) NOT NULL,
    name_en             VARCHAR(128),
    npc_type            VARCHAR(32) NOT NULL,       -- quest_giver, merchant, trainer, companion, faction_leader, info_broker, blacksmith
    floor               INTEGER NOT NULL,
    location            VARCHAR(256),
    faction             VARCHAR(64),                -- dark_elf, forest_elf, dkb, als, independent, fallen_elf
    appearance          TEXT,
    personality         TEXT,
    dialog_style        TEXT,                       -- 说话风格参考
    services_json       JSONB DEFAULT '{}',         -- {shop_items:[], training:[], info_topics:[]}
    related_quests_json JSONB DEFAULT '[]',
    initial_relationship INTEGER DEFAULT 0,
    description         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 3. Quest Definitions (全服共享任务元数据)
-- ============================================================
CREATE TABLE IF NOT EXISTS quest_definitions (
    id                  VARCHAR(64) PRIMARY KEY,
    name                VARCHAR(128) NOT NULL,
    quest_type          VARCHAR(32) NOT NULL,       -- main, floor_feature, daily, hidden
    floor               INTEGER NOT NULL,
    chapter             INTEGER DEFAULT 1,
    total_chapters      INTEGER DEFAULT 1,
    difficulty          VARCHAR(16) DEFAULT 'normal',  -- easy, normal, hard, extreme
    is_repeatable       BOOLEAN DEFAULT false,
    prerequisites_json  JSONB DEFAULT '{}',         -- {min_level:N, required_quests:[], required_flags:{}}
    trigger_json        JSONB DEFAULT '{}',         -- {type:"location"|"npc_talk"|"item"|"auto", target:"..."}
    objectives_json     JSONB DEFAULT '[]',         -- [{type:"kill"|"collect"|"talk"|"reach", target, count, desc}]
    rewards_json        JSONB DEFAULT '{}',         -- {exp, col, items:[], flags:{}, relationships:{}}
    failure_json        JSONB DEFAULT '{}',
    choices_json        JSONB DEFAULT '[]',         -- [{id, description, consequences:{}}]
    description         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- Floor 1 Seed Data: Monsters
-- All seeds use ON CONFLICT ... DO UPDATE for incremental upsert.
-- ============================================================

INSERT INTO monster_definitions (id, name, name_en, monster_type, floor, area, level_min, level_max, hp, atk, defense, ac, exp_reward, col_reward_min, col_reward_max, behavior_type, weaknesses, abilities_json, loot_table_json, description) VALUES

-- 草原低级怪
('f1_boar', '山猪', 'Wild Boar', 'animal', 1, '草原地带', 1, 2, 50, 12, 3, 8, 15, 5, 15, 'aggressive',
 '侧面攻击可避开獠牙',
 '[]',
 '[{"item_id":"material_boar_tusk","name":"山猪獠牙","chance":0.6},{"item_id":"material_boar_hide","name":"山猪毛皮","chance":0.4}]',
 '起始之城周围草原上游荡的野猪型怪物，体型约一米长，獠牙锋利但动作迟缓。新手练级的首选目标。'),

('f1_wolf', '野狼', 'Wild Wolf', 'animal', 1, '草原地带', 2, 3, 80, 18, 4, 10, 25, 10, 25, 'pack',
 '单独一只时较弱，注意群体围攻',
 '[{"name":"嚎叫召唤","desc":"HP低于50%时嚎叫，30%概率召唤1只同伴"}]',
 '[{"item_id":"material_wolf_fang","name":"狼牙","chance":0.5},{"item_id":"material_wolf_pelt","name":"狼毛皮","chance":0.35}]',
 '草原上成群活动的灰色野狼，速度较快，会协同围攻落单玩家。'),

('f1_worm', '蠕虫', 'Earthworm', 'insect', 1, '草原地带', 1, 1, 30, 8, 2, 7, 8, 2, 8, 'defensive',
 '体型柔软，斩击类攻击效果好',
 '[]',
 '[{"item_id":"material_worm_slime","name":"蠕虫黏液","chance":0.5}]',
 '从草原泥土中钻出的巨型蠕虫，约臂粗半米长。攻击力低但会缠绕减速。'),

('f1_beetle', '甲虫', 'Giant Beetle', 'insect', 1, '草原地带', 1, 2, 45, 10, 6, 11, 12, 3, 12, 'aggressive',
 '翻转后腹部防御为0',
 '[{"name":"坚硬甲壳","desc":"正面攻击防御+3"}]',
 '[{"item_id":"material_beetle_shell","name":"甲虫壳","chance":0.45},{"item_id":"material_beetle_horn","name":"甲虫角","chance":0.2}]',
 '拳头大小的黑色甲虫型怪物，甲壳坚硬但翻转后腹部毫无防御。'),

('f1_wasp', '黄蜂', 'Giant Wasp', 'insect', 1, '草原地带', 2, 3, 55, 15, 3, 12, 20, 8, 20, 'aggressive',
 '飞行中命中率较低，可等其俯冲时反击',
 '[{"name":"毒针","desc":"攻击有15%概率施加中毒(伤害)，持续30秒，每秒损失2HP"}]',
 '[{"item_id":"material_wasp_stinger","name":"黄蜂毒针","chance":0.3},{"item_id":"material_wasp_wing","name":"黄蜂翅膀","chance":0.4}]',
 '体长约30厘米的巨大黄蜂，飞行速度快，尾部毒针有中毒效果。'),

-- 迷宫塔怪物
('f1_kobold_trooper', '废墟狗头人突击兵', 'Ruin Kobold Trooper', 'humanoid', 1, '迷宫塔', 5, 6, 180, 30, 10, 12, 55, 25, 50, 'aggressive',
 '三连攻击后有约2秒失去平衡的硬直',
 '[{"name":"手斧三连击","desc":"连续三次手斧攻击，倍率1.8，攻击后2秒硬直"}]',
 '[{"item_id":"material_kobold_axe","name":"狗头人手斧","chance":0.3},{"item_id":"material_kobold_hide","name":"狗头人毛皮","chance":0.5}]',
 '身高约1.5米的直立犬型类人怪物，穿着简陋皮甲持手斧。擅长三连攻击但攻击后会失去平衡。迷宫塔内的主要遭遇对象。'),

('f1_kobold_guard', '废墟狗头人护卫兵', 'Ruin Kobold Sentinel', 'humanoid', 1, '迷宫塔', 6, 7, 250, 25, 18, 15, 70, 30, 60, 'defensive',
 '喉咙是弱点，弱点会心伤害x1.5',
 '[{"name":"盾牌格挡","desc":"有40%概率格挡正面攻击，减伤50%"},{"name":"斧枪突刺","desc":"远距离突刺，倍率1.2"}]',
 '[{"item_id":"material_kobold_armor","name":"狗头人金属片","chance":0.25},{"item_id":"material_kobold_axe","name":"狗头人手斧","chance":0.4}]',
 '穿着金属铠甲、持斧枪和圆盾的精英狗头人。防御力高，弱点在喉咙处。通常2-3只成组巡逻。'),

-- 楼层BOSS
('f1_boss_illfang', '狗头人领主伊尔凡古', 'Illfang the Kobold Lord', 'boss', 1, '迷宫塔顶层魔王房间', 10, 10, 2000, 45, 20, 14, 500, 500, 1000, 'phase',
 '第4阶段大刀剑技后有较长硬直；护卫兵优先清理',
 '[{"name":"4条HP机制","desc":"每消耗1条HP(500)涌出3只护卫兵"},{"name":"阶段切换","desc":"前3条HP使用骨斧+盾；第4条切换大刀(武士刀)"},{"name":"旋车","desc":"大刀剑技，垂直跳起空中旋转六道鲜红光，倍率3.0，附带晕眩"},{"name":"浮舟+绯扇","desc":"上挑+三连击组合技，倍率4.5"},{"name":"幻月","desc":"随机轨迹斩击，倍率2.0，硬直短"}]',
 '[{"item_id":"armor_midnight_coat","name":"午夜大衣","chance":1.0,"condition":"LA_reward"},{"item_id":"material_boss_fang","name":"魔王獠牙","chance":0.8}]',
 '第1层楼层BOSS。身高超过2米的巨大狗头人领主，全身深蓝色毛皮，血红色眼睛。拥有4条HP，前3阶段使用骨斧+圆盾战斗，最后阶段切换为大刀(武士刀)并释放强力剑技。每消耗一条HP会召唤3只狗头人护卫兵。魔王房间为宽20米、纵深100米的长方形空间，战斗中大门不关闭可撤退。')

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    monster_type = EXCLUDED.monster_type,
    floor = EXCLUDED.floor,
    area = EXCLUDED.area,
    level_min = EXCLUDED.level_min,
    level_max = EXCLUDED.level_max,
    hp = EXCLUDED.hp,
    atk = EXCLUDED.atk,
    defense = EXCLUDED.defense,
    ac = EXCLUDED.ac,
    exp_reward = EXCLUDED.exp_reward,
    col_reward_min = EXCLUDED.col_reward_min,
    col_reward_max = EXCLUDED.col_reward_max,
    behavior_type = EXCLUDED.behavior_type,
    weaknesses = EXCLUDED.weaknesses,
    abilities_json = EXCLUDED.abilities_json,
    loot_table_json = EXCLUDED.loot_table_json,
    description = EXCLUDED.description,
    updated_at = now();

-- ============================================================
-- Floor 1 Seed Data: NPCs
-- ============================================================

INSERT INTO npc_definitions (id, name, name_en, npc_type, floor, location, faction, appearance, personality, dialog_style, services_json, related_quests_json, initial_relationship, description) VALUES

('npc_argo', '亚鲁戈', 'Argo', 'info_broker', 1, '各层主街区（游荡）', 'independent',
 '小柄少女，脸颊两侧各有三条胡须状纹路（来源不明），灰黄色连帽斗篷。全敏捷型非战斗系。',
 '精明世故但有底线，绝不出卖封测玩家身份。说话带商人腔调，每句情报都明码标价。',
 '嘿嘿，这条情报嘛……500珂尔。不二价哦，小桐。',
 '{"info_topics":["boss_patterns","floor_maps","player_locations","quest_hints"],"pricing":{"basic":500,"detailed":1000,"secret":1500},"publications":["攻略册（免费版）","攻略册（付费版500Col）"]}',
 '["q_f1_argo_info"]',
 10,
 '情报贩子「老鼠」亚鲁戈，SAO最大的情报商。编写各层攻略册，经营面对面情报买卖。全AGI型非战斗玩家，跑得极快。绝对原则：绝不出卖封测玩家的真实身份。'),

('npc_agil', '艾基尔', 'Agil', 'merchant', 1, '托尔巴纳/各层前线城镇', 'independent',
 '褐色肌肤光头巨汉，身高190cm，体格壮硕。双手斧使。',
 '理性正义，作为前线攻略者兼商人。为人可靠，是少数不歧视封测玩家的人。',
 '直率坦诚，说话声音洪亮。作为商人时公道合理。',
 '{"shop_type":"general","buy_rate":0.5,"sell_items":["potion_heal_low","potion_antidote","material_basic"]}',
 '[]',
 15,
 '双手斧使巨汉艾基尔，前线攻略者兼商人。褐色肌肤，190cm的壮硕身材。理性正义的坦克型玩家，后来在各层前线城镇开设道具店。'),

('npc_diabel', '迪亚贝尔', 'Diabel', 'quest_giver', 1, '托尔巴纳·喷水池广场', 'independent',
 '蓝发骑士风范的青年，穿着骑士铠甲，持长剑和盾牌。',
 '有领袖魅力，自发组织第1层BOSS攻略战。隐瞒自己是封测玩家的身份。',
 '充满激情的领袖式演说风格，试图团结所有玩家。',
 '{}',
 '["q_f1_boss_raid"]',
 5,
 '自称「骑士」的蓝发青年，第1层BOSS攻略战的发起人和指挥官。在喷水池广场召集44人联合部队。实际上是隐瞒身份的封测玩家，企图独占LA奖励。在BOSS战中被伊尔凡古的大刀剑技击杀，成为攻略中首位牺牲的玩家领袖。'),

('npc_lind', '凛德', 'Lind', 'faction_leader', 1, '前线城镇', 'dkb',
 '苍白肌肤，使用弯刀的精英玩家。冷峻外表。',
 '精英主义，追求战力平衡。迪亚贝尔死后接手其队伍成立龙骑士旅团(DKB)。',
 '简洁冷淡，命令式口吻。重效率轻感情。',
 '{}',
 '[]',
 0,
 '龙骑士旅团(DKB)会长，迪亚贝尔死后接手其攻略队伍。弯刀使，约18人精英团队。主张精英路线，追求战力平衡。代表色蓝色。'),

('npc_kibaou', '牙王', 'Kibaou', 'faction_leader', 1, '起始之城/前线城镇', 'als',
 '刺猬头，中等身材，表情总是不满和愤怒。',
 '对封测玩家有强烈敌意，认为他们独占资源导致新手大量死亡。人海路线领袖。',
 '粗暴直接，经常大声指责封测玩家。煽动性强。',
 '{}',
 '[]',
 -5,
 '艾恩葛朗特解放队(ALS)会长，刺猬头的暴躁玩家。对封测玩家怀有强烈敌意，从起始城镇大量招募和训练新手玩家。代表色暗绿色。人海战术路线。'),

('npc_nezha', '涅兹哈', 'Nezha', 'blacksmith', 1, '托尔巴纳', 'independent',
 '传说勇者公会铁匠，外形不详但是SAO中首位达到实用水平的玩家铁匠。',
 '曾进行强化诈欺（偷换客户武器为相同外观的低级品），被揭发后悔改。技术实力真材实料。',
 '谨慎低调，因过去的诈欺事件而对信任格外珍惜。',
 '{"shop_type":"blacksmith","services":["enhance","repair","craft"],"enhance_bonus":5}',
 '[]',
 -10,
 'SAO首位玩家铁匠涅兹哈，隶属传说勇者公会。曾利用强化系统进行诈欺（偷换客户武器），被桐人揭发。技术实力过硬，是前线少数能进行高成功率强化的铁匠。')

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    npc_type = EXCLUDED.npc_type,
    floor = EXCLUDED.floor,
    location = EXCLUDED.location,
    faction = EXCLUDED.faction,
    appearance = EXCLUDED.appearance,
    personality = EXCLUDED.personality,
    dialog_style = EXCLUDED.dialog_style,
    services_json = EXCLUDED.services_json,
    related_quests_json = EXCLUDED.related_quests_json,
    initial_relationship = EXCLUDED.initial_relationship,
    description = EXCLUDED.description,
    updated_at = now();

-- ============================================================
-- Floor 1 Seed Data: Quests
-- ============================================================

INSERT INTO quest_definitions (id, name, quest_type, floor, chapter, total_chapters, difficulty, is_repeatable, prerequisites_json, trigger_json, objectives_json, rewards_json, failure_json, choices_json, description) VALUES

('q_f1_anneal_blade', '韧炼之剑', 'floor_feature', 1, 1, 1, 'hard', false,
 '{"min_level":3}',
 '{"type":"location","target":"霍鲁卡村","detail":"到达霍鲁卡村后自动触发，村长告知附近洞窟的传说"}',
 '[{"type":"kill","target":"f1_giant_wasp_queen","count":1,"desc":"击败巨型黄蜂女王"},{"type":"collect","target":"material_wasp_ovule","count":1,"desc":"获取黄蜂卵珠"}]',
 '{"exp":200,"col":0,"items":["sword_anneal_blade"],"flags":{"anneal_blade_obtained":true}}',
 '{}',
 '[]',
 '到达霍鲁卡村后获知的困难获取任务。需要深入洞窟击败巨型黄蜂女王并取回卵珠，交给村长后获得准稀有单手剑「韧炼之剑」(ATK 45)。这把剑性能优秀可用到第4层，是前线玩家的重要装备。'),

('q_f1_boss_raid', '第一次魔王攻略战', 'main', 1, 1, 1, 'extreme', false,
 '{"min_level":5,"recommended_level":8}',
 '{"type":"npc_talk","target":"npc_diabel","detail":"在托尔巴纳喷水池广场参加迪亚贝尔召集的攻略会议"}',
 '[{"type":"talk","target":"npc_diabel","count":1,"desc":"参加攻略会议"},{"type":"reach","target":"迷宫塔顶层魔王房间","count":1,"desc":"到达魔王房间"},{"type":"kill","target":"f1_boss_illfang","count":1,"desc":"击败狗头人领主伊尔凡古"}]',
 '{"exp":500,"col":500,"flags":{"floor1_cleared":true,"floor2_unlocked":true},"special":"LA奖励:午夜大衣(给予最后一击的玩家)"}',
 '{"condition":"全灭","desc":"攻略部队全灭，BOSS回复全部HP，可重新挑战"}',
 '[]',
 '第1层核心事件。迪亚贝尔在托尔巴纳喷水池广场召集44人联合部队挑战楼层BOSS狗头人领主伊尔凡古。BOSS拥有4条HP，前3阶段使用骨斧+盾，最后阶段切换大刀释放强力剑技。每条HP消耗后涌出3只护卫兵。历史上迪亚贝尔在此战中阵亡。'),

('q_f1_argo_info', '情报贩子的委托', 'floor_feature', 1, 1, 1, 'easy', false,
 '{}',
 '{"type":"npc_talk","target":"npc_argo","detail":"在起始之城或托尔巴纳偶遇亚鲁戈"}',
 '[{"type":"talk","target":"npc_argo","count":1,"desc":"与亚鲁戈对话"},{"type":"collect","target":"material_field_map_data","count":3,"desc":"收集3个区域的地图数据（探索新区域自动获得）"}]',
 '{"exp":100,"col":300,"items":[],"flags":{"argo_contact":true},"relationships":{"npc_argo":15}}',
 '{}',
 '[]',
 '偶遇情报贩子亚鲁戈后触发的入门任务。帮助她收集野外地图数据以编写攻略册。完成后与亚鲁戈建立联系，可以购买情报和攻略册。')

ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    quest_type = EXCLUDED.quest_type,
    floor = EXCLUDED.floor,
    chapter = EXCLUDED.chapter,
    total_chapters = EXCLUDED.total_chapters,
    difficulty = EXCLUDED.difficulty,
    is_repeatable = EXCLUDED.is_repeatable,
    prerequisites_json = EXCLUDED.prerequisites_json,
    trigger_json = EXCLUDED.trigger_json,
    objectives_json = EXCLUDED.objectives_json,
    rewards_json = EXCLUDED.rewards_json,
    failure_json = EXCLUDED.failure_json,
    choices_json = EXCLUDED.choices_json,
    description = EXCLUDED.description,
    updated_at = now();

-- ============================================================
-- Upgrade existing init_db.sql seeds to upsert (reference)
-- The sword_skill_definitions and item_definitions already use
-- ON CONFLICT (id) DO NOTHING. For full upsert support,
-- run the ALTER statements below to add updated_at columns.
-- ============================================================

-- Add updated_at to existing definition tables if missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'item_definitions' AND column_name = 'updated_at') THEN
        ALTER TABLE item_definitions ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'sword_skill_definitions' AND column_name = 'updated_at') THEN
        ALTER TABLE sword_skill_definitions ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();
    END IF;
END $$;
