from boilerplate.external.wtforms import fields,widgets
from boilerplate.external.wtforms import Form
from boilerplate.external.wtforms.compat import text_type
from webapp2_extras.i18n import lazy_gettext as _
from boilerplate.forms import *
from example.models import *
from boilerplate.models import User


# Imports for the wtf extensions
import decimal
import operator
import warnings

from boilerplate.external.wtforms import fields, widgets
from boilerplate.external.wtforms.compat import text_type, string_types



class ReferencePropertyField(fields.SelectFieldBase):
    """
    A field for ``db.ReferenceProperty``. The list items are rendered in a
    select.

    :param reference_class:
        A db.Model class which will be used to generate the default query
        to make the list of items. If this is not specified, The `query`
        property must be overridden before validation.
    :param get_label:
        If a string, use this attribute on the model class as the label
        associated with each option. If a one-argument callable, this callable
        will be passed model instance and expected to return the label text.
        Otherwise, the model object's `__str__` or `__unicode__` will be used.
    :param allow_blank:
        If set to true, a blank choice will be added to the top of the list
        to allow `None` to be chosen.
    :param blank_text:
        Use this to override the default blank option's label.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, reference_class=None, allow_blank=False, blank_text='', label_attribute='name',**kwargs):
        super(ReferencePropertyField, self).__init__(label, validators,**kwargs)
        self.label_attribute = label_attribute
        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        if reference_class is not None:
            self.query = reference_class.query().fetch()

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.query:
                if obj.key.urlsafe() == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.query:
            key = obj.key.urlsafe()
            label = obj.__getattr__(self.label_attribute)
            yield (key, label, self.object_data == obj.key )

    def process_data(self, value):
        try:
            self.data = ndb.Key(urlsafe=value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self.data =ndb.Key(urlsafe=valuelist[0])

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            for obj in self.query:
                if str(self.data) == str(obj.key):
                    break
            else:
                raise ValueError(self.gettext('Not a valid choice'))



"""
This form is just an example
"""
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

class AdminExampleForm(BaseForm):
    user= ReferencePropertyField( _('User'), reference_class=User,allow_blank=True, label_attribute='name')
    day= fields.TextField(_('Day'))
    basic_type = ChoiceField(_('Basic'),reference_class=Example,property='basic_type')
    sub_type = ChoiceField(_('SubType'),reference_class=Example,property='sub_type')
    certification_name = fields.TextField(_('Certification'))
    start_date=fields.DateTimeField(_('Start Date(Y-M-D H:M:S)'))
    end_date= fields.DateTimeField(_('End Date(Y-M-D H:M:S)'))
    list_columns=[('user_name','User'),
                  ('day', 'Day'),
                  ('start_date', 'Start Date'),
                  ('end_date', 'End Date'),
                  ('basic_type', 'Type'),
                  ('sub_type', 'Sub Type')]
    search_list=['user_name','basic_type','sub_type']