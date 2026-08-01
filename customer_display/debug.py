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
	
def start_import():
	doc = frappe.get_doc("Data Import","Stock Entry Import on 2026-01-01 22:40:58.797076")
	doc.start_import()

def start_import2():
	doc = frappe.get_doc("Data Import","Item Price Import on 2026-01-01 05:23:08.379058")
	doc.start_import()
def rename_customer():
	data = frappe.db.sql("select name , custom_kode from `tabCustomer` where name != custom_kode", as_list=1)
	count=0
	for row in data:
		frappe.rename_doc("Customer",row[0],row[1])
		frappe.db.commit()
		count=count+1
		print(count)

def debug():
	doc = frappe.get_doc("Company","BJB4")
	doc.create_default_accounts()