"""AppSettings -- InfraHub application configuration.

All environment variables are read via pydantic-settings.
DB_URL and JWT_SECRET are required and will cause a startup failure if missing.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """InfraHub application settings, loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database - Required, application fails to start if missing
    DB_URL: str

    # Authentication - Required, application fails to start if missing
    JWT_SECRET: str

    # LDAP
    LDAP_HOST: str = "localhost"
    LDAP_PORT: int = 389
    LDAP_USE_SSL: bool = False
    LDAP_BIND_DN: str = ""
    LDAP_BIND_PASSWORD: str = ""
    LDAP_BASE_DN: str = ""

    # ArgoCD
    ARGOCD_URL: str = "http://argocd.internal"
    ARGOCD_TOKEN: str = ""
    ARGOCD_APP_NAME: str = "infrahub-namespaces"

    # External bare-metal inventory API
    EXTERNAL_SERVER_API_URL: str = "http://baremetal-api.internal/servers"
    EXTERNAL_API_TIMEOUT_SECONDS: int = 30
    SYNC_INTERVAL_MINUTES: int = 60

    # Helm chart git repo (mounted in container)
    HELM_GIT_REPO_PATH: str = "/app/helm-repo"

    # Performance tier classification
    PERFORMANCE_TIER_CPU_THRESHOLD: int = 64

    # CPU tier conversion ratio
    CPU_HP_TO_REGULAR_RATIO: float = 2.0
