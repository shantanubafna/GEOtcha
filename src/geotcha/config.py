"""Configuration management for GEOtcha."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
from platformdirs import user_cache_dir, user_config_dir, user_data_dir
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _geotcha_config_dir() -> Path:
    return Path(user_config_dir("geotcha", ensure_exists=True))


def _geotcha_cache_dir() -> Path:
    return Path(user_cache_dir("geotcha", ensure_exists=True))


def _geotcha_data_dir() -> Path:
    return Path(user_data_dir("geotcha", ensure_exists=True))


def _load_toml_config() -> dict:
    """Load config from ~/.config/geotcha/config.toml if it exists."""
    config_file = _geotcha_config_dir() / "config.toml"
    if config_file.exists():
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    return {}


class Settings(BaseSettings):
    """GEOtcha configuration.

    Priority: CLI flags > env vars > config.toml > defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="GEOTCHA_",
        env_file=".env",
        extra="ignore",
    )

    # NCBI settings
    ncbi_api_key: str | None = Field(
        default=None, description="NCBI API key for higher rate limits",
    )
    ncbi_email: str | None = Field(default=None, description="Email for NCBI Entrez")
    ncbi_tool: str = Field(default="geotcha", description="Tool name for NCBI Entrez")
    rate_limit: float = Field(
        default=3.0, description="Requests per second (3 without key, 10 with)",
    )

    # Output settings
    output_dir: Path = Field(default=Path("./output"), description="Default output directory")
    output_format: str = Field(default="csv", description="Output format: csv or tsv")

    # Cache settings
    cache_dir: Path | None = Field(default=None, description="Cache directory for SOFT files")
    cache_ttl_days: int = Field(default=7, description="Cache TTL in days")

    # Pipeline settings
    default_subset_size: int = Field(default=5, description="Default subset size for test runs")
    per_gse_timeout: int = Field(default=120, description="Timeout per GSE in seconds")
    max_retries: int = Field(default=3, description="Max retries for API calls")

    # Filtering settings
    include_scrna: bool = Field(
        default=False, description="Include single-cell RNA-seq datasets",
    )

    # LLM settings
    llm_provider: str | None = Field(
        default=None, description="LLM provider: openai, anthropic, ollama",
    )
    llm_model: str | None = Field(default=None, description="LLM model name")
    llm_api_key: str | None = Field(default=None, description="LLM API key")

    # ML settings
    ml_mode: str = Field(
        default="off",
        description="ML harmonization mode: off, hybrid, or full",
    )
    ml_model_dir: Path | None = Field(
        default=None,
        description="Directory containing ML model artifacts",
    )
    ml_model_version: str = Field(
        default="v1",
        description="ML model version tag",
    )
    ml_device: str = Field(
        default="auto",
        description="Device for ML inference: auto, cpu, cuda, or mps",
    )
    ml_batch_size: int = Field(
        default=32,
        description="Batch size for ML inference",
    )
    ml_threshold: float = Field(
        default=0.65,
        description="Minimum ML confidence to accept a prediction",
    )
    ml_review_threshold: float = Field(
        default=0.50,
        description="Below this confidence, flag for manual review",
    )

    # Data directory for runs
    data_dir: Path | None = Field(default=None, description="Directory for run state files")

    # Parallelism settings
    max_workers: int = Field(default=4, description="Max parallel workers for GSE extraction")

    # Entrez cache settings
    enable_entrez_cache: bool = Field(
        default=True, description="Cache Entrez API responses to reduce repeat network calls",
    )

    # Non-interactive mode
    non_interactive: bool = Field(
        default=False, description="Disable all interactive prompts, use defaults",
    )
    yes: bool = Field(
        default=False, description="Auto-confirm all prompts (equivalent to non-interactive)",
    )

    # Logging
    log_json: bool = Field(
        default=False, description="Emit structured JSON logs to stderr",
    )

    def get_cache_dir(self) -> Path:
        d = self.cache_dir or _geotcha_cache_dir() / "soft_files"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_data_dir(self) -> Path:
        d = self.data_dir or _geotcha_data_dir() / "runs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_effective_rate_limit(self) -> float:
        if self.ncbi_api_key:
            return 10.0
        return 3.0

    def get_effective_max_workers(self) -> int:
        """Max parallel workers: capped at 2 without NCBI API key, 6 with."""
        if self.ncbi_api_key:
            return min(self.max_workers, 6)
        return min(self.max_workers, 2)

    @classmethod
    def load(cls, **overrides) -> Settings:
        """Load settings from config file, env vars, and overrides."""
        toml_config = _load_toml_config()
        merged = {**toml_config, **{k: v for k, v in overrides.items() if v is not None}}
        return cls(**merged)


def get_config_path() -> Path:
    return _geotcha_config_dir() / "config.toml"


def save_config(key: str, value: str) -> None:
    """Save a key-value pair to the config TOML file."""
    config_path = get_config_path()
    config: dict = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    config[key] = value
    # Write TOML manually (tomllib is read-only)
    lines = []
    for k, v in config.items():
        if isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        elif isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        else:
            lines.append(f'{k} = "{v}"')
    config_path.write_text("\n".join(lines) + "\n")
