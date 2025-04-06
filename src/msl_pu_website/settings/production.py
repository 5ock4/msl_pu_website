import logging
from .base import *

DEBUG = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting server with PRODUCTION environment settings!")

EMAIL_HOST = "smtp.rosti.cz"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "8148@rostiapp.cz"
EMAIL_HOST_PASSWORD = "970ee714319c4bf0b897a199c199122d"
# DEFAULT_FROM_EMAIL = "8148@rostiapp.cz"
DEFAULT_FROM_EMAIL = "info@msliga.info"

ALLOWED_HOSTS = ["*"] # TODO: set to production hostnames
SECRET_KEY = "django-insecure-=2=w-8a-k#fte^(-xsl-cc)a%!&$^a)$_qb#s0oaz^c=qifbx6" # TODO: decide how to generate and store this secret key

try:
    from .local import *
except ImportError:
    pass
