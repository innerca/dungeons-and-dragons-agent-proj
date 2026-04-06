# SAO Progressive DND 游戏系统蓝图

> 本文档为 GameServer 开发蓝图，将 SAO Progressive 小说设定转化为可编程的 CRPG 系统。
> 涵盖：任务/角色/战斗/经济/世界交互/持久化/规则自动化/记忆系统/ReAct 机制/认证隔离。

---

## 一、任务系统

### 1.1 任务类型分类

| 类型 | 说明 | 示例 |
|------|------|------|
| **主线-精灵战争** | 第 3-9 层贯穿的大型活动，选择阵营后不可变更 | 翡翠秘钥（第 3 层 10 章）/ 琉璃秘钥（第 4 层）/ 玛瑙秘钥（第 6 层） |
| **楼层特色** | 每层独有的剧情任务链 | 第 4 层造船/第 5 层三十年的叹息/第 6 层谜杀悬疑/第 7 层斗技场作弊 |
| **日常** | 可重复的小型任务 | 讨伐任务/采集任务/护送任务 |
| **隐藏** | 需满足特殊条件触发 | 体术传授（第 2 层）/冥想觉醒（第 6 层熟练度 500） |

### 1.2 任务状态机

```
[未发现] --触发条件--> [可接受] --接受--> [进行中] --完成条件--> [已完成]
                                              |
                                              +--失败条件--> [已失败]
```

**触发条件类型**：
- 到达指定地点（如发现战斗中的精灵骑士）
- 与 NPC 对话（如向罗摩罗说「请帮我造船」）
- 持有特定道具（如捡到造船钉）
- 达到特定等级/技能熟练度
- 前置任务完成

### 1.3 选择分支设计

**精灵阵营选择**（第 3 层，不可逆）：
```
发现两名精灵骑士交战
  ├── 帮助暗黑精灵 → 森林精灵骑士死亡 → 暗黑精灵阵营主线
  │   └── NPC 基滋梅尔（女性）可能存活成为同行 NPC
  └── 帮助森林精灵 → 暗黑精灵骑士死亡 → 森林精灵阵营主线
      └── NPC 为随机男性森林精灵骑士
```

**道德抉择**：
- 第 6 层：赛龙（杀人犯领主）被摩鲁特杀死后，是否追捕赛亚诺？
- 第 7 层：揭露柯尔罗伊家作弊 vs 保持沉默获取利益

### 1.4 各层特色任务设计

| # | 层 | 任务名 | 类型 | 核心机制 |
|---|---|--------|------|---------|
| 1 | 1 | 韧炼之剑 | 困难获取 | 完成指定条件获得准稀有武器 |
| 2 | 2 | 体术修行 | 隐藏技能 | 击碎巨石解锁特别技能「体术」 |
| 3 | 3 | 翡翠秘钥（10 章） | 主线 | 精灵阵营选择 + 10 章连续任务 |
| 4 | 3 | 公会组建 | 系统解锁 | 与镇长对话 → 夺回印章 → 约 20 小时 |
| 5 | 4 | 往日的船匠 | 楼层特色 | 素材收集 + BOSS 战 + 自由设计贡多拉 |
| 6 | 4 | 精灵秘钥护送 | 主线 | 护送翡翠+琉璃秘钥至第 5 层 |
| 7 | 5 | 三十年的叹息 | 楼层特色 | 推理解谜 + 灵魂系 NPC 交互 |
| 8 | 5 | 遗物猎人 | 日常 | 捡拾古代硬币/宝石/首饰 + NPC 鉴定 |
| 9 | 6 | 史塔基翁的诅咒 | 楼层特色 | 推理悬疑 + 7 名证人 + 密码破解 |
| 10 | 6 | 玛瑙秘钥 | 主线 | 穿越两区通路迷宫 + 35 格推盘益智 |
| 11 | 7 | 必胜秘笈 | 事件 | NPC 售卖斗技场预测 → 陷阱 |
| 12 | 7 | 识破作弊 | 楼层特色 | 采集证据 + 脱色剂制作 + 厩舍潜入 |
| 13 | 7 | 法鲁哈利的审判 | 楼层终章 | 五场领主决定战 |

---

## 二、角色成长系统

### 2.1 属性体系

| 属性 | 缩写 | SAO 对应 | 影响 |
|------|------|---------|------|
| 力量 | STR | 筋力 | 物理伤害、负重、格挡 |
| 敏捷 | AGI | 敏捷度 | 攻速、闪避、移速、先攻 |
| 体力 | VIT | 隐含 | HP 上限、HP 回复率、异常状态抗性 |
| 智力 | INT | 隐含 | 鉴定成功率、益智游戏效率、NPC 对话选项 |
| 技巧 | DEX | 隐含 | 会心率、制造成功率、陷阱发现 |
| 幸运 | LUK | 幸运（隐藏） | 掉宝率、稀有遭遇、强化成功率 |

**初始值**：全属性 10，角色创建时获得 10 点自由分配。
**升级加点**：每级获得 3 点自由分配。

### 2.2 等级与经验值

**升级公式**：
```
exp_to_next_level = 100 × level^1.5
```

| 等级 | 所需经验 | 累计经验 | 对应楼层 |
|------|---------|---------|---------|
| 1→2 | 100 | 100 | 第 1 层 |
| 5→6 | 1,118 | 3,486 | 第 1 层终 |
| 10→11 | 3,162 | 18,071 | 第 2-3 层 |
| 15→16 | 5,809 | 47,735 | 第 4-5 层 |
| 20→21 | 8,944 | 93,416 | 第 6-7 层 |

**经验分配规则**（复数玩家击杀）：
```
player_share = base_exp × (damage_dealt / total_damage × 0.5
                          + aggro_time / total_aggro_time × 0.3
                          + debuff_contribution × 0.2)
```

### 2.3 技能格子系统

- 无职业限制，自由选择技能
- 初始 2 个技能格子，每 5 级解锁 1 个，上限 10 格
- 技能格子可随时更换（保留熟练度），但装备中的技能冷却 24 小时后才能卸下
- **卡雷斯欧的水晶瓶**（极稀有）：保存一个技能的熟练度，等效增加一格

### 2.4 SAO 剑技 → D&D 战技映射

SAO 的剑技系统映射为 D&D 战斗大师风格的四阶段循环：

```
Stance（起手式）→ Assist（系统辅助加速）→ Delay（技后硬直）→ Switch（切换搭档）
```

**详细映射**：
| SAO 概念 | D&D/CRPG 映射 | 说明 |
|---------|--------------|------|
| 剑技起手式 | 战技宣言（消耗行动） | 玩家选择剑技，进入起手姿势 |
| 系统辅助 | 命中加成 + 伤害倍率 | 系统接管武器轨迹，保证命中 |
| 技后硬直 | 回合结束 + 反击窗口 | 硬直期间 AC 降低，敌人获得优势 |
| 切换 | 反应动作触发 | 搭档消耗反应动作接替前卫 |

### 2.5 剑技全表

#### 细剑系

| 剑技 | 连击 | 倍率 | 冷却(s) | 解锁等级 | 叙事描述 |
|------|------|------|---------|---------|---------|
| 线性攻击（Linear） | 1 | 1.0 | 1.5 | 1 | 剑摆身体中央，旋转往前笔直刺出。纯白光芒 |
| 倾斜突刺（Oblique） | 1 | 1.1 | 1.5 | 2 | 下段刺击，银色光芒。最快的剑技之一 |
| 平行刺击（Parallel Sting） | 2 | 1.6 | 2.5 | 4 | 快到肉眼几乎看不见的连续突刺 |
| 流星（Shooting Star） | 1 | 1.8 | 3.0 | 8 | 最大射程突进技，准备动作复杂出招慢 |
| 闪电突刺（Lightning Thrust） | 4 | 3.2 | 5.0 | 15 | 高速四连突刺，闪电般光芒 |

#### 单手剑系

| 剑技 | 连击 | 倍率 | 冷却(s) | 解锁等级 | 叙事描述 |
|------|------|------|---------|---------|---------|
| 斜斩（Slant） | 1 | 1.0 | 1.5 | 1 | 基本斜向斩击，淡蓝色光芒。可弹开敌人武器 |
| 垂直斩（Vertical） | 1 | 1.1 | 1.5 | 2 | 上段斩击 |
| 水平斩（Horizontal） | 1 | 1.0 | 1.5 | 2 | 水平横扫 |
| 愤怒刺击（Rage Spike） | 1 | 1.4 | 2.0 | 3 | 突进技。剑摆左腰，极低姿势冲刺，淡蓝色光芒 |
| 音速冲击（Sonic Leap） | 1 | 1.6 | 2.5 | 5 | 突进技。扛右肩姿势，可朝空中发动。黄绿色光芒 |
| 圆弧斩（Horizontal Arc） | 2 | 1.8 | 3.0 | 6 | V 字轨迹二连击 |
| 锐爪（Sharp Nail） | 3 | 2.4 | 3.5 | 8 | 右胸→左胸→胸口中央，如野兽爪痕 |
| 旋风斩（Cyclone） | 3 | 2.8 | 4.0 | 12 | 旋转三连斩 |
| 星爆气流斩（Starburst Stream） | 16 | 12.0 | 15.0 | 25 | 传说级双剑 16 连击（需双剑流技能） |

#### 单手斧系

| 剑技 | 连击 | 倍率 | 冷却(s) | 解锁等级 | 叙事描述 |
|------|------|------|---------|---------|---------|
| 漩流（Whirlpool） | 1 | 1.3 | 2.0 | 1 | 龙卷风般回转攻击 |
| 双重砍劈（Double Cleave） | 2 | 2.0 | 3.0 | 4 | 红色特效光，陀螺旋转连砍两次 |

#### 体术系（特别技能）

| 剑技 | 连击 | 倍率 | 冷却(s) | 解锁等级 | 叙事描述 |
|------|------|------|---------|---------|---------|
| 闪打（Flash Hit） | 1 | 0.8 | 1.0 | 1 | 最快单发拳击，红色光芒。可武装解除 |
| 弦月（Crescent Moon） | 1 | 1.2 | 2.0 | 3 | 后空翻上踢，红色光芒 |

#### 大刀/武士刀系（BOSS 专用参考）

| 剑技 | 连击 | 倍率 | 特殊效果 | 叙事描述 |
|------|------|------|---------|---------|
| 旋车（Tsumujiguruma） | 1 | 3.0 | 全方位 + 晕眩 | 垂直跳起空中旋转，六道鲜红光。一击 50% HP |
| 浮舟（Ukifune） | 1 | 0.5 | 击飞 | 正下方往上高高砍起，连续技起手式 |
| 绯扇（Hiougi） | 3 | 4.0 | 浮舟后续 | 上下连击+突刺，全部会心时极大伤害 |
| 幻月（Gengetsu） | 1 | 2.0 | 随机分歧 | 同一起始动作随机不同轨迹，技后硬直短 |
| 旋风（Tsujikaze） | 1 | 2.5 | 远距离 | 拔刀系直线技，反应时间极短 |

### 2.6 非战斗技能

| 技能 | 类型 | 效果 |
|------|------|------|
| 搜敌（Searching） | 感知 | 发现隐藏怪物/陷阱/宝箱。可衍生「追踪」 |
| 追踪（Tracking） | 感知衍生 | 追踪朋友登录玩家的足迹 |
| 隐蔽（Hiding） | 潜行 | 降低被怪物/NPC 发现的概率 |
| 铁匠（Blacksmithing） | 制造 | 武器强化/制造，熟练度越高成功率越高 |
| 烹饪（Cooking） | 制造 | 制作食物，高级品可附带支持效果 |
| 冥想（Meditation） | 恢复 | 加快 HP 回复/提升消灭异常状态概率。Mod「觉醒」（熟练度 500）|
| 骑乘（Riding） | 移动 | 驾驭骑乘动物 |
| 游泳（Swimming） | 移动 | 提升水中能力，防止溺水 |
| 吟唱（Singing） | 社交 | 影响 NPC 好感度 |
| 调合（Mixing） | 制造 | 合成药水/染料/脱色剂 |

### 2.7 特殊技能解锁条件

| 技能 | 条件 | 地点 |
|------|------|------|
| 体术 | 击碎巨石 | 第 2 层东边岩山山顶 |
| 冥想觉醒 Mod | 冥想熟练度 500 | 任意地点 |
| 双剑流 | 反应速度系统检测最高（隐含） | 自动解锁 |
| 驯兽（推测） | 完成 NPC 试炼 | 未确认 |

---

## 三、战斗系统

### 3.1 SAO 混合模型

SAO 的战斗介于回合制和实时之间。在本系统中采用**声明式回合制**：
- 玩家通过自然语言描述行动意图
- AI DM 解析意图并调用对应工具（ReAct）
- 引擎计算结果，DM 叙事输出

### 3.2 伤害公式

```
base_damage = weapon_ATK × skill_multiplier × (1 + STR / 100)
defense_reduction = target_defense × 0.6
raw_damage = base_damage - defense_reduction
final_damage = raw_damage × random(0.9, 1.1)   # ±10% 随机
critical_damage = final_damage × 1.5            # 弱点会心
true_critical = final_damage × 2.0              # 真会心（随机触发）
```

**武器 ATK 计算**：
```
ATK = base_ATK + sharpness_bonus × 5 + enhancement_level × 3
```

### 3.3 命中与会心

**命中判定**（d20）：
```
attack_roll = d20 + DEX_mod + weapon_accuracy_bonus
hit = attack_roll >= target_AC
```

**会心判定**：
- **弱点会心**：命中弱点部位时触发（武器准度强化提升概率）
  - 概率 = 5% + accuracy_bonus × 2%
- **真会心**：随机触发，与 LUK 相关
  - 概率 = 1% + LUK / 200
- 两者可同时触发 → 复合会心 = 3.0 倍

### 3.4 切换（Switch）机制

```
前卫使用剑技 → 命中敌人 → 进入技后硬直（AC-4, 1 回合）
  → 喊「切换！」 → 前卫后撤（不触发借机攻击）
  → 后卫冲上 → 获得先攻优势（下次攻击 +2 命中）
```

**POT 轮值（Potion Rotation）**：小队成员轮流承受伤害，受伤者切换到后方喝药水回复。

### 3.5 异常状态

| 状态 | 持续 | 效果 | 解除 |
|------|------|------|------|
| 晕眩 | 最长 10s | 完全无法行动，最恐怖 | 无法手动解除，等待自然消退 |
| 麻痹 | 30s-5min | 无法移动，可被攻击 | 解毒道具/基滋梅尔解毒戒指 |
| 翻倒 | 3-5s | 倒地，需时间起身 | 自然起身 |
| 盲目 | 10-30s | 视界全黑 | 等待消退 |
| 中毒（伤害） | 持续 | HP 持续减少 | 解毒药水/精灵解毒咒 |
| 中毒（麻痹） | 30s-3min | 逐渐麻痹 | 解毒药水 |
| 恶寒 | 持续 | 体感温度极低，打喷嚏，行动受阻 | 生火取暖/两人毛毯共享体温 |

### 3.6 武器耐久与破损

- 每次攻击/防御消耗耐久度（1-3 点）
- 耐久度为 0 时武器碎裂消失
- 耐久度可通过强化 D 参数提升上限
- 对史莱姆等使用斩击武器会严重消耗耐久

### 3.7 BOSS 战设计模式

**多 HP 条系统**：
```
BOSS HP: [████████] [████████] [████████] [████████]
          HP 条 1     HP 条 2     HP 条 3     HP 条 4
```
每消耗一条 HP 可能触发：
- 阶段切换（伊尔凡古第 4 条换武器）
- 随从涌出（每条 HP 涌出 3 只护卫兵）
- 新技能解锁（毒化/闪电吐息/全方位攻击）
- 隐藏 BOSS 登场（亚斯特里欧斯在巴兰 HP 变黄时涌出）

---

## 四、经济与道具系统

### 4.1 货币系统

**单位**：珂尔（Col），k = 1000 珂尔。

**物价参考表**：

| 项目 | 价格 | 备注 |
|------|------|------|
| 黑面包 | 1 Col | 最便宜食物 |
| 帕里尼（烤鱼面包） | 12 Col | 街头小吃 |
| 旅馆（最便宜 INN） | 15 Col/晚 | 简陋 |
| 旅馆（农家二楼） | 80 Col/晚 | 含浴室和牛奶 |
| 贡多拉单程 | 50 Col | 第 4 层城内交通 |
| 亚鲁戈攻略册 | 0-500 Col | 免费版/付费版 |
| 情报查询费 | 500-1500 Col | 亚鲁戈单次查询 |
| 低级回复药水 | 100 Col | 时间持续回复 |
| 韧炼之剑（未强化） | ~15,000 Col | 准稀有单手剑 |
| 韧炼之剑+6 收购价 | ~39,800 Col | 强化后市价 |
| 亚鲁戈画胡须理由 | 100,000 Col | 绝密情报 |
| 赌场最高奖品 | 10,000,000 Col | 窝鲁布达之剑（10 万筹码） |

### 4.2 物品分类

| 类型 | item_type | 可堆叠 | 示例 |
|------|-----------|--------|------|
| 武器 | weapon | 否 | 韧炼之剑、骑士刺剑、利刃手斧 |
| 防具（身体） | armor_body | 否 | 午夜大衣、胸甲、皮革铠甲 |
| 防具（饰品） | accessory | 否 | 烛光戒指、波纹耳环、腾跃之靴 |
| 消耗品 | consumable | 是 | 回复药水、解毒药水、转移水晶、回复水晶 |
| 素材 | material | 是 | 梦幻熊油、火焰熊爪子、良木心材 |
| 任务物品 | quest_item | 否 | 翡翠秘钥、金坠饰、黄金魔术方块 |
| 水晶 | crystal | 是 | 回复水晶、转移水晶 |

### 4.3 武器五参数强化系统

| 参数 | 缩写 | 效果 |
|------|------|------|
| 锐利度 | S (Sharp) | 伤害提升 |
| 速度 | Q (Quick) | 攻击速度提升 |
| 准度 | A (Accuracy) | 弱点命中率提升 + 瞄准辅助 |
| 重量 | H (Heavy) | 武器/装甲破坏率提升 |
| 耐久度 | D (Durability) | 武器耐用度提升 |

**强化规则**：
- 每次成功 +1，显示为 `武器名+N`，明细如 `3S3D`
- 素材 = 基材（固定必需） + 添加材（自选数量，决定种类与成功率）
- NPC 铁匠成功率低，玩家铁匠（技能熟练度高）成功率更高
- **失败惩罚**：损失素材（常见）/ 属性转换 / 属性减少（-1）/ 武器消灭（极低概率）
- **牛头徽章金属板**（第 2 层 LA 奖励，共 10 片）：使用 1 片可让成功率升至最大值且自由选择强化性能

### 4.4 制造系统

```
基材 + 添加材 + 心材（铸铁/铸块） → 铁匠锤打 → 成品
```

- 制造不会完全失败（有素材一定产出武器），但成品随机（外形/名称/性能有幅度）
- **锤打次数代表性能**：普通初期装备 5 下、风花剑级别 20 下、韧炼之剑级别 30 下、骑士刺剑达 40 下
- 铁匠技术越高 + 素材越好 + 心材品质越高 → 越可能出现高性能武器
- 用有感情的旧武器熔铸为心材可提升品质

### 4.5 关键装备数据库

| 装备 | 类型 | 楼层 | ATK/DEF | 强化上限 | 特殊效果 |
|------|------|------|---------|---------|---------|
| 韧炼之剑 | 单手剑 | 1 | 45 | +8 | 准稀有，可用到第 4 层 |
| 午夜大衣 | 防具 | 1 | DEF 20 | — | 第 1 层 LA 奖励，桐人标志 |
| 风花剑 | 细剑 | 1 | 35 | +5 | 掉宝道具 |
| 骑士刺剑 | 细剑 | 3 | 55 | +15 | 精灵铁匠制，锤打 40 下 |
| 巴蓝将军四角裤 | 防具 | 2 | — | — | 第 2 层 LA，STR+/疾病抗性 |
| 日暮之剑 | 单手剑 | 5 | 68 | +10 | AGI+7，准度自动瞄准弱点 |
| 苦痛之短刀 | 短刀 | 6 | 42 | — | 耐毒耐冷+低概率出血 |
| 卡雷斯欧水晶瓶 | 道具 | 3 | — | — | 保存技能熟练度=增加一格 |
| 黄金魔术方块 | 道具 | 6 | — | — | 分解矿物/植物为 20cm 砖块 |
| 窝鲁布达之剑 | 单手剑 | 7 | 120 | — | HP 自动回复/净化毒素/必定会心 |
| 回复水晶 | 消耗品 | 7+ | — | — | 瞬间回满 HP，掉率 0.1% |
| 碧叶披肩 | 防具 | 6 | — | — | 消除精灵衰弱状态，仅存约 10 件 |
| 武勇之旗 | 长兵器 | 5 | — | +10 | 公会旗，15m 内全员攻防+CT 缩短 |

### 4.6 交易系统

- **NPC 商店**：固定库存和价格，各层不同
- **玩家摊贩**：铺设「摊贩地毯」开设简易商店
- **情报买卖**：亚鲁戈模式——面对面以珂尔交易，500 珂尔/次查询
- **NPC 寄卖**：道具寄卖在 NPC 道具屋
- **遗物兑换**：第 5 层 NPC 兑换商（古代硬币 → 珂尔）
- **赌场筹码**：第 7 层窝鲁布达，1 筹码 = 100 珂尔，不能直接换回

---

## 五、世界交互系统

### 5.1 移动与地图

| 方式 | 条件 | 范围 |
|------|------|------|
| 徒步 | 无 | 同层内 |
| 转移门 | 楼层 BOSS 击败后开通 | 已开通的各层主街区间 |
| 转移水晶 | 消耗品（天价） | 瞬间移动至任意已开通转移门 |
| 精灵灵树 | 精灵阵营友好 + 认证戒指 | 各层精灵据点间 |
| 贡多拉 | 第 4 层专用 | 罗毕亚城内及城外水路 |
| 迷宫阶梯 | 到达迷宫塔 | 上下层连通 |

### 5.2 NPC 关系系统

**好感度**：-100（敌对）~ 0（中立）~ +100（挚友）

**交互类型与好感度变化**：
| 行为 | 好感度变化 | 示例 |
|------|-----------|------|
| 完成委托任务 | +10~+30 | 完成精灵活动章节 |
| 赠送喜好道具 | +5~+15 | 给基滋梅尔食物 |
| 战斗中保护 NPC | +10~+20 | 替 NPC 挡伤害 |
| 攻击/偷窃 NPC | -30~-50 | 攻击精灵卫兵 |
| 选择敌对阵营 | -100 | 帮助森林精灵后对暗黑精灵 |

**好感度阈值效果**：
- +30：解锁特殊对话选项
- +50：NPC 可加入小队
- +70：解锁专属商店/任务
- +90：NPC 赠送稀有道具

### 5.3 环境交互

- **游泳**：头部入水 HP 开始减少。装备入水产生「湿濡效果」重量增加。需「游泳」技能
- **攀爬**：岩壁攀爬，高处坠落有跌落伤害
- **天气**：第 5 层有降雨（视界变差、装备变重）
- **日夜循环**：影响怪物出没种类和强度，夜晚城镇附近出现强力怪物
- **安全区**：圈内防止犯罪指令保护；迷宫安全地带（特殊颜色火把辨认）

### 5.4 决斗系统

| 模式 | 结束条件 | 特殊规则 |
|------|---------|---------|
| 完全胜负 | HP 归零 | 角色死亡 = 真实死亡 |
| 半损胜负 | HP 减半 | 存在「合法 PK」漏洞 |
| 初击胜负 | 先命中强攻 | 最安全的决斗方式 |

**倒数 60 秒**：接受后倒数，剑技发动不必等归零（判定在 0 秒后 0.001 秒即合法）。

### 5.5 公会系统

- **建立条件**：完成公会任务获得会长印章
- **自动征收**：成员赚取珂尔按比例上交公会
- **武勇之旗**：公会旗帜插地后 15m 内全员获得攻防/CT/异常抗性支援效果
- **魔王房间发现权**：先发现者担任联合部队领袖

---

## 六、持久化与数据设计

### 6.1 PostgreSQL 核心表设计

```sql
-- 1. 玩家账号
CREATE TABLE players (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(32) UNIQUE NOT NULL,
    display_name    VARCHAR(64) NOT NULL,
    token_hash      VARCHAR(128) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    last_login_at   TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT true
);

-- 2. 角色核心属性
CREATE TABLE player_characters (
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
CREATE TABLE item_definitions (
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
CREATE TABLE character_inventory (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id        UUID REFERENCES player_characters(id),
    item_def_id         VARCHAR(64) REFERENCES item_definitions(id),
    quantity            INTEGER DEFAULT 1,
    current_durability  INTEGER,
    enhancement_level   INTEGER DEFAULT 0,
    enhancement_detail  VARCHAR(32),  -- e.g. '3S3D'
    is_equipped         BOOLEAN DEFAULT false,
    equipped_slot       VARCHAR(32),
    acquired_at         TIMESTAMPTZ DEFAULT now()
);

-- 5. 剑技定义（全服共享）
CREATE TABLE sword_skill_definitions (
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
CREATE TABLE character_sword_skills (
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
CREATE TABLE character_noncombat_skills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    skill_name      VARCHAR(64) NOT NULL,
    level           INTEGER DEFAULT 1,
    experience      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT true,
    UNIQUE(character_id, skill_name)
);

-- 8. 任务进度
CREATE TABLE character_quests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    quest_def_id    VARCHAR(64) NOT NULL,
    status          VARCHAR(16) DEFAULT 'active',
    progress_json   JSONB DEFAULT '{}',
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- 9. 世界标记（剧情分支/选择记录）
CREATE TABLE character_world_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID REFERENCES player_characters(id),
    flag_key        VARCHAR(128) NOT NULL,
    flag_value      TEXT NOT NULL,
    set_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(character_id, flag_key)
);

-- 10. NPC 关系
CREATE TABLE character_npc_relationships (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id            UUID REFERENCES player_characters(id),
    npc_id                  VARCHAR(64) NOT NULL,
    relationship_level      INTEGER DEFAULT 0,
    interaction_count       INTEGER DEFAULT 0,
    last_interaction_summary TEXT,
    UNIQUE(character_id, npc_id)
);

-- 11. 对话历史
CREATE TABLE conversation_messages (
    id              BIGSERIAL PRIMARY KEY,
    player_id       UUID REFERENCES players(id) NOT NULL,
    role            VARCHAR(16) NOT NULL,
    content         TEXT NOT NULL,
    token_count     INTEGER,
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_conv_player_time ON conversation_messages(player_id, created_at DESC);

-- 12. 对话摘要
CREATE TABLE conversation_summaries (
    id              BIGSERIAL PRIMARY KEY,
    player_id       UUID REFERENCES players(id),
    summary         TEXT NOT NULL,
    covers_from_id  BIGINT,
    covers_to_id    BIGINT,
    token_count     INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

### 6.2 Redis 缓存 Key 设计

命名规范：`sao:{domain}:{entity_id}:{sub}`

```
# 认证
sao:auth:token:{token}              → player_id     STRING, TTL 24h

# 玩家状态（Write-Through）
sao:player:{pid}:state              → HASH           TTL 2h, 活跃续期
sao:player:{pid}:inventory          → HASH           TTL 2h
sao:player:{pid}:skills             → HASH           TTL 2h
sao:player:{pid}:quests             → HASH           TTL 2h

# 对话（Write-Behind）
sao:player:{pid}:chat:history       → LIST            LPUSH, LTRIM 50, TTL 4h
sao:player:{pid}:chat:summary       → STRING          TTL 4h

# 战斗（临时）
sao:combat:{combat_id}              → HASH            TTL 30min

# 限流
sao:ratelimit:{pid}:chat            → STRING 计数     TTL 60s, 每分钟 ≤ 20

# 在线
sao:online:{pid}                    → "1"             TTL 5min, 心跳续期
```

### 6.3 缓存一致性策略

| 数据 | 策略 | 说明 |
|------|------|------|
| 玩家状态 | Write-Through | 先写 Redis，异步写 PG |
| 玩家登录 | Cache-Aside Load | 从 PG 加载到 Redis |
| 对话历史 | Write-Behind | 每 10 条或 30s 批量写 PG |
| 战斗状态 | Write-Through + TTL | 战斗结束同步状态后删 key |

---

## 七、底层规则自动化

### 7.1 骰子系统

```python
def roll(sides: int = 20, count: int = 1, modifier: int = 0) -> RollResult:
    """d20 核心骰 + modifier"""
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    natural_20 = any(r == sides for r in rolls)
    natural_1 = any(r == 1 for r in rolls)
    return RollResult(rolls=rolls, modifier=modifier, total=total,
                      critical=natural_20, fumble=natural_1)
```

### 7.2 经验分配公式

```python
def distribute_exp(base_exp: int, participants: list[CombatParticipant]) -> dict[str, int]:
    total_damage = sum(p.damage_dealt for p in participants)
    total_aggro = sum(p.aggro_time for p in participants)
    shares = {}
    for p in participants:
        share = base_exp * (
            p.damage_dealt / total_damage * 0.5 +
            p.aggro_time / total_aggro * 0.3 +
            p.debuff_contribution * 0.2
        )
        shares[p.player_id] = max(1, int(share))
    return shares
```

### 7.3 等级-属性成长曲线

```python
def calc_max_hp(level: int, vit: int) -> int:
    return 200 + level * 50 + vit * 10

def calc_exp_to_next(level: int) -> int:
    return int(100 * level ** 1.5)
```

### 7.4 怪物 AI 行为模式

| 模式 | 行为 | 适用怪物 |
|------|------|---------|
| 攻击型 | 锁定最近目标持续攻击 | 狗头人/牛头人 |
| 防御型 | 低 HP 时进入防御/逃跑 | 野犬/蜘蛛 |
| 群体型 | HP<50% 嚎叫呼叫同伴 | 咆哮狼 |
| 伏击型 | 静止伪装，近距离时突袭 | 树妖幼苗 |
| 阶段型 | 根据 HP 比例切换行为 | BOSS |
| 窃取型 | 抢夺道具后逃跑 | 狡猾老鼠人/姆利基 |

### 7.5 掉落概率表

| 品质 | 概率 | 示例 |
|------|------|------|
| 普通素材 | 60-80% | 毛皮/骨头/虫壳 |
| 优质素材 | 15-30% | 坚硬角/锐利牙 |
| 稀有素材 | 3-8% | 梦幻熊油/女王蜘蛛毒牙 |
| 装备 | 1-5% | 风花剑/韧炼之剑 |
| 极稀有 | 0.01-0.1% | 回复水晶/LA 专属 |

---

## 八、记忆系统架构

### 8.1 三层记忆模型总览

```
Layer 3: LLM 上下文  ← 每次请求临时组装 (~4700 tokens)
    ↑ 读取
Layer 2: Redis 会话   ← 热数据缓存 (TTL 2-4h)
    ↑↓ 同步
Layer 1: PostgreSQL   ← 永久存储 (无 TTL)
```

### 8.2 PostgreSQL 永久记忆层

见第六章 6.1 完整 Schema。12 张表覆盖：玩家账号、角色属性、物品、剑技、技能、任务、世界标记、NPC 关系、对话历史、对话摘要。

### 8.3 Redis 会话记忆层

见第六章 6.2 Key 设计。核心缓存策略见 6.3。

### 8.4 LLM 上下文记忆层

每次 LLM 调用的 messages 数组构建：

```
[system] DM 人设 + 世界规则摘要                     ~800 tokens   (固定模板)
[system] Tool Definitions (ReAct 工具 schema)       ~500 tokens   (固定)
[system] 当前玩家状态压缩快照                         ~200 tokens   (Redis)
[system] 之前冒险经历摘要                             ~300 tokens   (Redis summary)
[system] RAG 检索结果 (3-5 chunks)                   ~800 tokens   (ChromaDB)
[user/assistant...] 最近 10-15 轮对话                ~2000 tokens  (Redis history)
[user] 当前玩家输入                                   ~100 tokens
─────────────────────────────────────────────────────────────────────
总计                                                  ~4700 tokens / 请求
```

### 8.5 对话摘要压缩机制

```
触发条件: Redis history 消息数 > 40

执行流程:
1. 取最旧 20 条消息
2. 调用 LLM 生成摘要 (~200 字)
3. 存入 PG conversation_summaries
4. 更新 Redis sao:player:{pid}:chat:summary
5. LTRIM Redis history 保留最近 30 条
```

### 8.6 玩家状态快照格式

注入 LLM 上下文的压缩格式：

```
[玩家状态] 角色名 Lv.12 | HP 1850/2400 | Col 12,500
属性: STR 25 AGI 31 VIT 18 INT 12 DEX 20 LUK 8
位置: 第3层 兹姆福特 迷雾森林入口
装备: 韧炼之剑+6(3S3D) | 午夜大衣
活跃任务: 翡翠秘钥 第6章(潜入)
同行NPC: 基滋梅尔(HP 2800/3200)
```

### 8.7 数据流时序图

```
玩家输入 "我用 Linear 攻击哥布林"

  Frontend         Gateway          GameServer           Redis      PG      ChromaDB    LLM
     │                │                  │                  │        │          │         │
     │── WS msg ────>│                  │                  │        │          │         │
     │                │── gRPC ────────>│                  │        │          │         │
     │                │                  │                  │        │          │         │
     │                │                  │── HGETALL ─────>│        │          │         │
     │                │                  │── LRANGE ──────>│        │          │         │
     │                │                  │── GET summary ─>│        │          │         │
     │                │                  │<── 玩家数据 ────│        │          │         │
     │                │                  │                  │        │          │         │
     │                │                  │── query ──────────────────────────>│         │
     │                │                  │<── chunks ────────────────────────│         │
     │                │                  │                  │        │          │         │
     │                │                  │  [构建 context]  │        │          │         │
     │                │                  │── chat(tools) ──────────────────────────────>│
     │                │                  │<── tool_call: attack(linear, goblin) ───────│
     │                │                  │                  │        │          │         │
     │                │                  │  [ActionExecutor]│        │          │         │
     │                │                  │  d20+DEX → 命中  │        │          │         │
     │                │                  │  ATK×1.0 → 伤害  │        │          │         │
     │                │                  │── HSET state ──>│        │          │         │
     │                │                  │                  │─async─>│          │         │
     │                │                  │                  │        │          │         │
     │                │                  │── tool_result ──────────────────────────────>│
     │                │                  │<── streaming narrative ─────────────────────│
     │                │<── stream ──────│                  │        │          │         │
     │<── SSE ───────│                  │                  │        │          │         │
     │                │                  │── LPUSH history >│        │          │         │
```

---

## 九、ReAct 工具调用机制

### 9.1 State-in-Prompt vs ReAct 对比

| 维度 | State-in-Prompt | ReAct 工具调用 |
|------|----------------|---------------|
| 状态安全 | LLM 可能输出 hp:999999 | 所有数值由引擎计算 |
| 可重现性 | 同一输入不同结果 | 给定骰子种子完全确定 |
| 可审计 | 难追踪 | 每个 action 有日志 |
| 实现复杂度 | 低 | 高（需 Action Executor） |
| 推荐 | v0.300 MVP 快速验证 | **v0.400 最终方案** |

### 9.2 工具定义全集

#### 战斗类

| 工具 | 参数 | 说明 |
|------|------|------|
| `attack` | skill_id, target | 使用剑技/普攻攻击目标 |
| `defend` | — | 防御姿态（AC+2, 下回合） |
| `use_item` | item_id, target? | 使用消耗品（药水/水晶） |
| `flee` | direction | 逃跑（需通过检定） |

#### 移动类

| 工具 | 参数 | 说明 |
|------|------|------|
| `move_to` | area, location? | 移动到指定区域/地点 |
| `enter_dungeon` | dungeon_name | 进入迷宫/地城 |
| `use_teleport_crystal` | floor | 传送至指定层转移门 |

#### 交互类

| 工具 | 参数 | 说明 |
|------|------|------|
| `talk_to_npc` | npc_id, topic? | 与 NPC 对话 |
| `trade` | npc_id, action, item_id, qty | 买入/卖出道具 |
| `accept_quest` | quest_id | 接受任务 |
| `inspect` | target | 检查/鉴定目标 |

#### 角色类

| 工具 | 参数 | 说明 |
|------|------|------|
| `check_status` | — | 查看角色状态 |
| `check_inventory` | — | 查看背包 |
| `equip_item` | inventory_id, slot | 装备道具到指定槽位 |
| `rest` | type(short/long) | 短休/长休恢复 |
| `roll_dice` | sides, count, modifier | 骰子检定 |

### 9.3 Action Executor 五步验证链

```python
async def execute(player_id, state, tool_call) -> ActionResult:
    # Step 1: 权限验证
    if not has_permission(player_id, tool_call.name):
        return ActionResult(success=False, error="无权执行此操作")

    # Step 2: 前置条件
    if tool_call.name == "attack":
        if not state.has_skill(tool_call.args["skill_id"]):
            return ActionResult(success=False, error="未解锁该剑技")

    # Step 3: 资源消耗
    if state.current_hp <= 0:
        return ActionResult(success=False, error="HP 为 0，无法行动")

    # Step 4: 数值计算（纯确定性 + 骰子 RNG）
    result = compute_action(state, tool_call)

    # Step 5: 状态写入（先 Redis，异步 PG）
    await redis.hset(f"sao:player:{player_id}:state", result.state_changes)
    asyncio.create_task(pg.persist(player_id, result.state_changes))

    return result
```

### 9.4 完整交互时序

```python
async def stream_chat(player_id, message, model):
    # 1. 加载玩家状态 (Redis fallback PG)
    state = await state_service.load(player_id)

    # 2. 保存用户消息
    await conversation.save(player_id, "user", message)

    # 3. 构建三层记忆上下文
    context = await context_builder.build(player_id, message, state)

    # 4. ReAct 循环 (最多 5 轮 tool calls)
    actions = []
    for _ in range(5):
        response = await llm.chat_with_tools(context.messages, context.tools)

        if response.has_tool_calls:
            for call in response.tool_calls:
                result = await action_executor.execute(player_id, state, call)
                actions.append(result)
                context.add_tool_result(call.id, result)
        else:
            async for chunk in llm.stream(context.messages):
                yield ChatResponse(content=chunk, is_done=False)
            break

    # 5. 状态增量 + 持久化
    delta = compute_delta(original_state, state)
    await conversation.save(player_id, "assistant", narrative)
    yield ChatResponse(is_done=True, actions=actions, state_delta=delta)
```

### 9.5 错误处理与重试策略

| 错误类型 | 处理 |
|---------|------|
| 工具参数无效 | 返回错误提示，LLM 可重新调用 |
| 前置条件不满足 | 返回原因说明，LLM 叙事解释 |
| Redis 连接失败 | Fallback 到 PG 直接读写 |
| LLM 工具调用超过 5 轮 | 强制结束循环，输出当前叙事 |
| LLM 返回无效工具名 | 忽略该调用，日志告警 |

---

## 十、玩家隔离与认证

### 10.1 Token-Based 认证流程

```
注册: POST /api/v1/auth/register
  → 服务端生成 32 字节 random token
  → bcrypt hash 存 PG players.token_hash
  → raw token 存 Redis sao:auth:token:{token} → player_id (TTL 24h)
  → 返回 {player_id, token}

登录: POST /api/v1/auth/login
  → 验证用户名+密码
  → 生成新 token，同上存储
  → 返回 {player_id, token}

WS 连接: ws://host/ws?token=xxx
  → Gateway auth 中间件验证 token
  → 注入 player_id 到 gRPC context
```

### 10.2 Gateway 注入 player_id

```
前端 WS: {message: "攻击哥布林", model: "deepseek"}
  ↓ Gateway 从 token 解析 player_id
gRPC:    {player_id: "uuid-xxx", message: "攻击哥布林", model: "deepseek"}
```

**前端不发 player_id，不可伪造。**

### 10.3 四层数据隔离矩阵

| 层 | 措施 |
|---|---|
| Gateway | Auth 中间件从 token 解析 player_id |
| gRPC | ChatRequest.player_id 由 Gateway 强制设置 |
| GameServer | 所有 DB/Redis 查询带 player_id 过滤 |
| Redis | Key 前缀含 player_id (sao:player:{pid}:*) |

### 10.4 Proto 扩展定义

```protobuf
service GameService {
  rpc Chat(ChatRequest) returns (stream ChatResponse);
  rpc CreatePlayer(CreatePlayerRequest) returns (CreatePlayerResponse);
  rpc AuthenticatePlayer(AuthRequest) returns (AuthResponse);
  rpc CreateCharacter(CreateCharacterRequest) returns (CreateCharacterResponse);
  rpc GetPlayerState(GetPlayerStateRequest) returns (PlayerStateResponse);
}

message ChatRequest {
  string player_id = 1;
  string message = 2;
  string model = 3;
}

message ChatResponse {
  string content = 1;
  bool is_done = 2;
  string error = 3;
  repeated GameAction actions = 4;
  PlayerStateDelta state_delta = 5;
}

message GameAction {
  string action_type = 1;
  string description = 2;
  map<string, string> params = 3;
  bool success = 4;
  string result_summary = 5;
}

message PlayerStateDelta {
  int32 hp_change = 1;
  int32 xp_change = 2;
  int32 col_change = 3;
  repeated string items_gained = 4;
  repeated string items_lost = 5;
  string new_location = 6;
  bool level_up = 7;
}
```
