import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch
from frappe_books import review_bridge as bridge


class IntegrationTestReviewBridge(IntegrationTestCase):
    def test_only_accountant_can_select_trusted_source_items(self):
        original = frappe.session.user
        try:
            frappe.set_user('Guest')
            self.assertRaises(frappe.PermissionError, bridge.clients)
            self.assertRaises(frappe.PermissionError, lambda: bridge.assign('client', 'Clarify', [{'kind': 'ledger', 'name': 'example'}]))
            frappe.set_user('Administrator')
            for selection in [[], [{'kind': 'invalid', 'name': 'example'}], [{'kind': 'ledger', 'name': 'example'}] * 2]:
                self.assertRaises(frappe.ValidationError, lambda s=selection: bridge.assign('client', 'Clarify', s))
            with patch.object(bridge, 'invoke', return_value=['review-example']) as invoke:
                result = bridge.assign('client', 'Clarify', [{'kind': 'ledger', 'name': 'example', 'money_out': 999, 'source_site': 'other-company'}])
                self.assertEqual(result, ['review-example'])
                self.assertEqual(invoke.call_args.kwargs['items'], [{'kind': 'ledger', 'name': 'example'}])
        finally:
            frappe.set_user(original)
