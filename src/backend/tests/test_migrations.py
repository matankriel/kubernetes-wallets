"""Tests for STORY-001: Database schema migrations.

Verifies that all 6 migration files exist with correct revision chains
and that AppSettings fails fast if required environment variables are missing.
No real database is required for these structural tests.
"""

import importlib.util
import os
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).parent.parent / "alembic" / "versions"

EXPECTED_REVISIONS = [
    ("0001_org_hierarchy", None, "0001"),
    ("0002_org_extended", "0001", "0002"),
    ("0003_servers", "0002", "0003"),
    ("0004_server_allocations", "0003", "0004"),
    ("0005_quota_allocations", "0004", "0005"),
    ("0006_projects", "0005", "0006"),
]


def load_migration(filename: str):
    """Dynamically load a migration module by filename stem."""
    path = VERSIONS_DIR / f"{filename}.py"
    spec = importlib.util.spec_from_file_location(filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigrationFiles:
    def test_all_revision_files_exist(self):
        """All 6 migration files must exist under alembic/versions/."""
        for filename, _, _ in EXPECTED_REVISIONS:
            path = VERSIONS_DIR / f"{filename}.py"
            assert path.exists(), f"Migration file missing: {filename}.py"

    def test_revision_chain_is_correct(self):
        """Each revision must point to the correct down_revision (chain integrity)."""
        for filename, expected_down_revision, expected_revision in EXPECTED_REVISIONS:
            module = load_migration(filename)
            assert module.revision == expected_revision, (
                f"{filename}: expected revision={expected_revision}, got {module.revision}"
            )
            assert module.down_revision == expected_down_revision, (
                f"{filename}: expected down_revision={expected_down_revision!r}, "
                f"got {module.down_revision!r}"
            )

    def test_all_migrations_have_upgrade_function(self):
        """Every migration must have an upgrade() function."""
        for filename, _, _ in EXPECTED_REVISIONS:
            module = load_migration(filename)
            assert callable(getattr(module, "upgrade", None)), (
                f"{filename}: missing upgrade() function"
            )

    def test_all_migrations_have_downgrade_function(self):
        """Every migration must have a downgrade() function (all are reversible)."""
        for filename, _, _ in EXPECTED_REVISIONS:
            module = load_migration(filename)
            assert callable(getattr(module, "downgrade", None)), (
                f"{filename}: missing downgrade() function"
            )

    def test_first_revision_has_no_down_revision(self):
        """Revision 0001 must have down_revision=None (it is the base)."""
        module = load_migration("0001_org_hierarchy")
        assert module.down_revision is None

    def test_revision_0006_is_head(self):
        """Revision 0006 must be the head (no other revision points to it)."""
        all_down_revisions = set()
        for filename, _, _ in EXPECTED_REVISIONS:
            module = load_migration(filename)
            if module.down_revision is not None:
                all_down_revisions.add(module.down_revision)
        # 0006 is the head — nothing points to it as a down_revision
        assert "0006" not in all_down_revisions


class TestAppSettings:
    def test_app_settings_requires_db_url(self):
        """AppSettings must raise ValidationError if DB_URL is missing."""
        import pydantic

        # Pre-import so the module-level singleton doesn't run during env removal
        from app.config import AppSettings  # noqa: F401 (ensure module is cached)

        # Remove DB_URL and JWT_SECRET from env to test fail-fast behavior
        env_backup = {}
        for key in ("DB_URL", "JWT_SECRET"):
            env_backup[key] = os.environ.pop(key, None)

        try:
            with pytest.raises((pydantic.ValidationError, Exception)):
                AppSettings()
        finally:
            # Restore env
            for key, val in env_backup.items():
                if val is not None:
                    os.environ[key] = val

    def test_app_settings_loads_db_url_from_env(self, monkeypatch):
        """AppSettings must read DB_URL from environment variable."""
        monkeypatch.setenv("DB_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-characters-long")

        from app.config import AppSettings
        settings = AppSettings()
        assert settings.DB_URL == "postgresql+asyncpg://test:test@localhost/test"

    def test_app_settings_has_required_fields(self, monkeypatch):
        """AppSettings must expose DB_URL and JWT_SECRET as required fields."""
        monkeypatch.setenv("DB_URL", "postgresql+asyncpg://test:test@localhost/test")
        monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-characters-long")

        from app.config import AppSettings
        settings = AppSettings()
        # Verify key fields exist and have correct types
        assert isinstance(settings.DB_URL, str)
        assert isinstance(settings.JWT_SECRET, str)
        assert isinstance(settings.PERFORMANCE_TIER_CPU_THRESHOLD, int)
        assert settings.PERFORMANCE_TIER_CPU_THRESHOLD == 64
        assert isinstance(settings.CPU_HP_TO_REGULAR_RATIO, float)
        assert settings.CPU_HP_TO_REGULAR_RATIO == 2.0
