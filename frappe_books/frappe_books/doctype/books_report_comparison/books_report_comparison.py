from frappe.model.document import Document
import frappe
from frappe.utils import getdate
from frappe_books.accounting.money import as_decimal

class BooksReportComparison(Document):
    def validate(self):
        if getdate(self.to_date)<getdate(self.from_date):frappe.throw('The comparison end must follow its start.')
        seen=set()
        for row in self.balances:
            if row.account in seen:frappe.throw('Each comparison account must occur once.')
            seen.add(row.account)
            if frappe.db.get_value('Books Account',row.account,'is_group'):frappe.throw('Import comparison values into leaf accounts only.')
            as_decimal(row.balance)
        if self.status=='Approved':
            duplicates=frappe.get_all(self.doctype,filters={'status':'Approved','from_date':self.from_date,'to_date':self.to_date,'name':['!=',self.name or '']},pluck='name')
            if duplicates:frappe.throw('An approved comparison already exists for this period.')
