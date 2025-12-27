import frappe
from frappe import _

def clone_warehouse_to_children(doc, method):
	"""
	After you insert a Warehouse under ABKG, automatically create the same Warehouse
	(matching warehouse_name, type, etc.) in each child company, then show a msgprint.
	"""
	PARENT = "ABKG"

	# 1) Only run if the Warehouse was just created under ABKG
	if getattr(doc, "company", None) != PARENT:
		return

	# 2) Fetch all child companies of ABKG
	children = frappe.get_all(
		"Company",
		filters={"parent_company": PARENT},
		pluck="name"
	)
	if not children:
		# no children defined – nothing to clone
		return

	created_children = []
	for child in children:
		# 3) Skip if a Warehouse of the same name already exists for this child
		exists = frappe.db.exists(
			"Warehouse",
			{
				"warehouse_name": doc.warehouse_name,
				"company": child
			}
		)
		if exists:
			continue

		# 4) Build a brand-new Warehouse doc for the child
		new_wh = frappe.new_doc("Warehouse")
		new_wh.warehouse_name = doc.warehouse_name
		new_wh.company = child
		new_wh.is_group = doc.is_group

		# Copy any other fields you care about:
		new_wh.warehouse_type = doc.warehouse_type
		new_wh.disabled = doc.disabled

		# ───— remap parent_warehouse ────
		if doc.parent_warehouse:
			# 1) load the ABKG parent record
			parent_abkg = frappe.get_doc("Warehouse", doc.parent_warehouse)

			# 2) grab its human-facing name
			parent_name = parent_abkg.warehouse_name

			# 3) look up the child-company warehouse whose warehouse_name = parent_name
			mapped = frappe.get_value(
				"Warehouse",
				{
					"warehouse_name": parent_name,
					"company": child
				},
				"name"
			)
			if mapped:
				new_wh.parent_warehouse = mapped
			else:
				# if there is no equivalent parent under the child, leave it blank
				new_wh.parent_warehouse = None
		else:
			new_wh.parent_warehouse = None

		# … if you have custom fields on Warehouse, copy them the same way:
		# new_wh.custom_field_1 = doc.custom_field_1
		# new_wh.some_other_flag = doc.some_other_flag

		# 5) Insert under ignore_permissions (so site admins don’t get blocked)
		try:
			new_wh.insert(ignore_permissions=True)
			created_children.append(child)
		except Exception as e:
			# If there’s a failure, log it in case you need to debug:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=_("Failed to Clone Warehouse for {0}").format(child)
			)

	# 6) Finally, show a message back to the user
	if created_children:
		frappe.msgprint(
			_("Warehouse {0} has been created in child companies: {1}")
			.format(doc.warehouse_name, ", ".join(created_children))
		)
	else:
		frappe.msgprint(
			_("Warehouse {0} already exists in all child companies (or no new children).")
			.format(doc.warehouse_name)
		)