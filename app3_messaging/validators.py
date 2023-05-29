from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_image(file):
    file_size = file.size

    limit_mb = 10
    if file_size > 10485760:
        raise ValidationError(_("Max size of file is %s MB") % limit_mb)
