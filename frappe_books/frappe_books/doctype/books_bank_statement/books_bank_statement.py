from frappe.model.document import Document
from frappe_books import bank_import

class BooksBankStatement(Document):
    def validate(self):
        bank_import.validate(self)

    def on_submit(self):
        bank_import.submit(self)

    def on_cancel(self):
        bank_import.cancel(self)
