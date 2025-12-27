import frappe
from frappe import _

def create_user_permission_on_save(doc, method):
	if not doc.cabang_user:
		return
	
	for row in doc.cabang_user:
		if row.company:
			existing = frappe.db.exists("User Permission", {
				"user": doc.name,
				"allow": "Company",
				"for_value": row.company
			})
			
			if not existing:
				try:
					user_permission = frappe.get_doc({
						"doctype": "User Permission",
						"user": doc.name,
						"allow": "Company",
						"for_value": row.company,
						"apply_to_all_doctypes": 1 
					})
					user_permission.insert(ignore_permissions=True)
					frappe.msgprint(_("User Permission created for Company: {0}").format(row.company))
					
				except Exception as e:
					frappe.log_error(f"Error creating User Permission: {str(e)}")


def delete_user_permission_on_delete(doc, method):
	current_companies = [row.company for row in doc.cabang_user if row.company]
	
	user_permissions = frappe.get_all("User Permission", 
		filters={
			"user": doc.name,
			"allow": "Company"
		},
		fields=["name", "for_value"]
	)
	
	for perm in user_permissions:
		if perm.for_value not in current_companies:
			frappe.delete_doc("User Permission", perm.name, ignore_permissions=True)
			frappe.msgprint(_("User Permission deleted for Company: {0}").format(perm.for_value))

def make_perm_level_session(bootinfo):
	max_perm = frappe.db.sql(""" 
		SELECT hs.name,hs.role,MAX(tr.perm_level) 
		FROM `tabHas Role` hs 
		JOIN `tabRole` tr ON hs.role = tr.name 
		WHERE hs.parenttype = "User" and hs.parent = "{}" AND tr.perm_level IS NOT NULL; """.format(frappe.session.user))[0][2]

	if not max_perm:
		max_perm = 1

	bootinfo.max_perm_level = max_perm