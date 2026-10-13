"""Fixed read-only source operation in an isolated Frappe context.
Run by review_portal; never exposed as a client API or executed through a shell.
"""
import contextlib
import json
import os
import re
import sys
from pathlib import Path

def main():
    import frappe
    from frappe.utils import getdate
    request=json.load(sys.stdin)
    site=request['site']
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,100}',site):raise ValueError('Invalid configured site')
    sites=Path(request['sites_path']).resolve()
    target=(sites/site).resolve()
    if target.parent != sites or not target.is_dir():raise ValueError('Invalid configured site')
    os.chdir(sites)
    with contextlib.redirect_stdout(sys.stderr):
        frappe.init(site=site,sites_path=str(sites));frappe.connect();frappe.set_user('Administrator')
        try:
            parents=frappe.get_all('Books Bank Statement',filters={'status':['in',['Posted','Linked history']]},pluck='name',limit_page_length=0)
            filters={'parent':['in',parents or ['__none__']]}
            if request.get('line_ids'):filters['name']=['in',request['line_ids']]
            if request.get('search'):filters['description']=['like','%'+request['search']+'%']
            if request.get('from_date'):filters['transaction_date']=['>=',getdate(request['from_date'])]
            if request.get('to_date'):filters['transaction_date']=['between',[getdate(request.get('from_date') or '1900-01-01'),getdate(request['to_date'])]]
            rows=frappe.get_all('Books Bank Statement Line',filters=filters,fields=['name','parent','transaction_date','reference','description','money_in','money_out','offset_account','classification','business_percentage','personal_account'],order_by='transaction_date desc, idx desc',limit_page_length=201)
            company=frappe.db.get_single_value('Books Accounting Settings','company_name')
            result=dict(company=company,rows=[dict(r) for r in rows[:200]],has_more=len(rows)>200)
        finally:frappe.destroy()
    print(json.dumps(result,default=str))

if __name__=='__main__':main()
