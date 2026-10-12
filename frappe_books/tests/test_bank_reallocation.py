import frappe
from frappe.tests import IntegrationTestCase
from frappe_books import bank_import, bank_reallocation
from frappe_books.tests.accounting import make_account


class IntegrationTestBankReallocation(IntegrationTestCase):
    def test_bulk_change_preserves_bank_and_supports_ordered_undo(self):
        bank = make_account("Reallocate Bank", account_type="Bank")
        income = make_account("Reallocate Income", root_type="Income")
        old = make_account("Reallocate Old", root_type="Expense")
        new = make_account("Reallocate New", root_type="Expense")
        third = make_account("Reallocate Third", root_type="Expense")
        csv = f"date,description,money_out,money_in,balance,reference,account,classification\n2026-01-01,Receipt,0,100,100,IN,{income.name},Business\n2026-01-01,Payment one,10,0,90,OUT1,{old.name},Business\n2026-01-02,Payment two,20,0,70,OUT2,{old.name},Business\n"
        batch = bank_import.upload("Reallocation test", bank.name, 0, 70, csv, "reallocate-test.csv")
        bank_import.post(batch)
        lines = frappe.get_doc(bank_import.BATCH, batch).lines
        selected = [lines[1].name, lines[2].name]
        bank_entries = frappe.get_all("Books Ledger Entry", filters={"account": bank.name}, fields=["name", "debit", "credit", "posting_date"])
        journal_count = frappe.db.count("Books Journal Entry")
        change = bank_reallocation.reallocate(selected, new.name, "Business", "Both payments corrected")
        self.assertEqual(change["count"], 2)
        self.assertTrue(all(frappe.db.get_value(bank_import.LINE, name, "offset_account") == new.name for name in selected))
        self.assertEqual(frappe.get_all("Books Ledger Entry", filters={"account": bank.name}, fields=["name", "debit", "credit", "posting_date"]), bank_entries)
        self.assertEqual(frappe.db.count("Books Journal Entry"), journal_count)
        later = bank_reallocation.reallocate([selected[0]], third.name, "Business", "Later correction")
        with self.assertRaises(frappe.ValidationError):
            bank_reallocation.undo(change["name"])
        self.assertEqual(frappe.db.get_value(bank_reallocation.DOCTYPE, change["name"], "docstatus"), 1)
        bank_reallocation.undo(later["name"])
        bank_reallocation.undo(change["name"])
        self.assertTrue(all(frappe.db.get_value(bank_import.LINE, name, "offset_account") == old.name for name in selected))
        count = frappe.db.count("Books Ledger Entry")
        with self.assertRaises(frappe.ValidationError):
            bank_reallocation.reallocate(selected, bank.name, "Business", "Invalid bank target")
        self.assertEqual(frappe.db.count("Books Ledger Entry"), count)
