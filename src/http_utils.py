"""
One function every API call goes through: request_with_retry.

Why: real APIs fail in two ways.
  - TEMPORARY failures (429 rate limit, 5xx server errors, network timeouts): wait and try again.
  - PERMANENT failures (400 bad request, 401 bad key, 404 not found): retrying won't help, so stop.

The waits grow each time (exponential backoff): 0.5s, 1s, 2s, 4s, 8s, plus a little random
"jitter" so many workers don't all retry at the same moment. Real systems use bigger waits
(2s, 4s, 8s...); these are short so the demo runs quickly.
"""

import logging
import random
import time

import requests

log = logging.getLogger("http")
RETRYABLE = {429, 500, 502, 503, 504}


def request_with_retry(method, url, max_tries=5, **kwargs):
    kwargs.setdefault("timeout", 10)                   # never let a stuck server freeze us
    for attempt in range(1, max_tries + 1):
        wait = 0.5 * 2 ** (attempt - 1) + random.uniform(0, 0.25)
        try:
            r = requests.request(method, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            log.warning("Network problem on %s %s: %s (attempt %d/%d)", method, url, e, attempt, max_tries)
        else:
            if r.status_code not in RETRYABLE:
                r.raise_for_status()                   # 4xx like 400/401/404: raise, don't retry
                return r.json() if r.content else None
            if r.headers.get("Retry-After"):           # the server told us how long to wait
                wait = float(r.headers["Retry-After"])
            log.warning("HTTP %s on %s %s -> retry %d/%d in %.1fs",
                        r.status_code, method, url.split("?")[0], attempt, max_tries, wait)
        time.sleep(wait)
    raise RuntimeError(f"Gave up after {max_tries} tries: {method} {url}")
