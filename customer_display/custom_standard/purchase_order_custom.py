import frappe
from frappe.utils import nowdate

def auto_create_purchase_invoice(doc, method):
	# only if every item is flagged
	flags = [
		frappe.db.get_value("Item", d.item_code, "custom_auto_pi")
		for d in doc.items
	]
	if all(flags):
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier        = doc.supplier
		pi.company         = doc.company
		pi.posting_date    = nowdate()
		pi.set_posting_time = False

		for d in doc.items:
			pi.append("items", {
				"item_code":           d.item_code,
				"qty":                 d.qty,
				"rate":                d.rate,
				"uom":                 d.uom,
				"purchase_order":      doc.name,
				"purchase_order_item": d.name
			})

		pi.insert(ignore_permissions=True)
		pi.submit()

@frappe.whitelist()
def mark_need_review_if_vendor_mismatch(doc, method):
	if doc.workflow_state not in ("Cek Pajak C", "Need Review"):
		if doc.workflow_state in ("Approved"):
			for item in doc.items:
				expected_vendor = frappe.db.get_value("Item", item.item_code, "custom_vendor")
				doc_item = frappe.get_doc("Item",item.item_code)
				if expected_vendor and expected_vendor != doc.supplier:
					doc_item.custom_vendor = doc.supplier
					doc.db_update()					
			return
		else:
			return


	mismatch = False

	for item in doc.items:
		expected_vendor = frappe.db.get_value("Item", item.item_code, "custom_vendor")
		if expected_vendor and expected_vendor != doc.supplier:
			mismatch = True
			break

	if mismatch:
		doc.workflow_state = "Need Review"
		doc.db_update()