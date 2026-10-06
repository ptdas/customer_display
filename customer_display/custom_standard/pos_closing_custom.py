import frappe
from frappe.utils import get_datetime


@frappe.whitelist()
def get_pos_invoices(start, end, pos_profile, user):
	data = frappe.db.sql(
		"""
		SELECT
			name,
			TIMESTAMP(posting_date, posting_time) AS timestamp
		FROM
			`tabPOS Invoice`
		WHERE
			owner = %s
			AND docstatus = 1
			AND pos_profile = %s
			AND IFNULL(consolidated_invoice, '') = ''
			AND IFNULL(status, '') != 'Consolidated'
		""",
		(user, pos_profile),
		as_dict=1,
	)

	data = list(
		filter(
			lambda d: get_datetime(start) <= get_datetime(d.timestamp) <= get_datetime(end),
			data
		)
	)

	data = [
		frappe.get_doc("POS Invoice", d.name).as_dict()
		for d in data
	]

	return data