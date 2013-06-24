"""
Created on June 10, 2012
@author: peta15
"""

from wtforms import fields
from wtforms import Form
from wtforms import validators
from lib import utils
from webapp2_extras.i18n import lazy_gettext as _
from webapp2_extras.i18n import ngettext, gettext

FIELD_MAXLENGTH = 50 # intended to stop maliciously long input


class FormTranslations(object):
    def gettext(self, string):
        return gettext(string)

    def ngettext(self, singular, plural, n):
        return ngettext(singular, plural, n)


class BaseForm(Form):
    def __init__(self, request_handler):
        super(BaseForm, self).__init__(request_handler.request.POST)

    def _get_translations(self):
        return FormTranslations()


class PasswordResetCompleteForm(BaseForm):
    password = fields.TextField(_('Password'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    c_password = fields.TextField(_('Confirm Password'),
                                  [validators.Required(), validators.EqualTo('password', _('Passwords must match.')),
                                   validators.Length(max=FIELD_MAXLENGTH)])
    pass


class LoginForm(BaseForm):
    username = fields.TextField(_('Username'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)],
                                id='l_username')
    password = fields.TextField(_('Password'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)],
                                id='l_password')
    pass


class ContactForm(BaseForm):
    email = fields.TextField(_('Email'), [validators.Required(), validators.Length(min=7, max=FIELD_MAXLENGTH),
                                          validators.regexp(utils.EMAIL_REGEXP, message=_('Invalid email address.'))])
    name = fields.TextField(_('Name'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    message = fields.TextAreaField(_('Message'), [validators.Required(), validators.Length(max=65536)])
    pass


class RegisterForm(BaseForm):
    username = fields.TextField(_('Username'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH),
                                                validators.regexp(utils.ALPHANUMERIC_REGEXP, message=_(
                                                    'Username invalid. Use only letters and numbers.'))])
    name = fields.TextField(_('Name'), [validators.Length(max=FIELD_MAXLENGTH)])
    last_name = fields.TextField(_('Last Name'), [validators.Length(max=FIELD_MAXLENGTH)])
    email = fields.TextField(_('Email'), [validators.Required(), validators.Length(min=7, max=FIELD_MAXLENGTH),
                                          validators.regexp(utils.EMAIL_REGEXP, message=_('Invalid email address.'))])
    password = fields.TextField(_('Password'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    c_password = fields.TextField(_('Confirm Password'),
                                  [validators.Required(), validators.EqualTo('password', _('Passwords must match.')),
                                   validators.Length(max=FIELD_MAXLENGTH)])
    country = fields.SelectField(_('Country'), choices=[])
    tz = fields.SelectField(_('Timezone'), choices=[])
    pass


class EditProfileForm(BaseForm):
    username = fields.TextField(_('Username'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH),
                                                validators.regexp(utils.ALPHANUMERIC_REGEXP, message=_(
                                                    'Username invalid. Use only letters and numbers.'))])
    name = fields.TextField(_('Name'), [validators.Length(max=FIELD_MAXLENGTH)])
    last_name = fields.TextField(_('Last Name'), [validators.Length(max=FIELD_MAXLENGTH)])
    country = fields.SelectField(_('Country'), choices=[])
    tz = fields.SelectField(_('Timezone'), choices=[])
    pass


class EditPasswordForm(BaseForm):
    current_password = fields.TextField(_('Password'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    password = fields.TextField(_('Password'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    c_password = fields.TextField(_('Confirm Password'),
                                  [validators.Required(), validators.EqualTo('password', _('Passwords must match.')),
                                   validators.Length(max=FIELD_MAXLENGTH)])
    pass


class EditEmailForm(BaseForm):
    new_email = fields.TextField(_('Email'), [validators.Required(), validators.Length(min=7, max=FIELD_MAXLENGTH),
                                              validators.regexp(utils.EMAIL_REGEXP,
                                                                message=_('Invalid email address.'))])
    password = fields.TextField(_('Password'), [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    pass
