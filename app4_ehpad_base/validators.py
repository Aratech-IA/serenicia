from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_image(file):
    file_size = file.size

    limit_mb = 10
    if file_size > 10485760:
        raise ValidationError(_("Max size of file is %s MB") % limit_mb)


def validate_file_extension(value):
    try:
        if value.file.content_type != 'application/pdf':
            raise ValidationError(_('Only pdf file is accepted'))
    except AttributeError:
        pass
