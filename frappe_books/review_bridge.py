"""Accountant-only bridge from a company Books screen to the review inbox."""
import json
import subprocess
import sys
from pathlib import Path
import frappe
from frappe_books.review_portal import require_manager


def invoke(operation, **values):
    require_manager()
    sites = Path(frappe.get_site_path()).resolve().parent
    portal = frappe.conf.get('books_review_portal_site') or 'books.localhost'
    target = (sites / portal).resolve()
    if target.parent != sites or not target.is_dir():
        frappe.throw('The client review portal is not configured.')
    request = dict(operation=operation, portal=portal, source=frappe.local.site,
                   actor=frappe.session.user, sites_path=str(sites), **values)
    result = subprocess.run([sys.executable, '-m', 'frappe_books.review_bridge_worker'],
        input=json.dumps(request), text=True, capture_output=True, timeout=45,
        cwd=str(sites.parent))
    if result.returncode:
        frappe.log_error(title='Books client review assignment failed')
        frappe.throw('The review portal could not be reached. Please try again.')
    reply = json.loads(result.stdout)
    if reply.get('error'):
        frappe.throw(reply['error'])
    return reply['result']


@frappe.whitelist()
def clients():
    return invoke('clients')


@frappe.whitelist(methods=['POST'])
def assign(client: str, question: str, items: list, due_date: str = ''):
    require_manager()
    items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 50:
        frappe.throw('Select between 1 and 50 transactions.')
    normalized = []
    for item in items:
        if not isinstance(item, dict) or item.get('kind') not in {'bank', 'ledger'} or not isinstance(item.get('name'), str) or not 1 <= len(item['name']) <= 140:
            frappe.throw('Invalid transaction selection.')
        normalized.append(dict(kind=item['kind'], name=item['name']))
    if len({(i['kind'], i['name']) for i in normalized}) != len(normalized):
        frappe.throw('Select each transaction only once.')
    return invoke('assign', client=client, question=question, items=normalized, due_date=due_date)
