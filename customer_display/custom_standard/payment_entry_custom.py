import frappe
from frappe import _

def validate_ri_payment(doc, method):
	for ref in doc.references or []:
		if ref.reference_doctype=="Purchase Invoice" and ref.docstatus==1:
			pi = frappe.get_doc("Purchase Invoice", ref.reference_name)
			for line in pi.items:
				if frappe.get_value("Item", line.item_code, "custom_ri_required"):
					exists = frappe.db.exists("Purchase Receipt Item", {
						"purchase_order":      line.purchase_order,
						"purchase_order_item": line.po_detail
					})
					if not exists:
						frappe.throw(
							_("Cannot pay for {0}: missing Purchase Receipt for item {1}")
							  .format(pi.name, line.item_code),
							frappe.exceptions.ValidationError
						)
