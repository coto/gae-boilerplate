from boilerplate.external.wtforms import fields,widgets
from boilerplate.external.wtforms import Form
from boilerplate.external.wtforms.compat import text_type
from webapp2_extras.i18n import lazy_gettext as _
from boilerplate.forms import *
from myapp.models import *




class ChoiceField(fields.SelectFieldBase):
    widget = widgets.Select()
    def __init__(self, label=None, validators=None, coerce=text_type,property='id', reference_class=None, **kwargs):
        super(ChoiceField, self).__init__(label, validators, **kwargs)
        self.coerce = coerce
        self.reference_class = reference_class
        self.property = property
        self.choices= [(choice,choice) for choice in self.reference_class._properties[self.property]._choices]

    def iter_choices(self):
        for value, label in self.choices:
            yield (value, label, self.coerce(value) == self.data)

    def process_data(self, value):
        try:
            self.data = self.coerce(value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = self.coerce(valuelist[0])
            except ValueError:
                raise ValueError(self.gettext('Invalid Choice: could not coerce'))

    def pre_validate(self, form):
        for v, _ in self.choices:
            if self.data == v:
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))


class AdminUserForm(EditProfileForm):
    activated = fields.BooleanField('Activated')
    list_columns=[('username', 'Username'),
                  ('last_name', 'Last Name'),
                  ('email', 'E-Mail'),
                  ('country', 'Country')]
class AdminLessonForm(BaseForm):

    day= fields.TextField(_('Day'))
    basic_type = ChoiceField(_('Basic'),reference_class=Lesson,property='basic_type')
    sub_type = ChoiceField(_('SubType'),reference_class=Lesson,property='sub_type')
    certification_name = fields.TextField(_('Certification'))
    start_date=fields.DateTimeField(_('Start Date(Y-M-D H:M:S)'))
    end_date= fields.DateTimeField(_('End Date(Y-M-D H:M:S)'))
    list_columns=[('day', 'Day'),
                  ('start_date', 'Start Date'),
                  ('end_date', 'End Date'),
                  ('basic_type', 'Type'),
                  ('sub_type', 'Sub Type')]


