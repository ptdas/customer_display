import frappe
@frappe.whitelist()
def repair_gl_entry():	
	doctype = "Sales Invoice"
	docname = "ACC-SINV-2025-00063-1"

	docu = frappe.get_doc(doctype, docname)	
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	docu.make_gl_entries()


@frappe.whitelist()
def create_tutup_kasir():
	from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import make_closing_entry_from_opening
	closing_entry = make_closing_entry_from_opening(frappe.get_doc("POS Opening Entry","POS-OPE-2025-00009"))
	closing_entry.save()
	