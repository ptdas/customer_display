
import frappe
from frappe.utils import flt

def check_po_qty(doc,method):
	if doc.workflow_state != "Draft":
		return

	doc.custom_po_qty_beda = 0  # reset

	for item in doc.items:
		if item.purchase_order and item.purchase_order_item:
			po_item = frappe.get_doc("Purchase Order Item", item.purchase_order_item)
			if flt(item.qty) > flt(po_item.qty):
				doc.custom_po_qty_beda = 1
				doc.workflow_state = "PO PREC Qty Beda"
				break

	doc.db_update()

def check_abbr(doc, method):
	abbr = frappe.db.get_value("Company", doc.company, "abbr")
	if not abbr:
		return

	for row in doc.items:
		if row.expense_account:
			old_company = frappe.db.get_value("Account", row.expense_account, "company")
			old_abbr = frappe.db.get_value("Company", old_company, "abbr") if old_company else None
			if old_abbr and row.expense_account.endswith(f" - {old_abbr}"):
				root = row.expense_account.rsplit(" - ", 1)[0]
				new_acct = f"{root} - {abbr}"
				if frappe.db.exists("Account", new_acct):
					row.expense_account = new_acct

		if row.cost_center:
			old_cc_company = frappe.db.get_value("Cost Center", row.cost_center, "company")
			old_cc_abbr = frappe.db.get_value("Company", old_cc_company, "abbr") if old_cc_company else None
			if old_cc_abbr and row.cost_center.endswith(f" - {old_cc_abbr}"):
				root = row.cost_center.rsplit(" - ", 1)[0]
				new_cc = f"{root} - {abbr}"
				if frappe.db.exists("Cost Center", new_cc):
					row.cost_center = new_cc

@frappe.whitelist()
def get_po_item_qty(po_detail):
	if not frappe.has_permission("Purchase Order", "read"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	return frappe.db.get_value("Purchase Order Item", po_detail, "qty")