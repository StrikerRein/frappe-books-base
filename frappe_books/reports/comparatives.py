"""Reported prior-year figures are comparison data, never ledger postings."""
import frappe
from frappe import _
from frappe.utils import add_days,add_years,getdate,cint
from frappe_books.accounting.money import as_decimal,sum_decimal
from frappe_books.reports import financial_statements as statements
from frappe_books.reports.periods import get_fiscal_year

DOCTYPE='Books Report Comparison'


def available():
    return frappe.db.table_exists(DOCTYPE) and bool(frappe.get_list(DOCTYPE,filters={'status':'Approved'},pluck='name',limit_page_length=1))


def default_filters(trial=False):
    if not available():return {}
    latest=frappe.get_list(statements.LEDGER,filters={'reverted':0},fields=['posting_date'],order_by='posting_date desc',limit_page_length=1)
    if not latest:return {'compare_previous_year':1}
    start,end=get_fiscal_year(latest[0].posting_date)
    if trial:return dict(from_date=start,to_date=end,compare_previous_year=1)
    return dict(based_on='Fiscal Year',periodicity='Yearly',from_year=start.year,to_year=end.year,to_date=end,count=1,compare_previous_year=1)


def _context(filters,periods):
    first=getdate(filters.from_date) if periods is None else min(p.from_date for p in periods)
    last=getdate(filters.to_date) if periods is None else max(p.to_date for p in periods)
    start,end=get_fiscal_year(last)
    if first<start or last>end:
        return None,'Select a single financial year to show the prior-year comparison.'
    previous_start,previous_end=add_years(start,-1),add_years(end,-1)
    if not frappe.db.table_exists(DOCTYPE):return None,'No approved prior-year comparison has been loaded for this company.'
    names=frappe.get_list(DOCTYPE,filters={'status':'Approved','from_date':previous_start,'to_date':previous_end},pluck='name',limit_page_length=2)
    if not names:return None,f'No approved FY{previous_end.year} comparison has been loaded for this company.'
    if len(names)>1:frappe.throw('More than one approved comparison exists for this period. Review comparison records first.')
    doc=frappe.get_doc(DOCTYPE,names[0]);doc.check_permission('read')
    return doc,('Current columns cover the selected period; the AFS comparison is the full prior financial year. ' if first!=start or last!=end else '')


def _column(key,label,doc):
    return dict(fieldname=key,label=label,fieldtype='Currency',width=180,comparison_source=doc.name,from_date=doc.from_date,to_date=doc.to_date)


def append(report,filters,columns,rows,periods=None):
    if not cint(filters.get('compare_previous_year')):return columns,rows
    doc,note=_context(filters,periods)
    if not doc:return columns,rows,note
    accounts=statements._accounts();current_keys=[c['fieldname'] for c in columns if c['fieldname']!='account']
    current={r['account']:r for r in rows if r.get('account') in accounts and not accounts[r['account']].is_group}
    reference={r.account:as_decimal(r.balance) for r in doc.balances}
    roots=statements.TRIAL_BALANCE if report=='trial-balance' else statements.BALANCE_SHEET if report=='balance-sheet' else ('Income','Expense')
    comparison_keys=['comparison_debit','comparison_credit'] if report=='trial-balance' else ['comparison']
    keys=[*current_keys,*comparison_keys];width=len(keys);values={}
    for account in current.keys()|reference.keys():
        if account not in accounts:frappe.throw('A comparison account is missing from the chart of accounts.')
        root=accounts[account].root_type
        if root not in roots:continue
        balance=reference.get(account,as_decimal(0))
        comparative=[max(balance,as_decimal(0)),max(-balance,as_decimal(0))] if report=='trial-balance' else [statements._balance(root,balance,as_decimal(0))]
        values[account]=[*(as_decimal(current.get(account,{}).get(k) or 0) for k in current_keys),*comparative]
    sections=statements._sections(roots,values,width,accounts)
    year=getdate(doc.to_date).year
    label=f'FY{year} AFS reference'
    extra=[_column(k,label+suffix,doc) for k,suffix in zip(comparison_keys,[' (Dr)',' (Cr)'] if report=='trial-balance' else [''],strict=True)]
    if report=='trial-balance':
        result=statements._rows(sections,keys,filters.hide_group_amounts)
        totals=[sum_decimal(v) for v in zip(*(s['total'] for s in sections),strict=True)] if sections else [as_decimal(0)]*width
        result += [{},{'account':_('Total'),'indent':0,**dict(zip(keys,totals,strict=True))}]
        difference=totals[-2]-totals[-1]
        if difference:
            note+=f'FY{year} AFS reference totals differ by {abs(difference):,.2f} (debit less credit: {difference:,.2f}). These source figures include P&L alongside closing equity and are not an unclosed prior-year trial balance. No balancing journal has been posted. '
    elif report=='profit-and-loss':
        labels={'Income':_('Total Income (Credit)'),'Expense':_('Total Expense (Debit)')}
        result=statements._rows(sections,keys,filters.hide_group_amounts,labels)
        result += [{},{'account':_('Total Profit'),'indent':0,'bold':1,**dict(zip(keys,statements._profit(sections,width),strict=True))}]
    else:
        labels={'Asset':_('Total Asset (Debit)'),'Liability':_('Total Liability (Credit)'),'Equity':_('Total Equity (Credit)')}
        result=statements._rows(sections,keys,filters.hide_group_amounts,labels)
        old_profit=next((r for r in rows if r.get('account')==_('Provisional Profit / Loss (Credit)')),None)
        if old_profit:
            # Reported closing equity already includes the previous year's profit.
            profit=[*(as_decimal(old_profit.get(k) or 0) for k in current_keys),as_decimal(0)]
            credit=[s['total'] for s in sections if s['root_type']!='Asset']
            totals=[sum_decimal(v) for v in zip(profit,*credit,strict=True)]
            result += [{},{'account':_('Provisional Profit / Loss (Credit)'),'indent':0,**dict(zip(keys,profit,strict=True))},{'account':_('Total (Credit)'),'indent':0,**dict(zip(keys,totals,strict=True))}]
        note+='The comparative balance sheet uses reported closing equity; prior-year profit is not added again. '
    note+=f'Comparison: {doc.title} ({doc.from_date} to {doc.to_date}). Click a comparative account amount to see its workbook source; current amounts still open General Ledger.'
    return [*columns,*extra],result,note


def _source(name):
    frappe.has_permission('Books Ledger Entry','read',throw=True)
    doc=frappe.get_doc(DOCTYPE,name);doc.check_permission('read');return doc


@frappe.whitelist()
def get_source(name: str,account: str=''):
    doc=_source(name);accounts=statements._accounts()
    if account and account not in accounts:frappe.throw('Choose an account in this company.')
    def includes(name):
        if not account:return True
        while name:
            if name==account:return True
            name=accounts[name].parent_books_account
        return False
    lines=[dict(account=r.account,balance=r.balance,source_cell=r.source_cell) for r in doc.balances if includes(r.account)]
    return dict(name=doc.name,title=doc.title,from_date=doc.from_date,to_date=doc.to_date,source_sheet=doc.source_sheet,source_file=frappe.db.get_value('File',doc.source_file,'file_name'),notes=doc.notes,rows=lines)


@frappe.whitelist()
def download_source(name: str):
    doc=_source(name);file=frappe.get_doc('File',doc.source_file)
    if not file.is_private:frappe.throw('The comparison source must be a private file.')
    frappe.local.response.filename=file.file_name;frappe.local.response.filecontent=file.get_content()
    frappe.local.response.type='download';frappe.local.response.display_content_as='attachment'
