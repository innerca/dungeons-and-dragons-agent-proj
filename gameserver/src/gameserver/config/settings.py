from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field

import yaml


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} patterns with environment variable values."""
    pattern = re.compile(r"\$\{(\w+)\}")
    def replacer(match):
        if match is None:
            return ""
        var_name = match.group(1)
        return os.environ.get(var_name, "")
    return pattern.sub(replacer, value)


def _resolve_dict(d: dict) -> dict:
    """Recursively resolve environment variables in dict values."""
    resolved = {}
    for k, v in d.items():
        if isinstance(v, str):
            resolved[k] = _resolve_env_vars(v)
        elif isinstance(v, dict):
            resolved[k] = _resolve_dict(v)
        elif isinstance(v, list):
            resolved[k] = [
                _resolve_dict(item) if isinstance(item, dict)
                else _resolve_env_vars(item) if isinstance(item, str)
                else item
                for item in v
            ]
        else:
            resolved[k] = v
    return resolved


@dataclass
class ServerConfig:
    grpc_port: int = 50051


@dataclass
class DatabaseConfig:
    pg_min_size: int = 2
    pg_max_size: int = 10
    pg_command_timeout: int = 30


@dataclass
class RedisConfig:
    max_connections: int = 20
    key_prefix: str = "sao"


@dataclass
class CacheConfig:
    auth_token_ttl: int = 86400
    state_ttl: int = 7200
    history_ttl: int = 14400
    summary_ttl: int = 14400
    max_stored_messages: int = 50


@dataclass
class ProviderConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7
    provider_type: str = "openai"


@dataclass
class LLMConfig:
    default_provider: str = "deepseek"
    providers: dict[str, ProviderConfig] = field(default_factory=dict)


@dataclass
class CombatConfig:
    combat_state_ttl_seconds: int = 1800
    max_react_rounds: int = 5
    counter_attack_enabled: bool = True
    critical_weak_base: float = 0.05
    critical_weak_per_accuracy: float = 0.02
    critical_true_base: float = 0.01
    critical_true_luk_divisor: float = 200.0
    defense_reduction_factor: float = 0.6
    damage_variance_min: float = 0.9
    damage_variance_max: float = 1.1
    str_scaling_divisor: float = 100.0
    bare_hands_atk: int = 10
    crit_multiplier: float = 1.5
    flee_dc: int = 12
    generic_monster: dict = field(default_factory=lambda: {
        "hp": 100, "atk": 15, "defense": 5, "ac": 10,
    })


@dataclass
class LevelingConfig:
    exp_formula_base: int = 100
    exp_formula_exponent: float = 1.5
    stat_points_per_level: int = 3
    base_hp: int = 200
    hp_per_level: int = 50
    hp_per_vit: int = 10


@dataclass
class EconomyConfig:
    starting_col: int = 500
    npc_buy_rate: float = 0.5
    potion_heal_amount: int = 100


@dataclass
class EncounterConfig:
    rate: float = 0.25
    max_count: int = 3
    safe_areas: list[str] = field(default_factory=lambda: [
        "起始之城", "城镇", "旅馆", "商店", "广场", "转移门", "酒馆",
    ])


@dataclass
class FloorConfig:
    max_floor: int = 7
    floor_areas: dict[int, str] = field(default_factory=lambda: {
        1: "起始之城", 2: "乌尔巴斯", 3: "兹姆福特",
        4: "罗毕亚", 5: "卡尔路因", 6: "史塔基翁", 7: "窝鲁布达",
    })


@dataclass
class RestConfig:
    short_rest_recovery_rate: float = 0.25


@dataclass
class RelationshipTier:
    min: int = 0
    label: str = ""


@dataclass
class RelationshipConfig:
    min_level: int = -100
    max_level: int = 100
    tiers: list[RelationshipTier] = field(default_factory=lambda: [
        RelationshipTier(80, "挚友"),
        RelationshipTier(50, "亲密"),
        RelationshipTier(20, "友好"),
        RelationshipTier(0, "中立"),
        RelationshipTier(-30, "冷淡"),
        RelationshipTier(-60, "敌对"),
        RelationshipTier(-100, "仇恨"),
    ])


@dataclass
class ContextConfig:
    max_history_messages: int = 20
    max_rag_chunks: int = 5
    history_compression_threshold: int = 40
    history_trim_to: int = 30
    summary_max_chars: int = 600


@dataclass
class GameConfig:
    combat: CombatConfig = field(default_factory=CombatConfig)
    leveling: LevelingConfig = field(default_factory=LevelingConfig)
    economy: EconomyConfig = field(default_factory=EconomyConfig)
    encounter: EncounterConfig = field(default_factory=EncounterConfig)
    floor: FloorConfig = field(default_factory=FloorConfig)
    rest: RestConfig = field(default_factory=RestConfig)
    relationship: RelationshipConfig = field(default_factory=RelationshipConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    scene_keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Settings:
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    game: GameConfig = field(default_factory=GameConfig)

    @classmethod
    def load(cls, config_path: str | None = None) -> "Settings":
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent.parent.parent / "config" / "config.yaml"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Config file not found: {config_path}")
        except yaml.YAMLError as e:
            raise RuntimeError(f"Failed to parse config file: {e}")

        raw = _resolve_dict(raw)

        server_cfg = ServerConfig(**raw.get("server", {}))
        database_cfg = DatabaseConfig(**raw.get("database", {}))

        redis_raw = raw.get("redis", {})
        redis_cfg = RedisConfig(**redis_raw)

        cache_cfg = CacheConfig(**raw.get("cache", {}))

        llm_raw = raw.get("llm", {})
        providers = {}
        for name, pcfg in llm_raw.get("providers", {}).items():
            providers[name] = ProviderConfig(**pcfg)

        llm_cfg = LLMConfig(
            default_provider=llm_raw.get("default_provider", "deepseek"),
            providers=providers,
        )

        # Parse game config
        game_raw = raw.get("game", {})
        combat_cfg = CombatConfig(**game_raw.get("combat", {}))
        leveling_cfg = LevelingConfig(**game_raw.get("leveling", {}))
        context_cfg = ContextConfig(**game_raw.get("context", {}))

        economy_raw = game_raw.get("economy", {})
        economy_cfg = EconomyConfig(**economy_raw)

        encounter_cfg = EncounterConfig(**game_raw.get("encounter", {}))

        floor_raw = game_raw.get("floor", {})
        floor_areas_raw = floor_raw.get("floor_areas", {})
        floor_areas = {int(k): v for k, v in floor_areas_raw.items()}
        floor_cfg = FloorConfig(
            max_floor=floor_raw.get("max_floor", 7),
            floor_areas=floor_areas,
        )

        rest_cfg = RestConfig(**game_raw.get("rest", {}))

        rel_raw = game_raw.get("relationship", {})
        tiers_raw = rel_raw.get("tiers", [])
        tiers = [RelationshipTier(**t) for t in tiers_raw] if tiers_raw else RelationshipConfig().tiers
        rel_cfg = RelationshipConfig(
            min_level=rel_raw.get("min_level", -100),
            max_level=rel_raw.get("max_level", 100),
            tiers=tiers,
        )

        game_cfg = GameConfig(
            combat=combat_cfg,
            leveling=leveling_cfg,
            economy=economy_cfg,
            encounter=encounter_cfg,
            floor=floor_cfg,
            rest=rest_cfg,
            relationship=rel_cfg,
            context=context_cfg,
            scene_keywords=game_raw.get("scene_keywords", {}),
        )

        return cls(
            server=server_cfg,
            database=database_cfg,
            redis=redis_cfg,
            cache=cache_cfg,
            llm=llm_cfg,
            game=game_cfg,
        )


# ─── Global accessor ─────────────────────────────────────────────
_settings: Settings | None = None


def init_settings(settings: Settings) -> None:
    global _settings
    _settings = settings


def get_settings() -> Settings:
    if _settings is None:
        raise RuntimeError("Settings not initialized. Call init_settings() first.")
    return _settings
