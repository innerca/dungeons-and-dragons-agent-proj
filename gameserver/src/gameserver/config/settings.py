import os
import re
from pathlib import Path
from dataclasses import dataclass, field

import yaml


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} patterns with environment variable values."""
    pattern = re.compile(r"\$\{(\w+)\}")
    def replacer(match):
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
        else:
            resolved[k] = v
    return resolved


@dataclass
class ServerConfig:
    grpc_port: int = 50051


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


@dataclass
class LevelingConfig:
    exp_formula_base: int = 100
    exp_formula_exponent: float = 1.5
    stat_points_per_level: int = 3
    base_hp: int = 200
    hp_per_level: int = 50
    hp_per_vit: int = 10


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
    context: ContextConfig = field(default_factory=ContextConfig)
    scene_keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Settings:
    server: ServerConfig = field(default_factory=ServerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    game: GameConfig = field(default_factory=GameConfig)

    @classmethod
    def load(cls, config_path: str | None = None) -> "Settings":
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent.parent.parent / "config" / "config.yaml"
            )

        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)

        raw = _resolve_dict(raw)

        server_cfg = ServerConfig(**raw.get("server", {}))

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
        game_cfg = GameConfig(
            combat=combat_cfg,
            leveling=leveling_cfg,
            context=context_cfg,
            scene_keywords=game_raw.get("scene_keywords", {}),
        )

        return cls(server=server_cfg, llm=llm_cfg, game=game_cfg)
