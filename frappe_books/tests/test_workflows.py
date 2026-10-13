import json
import frappe
from frappe.tests import IntegrationTestCase
from frappe_books import workflows as wf, review_portal as portal


class IntegrationTestWorkflows(IntegrationTestCase):
    def test_custom_stages_client_answers_and_accountant_completion(self):
        original_user=frappe.session.user
        original_sources=frappe.conf.get('books_review_sources')
        client='workflow-test@example.test';source='workflow-example.localhost'
        frappe.set_user('Administrator');frappe.db.savepoint('workflow_test')
        try:
            if not frappe.db.exists('Role',portal.CLIENT_ROLE):
                frappe.get_doc(dict(doctype='Role',role_name=portal.CLIENT_ROLE,desk_access=0)).insert()
            if not frappe.db.exists('User',client):
                user=frappe.get_doc(dict(doctype='User',email=client,first_name='Workflow test',enabled=1,user_type='Website User',send_welcome_email=0,roles=[dict(role=portal.CLIENT_ROLE)]))
                user.flags.no_welcome_mail=True;user.insert(ignore_permissions=True)
            frappe.get_doc(dict(doctype=portal.ACCESS,client=client,source_site=source,enabled=1)).insert()
            frappe.conf.books_review_sources={source:'Example company'}
            custom=[dict(s) for s in wf.DEFAULT_STAGES]
            custom.insert(4,dict(name='Senior accountant sign-off',role='Review'))
            template=wf.save_template('Workflow test template','Tax',custom)
            name=wf.create(template,client,source,'Tax review test',question='Clarify this tax item')
            doc=frappe.get_doc(wf.WORKFLOW,name)
            self.assertEqual(doc.stage,'Assigned')
            # Editing a template does not rewrite an existing workflow.
            wf.save_template('Workflow test template','Tax',wf.DEFAULT_STAGES,name=template)
            self.assertEqual(len(json.loads(frappe.get_doc(wf.WORKFLOW,name).stages)),6)
            self.assertRaises(frappe.ValidationError,lambda:wf.advance(name,'Cannot skip unanswered question'))
            task=frappe.db.get_value(portal.TASK,{'workflow':name},'name')
            frappe.set_user(client)
            self.assertRaises(frappe.PermissionError,wf.workspace)
            self.assertRaises(frappe.PermissionError,lambda:wf.advance(name,'Client cannot approve'))
            portal.answer(task,'Tax item explained')
            self.assertEqual(frappe.db.get_value(wf.WORKFLOW,name,'stage'),'Client responded')
            frappe.set_user('Administrator');wf.advance(name,'Begin accountant review')
            self.assertRaises(frappe.ValidationError,lambda:wf.advance(name,'stale',expected_modified='old'))
            portal.review(task,'Follow-up','Need supporting explanation')
            self.assertEqual(frappe.db.get_value(wf.WORKFLOW,name,'stage'),'Assigned')
            frappe.set_user(client);portal.answer(task,'Supporting explanation provided')
            frappe.set_user('Administrator');wf.advance(name,'Review answer');wf.advance(name,'Senior review')
            self.assertRaises(frappe.ValidationError,lambda:wf.advance(name,'Cannot complete before task approval'))
            portal.review(task,'Reviewed','Explanation checked')
            wf.advance(name,'Final approval')
            self.assertEqual(frappe.db.get_value(wf.WORKFLOW,name,'stage'),'Complete')
            wf.advance(name,'Reopen for further review',reopen=True)
            self.assertEqual(frappe.db.get_value(wf.WORKFLOW,name,'stage'),'Accountant review')
            events=json.loads(frappe.get_doc(wf.WORKFLOW,name).workflow_log)
            self.assertTrue(any(e['action']=='Reopened' for e in events))
            self.assertTrue(any(e.get('by')==client for e in events))
            bad=[dict(s) for s in wf.DEFAULT_STAGES];bad[2]['role']='Complete'
            self.assertRaises(frappe.ValidationError,lambda:wf.stages(bad))
        finally:
            frappe.set_user('Administrator');frappe.db.rollback(save_point='workflow_test')
            frappe.conf.books_review_sources=original_sources;frappe.set_user(original_user)
