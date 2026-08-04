"""PII-free Flying Pig build identity shared by helper diagnostics."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from src._build_metadata import BUILD_METADATA


def build_identity() -> dict[str, str | None]:
    """Return generated version metadata without runtime environment or path values."""
    try:
        app_version = version("flyingpig")
    except PackageNotFoundError:
        app_version = "1.0.2"
    revision = BUILD_METADATA.get("revision")
    built_at = BUILD_METADATA.get("built_at")
    channel = BUILD_METADATA.get("channel")
    if not channel:
        channel = "packaged" if revision or built_at else "development"
    identity = f"{app_version}+{revision}" if revision else f"{app_version}+{channel}"
    return {
        "version": app_version,
        "revision": revision,
        "built_at": built_at,
        "channel": channel,
        "identity": identity,
    }
