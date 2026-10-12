"""Bank statement batches retain source lines and post one voucher per upload."""
import csv
import hashlib
import io
import json

import frappe
from frappe.utils import getdate
from frappe_books.accounting.money import rounded
from frappe_books.accounting.ledger import validate_leaf_accounts, reverse_entries
from frappe_books.bank_allocations import allocations

BATCH = "Books Bank Statement"
LINE = "Books Bank Statement Line"


def check(action="read"):
    frappe.has_permission(BATCH, action, throw=True)


@frappe.whitelist()
def list_batches():
    check()
    return frappe.get_list(BATCH, fields=["name", "title", "bank_account", "from_date", "to_date", "opening_balance", "closing_balance", "status"], order_by="creation desc", limit_page_length=200)


@frappe.whitelist()
def get_batch(name: str):
    doc = frappe.get_doc(BATCH, name)
    doc.check_permission("read")
    return doc.as_dict()


@frappe.whitelist()
def accounts():
    check()
    return frappe.get_list("Books Account", filters={"is_group": 0}, fields=["name", "account_type", "root_type"], limit_page_length=0, order_by="name")


@frappe.whitelist()
def upload(title: str, bank_account: str, opening_balance: str | float, closing_balance: str | float, content: str, filename: str):
    check("create")
    if not filename.lower().endswith(".csv"):
        frappe.throw("Upload a CSV bank statement using the supplied template.")
    if len(content.encode()) > 10_000_000:
        frappe.throw("The statement exceeds the 10 MB limit.")
    digest = hashlib.sha256(content.encode()).hexdigest()
    if frappe.db.exists(BATCH, {"source_hash": digest, "bank_account": bank_account}):
        frappe.throw("This file has already been imported for this bank account.")
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    required = {"date", "description", "money_out", "money_in"}
    if not required.issubset(set(reader.fieldnames or [])):
        frappe.throw("CSV needs date, description, money_out and money_in columns. Download the template.")
    rows = []
    for index, row in enumerate(reader, 2):
        if not any(row.values()):
            continue
        try:
            date = getdate(row["date"])
            out = rounded(row["money_out"] or 0)
            incoming = rounded(row["money_in"] or 0)
        except (ValueError, TypeError):
            frappe.throw(f"Invalid date or amount on CSV row {index}.")
        rows.append(dict(transaction_date=date, description=row["description"], money_out=out, money_in=incoming, statement_balance=rounded(row["balance"]) if row.get("balance") else None, has_statement_balance=bool(row.get("balance")), reference=row.get("reference") or f"Row {index}", offset_account=row.get("account"), classification=row.get("classification") or "Review", business_percentage=row.get("business_percentage") or 0, personal_account=row.get("personal_account"), source_file=filename, source_row=index))
    if not rows or len(rows) > 10000:
        frappe.throw("A statement must contain 1 to 10,000 transactions.")
    doc = frappe.get_doc(dict(doctype=BATCH, title=title, bank_account=bank_account, opening_balance=opening_balance, closing_balance=closing_balance, source_hash=digest, source_filename=filename, lines=rows))
    doc.insert()
    from frappe.utils.file_manager import save_file
    file = save_file(filename, content.encode(), BATCH, doc.name, is_private=1)
    doc.source_attachment = file.file_url
    doc.save()
    return doc.name


@frappe.whitelist()
def save_categories(name: str, lines: list[dict]):
    doc = frappe.get_doc(BATCH, name)
    doc.check_permission("write")
    if doc.docstatus or doc.status != "Draft":
        frappe.throw("Posted statements cannot be edited.")
    changes = {r["name"]: r for r in frappe.parse_json(lines)}
    for row in doc.lines:
        if row.name in changes:
            row.offset_account = changes[row.name]["offset_account"]
            row.classification = changes[row.name]["classification"]
            row.business_percentage = changes[row.name].get("business_percentage") or 0
            row.personal_account = changes[row.name].get("personal_account")
    doc.save()
    return doc.name


@frappe.whitelist()
def post(name: str):
    doc = frappe.get_doc(BATCH, name)
    doc.check_permission("submit")
    if doc.status != "Draft":
        frappe.throw("Only draft statements can be posted.")
    doc.submit()
    return doc.name


def validate(doc):
    if doc.status == "Linked history" and not doc.is_new():
        frappe.throw("Imported historical statements are read-only.")
    if doc.docstatus == 1 and doc.status == "Linked history":
        frappe.throw("Historical bank statements link existing postings and cannot be posted again.")
    if not doc.lines:
        frappe.throw("Add statement transactions before saving.")
    balance = rounded(doc.opening_balance)
    for row in doc.lines:
        if row.classification != "Mixed spend":
            row.business_percentage = 0
            row.personal_account = None
        out, incoming = rounded(row.money_out), rounded(row.money_in)
        if out == 0 and incoming == 0 and row.classification == "Bank memo":
            row.running_balance = balance
            if row.has_statement_balance and rounded(row.statement_balance) != balance:
                frappe.throw(f"Statement balance does not reconcile on memo line {row.idx}.")
            continue
        if min(out, incoming) < 0 or (out == 0) == (incoming == 0):
            frappe.throw(f"Line {row.idx} must contain either money in or money out.")
        if row.offset_account == doc.bank_account:
            frappe.throw(f"Line {row.idx}: the category must differ from the bank account.")
        if row.classification == "Mixed spend":
            allocations(row)
        balance += incoming - out
        row.running_balance = balance
        if row.has_statement_balance and rounded(row.statement_balance) != balance:
            frappe.throw(f"Statement balance does not reconcile on line {row.idx}.")
    if balance != rounded(doc.closing_balance):
        frappe.throw(f"Opening plus movements is {balance}; supplied closing is {doc.closing_balance}.")
    doc.from_date = min(getdate(r.transaction_date) for r in doc.lines)
    doc.to_date = max(getdate(r.transaction_date) for r in doc.lines)
    doc.status = "Posted" if doc.docstatus == 1 else "Cancelled" if doc.docstatus == 2 else doc.status or "Draft"


def submit(doc):
    if doc.status == "Linked history":
        frappe.throw("This statement links existing postings and cannot be posted again.")
    validate_leaf_accounts({doc.bank_account, *(r.offset_account for r in doc.lines if r.offset_account)})
    if frappe.db.get_value("Books Account", doc.bank_account, "account_type") != "Bank":
        frappe.throw("Select a bank account for the statement.")
    opening = frappe.db.sql("SELECT COALESCE(SUM(debit-credit),0) FROM `tabBooks Ledger Entry` WHERE account=%s AND posting_date < %s AND reverted=0", (doc.bank_account, doc.from_date))[0][0]
    if rounded(opening) != rounded(doc.opening_balance):
        frappe.throw(f"Ledger opening balance is {opening}; statement opening is {doc.opening_balance}. Reconcile the opening balance before posting.")
    if frappe.db.exists("Books Ledger Entry", {"account": doc.bank_account, "posting_date": ["between", [doc.from_date, doc.to_date]], "reverted": 0}):
        frappe.throw("This bank period already has ledger postings. Check overlapping statements before posting.")
    for row in doc.lines:
        if rounded(row.money_out) == 0 and rounded(row.money_in) == 0:
            continue
        if not row.offset_account:
            frappe.throw(f"Select a category for line {row.idx} before posting.")
        amounts = {doc.bank_account: rounded(row.money_in) - rounded(row.money_out), **allocations(row)}
        for account, amount in amounts.items():
            debit, credit = max(amount, 0), max(-amount, 0)
            frappe.get_doc(dict(doctype="Books Ledger Entry", posting_date=row.transaction_date, account=account, debit=debit, credit=credit, voucher_type=BATCH, voucher_no=doc.name, bank_statement=doc.name, bank_transaction=row.name, bank_description=row.description)).insert(ignore_permissions=True)


def cancel(doc):
    for name in frappe.get_all("Books Bank Reallocation Line", filters={"bank_statement": doc.name}, pluck="parent"):
        if frappe.db.get_value("Books Bank Reallocation", name, "docstatus") == 1:
            frappe.throw("Undo this statement's reallocations before cancelling it.")
    reverse_entries(doc)
