import io
import json
import uuid
from pathlib import Path
from unittest.mock import patch
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request
import frappe
from frappe.tests import IntegrationTestCase
from frappe_books import review_documents as docs,review_portal as portal


class IntegrationTestPortalV2(IntegrationTestCase):
    def test_private_documents_progress_and_reusable_splits(self):
        original_user=frappe.session.user;original_sources=frappe.conf.get('books_review_sources')
        original_request=getattr(frappe.local,'request',None);original_response=frappe.local.response
        first='portal-v2-first@example.test';second='portal-v2-second@example.test'
        site='portal-v2-example.localhost';other='portal-v2-other.localhost';shared='portal-v2-shared.localhost'
        paths=[];frappe.set_user('Administrator');frappe.db.savepoint('portal_v2_test')
        try:
            for email in [first,second]:
                if not frappe.db.exists('User',email):
                    user=frappe.get_doc(dict(doctype='User',email=email,first_name='Portal v2 fixture',enabled=1,user_type='Website User',send_welcome_email=0,roles=[dict(role=portal.CLIENT_ROLE)]));user.flags.no_welcome_mail=True;user.insert(ignore_permissions=True)
            frappe.conf.books_review_sources={site:'Example own account',other:'Other client',shared:'Example joint property'}
            for email,source in [(first,site),(first,shared),(second,other),(second,shared)]:
                frappe.get_doc(dict(doctype=portal.ACCESS,client=email,source_site=source,enabled=1)).insert()
            document=docs.create_request(first,site,'Document','Example certificate','Upload the example certificate')[0]
            docs.create_request(first,site,'Decision','Example split','Confirm the example allocation')
            docs.create_request(first,shared,'Question','Joint question','Explain the example shared item')
            docs.create_request(second,shared,'Question','Other assigned question','Visible only to the other client')
            docs.create_request(second,other,'Question','Other company question','Other client only')
            snapshot=dict(name='v2-example-bank-line',parent='EXAMPLE-STATEMENT',transaction_date='2025-06-01',reference='EXAMPLE',description='Internet subscription',money_out=100,money_in=0,offset_account='Example expense',classification='Business')
            with patch.object(portal,'source_rows',return_value=dict(rows=[snapshot])):
                transaction=portal.assign(first,site,'Confirm this example expense',[snapshot['name']])[0]
            frappe.set_user(first)
            overview=docs.overview(2026)
            self.assertEqual({e['site'] for e in overview['entities']},{site,shared})
            self.assertEqual(overview['total'],4)
            self.assertEqual(docs.overview(2025)['total'],0)
            self.assertEqual(len(portal.list_reviews(tax_year=2026)),4)
            self.assertEqual(portal.list_reviews(source_site=other),[])
            self.assertRaises(frappe.PermissionError,lambda:docs.overview(2026,client=second))
            self.assertRaises(frappe.PermissionError,lambda:portal.preview_client(second))
            self.assertRaises(frappe.ValidationError,lambda:portal.answer(document,'No uploaded file'))
            for filename,content in [('../unsafe.pdf',b'%PDF-1.4'),('unsafe.html',b'<script>'),('fake.pdf',b'not pdf')]:
                self.assertRaises(frappe.ValidationError,lambda n=filename,c=content:docs.validate_file(n,c))
            self.assertRaises(frappe.ValidationError,lambda:docs.validate_file('too-large.pdf',b'%PDF-'+b'0'*docs.MAX_SIZE))
            old=str(frappe.get_doc(portal.TASK,document).modified)
            from pypdf import PdfWriter
            buffer=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=72,height=72);writer.write(buffer);content=buffer.getvalue()
            filename='portalv2-fixture-'+uuid.uuid4().hex+'.pdf'
            frappe.local.request=Request(EnvironBuilder(method='POST',data={'file':(io.BytesIO(content),filename)}).get_environ())
            answer=docs.upload(document,'Example supporting document',old)
            self.assertEqual(answer['status'],'Answered');self.assertEqual(len(answer['attachments']),1)
            file_id=answer['attachments'][0]['name'];file=frappe.get_doc('File',file_id)
            paths.append(Path(file.get_full_path()));self.assertEqual(file.is_private,1)
            self.assertRaises(frappe.ValidationError,lambda:docs.upload(document,'stale',old))
            frappe.local.response=frappe._dict();docs.download(document,file_id)
            self.assertEqual(frappe.local.response.filecontent,content)
            self.assertEqual(frappe.local.response.display_content_as,'attachment')
            frappe.set_user(second)
            self.assertRaises(frappe.PermissionError,lambda:docs.download(document,file_id))
            self.assertRaises(frappe.PermissionError,lambda:docs.upload(document))
            frappe.set_user('Administrator');portal.review(document,'Reviewed','Example certificate checked')
            frappe.set_user(first)
            portal.answer(transaction,'40 percent relates to business','Mixed',40,propose_rule=True)
            self.assertEqual(docs.overview(2026)['reviewing'],1)
            frappe.set_user('Administrator')
            self.assertRaises(frappe.ValidationError,lambda:docs.approve_rule(transaction,'Internet','not yet reviewed'))
            portal.review(transaction,'Reviewed','Example split checked')
            rule=docs.approve_rule(transaction,'Internet','Approved example split')
            self.assertEqual(docs.rule_parameters(rule,site)['percentage'],40)
            self.assertRaises(frappe.PermissionError,lambda:docs.rule_parameters(rule,other))
            self.assertRaises(frappe.ValidationError,lambda:docs.approve_rule(transaction,'Internet','Duplicate'))
            self.assertEqual(len(docs.matching_rules(frappe.get_doc(portal.TASK,transaction))),1)
            preview=portal.preview_client(first)
            self.assertFalse(preview['profile']['accountant']);self.assertEqual(preview['overview']['resolved'],2)
            self.assertNotIn(other,{e['site'] for e in preview['overview']['entities']})
            portal.review(transaction,'Follow-up','Recheck example split')
            self.assertRaises(frappe.ValidationError,lambda:docs.rule_parameters(rule,site))
            self.assertEqual(docs.matching_rules(frappe.get_doc(portal.TASK,transaction)),[])
            frappe.set_user('Guest');self.assertRaises(frappe.PermissionError,docs.overview)
            self.assertRaises(frappe.PermissionError,lambda:docs.download(document,file_id))
        finally:
            frappe.set_user('Administrator');frappe.db.rollback(save_point='portal_v2_test')
            private=Path(frappe.get_site_path('private','files')).resolve()
            for path in paths:
                if path.resolve().parent==private and path.name.startswith('portalv2-fixture-'):path.unlink(missing_ok=True)
            frappe.conf.books_review_sources=original_sources;frappe.local.request=original_request;frappe.local.response=original_response;frappe.set_user(original_user)
