"""Reusable client work, with frozen stage definitions and explicit accountant approval."""
import json
import frappe
from frappe.utils import getdate, now_datetime
from frappe_books import review_portal as review

TEMPLATE = 'Books Workflow Template'
WORKFLOW = 'Books Workflow'
ROLES = {'Draft', 'Assigned', 'Responded', 'Review', 'Complete'}
DEFAULT_STAGES = [dict(name=n, role=r) for n,r in [('Draft','Draft'),('Assigned','Assigned'),('Client responded','Responded'),('Accountant review','Review'),('Complete','Complete')]]


def stages(value):
    value=frappe.parse_json(value)
    if not isinstance(value,list) or not 5 <= len(value) <= 20:
        frappe.throw('Use between 5 and 20 stages.')
    clean=[]
    for item in value:
        name=str(item.get('name','')).strip() if isinstance(item,dict) else ''
        role=item.get('role') if isinstance(item,dict) else None
        if not name or len(name)>100 or role not in ROLES:
            frappe.throw('Each stage needs a name and a valid responsibility.')
        clean.append(dict(name=name,role=role))
    if len({s['name'] for s in clean})!=len(clean) or {s['role'] for s in clean}!=ROLES:
        frappe.throw('Use unique stage names and include Draft, Assigned, Responded, Review and Complete responsibilities.')
    roles=[s['role'] for s in clean]
    if roles[:3]!=['Draft','Assigned','Responded'] or roles[-1]!='Complete' or any(r!='Review' for r in roles[3:-1]):
        frappe.throw('Start with Draft, Assigned and Responded, then add accountant review stages and finish with Complete.')
    return clean


def seed_templates():
    for name,topic in [('Transaction clarification','Accounting'),('Tax review','Tax'),('General client query','Other')]:
        if not frappe.db.exists(TEMPLATE,name):
            frappe.get_doc(dict(doctype=TEMPLATE,title=name,topic=topic,enabled=1,stages=json.dumps(DEFAULT_STAGES))).insert(ignore_permissions=True)


def audit(doc,action,**values):
    events=json.loads(doc.workflow_log or '[]')
    events.append(dict(action=action,by=frappe.session.user,at=str(now_datetime()),**values))
    doc.workflow_log=json.dumps(events,default=str)


def role(doc):
    return next((s['role'] for s in json.loads(doc.stages) if s['name']==doc.stage),None)


def set_role(doc,desired,reason):
    target=next(s['name'] for s in json.loads(doc.stages) if s['role']==desired)
    if doc.stage!=target:
        audit(doc,'Stage changed',from_stage=doc.stage,to_stage=target,note=reason)
        doc.stage=target;doc.save(ignore_permissions=True)


def create_case(template,client,source_site,title,due_date=''):
    review.require_manager()
    if not review.allowed(client,source_site):frappe.throw('This client cannot access that company.',frappe.PermissionError)
    definition=frappe.get_doc(TEMPLATE,template)
    if not definition.enabled:frappe.throw('Choose an enabled workflow template.')
    definition_stages=stages(definition.stages)
    title=(title or '').strip()
    if not title or len(title)>140:frappe.throw('Enter a workflow title of up to 140 characters.')
    if due_date:getdate(due_date)
    doc=frappe.get_doc(dict(doctype=WORKFLOW,template=template,topic=definition.topic,client=client,source_site=source_site,company=review.sources()[source_site],title=title,due_date=due_date or None,stage=definition_stages[0]['name'],stages=json.dumps(definition_stages)))
    audit(doc,'Created');doc.insert();return doc


def attach(doc,names):
    for name in names:
        task=frappe.get_doc(review.TASK,name)
        if task.client!=doc.client or task.source_site!=doc.source_site or task.workflow:
            frappe.throw('This task cannot be attached to that workflow.')
        task.workflow=doc.name;task.save()
    audit(doc,'Tasks assigned',tasks=names)
    set_role(doc,'Assigned','Questions assigned to client')
    doc.save()


def task_updated(task):
    if not task.workflow:return
    doc=frappe.get_doc(WORKFLOW,task.workflow,for_update=True)
    if task.status=='Follow-up':set_role(doc,'Assigned','Client clarification requested')
    elif task.status=='Answered' and role(doc)=='Assigned':
        statuses=frappe.get_all(review.TASK,filters={'workflow':doc.name},pluck='status',limit_page_length=0)
        if statuses and all(s in {'Answered','Reviewed'} for s in statuses):set_role(doc,'Responded','All client questions answered')
    audit(doc,'Task updated',task=task.name,status=task.status)
    doc.save(ignore_permissions=True)


def workspace(source_site=None):
    review.require_manager()
    templates=[dict(d) for d in frappe.get_all(TEMPLATE,fields=['name','title','topic','enabled','stages','modified'],limit_page_length=0)]
    filters={'source_site':source_site} if source_site else {}
    cases=[]
    for name in frappe.get_all(WORKFLOW,filters=filters,pluck='name',order_by='modified desc',limit_page_length=300):
        doc=frappe.get_doc(WORKFLOW,name)
        tasks=frappe.get_all(review.TASK,filters={'workflow':name},fields=['name','question','status','kind','answer','classification','percentage','suggested_category','review_note','modified'],limit_page_length=0)
        cases.append(dict(name=name,title=doc.title,template=doc.template,topic=doc.topic,client=doc.client,company=doc.company,source_site=doc.source_site,due_date=doc.due_date,stage=doc.stage,stages=json.loads(doc.stages),modified=doc.modified,tasks=tasks,history=json.loads(doc.workflow_log or '[]')))
    profile=review.profile()
    return dict(templates=templates,cases=cases,clients=profile['clients'],sources={s:l for s,l in profile['sources'].items() if not source_site or s==source_site})


def save_template(title,topic,stage_list,name='',expected_modified=''):
    review.require_manager()
    clean=stages(stage_list);title=(title or '').strip();topic=(topic or '').strip()
    if not title or len(title)>100 or not topic or len(topic)>100:frappe.throw('Enter a template name and topic of up to 100 characters.')
    if name:
        doc=frappe.get_doc(TEMPLATE,name,for_update=True)
        if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('This template changed. Refresh before saving.')
        if title!=doc.title:frappe.throw('Keep the existing template name, or create a new template.')
    else:doc=frappe.new_doc(TEMPLATE)
    doc.update(dict(title=title,topic=topic,enabled=1,stages=json.dumps(clean)));doc.save();return doc.name


def create(template,client,source_site,title,due_date='',question=''):
    doc=create_case(template,client,source_site,title,due_date)
    if question:
        review.assign(client,source_site,question,due_date=due_date,workflow_name=doc.name)
    return doc.name


def add_question(name,question,expected_modified=''):
    review.require_manager();doc=frappe.get_doc(WORKFLOW,name,for_update=True)
    if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('This workflow changed. Refresh first.')
    if role(doc)=='Complete':frappe.throw('Reopen this workflow before adding questions.')
    names=review.assign(doc.client,doc.source_site,question,due_date=str(doc.due_date or ''),workflow_name=doc.name)
    return names


def advance(name,note,expected_modified='',reopen=False):
    review.require_manager();doc=frappe.get_doc(WORKFLOW,name,for_update=True)
    if expected_modified and str(doc.modified)!=expected_modified:frappe.throw('This workflow changed. Refresh before moving it.')
    note=(note or '').strip()
    if not note or len(note)>4000:frappe.throw('Enter a stage-change note of up to 4,000 characters.')
    configured=json.loads(doc.stages);position=next(i for i,s in enumerate(configured) if s['name']==doc.stage)
    statuses=frappe.get_all(review.TASK,filters={'workflow':doc.name},pluck='status',limit_page_length=0)
    if reopen:
        if role(doc)!='Complete':frappe.throw('Only a completed workflow can be reopened.')
        target=configured[3]
    else:
        if position==len(configured)-1:frappe.throw('This workflow is complete.')
        target=configured[position+1]
        if target['role']=='Assigned' and not statuses:frappe.throw('Add a client question before assigning this workflow.')
        if target['role'] in {'Responded','Review'} and (not statuses or any(s in {'Open','Follow-up'} for s in statuses)):frappe.throw('Wait until all client questions have answers.')
        if target['role']=='Complete' and (not statuses or any(s!='Reviewed' for s in statuses)):frappe.throw('Review and complete every question before completing the workflow.')
    audit(doc,'Reopened' if reopen else 'Stage changed',from_stage=doc.stage,to_stage=target['name'],note=note)
    doc.stage=target['name'];doc.save();return doc.name
