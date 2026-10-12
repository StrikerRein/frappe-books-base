import frappe
from frappe.tests import IntegrationTestCase
from frappe_books import bank_import
from frappe_books.tests.accounting import make_account


class IntegrationTestBankImport(IntegrationTestCase):
    def test_one_batch_preserves_lines_and_balances(self):
        bank = make_account("Batch Bank", account_type="Bank")
        income = make_account("Batch Income", root_type="Income")
        expense = make_account("Batch Expense", root_type="Expense")
        csv = f"date,description,money_out,money_in,balance,reference,account,classification\n2026-01-01,Receipt,0,100,100,IN,{income.name},Business\n2026-01-02,Cost,20,0,80,OUT,{expense.name},Business\n"
        journal_count = frappe.db.count("Books Journal Entry")
        name = bank_import.upload("Test bank batch", bank.name, 0, 80, csv, "test.csv")
        bank_import.post(name)
        doc = frappe.get_doc("Books Bank Statement", name)
        self.assertEqual(doc.docstatus, 1)
        self.assertEqual(len(doc.lines), 2)
        entries = frappe.get_all("Books Ledger Entry", filters={"voucher_no": name}, fields=["debit", "credit", "bank_statement", "bank_transaction", "posting_date"])
        self.assertEqual(len(entries), 4)
        self.assertEqual(sum(e.debit for e in entries), sum(e.credit for e in entries))
        self.assertEqual({e.bank_transaction for e in entries}, {r.name for r in doc.lines})
        self.assertTrue(all(e.bank_statement == name for e in entries))
        self.assertEqual(frappe.db.count("Books Journal Entry"), journal_count)
        with self.assertRaises(frappe.ValidationError):
            bank_import.upload("Duplicate", bank.name, 0, 80, csv, "test.csv")
        doc.cancel()
        self.assertEqual(frappe.db.count("Books Ledger Entry", {"voucher_no": name, "reverted": 0}), 0)

    def test_unreconciled_statement_is_rejected(self):
        bank = make_account("Reconcile Bank", account_type="Bank")
        with self.assertRaises(frappe.ValidationError):
            bank_import.upload("Invalid closing", bank.name, 0, 99, "date,description,money_out,money_in\n2026-01-01,Receipt,0,100\n", "invalid.csv")
