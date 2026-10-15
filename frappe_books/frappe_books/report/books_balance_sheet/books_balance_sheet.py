from frappe_books.reports import financial_statements as statements
from frappe_books.reports import comparatives
from frappe_books.reports.filters import with_defaults
from frappe_books.reports.periods import get_periods


def execute(filters=None):
	filters = with_defaults(filters, get_default_filters())
	periods = get_periods(filters)
	return comparatives.append("balance-sheet", filters, statements.get_statement_columns(periods), statements.get_balance_sheet(filters, periods), periods)


def get_default_filters():
	return {**statements.get_statement_default_filters(), **comparatives.default_filters(trial=False)}
