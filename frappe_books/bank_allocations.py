"""Exact business/personal allocations of a full statement amount."""
from decimal import Decimal, InvalidOperation
import frappe
from frappe_books.accounting.money import rounded
from frappe_books.accounting.ledger import validate_leaf_accounts


def allocations(line):
    net = rounded(line.money_out) - rounded(line.money_in)
    if line.classification != "Mixed spend":
        return {line.offset_account: net} if net else {}
    if rounded(line.money_out) <= 0 or rounded(line.money_in):
        frappe.throw("Mixed spend applies to payments only.")
    try:
        percentage = Decimal(str(line.get("business_percentage") or 0))
    except InvalidOperation:
        frappe.throw("Enter a valid business-use percentage.")
    if not percentage.is_finite() or not 0 < percentage < 100:
        frappe.throw("Mixed spend needs a business-use percentage greater than 0 and less than 100.")
    personal = line.get("personal_account")
    if not personal or not line.offset_account or personal == line.offset_account:
        frappe.throw("Choose different business and personal category accounts.")
    validate_leaf_accounts({line.offset_account, personal})
    if frappe.db.get_value("Books Account", personal, "root_type") not in {"Asset", "Liability", "Equity"}:
        frappe.throw("Use an owner/personal balance-sheet account for the personal portion.")
    if any(frappe.db.get_value("Books Account", account, "account_type") == "Bank" for account in [personal, line.offset_account]):
        frappe.throw("Allocation categories cannot be bank accounts.")
    business = rounded(net * percentage / 100)
    return {account: amount for account, amount in [(line.offset_account, business), (personal, net - business)] if amount}
