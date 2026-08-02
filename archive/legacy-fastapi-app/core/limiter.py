"""
Shared rate limiter instance.

slowapi requires a SINGLE Limiter instance to be used both for
``app.state.limiter`` (so its middleware can enforce limits) AND for every
``@limiter.limit(...)`` decorator. Previously each router created its own
private ``Limiter``, so the limits were registered on instances the app never
saw — rate limiting was silently disabled (Bug #6 regression).

Import ``limiter`` from here in ``app.main`` and in every route module.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
