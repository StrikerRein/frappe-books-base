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
            if source not in portal.sources() and not (request['operation']=='workflow' and source==request['portal']):
                frappe.throw('This company is not enabled for client reviews.')
            if request['operation'] == 'workflow':
                from frappe_books import workflows
                operation=request['workflow_operation']
                values=request['values']
                if operation=='workspace':
                    result=workflows.workspace(None if source==request['portal'] else source)
                elif operation=='save_template':
                    result=workflows.save_template(**values)
                elif operation=='create':
                    if source!=request['portal']:values['source_site']=source
                    result=workflows.create(**values)
                elif operation=='review_task':
                    task=frappe.get_doc(portal.TASK,values.get('name'))
                    if source!=request['portal'] and task.source_site!=source:frappe.throw('This task belongs to another company.')
                    result=portal.review(**values)
                elif operation in {'add_question','advance'}:
                    case=frappe.get_doc(workflows.WORKFLOW,values.get('name'))
                    if source!=request['portal'] and case.source_site!=source:frappe.throw('This workflow belongs to another company.')
                    result=getattr(workflows,operation)(**values)
                else:frappe.throw('Invalid workflow operation.')
                frappe.db.commit()
            elif request['operation'] == 'clients':
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
                from frappe_books import workflows
                case=workflows.create_case(request.get('workflow_template') or 'Transaction clarification',client,source,question[:140],due or '')
                workflows.attach(case,result)
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
