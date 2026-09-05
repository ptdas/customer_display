import frappe

from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	AccountsReceivableSummary,
)


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}

	columns, data = AccountsReceivableSummary(filters).run(args)

	# Tambahkan Vendor Name dan Customer Name setelah Party
	columns.insert(
		2,
		{
			"label": "Vendor Name",
			"fieldname": "vendor_name",
			"fieldtype": "Data",
			"width": 120,
		},
	)

	columns.insert(
		3,
		{
			"label": "Customer Name",
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 120,
		},
	)

	# Kumpulkan Supplier dan Customer berdasarkan Party Type
	supplier_names = list({
		row.get("party")
		for row in data
		if row.get("party_type") == "Supplier" and row.get("party")
	})

	customer_names = list({
		row.get("party")
		for row in data
		if row.get("party_type") == "Customer" and row.get("party")
	})

	# Mapping Supplier
	supplier_map = {}

	if supplier_names:
		supplier_map = dict(
			frappe.db.get_all(
				"Supplier",
				filters={
					"name": ["in", supplier_names],
				},
				fields=[
					"name",
					"supplier_name",
				],
				as_list=True,
			)
		)

	# Mapping Customer
	customer_map = {}

	if customer_names:
		customer_map = dict(
			frappe.db.get_all(
				"Customer",
				filters={
					"name": ["in", customer_names],
				},
				fields=[
					"name",
					"customer_name",
				],
				as_list=True,
			)
		)

	# Isi nama sesuai Party Type
	for row in data:
		row["vendor_name"] = ""
		row["customer_name"] = ""

		party = row.get("party")
		party_type = row.get("party_type")

		if party_type == "Supplier":
			row["vendor_name"] = supplier_map.get(party, "")

		elif party_type == "Customer":
			row["customer_name"] = customer_map.get(party, "")

	return columns, data