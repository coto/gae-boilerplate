from webapp2_extras.routes import RedirectRoute
from webapp2_extras.routes import PathPrefixRoute
from forms import *
import handlers


_routes = [
    PathPrefixRoute('/admin', [
        RedirectRoute('/users/', handlers.List, name='user-list', strict_slash=True,defaults={'_class':User,'_form_class':AdminUserForm}),
        RedirectRoute('/users/add/', handlers.Edit, name='user-add', strict_slash=True, handler_method='add',defaults={'_class': User,'_form_class':AdminUserForm}),
        RedirectRoute('/users/delete/<user_id>/', handlers.Edit, name='user-delete', strict_slash=True, handler_method='delete',defaults={'_class': User, '_form_class':AdminUserForm}),
        RedirectRoute('/users/<user_id>/', handlers.Edit, name='user-edit', strict_slash=True, handler_method='edit',defaults={'_class': User, '_form_class':AdminUserForm}),

        RedirectRoute('/lessons/', handlers.List, name='lesson-list', strict_slash=True,defaults={'_class': Lesson,'_form_class':AdminLessonForm}),
        RedirectRoute('/lessons/add/', handlers.Edit, name='lesson-add', strict_slash=True, handler_method='add',defaults={'_class': Lesson,'_form_class':AdminLessonForm}),
        RedirectRoute('/lessons/delete/<user_id>/', handlers.Edit, name='lesson-delete', strict_slash=True, handler_method='delete',defaults={'_class': Lesson,'_form_class':AdminLessonForm}),
        RedirectRoute('/lessons/<user_id>/', handlers.Edit, name='lesson-edit', strict_slash=True, handler_method='edit',defaults={'_class': Lesson,'_form_class':AdminLessonForm}),

    ])
]

def get_routes():
    return _routes

def add_routes(app):
    for r in _routes:
        app.router.add(r)
