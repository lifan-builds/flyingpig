"""Site adapter registry."""

from urllib.parse import urlparse

from src.sites.amex import AmexAdapter
from src.sites.base import BaseSiteAdapter
from src.sites.generic import GenericAdapter
from src.sites.profile_adapter import ProfileBackedAdapter
from src.sites.profiles import PROFILES

_ADAPTERS: dict[str, type[BaseSiteAdapter]] = {
    "amex": AmexAdapter,
    "generic": GenericAdapter,
}


def get_site_adapter(site: str) -> BaseSiteAdapter:
    """Get an instantiated site adapter by name."""
    site_id = site.lower()
    adapter_cls = _ADAPTERS.get(site_id)
    if adapter_cls is not None:
        return adapter_cls()
    profile = PROFILES.get(site_id)
    if profile is not None:
        return ProfileBackedAdapter(profile)
    available = ", ".join(list_sites())
    raise ValueError(f"Unknown site '{site}'. Available sites: {available}")


def list_sites() -> list[str]:
    """Return all registered site names."""
    return sorted({*_ADAPTERS.keys(), *PROFILES.keys()})


def resolve_from_url(url: str | None) -> str:
    """Return the site id whose hostname_patterns match the URL.

    Falls back to 'generic' when no specialized adapter matches. The
    generic adapter is never selected by this function directly (its
    patterns list is empty) — it's only returned as the fallback.
    """
    if not url:
        return "generic"
    haystack = url.lower()
    # Also include just the host in the haystack for safety.
    try:
        host = urlparse(url).hostname or ""
        haystack = f"{haystack} {host.lower()}"
    except Exception:
        pass
    for site_id, cls in _ADAPTERS.items():
        if site_id == "generic":
            continue
        for pattern in cls.hostname_patterns():
            if pattern.lower() in haystack:
                return site_id
    for site_id, profile in PROFILES.items():
        for pattern in profile.hostname_patterns:
            if pattern.lower() in haystack:
                return site_id
    return "generic"
