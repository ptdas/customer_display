
import frappe
from frappe.utils import getdate
from datetime import timedelta

def execute(filters=None):
	if not filters:
		filters = {}

	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	parent_company = filters.get("parent_company")

	companies = []
	if parent_company:
		companies.append(parent_company)
		child_companies = frappe.get_all(
			"Company",
			filters={"parent_company": parent_company},
			pluck="name"
		)
		companies.extend(child_companies)

	columns = [
		{"label": "User", "fieldname": "user", "fieldtype": "Data", "width": 160},
		{"label": "Pos Profile", "fieldname": "pos_profile", "fieldtype": "Data", "width": 160},
		{"label": "Kas Awal", "fieldname": "kas_awal", "fieldtype": "Currency", "width": 120},
		{"label": "Jual Cash", "fieldname": "jual_cash", "fieldtype": "Currency", "width": 120},
		{"label": "Jual Card", "fieldname": "jual_card", "fieldtype": "Currency", "width": 120},
		{"label": "Voucher", "fieldname": "voucher", "fieldtype": "Currency", "width": 80},
		{"label": "Retur Cash", "fieldname": "retur_cash", "fieldtype": "Currency", "width": 120},
		{"label": "Retur Kartu", "fieldname": "retur_kartu", "fieldtype": "Currency", "width": 120},
		{"label": "Kas Akhir", "fieldname": "kas_akhir", "fieldtype": "Currency", "width": 120},
		{"label": "Byk", "fieldname": "byk", "fieldtype": "Int", "width": 70},
	]

	data_map = {}

	filters_pos = {
		"docstatus": 1,
		"posting_date": ["between", [from_date, to_date]]
	}
	if companies:
		filters_pos["company"] = ["in", companies]

	closings = frappe.get_all(
		"POS Closing Entry",
		filters=filters_pos,
		fields=["name", "user", "pos_profile"]
	)

	if not closings:
		return columns, []

	for closing in closings:
		values = get_tutup_kasir(closing.name)

		byk = len(
			frappe.get_all(
				"POS Invoice Reference",
				filters={"parent": closing.name},
				pluck="pos_invoice"
			)
		)

		if closing.user not in data_map:
			data_map[closing.user] = {
				"user": closing.user,
				"pos_profile": closing.pos_profile,
				"kas_awal": 0,
				"jual_cash": 0,
				"jual_card": 0,
				"voucher": 0,
				"retur_cash": 0,
				"retur_kartu": 0,
				"kas_akhir": 0,
				"byk": 0
			}

		data_map[closing.user]["kas_awal"]    += values["kas_awal"]
		data_map[closing.user]["jual_cash"]   += values["jual_cash"]
		data_map[closing.user]["jual_card"]   += values["jual_card"]
		data_map[closing.user]["voucher"]     += values["voucher"]
		data_map[closing.user]["retur_cash"]  += values["retur_cash"]
		data_map[closing.user]["retur_kartu"] += values["retur_kartu"]
		data_map[closing.user]["kas_akhir"]   += values["kas_akhir"]

		data_map[closing.user]["byk"] += byk

	return columns, list(data_map.values())


def get_tutup_kasir(name):
	doc = frappe.get_doc("POS Closing Entry", name)

	result = {
		"kas_awal": 0,
		"jual_cash": 0,
		"jual_card": 0,
		"voucher": 0,
		"retur_cash": 0,
		"retur_kartu": 0,
		"kas_akhir": 0,
	}

	mop_cache = {}

	for row in doc.payment_reconciliation:
		result["kas_awal"] += row.opening_amount or 0

		mop = row.mode_of_payment
		if mop not in mop_cache:
			mop_cache[mop] = frappe.db.get_value(
				"Mode of Payment",
				mop,
				"custom_mop_type"
			)

		amount = (row.closing_amount or 0) - (row.opening_amount or 0)
		print(amount)

		if mop_cache[mop] == "Cash":
			result["jual_cash"] += amount
		elif mop_cache[mop] == "Bank":
			result["jual_card"] += amount
		elif mop_cache[mop] == "Voucher":
			result["voucher"] += amount

	total_change = 0 

	for row in doc.pos_transactions:
		pos_invoice = frappe.get_value(
			"POS Invoice",
			row.pos_invoice,
			["custom_si_pos_id", "custom_si_pos_no", "change_amount"],
			as_dict=True
		)

		if not pos_invoice:
			continue

		total_change += pos_invoice.change_amount

		sales_invoice = frappe.db.get_value(
			"Sales Invoice",
			{
				"custom_si_pos_id": pos_invoice.custom_si_pos_id,
				"custom_si_pos_no": pos_invoice.custom_si_pos_no,
			},
			"name"
		)

		if not sales_invoice:
			continue

		total_return = frappe.db.get_value(
			"Sales Invoice",
			{
				"is_return": 1,
				"return_against": sales_invoice
			},
			"SUM(grand_total)"
		) or 0

		if not total_return:
			continue

		mop = frappe.db.get_value(
			"Sales Invoice Payment",
			{"parent": sales_invoice},
			"mode_of_payment"
		)

		if mop == "Cash":
			result["retur_cash"] += total_return
		else:
			result["retur_kartu"] += total_return

	
	print(result["jual_cash"])
	print("total_change: " +str(total_change))

	result["jual_cash"] = result["jual_cash"] - total_change

	print(result["jual_cash"])

	result["kas_akhir"] = (
		result["kas_awal"]
		+ result["jual_cash"]
		- result["retur_cash"]
	)

	return result

