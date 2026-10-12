import frappe
from frappe.tests import IntegrationTestCase
from frappe_books import bank_import, bank_reallocation
from frappe_books.tests.accounting import make_account


class IntegrationTestBankReallocation(IntegrationTestCase):
    def test_mixed_spend_rounding_revision_and_undo(self):
        bank = make_account("Split Bank", account_type="Bank")
        income = make_account("Split Income", root_type="Income")
        business = make_account("Split Costs", root_type="Expense")
        personal = make_account("Split Owner")
        csv = f"date,description,money_out,money_in,balance,reference,account,classification,business_percentage,personal_account\n2026-01-01,Receipt,0,1000,1000,IN,{income.name},Business,,\n2026-01-01,Shared payment,100.01,0,899.99,OUT,{business.name},Mixed spend,33.33,{personal.name}\n"
        batch = bank_import.upload("Split test", bank.name, 0, 899.99, csv, "split-test.csv")
        bank_import.post(batch)
        line = frappe.get_doc(bank_import.BATCH, batch).lines[1]
        entries = frappe.get_all("Books Ledger Entry", filters={"bank_transaction": line.name}, fields=["account", "debit", "credit"])
        self.assertEqual(sum(e.debit - e.credit for e in entries), 0)
        self.assertEqual([e.debit for e in entries if e.account == business.name], [33.33])
        self.assertEqual([e.debit for e in entries if e.account == personal.name], [66.68])
        change = bank_reallocation.reallocate([line.name], business.name, "Mixed spend", "60 percent supported", business_percentage=60, personal_account=personal.name)
        self.assertEqual(frappe.db.get_value(bank_import.LINE, line.name, "business_percentage"), 60)
        bank_reallocation.undo(change["name"])
        self.assertEqual(frappe.db.get_value(bank_import.LINE, line.name, "business_percentage"), 33.33)
        with self.assertRaises(frappe.ValidationError):
            bank_reallocation.reallocate([line.name], business.name, "Mixed spend", "Invalid percentage", business_percentage=101, personal_account=personal.name)

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
