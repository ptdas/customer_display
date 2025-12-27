import frappe

@frappe.whitelist()
def get_pos_profiles_based_on_user(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session.user

	if "99_Open All POS Profile" in frappe.get_roles(user):
		return frappe.db.sql("""
			SELECT name, name FROM `tabPOS Profile`
			WHERE `tabPOS Profile`.name LIKE %(txt)s
			ORDER BY `tabPOS Profile`.name
			LIMIT %(start)s, %(page_len)s
		""", {
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len
		})
	else:
		return frappe.db.sql("""
			SELECT p.name, p.name
			FROM `tabPOS Profile` p
			JOIN `tabPOS Profile User` au ON au.parent = p.name
			WHERE au.user = %(user)s
			AND p.name LIKE %(txt)s
			ORDER BY p.name
			LIMIT %(start)s, %(page_len)s
		""", {
			"user": user,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len
		})

@frappe.whitelist()
def get_max_perm_level_on_user(user):
	max_perm = frappe.db.sql("""
		SELECT hs.name,hs.role,MAX(tr.perm_level) 
		FROM `tabHas Role` hs 
		JOIN `tabRole` tr ON hs.role = tr.name 
		WHERE hs.parenttype = "User" and hs.parent = "{}" AND tr.perm_level IS NOT NULL;
	""".format(user))

	return max_perm[0][2]