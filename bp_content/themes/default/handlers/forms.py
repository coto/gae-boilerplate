__author__ = 'coto'
"""
Created on June 10, 2012
@author: peta15
"""

from wtforms import fields
from wtforms import Form
from wtforms import validators
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


# ==== Forms ====

class DeleteAccountForm(BaseForm):
    password = fields.TextField(_('Password'), [validators.Required(),
                                                validators.Length(max=FIELD_MAXLENGTH, message=_(
                                                    "Field cannot be longer than %(max)d characters."))],
                                id='l_password')
    pass
