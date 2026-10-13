import frappe
from frappe_books.review_portal import require_login

no_cache=1

def get_context(context):
    if frappe.session.user=='Guest':
        frappe.local.flags.redirect_location='/login?redirect-to=%2Fclient-review'
        raise frappe.Redirect
    require_login()
    context.csrf_token=frappe.sessions.get_csrf_token()
    context.no_cache=1
