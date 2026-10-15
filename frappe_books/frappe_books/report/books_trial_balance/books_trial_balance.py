from frappe_books.reports import financial_statements as statements
from frappe_books.reports import comparatives
from frappe_books.reports.filters import with_defaults


def execute(filters=None):
	filters = with_defaults(filters, get_default_filters())
	return comparatives.append("trial-balance", filters, statements.get_trial_balance_columns(), statements.get_trial_balance(filters))


def get_default_filters():
	return {**statements.get_trial_balance_default_filters(), **comparatives.default_filters(trial=True)}
