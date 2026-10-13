"""Fixed cross-site operations; source and accountant come from the server session."""
import contextlib
import json
import os
import sys
from pathlib import Path


def main():
    import frappe
    from frappe_books import review_portal as portal
    from frappe.utils import getdate
    request = json.load(sys.stdin)
    sites = Path(request['sites_path']).resolve()
    target = (sites / request['portal']).resolve()
    if target.parent != sites or not target.is_dir():
        raise ValueError('Invalid portal site')
    os.chdir(sites)
    with contextlib.redirect_stdout(sys.stderr):
        frappe.init(site=request['portal'], sites_path=str(sites))
        frappe.connect()
        try:
            frappe.set_user(request['actor'])
            portal.require_manager()
            if not frappe.db.get_value('User', request['actor'], 'enabled'):
                frappe.throw('Accountant access is disabled.')
            source = request['source']
            if source not in portal.sources():
                frappe.throw('This company is not enabled for client reviews.')
            if request['operation'] == 'clients':
                result = [c for c in portal.profile()['clients'] if source in c['sources']]
            elif request['operation'] == 'assign':
                client = request['client']
                if not portal.allowed(client, source):
                    frappe.throw('This client does not have access to this company.')
                question = request['question'].strip()
                if not question or len(question) > 4000:
                    frappe.throw('Enter a question of up to 4,000 characters.')
                due = request.get('due_date') or None
                if due: getdate(due)
                # Read trusted snapshots in the source context, never browser supplied amounts.
                raw = portal.source_rows(source, review_items=request['items'])['rows']
                if len(raw) != len(request['items']):
                    frappe.throw('A selected transaction is unavailable. Refresh the report.')
                result = []
                for row in raw:
                    key = row['review_key']
                    if frappe.db.exists(portal.TASK, {'client': client, 'source_site': source,
                        'source_line': key, 'status': ['in', ['Open', 'Answered', 'Follow-up']]}):
                        frappe.throw('A selected transaction already has an active review for this client.')
                    doc = frappe.get_doc(dict(doctype=portal.TASK, client=client,
                        source_site=source, company=portal.sources()[source], kind='Transaction',
                        status='Open', question=question, due_date=due, source_line=key,
                        snapshot=json.dumps(row, default=str)))
                    portal.log(doc, 'Assigned', question=question)
                    doc.insert()
                    result.append(doc.name)
                frappe.db.commit()
            else:
                frappe.throw('Invalid review operation.')
            reply = {'result': result}
        except Exception as exc:
            frappe.db.rollback()
            reply = {'error': str(exc)}
        finally:
            frappe.destroy()
    print(json.dumps(reply, default=str))


if __name__ == '__main__':
    main()
