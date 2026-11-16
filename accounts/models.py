from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    """მომხმარებელი — ავტორიზაცია ხდება ელ-ფოსტით."""

    email = models.EmailField('ელ-ფოსტა', unique=True)
    phone = models.CharField(
        'ტელეფონი',
        max_length=9,
        unique=True,
        validators=[RegexValidator(r'^5\d{8}$', 'ნომერი უნდა იყოს 9 ციფრი და იწყებოდეს 5-ით')],
    )

    personal_id = models.CharField(
        'პირადი ნომერი',
        max_length=11,
        unique=True,
        null=True,
        validators=[RegexValidator(r'^\d{11}$', 'პირადი ნომერი უნდა შედგებოდეს 11 ციფრისგან')],
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email
