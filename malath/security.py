import hmac
import os
import time
from collections import defaultdict, deque
from datetime import timedelta
from secrets import token_urlsafe
from urllib.parse import urljoin, urlsplit

from flask import current_app, request, session, url_for

CSRF_SESSION_KEY = "_csrf_token"
PIN_VERIFIED_AT_SESSION_KEY = "pin_verified_at"
LEGACY_PIN_SESSION_KEY = "pin_verified"
_RATE_LIMITS = defaultdict(deque)


class CSRFError(ValueError):
    pass


def get_secret_key():
    secret_key = os.getenv("SECRET_KEY")
    environment = os.getenv("FLASK_ENV", os.getenv("MALATH_ENV", "development")).lower()
    testing = environment == "testing"

    if secret_key:
        return secret_key
    if environment in {"production", "prod"}:
        raise RuntimeError("SECRET_KEY is required when running Malath in production.")
    if testing:
        return "testing-secret-key"
    return os.urandom(32)


def get_session_cookie_secure():
    configured = os.getenv("SESSION_COOKIE_SECURE")
    environment = os.getenv("FLASK_ENV", os.getenv("MALATH_ENV", "development")).lower()

    if configured is not None:
        return configured.lower() in {"1", "true", "yes", "on"}
    return environment in {"production", "prod"}


def get_pin_verification_minutes():
    return int(os.getenv("PIN_VERIFICATION_MINUTES", "15"))


def generate_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    if not current_app.config.get("CSRF_ENABLED", True):
        return

    expected = session.get(CSRF_SESSION_KEY)
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise CSRFError("The form security token is missing or invalid.")


def is_safe_redirect_url(target):
    if not target:
        return False

    reference = urlsplit(request.host_url)
    test = urlsplit(urljoin(request.host_url, target))
    return test.scheme in {"http", "https"} and reference.netloc == test.netloc


def safe_redirect_target(target, default_endpoint, **values):
    if is_safe_redirect_url(target):
        return target
    return url_for(default_endpoint, **values)


def password_meets_policy(password):
    return (
        len(password) >= 8
        and any(character.isalpha() for character in password)
        and any(character.isdigit() for character in password)
    )


def check_rate_limit(scope, identifier, limit=None, window_seconds=None):
    limit = limit or current_app.config["RATE_LIMIT_DEFAULT"]
    window_seconds = window_seconds or current_app.config["RATE_LIMIT_WINDOW_SECONDS"]
    now = time.time()
    key = f"{scope}:{identifier}"
    attempts = _RATE_LIMITS[key]

    while attempts and now - attempts[0] > window_seconds:
        attempts.popleft()

    if len(attempts) >= limit:
        return False

    attempts.append(now)
    return True


def reset_rate_limits():
    _RATE_LIMITS.clear()


def mark_pin_verified():
    session[PIN_VERIFIED_AT_SESSION_KEY] = time.time()
    session.pop(LEGACY_PIN_SESSION_KEY, None)


def clear_pin_verification():
    session.pop(PIN_VERIFIED_AT_SESSION_KEY, None)
    session.pop(LEGACY_PIN_SESSION_KEY, None)


def is_pin_verified():
    verified_at = session.get(PIN_VERIFIED_AT_SESSION_KEY)
    if verified_at is None:
        session.pop(LEGACY_PIN_SESSION_KEY, None)
        return False

    try:
        verified_at = float(verified_at)
    except (TypeError, ValueError):
        clear_pin_verification()
        return False

    duration = timedelta(minutes=current_app.config["PIN_VERIFICATION_MINUTES"])
    if time.time() - verified_at > duration.total_seconds():
        clear_pin_verification()
        return False

    return True
