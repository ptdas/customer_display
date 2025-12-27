import frappe

def create_customer_display_settings(self,method):
	if not frappe.db.exists("Customer Display Settings", {"pos_profile": self.name}):
		frappe.get_doc({
			"doctype": "Customer Display Settings",
			"pos_profile": self.name,
			"current_customer": "",
			"current_points": 0,
			"paid_amount": 0,
			"change_amount": 0,
			"current_items": []
		}).insert(ignore_permissions=True)