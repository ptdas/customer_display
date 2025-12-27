import frappe
from frappe.utils import now_datetime, get_datetime, time_diff_in_hours

@frappe.whitelist()
def approval_return(self,method):
	if not self.is_return:
		return

	doc_asli = frappe.get_doc("Sales Invoice",self.return_against)
	hours_passed = time_diff_in_hours(now_datetime(), doc_asli.creation)

	if hours_passed > 72:
		self.workflow_state = "Need Approval"
		self.db_update()

