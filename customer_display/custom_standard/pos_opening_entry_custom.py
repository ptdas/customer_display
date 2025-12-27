import frappe
from frappe.utils import nowdate


def check_double(self,method):
	user = frappe.session.user

	if "99_ByPass Open POS" in frappe.get_roles(user):
		return 

	existing = frappe.db.exists("POS Opening Entry", {
		"user": self.user,
		"posting_date": self.posting_date,
		"docstatus": ("!=", 2),
		"name": ("!=", self.name)
	})

	if existing:
		frappe.throw(f"User '{self.user}' already has a POS Opening Entry for today.")
