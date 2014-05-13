from webapp2_extras.routes import RedirectRoute
import users
import admin
import emails
import visitlogs
import crontasks


_routes = [
    RedirectRoute('/admin/', users.AdminUserGeoChartHandler, name='admin-users-geochart', strict_slash=True),
    RedirectRoute('/admin/users/', users.AdminUserListHandler, name='admin-users-list', strict_slash=True),
    RedirectRoute('/admin/users/<user_id>/', users.AdminUserEditHandler, name='admin-user-edit', strict_slash=True, handler_method='edit'),

    RedirectRoute('/admin/emails/', emails.AdminEmailListHandler, name='admin-emails-list', strict_slash=True),
    RedirectRoute('/admin/emails/<email_id>/', emails.AdminEmailViewHandler, name='admin-email-view', strict_slash=True),

    RedirectRoute('/admin/visitlogs/', visitlogs.AdminVisitLogsListHandler, name='admin-visitlogs-list', strict_slash=True),

    RedirectRoute('/admin/logout/', admin.AdminLogoutHandler, name='admin-logout', strict_slash=True),

    RedirectRoute('/admin/crontasks/cleanuptokens/', crontasks.AdminCleanupTokensHandler, name='admin-crontasks-cleanuptokens', strict_slash=True),

]

def get_routes():
    return _routes

def add_routes(app):
    for r in _routes:
        app.router.add(r)
