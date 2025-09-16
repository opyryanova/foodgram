from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator

from users.constants import FORBIDDEN_USERNAMES


def forbid_usernames(value: str):
    if value and value.lower() in FORBIDDEN_USERNAMES:
        raise ValidationError("Nelzya ispolzovat eto imia polzovatelia.")
    return value


USERNAME_VALIDATORS = [UnicodeUsernameValidator(), forbid_usernames]
