import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch
from frappe_books import review_portal as portal

class IntegrationTestReviewPortal(IntegrationTestCase):
    def test_assignment_isolation_and_answer_review_history(self):
        original_sources=frappe.conf.get('books_review_sources')
        original_user=frappe.session.user
        first='review-first@example.test';second='review-second@example.test'
        frappe.set_user('Administrator')
        frappe.db.savepoint('client_review_test')
        try:
            if not frappe.db.exists('Role',portal.CLIENT_ROLE):
                frappe.get_doc(dict(doctype='Role',role_name=portal.CLIENT_ROLE,desk_access=0)).insert()
            for email in [first,second]:
                if not frappe.db.exists('User',email):
                    user=frappe.get_doc(dict(doctype='User',email=email,first_name='Review test',enabled=1,user_type='Website User',send_welcome_email=0,roles=[dict(role=portal.CLIENT_ROLE)]))
                    user.flags.no_welcome_mail=True;user.insert(ignore_permissions=True)
                frappe.get_doc(dict(doctype=portal.ACCESS,client=email,source_site='review-example.localhost',enabled=1)).insert()
            frappe.conf.books_review_sources={'review-example.localhost':'Example business'}
            snapshot=dict(name='example-line',parent='example-batch',transaction_date='2025-06-01',reference='EXAMPLE',description='Example payment',money_out=100,money_in=0,offset_account='Example expense',classification='Review')
            with patch.object(portal,'source_rows',return_value={'rows':[snapshot]}):
                task=portal.assign(first,'review-example.localhost','Identify this payment',['example-line'])[0]
            frappe.set_user(second)
            self.assertEqual(portal.list_reviews(),[])
            for call in [lambda:portal.answer(task,'Unauthorized'),lambda:portal.find_transactions('review-example.localhost'),lambda:portal.review(task,'Reviewed','Unauthorized')]:
                self.assertRaises(frappe.PermissionError,call)
            self.assertFalse(frappe.has_permission(portal.TASK,'read'))
            self.assertFalse(frappe.has_permission('Books Bank Statement','read'))
            frappe.set_user(first)
            for value in [0,100,-1,101,float('nan')]:
                self.assertRaises(frappe.ValidationError,lambda v=value:portal.answer(task,'Mixed use','Mixed',v))
            answer=portal.answer(task,'60 percent business use','Mixed',60,'Utilities')
            self.assertEqual(answer['status'],'Answered')
            self.assertEqual(answer['percentage'],60)
            self.assertNotIn('history',answer)
            frappe.set_user('Administrator')
            followup=portal.review(task,'Follow-up','Explain the percentage',str(answer['modified']))
            self.assertEqual(followup['status'],'Follow-up')
            frappe.set_user(first)
            answer=portal.answer(task,'Meter usage supports the split','Mixed',60,'Utilities',str(followup['modified']))
            frappe.set_user('Administrator')
            completed=portal.review(task,'Reviewed','Reviewed, no ledger posting',str(answer['modified']))
            self.assertEqual(len(completed['history']),5)
            frappe.set_user(first)
            self.assertRaises(frappe.ValidationError,lambda:portal.answer(task,'Replace completed answer','Private'))
            frappe.set_user('Guest')
            self.assertRaises(frappe.PermissionError,portal.profile)
            self.assertRaises(frappe.PermissionError,portal.list_reviews)
        finally:
            frappe.set_user('Administrator');frappe.db.rollback(save_point='client_review_test')
            frappe.conf.books_review_sources=original_sources
            frappe.set_user(original_user)
