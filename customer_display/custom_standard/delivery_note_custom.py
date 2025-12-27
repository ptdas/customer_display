import frappe

frappe.whitelist()
def set_expense(doc,method):
	das_setting = frappe.get_single("DAS Accounting Settings")
	for row in das_setting.das_accounting_settings_table:
		if row.company == doc.company:
			ex = row.expense_account_untuk_dn

	for row in doc.items:
		row.expense_account = ex
	