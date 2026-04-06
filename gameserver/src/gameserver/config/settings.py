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
class Settings:
    server: ServerConfig = field(default_factory=ServerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

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

        return cls(server=server_cfg, llm=llm_cfg)
