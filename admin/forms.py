from boilerplate.external.wtforms import fields,widgets
from boilerplate.external.wtforms import Form
from boilerplate.external.wtforms.compat import text_type
from webapp2_extras.i18n import lazy_gettext as _
from boilerplate.forms import *
from example.models import *
from boilerplate.models import User


class AdminUserForm(EditProfileForm):
    activated = fields.BooleanField('Activated')
    list_columns=[('username', 'Username'),
                  ('last_name', 'Last Name'),
                  ('email', 'E-Mail'),
                  ('country', 'Country')]
    search_list=['last_name','username','email']



