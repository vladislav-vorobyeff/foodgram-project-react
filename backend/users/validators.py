from django.core.exceptions import ValidationError


def validate_username_me(value):
    if 'me' in value.lower():
        raise ValidationError('me использовать нельзя')
