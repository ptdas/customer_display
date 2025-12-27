# in your_app/your_module/account.py

import frappe
from frappe import _


@frappe.whitelist()
def debug_clone_account():
	clone_account_to_children(frappe.get_doc("Account","30.0000.000 - Modal - A"),"validate")



@frappe.whitelist()
def clone_account_to_children(doc, method):
	"""
	After you insert an Account under ABKG, automatically create the same Account
	(matching account_name, type, etc.) in each child company, then show a msgprint.
	"""
	PARENT = "ABKG"

	# 1) Only run if this Account was just created under ABKG
	if doc.company != PARENT:
		return

	# 2) Fetch all child companies of ABKG
	children = frappe.get_all(
		"Company",
		filters={"parent_company": PARENT},
		pluck="name"
	)
	if not children:
		return


	created = []
	for child in children:
		# 3) Skip if an Account with the same name already exists for this child
		if frappe.db.exists("Account", {"account_name": doc.account_name, "account_number": doc.account_number ,"company": child}):
			continue

		# 4) Build a brand-new Account doc for the child
		new_ac = frappe.new_doc("Account")
		new_ac.account_name   = doc.account_name
		new_ac.company        = child
		new_ac.account_type   = doc.account_type
		new_ac.root_type      = doc.root_type
		new_ac.is_group       = doc.is_group
		new_ac.report_type    = doc.report_type
		new_ac.default_currency = getattr(doc, "default_currency", None)
		new_ac.disabled       = doc.disabled
		new_ac.account_number = doc.account_number


		# ─── remap parent_account ───
		if doc.parent_account:
			# load the parent (ABKG) to get its human name
			parent = frappe.get_doc("Account", doc.parent_account)
			parent_name = parent.account_name

			# look up the child-company account whose account_name = parent_name
			mapped = frappe.db.get_value(
				"Account",
				{"account_name": parent_name, "company": child},
				"name"
			)
			new_ac.parent_account = mapped or None

		# 5) Insert under ignore_permissions
		try:
			new_ac.insert(ignore_permissions=True,ignore_mandatory=True)
			created.append(child)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				_("Failed to Clone Account for {0}").format(child)
			)

	# 6) Feedback to user
	if created:
		frappe.msgprint(
			_("Account {0} cloned into child companies: {1}")
			.format(doc.account_name, ", ".join(created))
		)
	else:
		frappe.msgprint(
			_("Account {0} already exists in all child companies (or none to clone).")
			.format(doc.account_name)
		)