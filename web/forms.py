'''
Created on June 10, 2012
@author: peta15
'''
from wtforms.form import Form
from wtforms import fields
from wtforms import validators
from lib import utils

FIELD_MAXLENGTH = 50 # intended to stop maliciously long input

class CurrentPasswordMixin(Form):
    current_password = fields.TextField('Password', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    
class PasswordMixin(Form):
    password = fields.TextField('Password', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])

class ConfirmPasswordMixin(Form):
    c_password = fields.TextField('Confirm Password', [validators.EqualTo('password', 'Passwords must match.'), validators.Length(max=FIELD_MAXLENGTH)])

class UserMixin(Form):
    email = fields.TextField('Email', [validators.Required(), validators.Length(min=8, max=FIELD_MAXLENGTH), validators.regexp(utils.EMAIL_REGEXP, message='Invalid email address.')])
    username = fields.TextField('Username', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH), validators.regexp(utils.ALPHANUMERIC_REGEXP, message='Username invalid.  Use only letters and numbers.')])
    name = fields.TextField('Name', [validators.Length(max=FIELD_MAXLENGTH)])
    last_name = fields.TextField('Name', [validators.Length(max=FIELD_MAXLENGTH)])
    country = fields.SelectField('Country', choices=utils.COUNTRIES)


class PasswordResetCompleteForm(PasswordMixin, ConfirmPasswordMixin):
    pass

# mobile form does not require c_password as last letter is shown while typing and typing is difficult on mobile
class PasswordResetCompleteMobileForm(PasswordMixin):
    pass

class LoginForm(PasswordMixin):
    username = fields.TextField('Username', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])

class ContactForm(Form):
    email = fields.TextField('Email', [validators.Required(), validators.Length(min=8, max=FIELD_MAXLENGTH), validators.regexp(utils.EMAIL_REGEXP, message='Invalid email address.')])
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    message = fields.TextAreaField('Message', [validators.Required(), validators.Length(max=65536)])
    
class RegisterForm(PasswordMixin, ConfirmPasswordMixin, UserMixin):
    pass

# mobile form does not require c_password as last letter is shown while typing and typing is difficult on mobile
class RegisterMobileForm(PasswordMixin, UserMixin):
    pass

class EditProfileForm(UserMixin):
    pass

class EditPasswordForm(PasswordMixin, ConfirmPasswordMixin, CurrentPasswordMixin):
    pass

# mobile form does not require c_password as last letter is shown while typing and typing is difficult on mobile
class EditPasswordMobileForm(PasswordMixin, CurrentPasswordMixin):
    pass
