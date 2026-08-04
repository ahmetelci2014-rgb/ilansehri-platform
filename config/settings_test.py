"""Deterministic settings used only by automated tests.

Production keeps WhiteNoise's manifest storage. Tests intentionally use the
plain static-files backend so template rendering does not depend on a
collectstatic manifest created by another process.
"""

from .settings import *  # noqa: F401,F403

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
