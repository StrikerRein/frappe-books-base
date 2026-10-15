"""Client review inbox. Answers are proposals; this module never posts ledger entries."""
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, quote
import frappe
from frappe.utils import getdate, now_datetime

TASK='Books Client Review'
ACCESS='Books Review Access'
CLIENT_ROLE='Books Review Client'
USES={'Business','Private','Rental','Transfer','Mixed','Unsure','Other'}

def manager():
    return frappe.session.user=='Administrator' or 'System Manager' in frappe.get_roles()

def require_manager():
    if not manager():frappe.throw('Only the accountant can manage reviews.',frappe.PermissionError)

def require_login():
    if frappe.session.user=='Guest':frappe.throw('Sign in to review your assigned items.',frappe.PermissionError)
    if not manager() and CLIENT_ROLE not in frappe.get_roles():frappe.throw('Client review access is not enabled.',frappe.PermissionError)

def sources():
    value=frappe.conf.get('books_review_sources') or {}
    if isinstance(value,str):value=json.loads(value)
    return {site:label for site,label in value.items() if re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,100}',site)}

def allowed(client,site):
    return site in sources() and bool(frappe.db.exists(ACCESS,{'client':client,'source_site':site,'enabled':1})) and bool(frappe.db.get_value('User',client,'enabled'))

def check_task(doc):
    require_login()
    if not manager() and (doc.client!=frappe.session.user or not allowed(doc.client,doc.source_site)):
        frappe.throw('This review is not assigned to you.',frappe.PermissionError)

def source_rows(site,**filters):
    require_manager()
    if site not in sources():frappe.throw('Choose an enabled account.')
    request=dict(site=site,sites_path=str(Path(frappe.get_site_path()).resolve().parent),**filters)
    try:
        result=subprocess.run([sys.executable,'-m','frappe_books.review_source'],input=json.dumps(request),text=True,capture_output=True,timeout=25,check=True,cwd=str(Path(frappe.get_site_path()).resolve().parent.parent))
        return json.loads(result.stdout)
    except (subprocess.SubprocessError,ValueError):
        frappe.log_error(title='Client review source could not be read')
        frappe.throw('This account could not be loaded. Please try again or check the account service.')

def log(doc,action,**values):
    history=json.loads(doc.review_log or '[]')
    history.append(dict(action=action,by=frappe.session.user,at=str(now_datetime()),**values))
    doc.review_log=json.dumps(history,default=str)

def serialize(doc):
    snap=json.loads(doc.snapshot or '{}')
    result=dict(name=doc.name,client=doc.client,company=doc.company,source_site=doc.source_site,kind=doc.kind,status=doc.status,question=doc.question,due_date=doc.due_date,transaction=snap,answer=doc.answer,classification=doc.classification,percentage=doc.percentage,suggested_category=doc.suggested_category,answered_at=doc.answered_at,review_note=doc.review_note,modified=doc.modified)
    if doc.get('workflow'):
        workflow=frappe.get_doc('Books Workflow',doc.workflow)
        result.update(workflow=workflow.name,workflow_title=workflow.title,workflow_stage=workflow.stage,workflow_topic=workflow.topic)
    if manager():
        result['history']=json.loads(doc.review_log or '[]')
        base=(frappe.conf.get('books_review_source_urls') or {}).get(doc.source_site,'')
        parsed=urlsplit(base)
        if parsed.scheme in {'http','https'} and parsed.hostname and not parsed.username and not parsed.password and snap.get('name'):
            if snap.get('source_kind') == 'ledger':
                filters=dict(account=snap.get('offset_account'),fromDate=snap.get('transaction_date'),toDate=snap.get('transaction_date'),referenceType='All',referenceName=snap.get('reference'),groupBy='none')
                result['source_url']=base.rstrip('/')+'/books/report/GeneralLedger?defaultFilters='+quote(json.dumps(filters),safe='')
            else:
                result['source_url']=base.rstrip('/')+'/books/bank-statements/'+quote(snap['parent'],safe='')+'?transaction='+quote(snap['name'],safe='')
    from frappe_books import review_documents as documents
    result.update(tax_year=doc.get('tax_year') or 2026,item_title=doc.get('item_title') or doc.question,propose_rule=bool(doc.get('propose_rule')),attachments=documents.attachments(doc))
    if manager():result['matching_rules']=documents.matching_rules(doc)
    return result

@frappe.whitelist()
def profile():
    require_login()
    result=dict(accountant=manager(),user=frappe.session.user,full_name=frappe.db.get_value('User',frappe.session.user,'full_name'))
    if manager():
        grants=frappe.get_all(ACCESS,filters={'enabled':1},fields=['client','source_site'],limit_page_length=0)
        clients={}
        for grant in grants:
            if allowed(grant.client,grant.source_site):
                clients.setdefault(grant.client,dict(email=grant.client,label=frappe.db.get_value('User',grant.client,'full_name'),sources=[]))['sources'].append(grant.source_site)
        result.update(clients=list(clients.values()),sources=sources())
    return result

@frappe.whitelist()
def list_reviews(status: str='',client: str='',tax_year: int=0,source_site: str='',kind: str=''):
    require_login()
    filters={}
    if tax_year:
        from frappe_books.review_documents import tax_year as valid_year
        filters['tax_year']=valid_year(tax_year)
    if kind:
        if kind not in {'Transaction','Document','Question','Decision'}:frappe.throw('Invalid review type.')
        filters['kind']=kind
    if source_site:filters['source_site']=source_site
    if status:
        if status not in {'Open','Answered','Follow-up','Reviewed'}:frappe.throw('Invalid review status.')
        filters['status']=status
    if manager():
        if client:filters['client']=client
    else:
        permitted=frappe.get_all(ACCESS,filters={'client':frappe.session.user,'enabled':1},pluck='source_site')
        scoped=[s for s in permitted if allowed(frappe.session.user,s) and (not source_site or s==source_site)]
        filters.update(client=frappe.session.user,source_site=['in',scoped or ['__none__']])
    names=frappe.get_all(TASK,filters=filters,pluck='name',order_by='creation desc',limit_page_length=0)
    return [serialize(frappe.get_doc(TASK,n)) for n in names]

@frappe.whitelist()
def find_transactions(source_site: str,search: str='',from_date: str='',to_date: str=''):
    require_manager()
    if len(search)>200:frappe.throw('Search is too long.')
    return source_rows(source_site,search=search,from_date=from_date,to_date=to_date)

@frappe.whitelist(methods=['POST'])
def assign(client: str,source_site: str,question: str,line_ids: list[str]|None=None,due_date: str='',workflow_name: str='',workflow_template: str='Transaction clarification',tax_year: int=2026):
    require_manager()
    if not allowed(client,source_site):frappe.throw('This client does not have access to that account.',frappe.PermissionError)
    from frappe_books.review_documents import tax_year as valid_year
    tax_year=valid_year(tax_year)
    question=(question or '').strip()
    if not question or len(question)>4000:frappe.throw('Enter a question of up to 4,000 characters.')
    if due_date:getdate(due_date)
    ids=frappe.parse_json(line_ids or [])
    if not isinstance(ids,list) or len(ids)>50 or len(set(ids))!=len(ids) or any(not isinstance(i,str) or len(i)>140 for i in ids):frappe.throw('Select up to 50 different transactions.')
    rows=source_rows(source_site,line_ids=ids)['rows'] if ids else [None]
    if ids and {r['name'] for r in rows}!=set(ids):frappe.throw('A selected transaction could not be found. Refresh the selection.')
    created=[]
    frappe.db.savepoint('review_assign')
    try:
        for row in rows:
            if row and frappe.db.exists(TASK,{'client':client,'source_site':source_site,'source_line':row['name'],'status':['in',['Open','Answered','Follow-up']]}):
                frappe.throw('A selected transaction already has an active review for this client.')
            doc=frappe.get_doc(dict(doctype=TASK,client=client,source_site=source_site,company=sources()[source_site],kind='Transaction' if row else 'Question',tax_year=tax_year,status='Open',question=question,due_date=due_date or None,source_line=row['name'] if row else None,snapshot=json.dumps(row,default=str) if row else '{}'))
            log(doc,'Assigned',question=question)
            doc.insert();created.append(doc.name)
        from frappe_books import workflows
        case=frappe.get_doc(workflows.WORKFLOW,workflow_name) if workflow_name else workflows.create_case(workflow_template,client,source_site,question[:140],due_date)
        workflows.attach(case,created)
    except BaseException:
        frappe.db.rollback(save_point='review_assign');raise
    return created

@frappe.whitelist(methods=['POST'])
def answer(name: str,explanation: str,classification: str='Unsure',percentage: float=0,suggested_category: str='',expected_modified: str='',propose_rule: bool=False):
    require_login()
    doc=frappe.get_doc(TASK,name,for_update=True);check_task(doc)
    if doc.client!=frappe.session.user:frappe.throw('Only the assigned client can answer this review.',frappe.PermissionError)
    if doc.status=='Reviewed':frappe.throw('This review is complete. Ask your accountant to reopen it.')
    if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('This review changed. Refresh before answering.')
    if doc.kind=='Document':
        from frappe_books.review_documents import attachments
        if not attachments(doc):frappe.throw('Please upload the requested document before submitting it.')
    if doc.kind!='Transaction':classification='Unsure';percentage=0;suggested_category=''
    explanation=(explanation or '').strip()
    if not explanation or len(explanation)>4000:frappe.throw('Enter an explanation of up to 4,000 characters.')
    if classification not in USES:frappe.throw('Choose how this transaction was used.')
    percentage=float(percentage or 0)
    if classification=='Mixed' and (not math.isfinite(percentage) or not 0<percentage<100):frappe.throw('Enter a mixed-use percentage greater than 0 and less than 100.')
    if len(suggested_category)>200:frappe.throw('Suggested category is too long.')
    doc.propose_rule=bool(propose_rule) and classification=='Mixed'
    doc.update(dict(answer=explanation,classification=classification,percentage=percentage if classification=='Mixed' else 100 if classification in {'Business','Rental'} else 0,suggested_category=suggested_category,status='Answered',answered_at=now_datetime()))
    log(doc,'Answered',answer=doc.answer,classification=doc.classification,percentage=doc.percentage,suggested_category=doc.suggested_category)
    doc.save(ignore_permissions=True)
    from frappe_books.workflows import task_updated
    task_updated(doc)
    return serialize(doc)

@frappe.whitelist(methods=['POST'])
def review(name: str,action: str,note: str,expected_modified: str=''):
    require_manager()
    doc=frappe.get_doc(TASK,name,for_update=True)
    if action not in {'Reviewed','Follow-up'}:frappe.throw('Choose complete review or follow-up.')
    if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('A new answer arrived. Refresh before reviewing.')
    if action=='Reviewed' and doc.status!='Answered':frappe.throw('Wait for a client answer before completing this review.')
    if not (note or '').strip() or len(note)>4000:frappe.throw('Enter a review note of up to 4,000 characters.')
    doc.update(dict(status=action,review_note=note.strip(),reviewed_by=frappe.session.user,reviewed_at=now_datetime()))
    log(doc,action,note=doc.review_note)
    if action=='Follow-up':
        from frappe_books.review_documents import pause_rules
        pause_rules(doc)
    doc.save()
    from frappe_books.workflows import task_updated
    task_updated(doc)
    return serialize(doc)


@frappe.whitelist()
def overview(tax_year: int=2026):
    from frappe_books.review_documents import overview as run
    return run(tax_year)

@frappe.whitelist(methods=['POST'])
def create_request(client: str,source_site: str,kind: str,title: str,question: str='',tax_year: int=2026,due_date: str=''):
    from frappe_books.review_documents import create_request as run
    return run(client,source_site,kind,title,question,tax_year,due_date)

@frappe.whitelist(methods=['POST'])
def upload_document(name: str,comment: str='',expected_modified: str=''):
    from frappe_books.review_documents import upload
    return upload(name,comment,expected_modified)

@frappe.whitelist()
def download_document(name: str,file_id: str):
    from frappe_books.review_documents import download
    return download(name,file_id)

@frappe.whitelist(methods=['POST'])
def approve_rule(name: str,match_text: str,note: str,expected_modified: str=''):
    from frappe_books.review_documents import approve_rule as run
    return run(name,match_text,note,expected_modified)


@frappe.whitelist()
def preview_client(client: str,tax_year: int=2026):
    require_manager()
    from frappe_books import review_documents as documents
    overview=documents.overview(tax_year,client=client)
    permitted={e['site'] for e in overview['entities']}
    if not permitted:frappe.throw('This client has no enabled review access.')
    rows=[r for r in list_reviews(client=client,tax_year=tax_year) if r['source_site'] in permitted]
    return dict(profile=dict(accountant=False,preview=True,user=client,full_name=frappe.db.get_value('User',client,'full_name')),overview=overview,items=rows)
