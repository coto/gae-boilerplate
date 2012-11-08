from webapp2_extras.routes import RedirectRoute
from webapp2_extras.routes import PathPrefixRoute
import handlers
from forms import *
#  The next line is for the example and you will want to remove in your project
from example.forms import *

"""
You will to change the next line.  The 'class' is the model you want in your admin.  The 'adminform' will be the form used
to edit the entry.  You will place the adminform in forms.py
You will then be able to point your browser to /admin/<class>/  and get the list view of your model
The Example class and the AdminExampleForm is just an example and not to be included in your project.
"""
models=[{'class':Example, 'admin_form':AdminExampleForm},{'class':User, 'admin_form':AdminUserForm}]


redirect_list=[]
for model in models:

    redirect_list.append(RedirectRoute('/%s/'%model['class'].__name__.lower(), handlers.List, name='%s-list'%model['class'].__name__.lower(),
        strict_slash=True,defaults={'_class':model['class'],'_form_class':model['admin_form']}))

    redirect_list.append(RedirectRoute('/%s/add/'%model['class'].__name__.lower(), handlers.Edit, name='%s-add'%model['class'].__name__.lower(),
        handler_method='add',strict_slash=True,defaults={'_class':model['class'],'_form_class':model['admin_form']}))

    redirect_list.append(RedirectRoute('/%s/delete/<id>'%model['class'].__name__.lower(), handlers.Edit, name='%s-delete'%model['class'].__name__.lower(),
        handler_method='delete',strict_slash=True,defaults={'_class':model['class'],'_form_class':model['admin_form']}))

    redirect_list.append(RedirectRoute('/%s/<id>/'%model['class'].__name__.lower(), handlers.Edit, name='%s-edit'%model['class'].__name__.lower(),
        handler_method='edit',strict_slash=True,defaults={'_class':model['class'],'_form_class':model['admin_form']}))

redirect_list.append(RedirectRoute('/', handlers.Home, name='=home', strict_slash=True,defaults={}))
_routes = [PathPrefixRoute('/admin', redirect_list)]

def get_routes():
    return _routes

def add_routes(app):
    for r in _routes:
        app.router.add(r)
