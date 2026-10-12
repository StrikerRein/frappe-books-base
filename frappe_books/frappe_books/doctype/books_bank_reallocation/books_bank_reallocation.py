from frappe.model.document import Document
from frappe_books import bank_reallocation

class BooksBankReallocation(Document):
    def validate(self):
        bank_reallocation.validate(self)

    def on_submit(self):
        bank_reallocation.apply(self)

    def on_cancel(self):
        bank_reallocation.cancel(self)
