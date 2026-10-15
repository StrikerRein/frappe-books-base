"""Assigned private documents and year/entity progress; no accounting postings."""
import io
import json
import re
import zipfile
from pathlib import PurePosixPath
import frappe
from frappe.utils import getdate
from frappe_books import review_portal as portal

MAX_SIZE=10*1024*1024
RULE='Books Client Allocation Rule'


def tax_year(value=2026):
    try:year=int(value)
    except (TypeError,ValueError):frappe.throw('Choose a valid tax year.')
    if not 2000<=year<=2100:frappe.throw('Choose a tax year between 2000 and 2100.')
    return year


def infer_year(date):
    date=getdate(date)
    return date.year+(1 if date.month>=3 else 0)


def grants(client=None):
    if portal.manager() and not client:return portal.sources()
    if client and not portal.manager():frappe.throw('Only the accountant can preview a client.',frappe.PermissionError)
    return {s:l for s,l in portal.sources().items() if portal.allowed(client or frappe.session.user,s)}


def overview(year=2026,client=None):
    portal.require_login();year=tax_year(year)
    visible=grants(client)
    filters={'tax_year':year,'source_site':['in',list(visible) or ['__none__']]}
    if client or not portal.manager():filters['client']=client or frappe.session.user
    rows=frappe.get_all(portal.TASK,filters=filters,fields=['source_site','kind','status'],limit_page_length=0)
    entities={s:dict(site=s,label=l,total=0,resolved=0,waiting=0,reviewing=0,transactions=0,documents=0,questions=0) for s,l in visible.items()}
    for row in rows:
        entity=entities[row.source_site];entity['total']+=1
        if row.status=='Reviewed':entity['resolved']+=1
        elif row.status=='Answered':entity['reviewing']+=1
        else:
            entity['waiting']+=1
            entity['transactions' if row.kind=='Transaction' else 'documents' if row.kind=='Document' else 'questions']+=1
    return dict(tax_year=year,entities=list(entities.values()),total=len(rows),resolved=sum(r.status=='Reviewed' for r in rows),reviewing=sum(r.status=='Answered' for r in rows))


def create_request(client,source_site,kind,title,question,year=2026,due_date=''):
    portal.require_manager()
    if kind not in {'Document','Question','Decision'}:frappe.throw('Choose a document, question or decision request.')
    title=(title or '').strip()
    if not title or len(title)>140:frappe.throw('Enter a short request title of up to 140 characters.')
    ids=portal.assign(client,source_site,question or title,due_date=due_date,workflow_template='Tax review',tax_year=tax_year(year))
    doc=frappe.get_doc(portal.TASK,ids[0]);doc.update(dict(kind=kind,item_title=title));doc.save()
    portal.log(doc,'Request type set',kind=kind,title=title);doc.save()
    return ids


def attachments(doc):
    # Only private files explicitly attached to this assigned item are exposed.
    return [dict(name=r.name,file_name=r.file_name,size=r.file_size) for r in frappe.get_all('File',filters={'attached_to_doctype':portal.TASK,'attached_to_name':doc.name,'is_private':1,'is_folder':0},fields=['name','file_name','file_size'],order_by='creation asc',limit_page_length=0)]


def validate_file(filename,content):
    if not filename or len(filename)>180 or '\\' in filename or PurePosixPath(filename).name!=filename or any(ord(c)<32 for c in filename):frappe.throw('Use a simple document filename.')
    if not 0<len(content)<=MAX_SIZE:frappe.throw('Choose a non-empty file no larger than 10 MB.')
    ext=PurePosixPath(filename).suffix.lower()
    valid=(ext=='.pdf' and content.startswith(b'%PDF-')) or (ext=='.png' and content.startswith(b'\x89PNG\r\n\x1a\n')) or (ext in {'.jpg','.jpeg'} and content.startswith(b'\xff\xd8\xff'))
    if ext=='.pdf' and valid:
        try:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(content))
        except Exception:frappe.throw('This PDF could not be read. Please upload a valid PDF document.')
        if reader.is_encrypted:frappe.throw('Please upload an unlocked PDF so your accountant can review it.')
        from frappe.utils.pdf import pdf_contains_js
        if pdf_contains_js(content):frappe.throw('Upload a PDF without embedded scripts.')
    if ext in {'.docx','.xlsx'}:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names=archive.namelist()
                required='word/document.xml' if ext=='.docx' else 'xl/workbook.xml'
                valid=required in names and '[Content_Types].xml' in names and not any('vbaproject' in n.lower() for n in names) and sum(i.file_size for i in archive.infolist())<=100*1024*1024
        except (zipfile.BadZipFile,ValueError):valid=False
    if not valid:frappe.throw('Upload a PDF, JPG, PNG, DOCX or XLSX document with a matching file format.')


def upload(name,comment='',expected_modified=''):
    portal.require_login()
    doc=frappe.get_doc(portal.TASK,name,for_update=True);portal.check_task(doc)
    if portal.manager() or doc.client!=frappe.session.user:frappe.throw('Only the assigned client can upload to this request.',frappe.PermissionError)
    if doc.kind!='Document' or doc.status=='Reviewed':frappe.throw('Choose an open document request.')
    if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('This request changed. Refresh before uploading.')
    if len(attachments(doc))>=10:frappe.throw('This request already contains 10 documents. Ask your accountant for another request.')
    if len(comment)>4000:frappe.throw('Keep your comment within 4,000 characters.')
    file=frappe.request.files.get('file')
    if not file:frappe.throw('Choose a document to upload.')
    content=file.stream.read(MAX_SIZE+1);validate_file(file.filename,content)
    from frappe.utils.file_manager import save_file
    saved=save_file(file.filename,content,portal.TASK,doc.name,is_private=1)
    portal.log(doc,'Document uploaded',file=saved.name,file_name=saved.file_name)
    doc.save(ignore_permissions=True)
    return portal.answer(doc.name,comment or 'Document uploaded for your review.',expected_modified=str(doc.modified))


def download(name,file_id):
    portal.require_login()
    doc=frappe.get_doc(portal.TASK,name);portal.check_task(doc)
    if file_id not in {f['name'] for f in attachments(doc)}:frappe.throw('This file does not belong to your assigned request.',frappe.PermissionError)
    file=frappe.get_doc('File',file_id)
    frappe.local.response.filename=file.file_name
    frappe.local.response.filecontent=file.get_content()
    frappe.local.response.type='download'
    frappe.local.response.display_content_as='attachment'
    frappe.local.response.headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}


def approve_rule(name,match_text,note,expected_modified=''):
    portal.require_manager();doc=frappe.get_doc(portal.TASK,name,for_update=True)
    if doc.status!='Reviewed' or doc.classification!='Mixed' or not doc.propose_rule:frappe.throw('First complete review of the client’s proposed mixed-use split.')
    if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('This answer changed. Refresh first.')
    match_text=(match_text or '').strip();note=(note or '').strip()
    if not 3<=len(match_text)<=200 or not note or len(note)>4000:frappe.throw('Enter a description match of 3–200 characters and an approval note.')
    existing=frappe.db.exists(RULE,{'client':doc.client,'source_site':doc.source_site,'tax_year':doc.tax_year,'match_text':match_text,'enabled':1})
    if existing:frappe.throw('An approved rule already exists for this description and tax year.')
    rule=frappe.get_doc(dict(doctype=RULE,client=doc.client,source_site=doc.source_site,tax_year=doc.tax_year,match_text=match_text,percentage=doc.percentage,review_task=doc.name,approval_note=note));rule.insert()
    portal.log(doc,'Allocation rule approved',rule=rule.name,match_text=match_text,percentage=doc.percentage,note=note);doc.save()
    return rule.name


def rule_parameters(name,source_site):
    portal.require_manager()
    doc=frappe.get_doc(RULE,name)
    if not doc.enabled:frappe.throw('This split rule was paused while further clarification is requested.')
    if doc.source_site!=source_site:frappe.throw('This allocation rule belongs to another company.',frappe.PermissionError)
    import calendar
    year=tax_year(doc.tax_year)
    return dict(name=doc.name,match_text=doc.match_text,percentage=doc.percentage,reason='Approved client split '+doc.name+': '+doc.approval_note,from_date=f'{year-1}-03-01',to_date=f'{year}-02-{calendar.monthrange(year,2)[1]}')


def rule_link(rule,site):
    from urllib.parse import urlsplit,quote
    base=(frappe.conf.get('books_review_source_urls') or {}).get(site,'')
    parsed=urlsplit(base)
    if parsed.scheme in {'http','https'} and parsed.hostname and not parsed.username and not parsed.password:
        return base.rstrip('/')+'/books/bank-reallocation?rule='+quote(rule,safe='')


def matching_rules(doc):
    if not portal.manager():return []
    description=json.loads(doc.snapshot or '{}').get('description','').casefold()
    return [dict(r,apply_url=rule_link(r.name,doc.source_site)) for r in frappe.get_all(RULE,filters={'client':doc.client,'source_site':doc.source_site,'tax_year':doc.tax_year,'enabled':1},fields=['name','match_text','percentage','approval_note'],limit_page_length=0) if r.match_text.casefold() in description]


def pause_rules(task):
    for name in frappe.get_all(RULE,filters={'review_task':task.name,'enabled':1},pluck='name'):
        rule=frappe.get_doc(RULE,name);rule.enabled=0;rule.save(ignore_permissions=True)
        portal.log(task,'Allocation rule paused',rule=name,note='Further client clarification requested')
