import math
import frappe
from frappe.model.document import Document

class BooksClientAllocationRule(Document):
    def validate(self):
        percentage=float(self.percentage or 0)
        if not math.isfinite(percentage) or not 0<percentage<100:
            frappe.throw('A mixed-use rule needs a percentage between 0 and 100.')
        task=frappe.get_doc('Books Client Review',self.review_task)
        if task.client!=self.client or task.source_site!=self.source_site or task.tax_year!=self.tax_year:
            frappe.throw('The split rule must belong to the same client, entity and tax year as its reviewed task.')
        if self.enabled and (task.status!='Reviewed' or task.classification!='Mixed' or not task.propose_rule or not math.isclose(percentage,float(task.percentage),abs_tol=.0001)):
            frappe.throw('Approve only the client split recorded in a completed review.')
