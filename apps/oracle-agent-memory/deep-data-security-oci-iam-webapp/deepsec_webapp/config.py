# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Validated environment configuration for the learning application."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import SplitResult, urlsplit

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# The bundled Flask server is a local learning aid. Keeping both the advertised
# URL and bind address on loopback prevents an accidental network-facing launch.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _load_environment(variable_name: str, default_filename: str) -> None:
    """Load one configured dotenv file without replacing exported values."""
    env_file = Path(os.environ.get(variable_name, _PROJECT_ROOT / default_filename)).expanduser()
    load_dotenv(env_file, override=False)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment setting {name} is missing.")
    return value


def _optional(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _positive_int(name: str) -> int:
    try:
        value = int(_required(name))
    except ValueError as exc:
        raise RuntimeError(f"Environment setting {name} must be an integer.") from exc
    if value <= 0:
        raise RuntimeError(f"Environment setting {name} must be positive.")
    return value


def _port_or_default(name: str, default: int) -> int:
    value = os.environ.get(name, str(default)).strip()
    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment setting {name} must be an integer.") from exc
    return _validated_port(parsed_value)


def _validated_port(value: int) -> int:
    """Reject invalid TCP ports from environment and direct construction."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise RuntimeError("OAM_WEB_PORT must be between 1 and 65535.")
    return value


def _origin_parts(name: str, value: str) -> SplitResult:
    """Parse an absolute origin and reject URL components this example does not use."""
    try:
        parsed = urlsplit(value)
        # Accessing ``port`` also validates malformed and out-of-range ports.
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"Environment setting {name} must be a valid URL origin.") from exc
    if (
        not parsed.scheme
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"Environment setting {name} must be a valid URL origin.")
    return parsed


def _validated_identity_domain_url(value: str) -> str:
    """Validate an HTTPS-only OCI IAM origin."""
    parsed = _origin_parts("OAM_DEEPSEC_OCI_DOMAIN_URL", value)
    if parsed.scheme.lower() != "https":
        raise RuntimeError("OAM_DEEPSEC_OCI_DOMAIN_URL must use HTTPS.")
    return value


def _identity_domain_url() -> str:
    """Return an HTTPS-only OCI IAM origin so OAuth secrets never use plaintext HTTP."""
    return _validated_identity_domain_url(_required("OAM_DEEPSEC_OCI_DOMAIN_URL").rstrip("/"))


def _validated_local_base_url(value: str) -> str:
    """Validate this example's loopback browser boundary."""
    parsed = _origin_parts("OAM_WEB_BASE_URL", value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise RuntimeError("OAM_WEB_BASE_URL must use HTTP or HTTPS.")
    if parsed.hostname.lower() not in LOOPBACK_HOSTS:
        raise RuntimeError("OAM_WEB_BASE_URL must use a loopback host for this example.")
    return value


def _local_base_url() -> str:
    """Return the browser origin after enforcing this example's loopback boundary."""
    return _validated_local_base_url(_required("OAM_WEB_BASE_URL").rstrip("/"))


def _validated_local_bind_host(host: str) -> str:
    """Validate a loopback-only development-server bind address."""
    if host not in LOOPBACK_HOSTS:
        raise RuntimeError("OAM_WEB_HOST must be a loopback host for this example.")
    return host


def _local_bind_host() -> str:
    """Return a loopback-only development-server bind address."""
    return _validated_local_bind_host(os.environ.get("OAM_WEB_HOST", "127.0.0.1").strip().lower())


@dataclass(frozen=True)
class RuntimeConfig:
    """Settings used by the running web process."""

    dsn: str
    config_dir: str | None
    wallet_location: str | None
    wallet_password: str | None
    owner_user: str
    app_pool_user: str
    app_pool_password: str
    domain_url: str
    oauth_client_id: str
    oauth_client_secret: str
    end_user_scope: str
    database_access_scope: str
    secret_key: str
    base_url: str
    host: str
    port: int
    memory_store_id: str
    embedding_model: str
    embedding_api_key: str | None
    embedding_api_base: str | None
    embedding_dimension: int

    def __post_init__(self) -> None:
        """Enforce network boundaries even when callers construct settings directly."""
        _validated_identity_domain_url(self.domain_url)
        _validated_local_base_url(self.base_url)
        _validated_local_bind_host(self.host.lower())
        _validated_port(self.port)

    @property
    def redirect_uri(self) -> str:
        """Return the callback URI registered in OCI IAM."""
        return f"{self.base_url}/auth/callback"

    @property
    def secure_browser_transport(self) -> bool:
        """Return whether the configured browser origin uses HTTPS."""
        return urlsplit(self.base_url).scheme.lower() == "https"

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """Build runtime configuration from ``.deepsec.runtime.env``."""
        _load_environment("OAM_WEB_ENV_FILE", ".deepsec.runtime.env")
        return cls._from_current_environment()

    @classmethod
    def _from_current_environment(cls) -> "RuntimeConfig":
        """Build runtime configuration from already loaded environment values."""
        secret_key = _required("OAM_WEB_SECRET_KEY")
        if len(secret_key) < 32:
            raise RuntimeError("OAM_WEB_SECRET_KEY must contain at least 32 characters.")
        return cls(
            dsn=_required("OAM_DEEPSEC_DSN"),
            config_dir=_optional("OAM_DEEPSEC_CONFIG_DIR"),
            wallet_location=_optional("OAM_DEEPSEC_WALLET_LOCATION"),
            wallet_password=_optional("OAM_DEEPSEC_WALLET_PASSWORD"),
            owner_user=_required("OAM_DEEPSEC_OWNER_USER").upper(),
            app_pool_user=_required("OAM_DEEPSEC_APP_DB_USER"),
            app_pool_password=_required("OAM_DEEPSEC_APP_POOL_PASSWORD"),
            domain_url=_identity_domain_url(),
            oauth_client_id=_required("OAM_WEB_OCI_CLIENT_ID"),
            oauth_client_secret=_required("OAM_WEB_OCI_CLIENT_SECRET"),
            end_user_scope=_required("OAM_WEB_OCI_END_USER_SCOPE"),
            database_access_scope=_required("OAM_WEB_OCI_DATABASE_ACCESS_SCOPE"),
            secret_key=secret_key,
            base_url=_local_base_url(),
            host=_local_bind_host(),
            port=_port_or_default("OAM_WEB_PORT", 8000),
            memory_store_id=_required("OAM_WEB_MEMORY_STORE_ID").upper(),
            embedding_model=_required("OAM_WEB_EMBEDDING_MODEL"),
            embedding_api_key=_optional("OAM_WEB_EMBEDDING_API_KEY"),
            embedding_api_base=_optional("OAM_WEB_EMBEDDING_API_BASE"),
            embedding_dimension=_positive_int("OAM_WEB_EMBEDDING_DIMENSION"),
        )


@dataclass(frozen=True)
class SetupConfig:
    """Additional settings used only by database setup."""

    runtime: RuntimeConfig
    admin_user: str
    admin_password: str
    owner_password: str
    iam_group: str

    @classmethod
    def from_env(cls) -> "SetupConfig":
        """Build setup configuration from ``.deepsec.env``."""
        _load_environment("OAM_DEEPSEC_ENV_FILE", ".deepsec.env")
        runtime = RuntimeConfig._from_current_environment()
        return cls(
            runtime=runtime,
            admin_user=_required("OAM_DEEPSEC_ADMIN_USER"),
            admin_password=_required("OAM_DEEPSEC_ADMIN_PASSWORD"),
            owner_password=_required("OAM_DEEPSEC_OWNER_PASSWORD"),
            iam_group=_required("OAM_DEEPSEC_OCI_IAM_GROUP"),
        )
