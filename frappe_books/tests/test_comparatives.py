"""Comparison columns retain posted figures and disclose source limitations."""
import unittest
from unittest.mock import patch
from decimal import Decimal
import frappe
from frappe_books.reports import comparatives as c

class TestComparatives(unittest.TestCase):
    def setUp(self):
        self.accounts={}
        for root in ('Asset','Liability','Equity','Income','Expense'):
            self.accounts[root]=frappe._dict(name=root,root_type=root,is_group=1,parent_books_account=None)
            self.accounts[root+' leaf']=frappe._dict(name=root+' leaf',root_type=root,is_group=0,parent_books_account=root)
        self.doc=frappe._dict(name='TEST-CMP',title='Reported accounts',from_date='2024-03-01',to_date='2025-02-28',balances=[frappe._dict(account=k+' leaf',balance=v) for k,v in dict(Asset=100,Liability=-30,Equity=-70,Income=-80,Expense=72).items()])
        self.filters=frappe._dict(compare_previous_year=1,hide_group_amounts=0,from_date='2025-03-01',to_date='2026-02-28')
        self.columns=[dict(fieldname='account'),dict(fieldname='current')]
    def run_report(self,kind,rows=None):
        with patch.object(c,'_context',return_value=(self.doc,'')),patch.object(c.statements,'_accounts',return_value=self.accounts):
            return c.append(kind,self.filters,self.columns,rows or [])
    def test_prior_only_accounts_and_current_values(self):
        cols,rows,note=self.run_report('profit-and-loss',[dict(account='Income leaf',current=120)])
        by={r.get('account'):r for r in rows}
        self.assertEqual(by['Expense leaf']['comparison'],72)
        self.assertEqual(by['Income leaf']['current'],120)
        self.assertEqual(by['Total Profit']['comparison'],8)
        self.assertEqual(by['Total Profit']['current'],120)
        self.assertEqual(cols[-1]['comparison_source'],'TEST-CMP')
    def test_balance_sheet_does_not_double_count_closed_profit(self):
        _,rows,_=self.run_report('balance-sheet',[dict(account='Provisional Profit / Loss (Credit)',current=5)])
        by={r.get('account'):r for r in rows}
        self.assertEqual(by['Total Asset (Debit)']['comparison'],100)
        self.assertEqual(by['Total (Credit)']['comparison'],100)
        self.assertEqual(by['Provisional Profit / Loss (Credit)']['comparison'],0)
    def test_trial_balance_discloses_reference_difference(self):
        self.columns=[dict(fieldname='account'),dict(fieldname='opening_debit')]
        _,rows,note=self.run_report('trial-balance',[dict(account='Asset leaf',opening_debit=100)])
        by={r.get('account'):r for r in rows}
        self.assertEqual(by['Asset leaf']['opening_debit'],100)
        self.assertEqual(by['Total']['comparison_debit']-by['Total']['comparison_credit'],Decimal(-8))
        self.assertIn('not an unclosed prior-year trial balance',note)
    def test_disabled_and_missing_comparisons_keep_original_columns(self):
        self.filters.compare_previous_year=0
        self.assertEqual(c.append('trial-balance',self.filters,self.columns,[]),(self.columns,[]))
        self.filters.compare_previous_year=1
        with patch.object(c,'_context',return_value=(None,'No approved comparison')):
            self.assertEqual(c.append('trial-balance',self.filters,self.columns,[]),(self.columns,[],'No approved comparison'))
    def test_hidden_groups_retain_leaf_and_section_totals(self):
        self.filters.hide_group_amounts=1
        _,rows,_=self.run_report('profit-and-loss')
        by={r.get('account'):r for r in rows}
        self.assertIsNone(by['Income']['comparison'])
        self.assertEqual(by['Income leaf']['comparison'],80)
        self.assertEqual(by['Total Income (Credit)']['comparison'],80)
