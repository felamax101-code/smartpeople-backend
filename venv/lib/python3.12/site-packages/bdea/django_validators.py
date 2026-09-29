# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from bdea.client import is_disposable_email


def disposable_email_validator(email):
    """Disposable email validator."""
    apikey = settings.BDEA_APIKEY
    if is_disposable_email(email, apikey):
        raise ValidationError(_('Temporary or disposable email addresses are not allowed'))
