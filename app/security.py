import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

ITERATIONS = 600_000


def hash_password(password):
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${value}"


def verify_password(password, encoded):
    try:
        _, iterations, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class RateLimiter:
    """Single-process demo limiter. Use shared storage before multiple workers."""
    def __init__(self):
        self.events = defaultdict(deque)

    def allow(self, key, limit, window=60):
        now = time.monotonic()
        # Bound the number of stale keys in a long running demo.
        if len(self.events) > 5000:
            self.events = defaultdict(deque, {k: v for k, v in self.events.items()
                                               if v and v[-1] > now-window})
        q = self.events[key]
        while q and q[0] <= now-window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True
