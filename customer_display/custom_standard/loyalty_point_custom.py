
import frappe
from frappe.utils import flt

def payment_entry_on_submit(doc, method):
	for row in doc.references:
		if row.reference_doctype == "Sales Invoice":
			si_name = row.reference_name

			# Reload the Sales Invoice to get current outstanding_amount
			si = frappe.get_doc("Sales Invoice", si_name)

			# Only proceed if the invoice is submitted and now fully paid
			# (outstanding_amount should already have been updated by payment submission)
			if flt(si.outstanding_amount) == 0 and si.docstatus == 1:
				try:
					# Call your custom method here.
					# Pass 'si' (the Sales Invoice doc) or pass its name,
					# depending on how you wrote custom_make_loyalty_point_entry.
					si.make_loyalty_point_entry()
				except Exception:
					# Log any errors so they don’t stop the Payment Entry submit
					frappe.log_error(
						message=frappe.get_traceback(),
						title="custom_make_loyalty_point_entry failed for " + si_name
					)