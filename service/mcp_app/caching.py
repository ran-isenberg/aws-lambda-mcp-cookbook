"""Cache hints advertised on the server's catalog listings."""

from collections.abc import Mapping

from mcp.server.caching import CacheableMethod, CacheHint

# The catalog is static: the same three capabilities on every invocation, identical for every
# caller. Advertising a TTL stops clients re-listing on every turn, which on Lambda is a billed
# invocation each time. 'resources/read' is deliberately absent - user profiles are per-caller,
# and a public scope there would let a shared cache serve one user's profile to another.
#
# The TTL is also the worst-case delay before a deployed change reaches clients. This architecture
# has no faster path: the listChanged notifications that would push an update travel on a
# 'subscriptions/listen' stream, and an API Gateway HTTP API caps integrations at 30 seconds, so no
# long-lived stream survives. Five minutes trades most of the saving for a bounded staleness window
# - raise it only if you can accept clients running that much older a catalog after a deploy.
#
# ‼️ scope='public' lets shared intermediaries cache one copy for everybody. That is only sound
# while the catalog is identical for every caller. If you ever filter tools, prompts or templates
# by the authenticated principal, switch these to scope='private' or drop the hint entirely -
# otherwise a proxy can serve one caller's catalog to another.
CATALOG_CACHE_HINT = CacheHint(ttl_ms=300_000, scope='public')

CACHE_HINTS: Mapping[CacheableMethod, CacheHint] = {
    'tools/list': CATALOG_CACHE_HINT,
    'prompts/list': CATALOG_CACHE_HINT,
    'resources/templates/list': CATALOG_CACHE_HINT,
    'server/discover': CATALOG_CACHE_HINT,
}
