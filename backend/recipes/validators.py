from django.core.validators import RegexValidator


SLUG_REGEX = r"^[-a-zA-Z0-9_]+$"

SLUG_VALIDATOR = RegexValidator(
    regex=SLUG_REGEX,
    message="Разрешены латиница, цифры, дефис и нижнее подчеркивание.",
)
