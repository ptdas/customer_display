# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	if filters is None:
		filters = {"date":"2025-12-30"}
	
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"label": _("Nama User"),
			"fieldname": "nama_user",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Kas Awal"),
			"fieldname": "kas_awal",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Jual Cash"),
			"fieldname": "jual_cash",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Jual Kartu"),
			"fieldname": "jual_kartu",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Vch"),
			"fieldname": "vch",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Retur Cash"),
			"fieldname": "retur_cash",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Retur Kartu"),
			"fieldname": "retur_kartu",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Kas Akhir"),
			"fieldname": "kas_akhir",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Byk"),
			"fieldname": "byk",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Point J"),
			"fieldname": "point_j",
			"fieldtype": "Float",
			"width": 100
		},
#		{
#			"label": _("Point R"),
#			"fieldname": "point_r",
#			"fieldtype": "Float",
#			"width": 100
#		},
#		{
#			"label": _("Point"),
#			"fieldname": "point",
#			"fieldtype": "Float",
#			"width": 100
		# }
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Get all POS Closing Entries
	pos_closing_entries = frappe.db.sql(f"""
		SELECT 
			name,
			user,
			posting_date
		FROM `tabPOS Closing Entry`
		WHERE docstatus = 1
		{conditions}
		ORDER BY posting_date DESC
	""", filters, as_dict=1)
	
	if not pos_closing_entries:
		return []
	
	pos_closing_names = [entry.name for entry in pos_closing_entries]
	
	# Get all Users' first names
	users = list(set([entry.user for entry in pos_closing_entries]))
	user_names = frappe.db.sql("""
		SELECT name, first_name
		FROM `tabUser`
		WHERE name IN %(users)s
	""", {"users": users}, as_dict=1)
	user_name_map = {u.name: u.first_name or u.name for u in user_names}
	
	# Get all Kas Awal (Opening Amount for Cash)
	kas_awal_data = frappe.db.sql("""
		SELECT parent, SUM(opening_amount) as total
		FROM `tabPOS Closing Entry Detail`
		WHERE parent IN %(parents)s
		AND mode_of_payment = 'Cash'
		GROUP BY parent
	""", {"parents": pos_closing_names}, as_dict=1)
	kas_awal_map = {row.parent: row.total for row in kas_awal_data}
	
	# Get all POS Transactions
	pos_transactions = frappe.db.sql("""
		SELECT parent, pos_invoice
		FROM `tabPOS Invoice Reference`
		WHERE parent IN %(parents)s
	""", {"parents": pos_closing_names}, as_dict=1)
	
	# Group transactions by parent
	transactions_map = {}
	all_pos_invoices = []
	for txn in pos_transactions:
		if txn.parent not in transactions_map:
			transactions_map[txn.parent] = []
		transactions_map[txn.parent].append(txn.pos_invoice)
		all_pos_invoices.append(txn.pos_invoice)
	
	if not all_pos_invoices:
		# Return data with only kas_awal
		data = []
		for entry in pos_closing_entries:
			data.append({
				"nama_user": user_name_map.get(entry.user, entry.user),
				"kas_awal": kas_awal_map.get(entry.name, 0),
				"jual_cash": 0,
				"jual_kartu": 0,
				"vch": 0,
				"retur_cash": 0,
				"retur_kartu": 0,
				"kas_akhir": kas_awal_map.get(entry.name, 0),
				"byk": 0,
				"point_j": 0,
				"point_r": 0,
				"point": 0
			})
		# Sort by nama_user before returning
		data.sort(key=lambda x: x["nama_user"].lower())
		return data
	
	# Get all POS Invoice details including custom fields
	pos_invoice_data = frappe.db.sql("""
		SELECT name, is_return, custom_si_pos_no, custom_si_pos_id, change_amount, loyalty_points
		FROM `tabPOS Invoice`
		WHERE name IN %(invoices)s
	""", {"invoices": all_pos_invoices}, as_dict=1)
	pos_invoice_map = {inv.name: inv for inv in pos_invoice_data}
	
	# Collect all custom_si_pos_no and custom_si_pos_id from POS Invoices
	pos_reference_ids = []
	for inv in pos_invoice_data:
		if inv.custom_si_pos_no:
			pos_reference_ids.append(inv.custom_si_pos_no)
		if inv.custom_si_pos_id:
			pos_reference_ids.append(inv.custom_si_pos_id)
	
	# Remove duplicates
	pos_reference_ids = list(set(pos_reference_ids)) if pos_reference_ids else []
	
	# Get all Payments from POS Invoices
	payments_data = frappe.db.sql("""
		SELECT parent, mode_of_payment, amount
		FROM `tabSales Invoice Payment`
		WHERE parent IN %(invoices)s
	""", {"invoices": all_pos_invoices}, as_dict=1)
	
	# Group payments by parent
	payments_map = {}
	for payment in payments_data:
		if payment.parent not in payments_map:
			payments_map[payment.parent] = []
		payments_map[payment.parent].append(payment)
	
	# Get all Return Invoices that reference the POS Invoices
	return_invoices = []
	if pos_reference_ids:
		return_invoices = frappe.db.sql("""
			SELECT name, custom_si_pos_no, custom_si_pos_id
			FROM `tabSales Invoice`
			WHERE (custom_si_pos_no IN %(ref_ids)s OR custom_si_pos_id IN %(ref_ids)s)
			AND is_return = 1
		""", {"ref_ids": pos_reference_ids}, as_dict=1, debug=1)
	
	# Group return invoices by original invoice
	return_invoice_map = {}
	all_return_invoices = []
	for ret_inv in return_invoices:
		key = ret_inv.custom_si_pos_no  # or custom_si_pos_id
		if key not in return_invoice_map:
			return_invoice_map[key] = []
		return_invoice_map[key].append(ret_inv.name)
		all_return_invoices.append(ret_inv.name)
	
	# Get payments from Return Invoices
	return_payments_data = []
	if all_return_invoices:
		return_payments_data = frappe.db.sql("""
			SELECT parent, mode_of_payment, amount
			FROM `tabSales Invoice Payment`
			WHERE parent IN %(invoices)s
		""", {"invoices": all_return_invoices}, as_dict=1)
	
	return_payments_map = {}
	for payment in return_payments_data:
		if payment.parent not in return_payments_map :
			return_payments_map[payment.parent] = []
		elif payment.amount > 0:
			return_payments_map[payment.parent].append(payment)
	
	# Handle unpaid return invoices - get proportional payment from original invoice
	if all_return_invoices:
		unpaid_returns = frappe.db.sql("""
			SELECT 
				si.name,
				si.custom_si_pos_no,
				si.custom_si_pos_id,
				si.grand_total as return_amount,
				orig.grand_total as original_amount,
				orig.name as orig_name
			FROM `tabSales Invoice` si
			LEFT JOIN `tabSales Invoice` orig ON (si.return_against = orig.name)
			WHERE si.name IN %(invoices)s
			AND si.is_return = 1
		""", {"invoices": all_return_invoices}, as_dict=1)


	
		# Get original invoice payments for unpaid returns
		original_invoice_names = [ur.orig_name for ur in unpaid_returns]
		if original_invoice_names:

			original_payments = frappe.db.sql("""
				SELECT parent, mode_of_payment, amount
				FROM `tabSales Invoice Payment`
				WHERE parent IN %(invoices)s
			""", {"invoices": original_invoice_names}, as_dict=1)
			
			# Group original payments by parent
			original_payments_map = {}
			for payment in original_payments:
				if payment.parent not in original_payments_map:
					original_payments_map[payment.parent] = []
				original_payments_map[payment.parent].append(payment)
			
			# Calculate proportional payments for unpaid returns
			for ur in unpaid_returns:
				original_inv_name = ur.orig_name
				if original_inv_name and original_inv_name in original_payments_map and ur.original_amount > 0:
					# Calculate proportion
					proportion = abs(ur.return_amount) / ur.original_amount
					
					# Apply proportion to each payment method
					proportional_payments = []
					for orig_payment in original_payments_map[original_inv_name]:
						proportional_amount = orig_payment.amount * proportion
						proportional_payments.append({
							"parent": ur.name,
							"mode_of_payment": orig_payment.mode_of_payment,
							"amount": proportional_amount
						})
					
					# Add to return_payments_map
					if ur.name not in return_payments_map:
						return_payments_map[ur.name] = []					

					return_payments_map[ur.name].extend(proportional_payments)
	
	# Get all Loyalty Points for POS Invoices
	# Need to get is_return from Sales Invoice
	all_invoices_for_loyalty = all_pos_invoices + all_return_invoices if all_return_invoices else all_pos_invoices
	
	loyalty_points_data = []
	if all_invoices_for_loyalty:
		loyalty_points_data = frappe.db.sql("""
			SELECT 
				lpe.invoice, 
				si.is_return,
				SUM(lpe.loyalty_points) as total
			FROM `tabLoyalty Point Entry` lpe
			INNER JOIN `tabSales Invoice` si ON lpe.invoice = si.name
			WHERE lpe.invoice IN %(invoices)s
			AND (lpe.redeem_against IS NULL OR lpe.redeem_against = '')
			AND lpe.loyalty_points > 0
			GROUP BY lpe.invoice, si.is_return
		""", {"invoices": all_invoices_for_loyalty}, as_dict=1)
	
	loyalty_points_map = {}
	return_loyalty_points_map = {}
	for lp in loyalty_points_data:
		if lp.is_return == 0:
			loyalty_points_map[lp.invoice] = lp.total
		else:
			return_loyalty_points_map[lp.invoice] = lp.total
	
	# Process data
	data = []
	for entry in pos_closing_entries:
		row = process_pos_closing_entry(
			entry,
			user_name_map,
			kas_awal_map,
			transactions_map,
			pos_invoice_map,
			payments_map,
			return_invoice_map,
			return_payments_map,
			loyalty_points_map,
			return_loyalty_points_map
		)
		data.append(row)
	
	# Sort data by nama_user (first name) before returning
	data.sort(key=lambda x: x["nama_user"].lower())
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("date"):
		conditions.append("posting_date = %(date)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def process_pos_closing_entry(entry, user_name_map, kas_awal_map, transactions_map, 
							   pos_invoice_map, payments_map, return_invoice_map, 
							   return_payments_map, loyalty_points_map, return_loyalty_points_map):
	
	user_name = user_name_map.get(entry.user, entry.user)
	kas_awal = kas_awal_map.get(entry.name, 0)
	
	jual_cash = 0
	jual_kartu = 0
	retur_cash = 0
	retur_kartu = 0
	new_retur_cash = 0
	new_retur_kartu = 0
	byk = 0
	point_j = 0
	point_r = 0
	point_j_redemption = 0
	
	pos_invoices = transactions_map.get(entry.name, [])
	
	for pos_invoice in pos_invoices:
		pos_inv = pos_invoice_map.get(pos_invoice)
		
		if not pos_inv:
			continue
		
		if pos_inv.is_return == 0:
			# Jual Cash and Jual Kartu
			payments = payments_map.get(pos_invoice, [])
			for payment in payments:
				if payment.mode_of_payment == "Cash":
					jual_cash += payment.amount
				else:
					jual_kartu += payment.amount
			
			byk += 1
			
			# Point J - from POS Invoice (non-return)
			if pos_invoice in loyalty_points_map:
				point_j += loyalty_points_map[pos_invoice]

			if pos_inv.change_amount:
				jual_cash = jual_cash - pos_inv.change_amount

		
		# Handle Return Invoices
		return_invoices = return_invoice_map.get(pos_inv["custom_si_pos_no"], [])
		for ret_inv in return_invoices:
			payments = return_payments_map.get(ret_inv, [])
			for payment in payments:
				if payment["mode_of_payment"] == "Cash":
					retur_cash += payment["amount"]
				else:
					retur_kartu += payment["amount"]
			
			# Point R - from Return Sales Invoice
			if ret_inv in return_loyalty_points_map:
				point_r += return_loyalty_points_map[ret_inv]

		# Point J Redemption - dari field loyalty_points POS Invoice
		if pos_inv.is_return == 0 and hasattr(pos_inv, "loyalty_points"):
			point_j_redemption += pos_inv.loyalty_points or 0

		# === RETUR dari POS Invoice ===

		if pos_inv.is_return:
			payments = payments_map.get(pos_invoice, [])
			for payment in payments:
				amt = abs(payment.amount)  
				if payment.mode_of_payment == "Cash":
					new_retur_cash += amt
				else:
					new_retur_kartu += amt

	
	# Calculate Kas Akhir
	# kas_akhir = kas_awal + jual_cash - retur_cash 
	kas_akhir = kas_awal + jual_cash - new_retur_cash
	
	# Calculate Point
	point = point_j - point_r
	
	return {
		"nama_user": user_name,
		"kas_awal": kas_awal,
		"jual_cash": jual_cash,
		"jual_kartu": jual_kartu,
		"vch": 0,
		"retur_cash": new_retur_cash,
		"retur_kartu": new_retur_kartu,
		"kas_akhir": kas_akhir,
		"byk": byk,
		"point_j": point_j_redemption,
		"point_r": point_r,
		"point": point
	}
