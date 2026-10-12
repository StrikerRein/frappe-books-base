"""Audited category corrections keep the original statement and bank ledger intact."""
from collections import defaultdict

import frappe
from frappe.utils import getdate
from frappe_books.bank_import import BATCH, LINE, check
from frappe_books.accounting.ledger import validate_leaf_accounts, reverse_entries
from frappe_books.accounting.money import rounded

DOCTYPE = "Books Bank Reallocation"


@frappe.whitelist()
def transactions(from_date: str = "", to_date: str = "", account: str = "", search: str = ""):
    check()
    parents = frappe.get_list(BATCH, filters={"status": ["in", ["Posted", "Linked history"]]}, pluck="name", limit_page_length=0)
    if not parents:
        return {"rows": [], "has_more": False}
    filters = {"parent": ["in", parents]}
    if from_date:
        filters["transaction_date"] = [">=", getdate(from_date)]
    if to_date:
        filters["transaction_date"] = ["between", [getdate(from_date) if from_date else "1900-01-01", getdate(to_date)]]
    if account:
        filters["offset_account"] = ["descendants of (inclusive)", account]
    if search:
        filters["description"] = ["like", "%" + search + "%"]
    rows = frappe.get_all(LINE, filters=filters, fields=["name", "parent", "transaction_date", "reference", "description", "money_in", "money_out", "offset_account", "classification", "last_reallocation"], order_by="transaction_date desc, parent desc, idx desc", limit_page_length=5001)
    has_more = len(rows) > 5000
    rows = [r for r in rows if rounded(r.money_in) or rounded(r.money_out)]
    return {"rows": rows[:5000], "has_more": has_more}


@frappe.whitelist()
def reallocate(transaction_ids: list[str], target_account: str, classification: str, reason: str, expected: list[dict] | None = None):
    frappe.has_permission(DOCTYPE, "create", throw=True)
    frappe.has_permission(DOCTYPE, "submit", throw=True)
    if not transaction_ids or len(transaction_ids) > 1000 or len(set(transaction_ids)) != len(transaction_ids):
        frappe.throw("Select 1 to 1,000 different bank transactions.")
    changes = []
    expected_map = {r["name"]: r for r in expected} if expected is not None else None
    for name in sorted(transaction_ids):
        line = frappe.get_doc(LINE, name)
        doc = frappe.get_doc(BATCH, line.parent)
        doc.check_permission("write")
        if expected_map is not None:
            before = expected_map.get(name)
            if not before or before.get("offset_account") != line.offset_account or (before.get("last_reallocation") or "") != (line.get("last_reallocation") or ""):
                frappe.throw("A selected transaction changed. Refresh and review the selection again.")
        changes.append(dict(bank_statement=line.parent, bank_transaction=line.name, old_account=line.offset_account, old_classification=line.classification, previous_reallocation=line.get("last_reallocation")))
    doc = frappe.get_doc(dict(doctype=DOCTYPE, target_account=target_account, target_classification=classification, reason=reason, changes=changes))
    frappe.db.savepoint("bank_reallocation")
    try:
        doc.insert()
        doc.submit()
    except BaseException:
        frappe.db.rollback(save_point="bank_reallocation")
        raise
    return {"name": doc.name, "count": len(doc.changes)}


@frappe.whitelist()
def history(bank_statement: str):
    doc = frappe.get_doc(BATCH, bank_statement)
    doc.check_permission("read")
    names = frappe.get_all("Books Bank Reallocation Line", filters={"bank_statement": bank_statement}, pluck="parent")
    return frappe.get_list(DOCTYPE, filters={"name": ["in", names]}, fields=["name", "creation", "owner", "target_account", "target_classification", "reason", "docstatus"], order_by="creation desc", limit_page_length=100) if names else []


@frappe.whitelist()
def undo(name: str):
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("cancel")
    frappe.db.savepoint("bank_reallocation_undo")
    try:
        doc.cancel()
    except BaseException:
        frappe.db.rollback(save_point="bank_reallocation_undo")
        raise
    return doc.name


def validate(doc):
    validate_leaf_accounts({doc.target_account})
    if not (doc.reason or "").strip():
        frappe.throw("Enter a reason for the category change.")
    if doc.target_classification not in {"Business", "Personal", "Transfer", "Review"}:
        frappe.throw("Choose a valid classification.")
    if not doc.changes or len(doc.changes) > 1000:
        frappe.throw("Select 1 to 1,000 transactions.")
    if len({r.bank_transaction for r in doc.changes}) != len(doc.changes):
        frappe.throw("A transaction can only occur once in a reallocation.")


def apply(doc):
    for change in doc.changes:
        line = frappe.get_doc(LINE, change.bank_transaction, for_update=True)
        batch = frappe.get_doc(BATCH, change.bank_statement)
        batch.check_permission("write")
        if line.parent != batch.name or batch.status not in {"Posted", "Linked history"}:
            frappe.throw("Only posted bank transactions can be reallocated.")
        if doc.target_account == batch.bank_account:
            frappe.throw("The new category cannot be the statement's bank account.")
        if frappe.db.get_value("Books Account", doc.target_account, "account_type") == "Bank":
            frappe.throw("Use a category account rather than another bank account.")
        if line.offset_account != change.old_account or line.classification != change.old_classification or (line.get("last_reallocation") or "") != (change.previous_reallocation or ""):
            frappe.throw("A selected transaction changed. Refresh and select it again.")
        if line.offset_account == doc.target_account and line.classification == doc.target_classification:
            frappe.throw("A selected transaction already has this category and classification.")
        net = rounded(line.money_out) - rounded(line.money_in)
        if not net:
            frappe.throw("Bank memo lines have no accounting allocation to change.")
        actual = defaultdict(lambda: rounded(0))
        for entry in frappe.get_all("Books Ledger Entry", filters={"bank_transaction": line.name, "bank_statement": batch.name, "reverted": 0}, fields=["account", "debit", "credit"]):
            if entry.account != batch.bank_account:
                actual[entry.account] += rounded(entry.debit) - rounded(entry.credit)
        actual = {a: amount for a, amount in actual.items() if amount}
        if actual != {line.offset_account: net}:
            frappe.throw(f"Transaction {line.reference} has a split or inconsistent allocation; review it separately.")
        if line.offset_account != doc.target_account:
            for account, amount in ((line.offset_account, -net), (doc.target_account, net)):
                frappe.get_doc(dict(doctype="Books Ledger Entry", posting_date=line.transaction_date, account=account, debit=max(amount, 0), credit=max(-amount, 0), voucher_type=DOCTYPE, voucher_no=doc.name, bank_statement=batch.name, bank_transaction=line.name, bank_description=line.description)).insert(ignore_permissions=True)
        frappe.db.set_value(LINE, line.name, {"offset_account": doc.target_account, "classification": doc.target_classification, "last_reallocation": doc.name}, update_modified=False)
        frappe.db.set_value(BATCH, batch.name, "modified", frappe.utils.now())


def cancel(doc):
    for change in doc.changes:
        batch = frappe.get_doc(BATCH, change.bank_statement)
        batch.check_permission("write")
        if frappe.db.get_value(LINE, change.bank_transaction, "last_reallocation") != doc.name:
            frappe.throw("A later reallocation exists. Undo the latest change first.")
    reverse_entries(doc)
    for change in doc.changes:
        frappe.db.set_value(LINE, change.bank_transaction, {"offset_account": change.old_account, "classification": change.old_classification, "last_reallocation": change.previous_reallocation}, update_modified=False)
