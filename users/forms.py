from django import forms
from django.contrib.auth.forms import (
    ReadOnlyPasswordHashField,
    UserCreationForm as BaseUserCreationForm,
)
from django.utils.translation import gettext_lazy as _

from .models import User


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=_('Password'),
        help_text=_(
            'Raw passwords are not stored, so there is no way to see this '
            'user’s password, but you can change the password using '
            "<a href='{}'>this form</a>."
        ),
    )

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields.get('password')
        if password:
            password.help_text = password.help_text.format('../password/')
        user_permissions = self.fields.get('user_permissions')
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related(
                'content_type'
            )


class UserCreationForm(BaseUserCreationForm):

    class Meta:
        model = User
        # fields = ('phone_number', 'nickname')
        fields = ('email',)

