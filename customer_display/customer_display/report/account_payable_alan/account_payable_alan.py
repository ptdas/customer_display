# Copyright (c) 2015, Frappe Technologies, Inc. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
	ReceivablePayableReport,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})

	filters.setdefault("range1", 30)
	filters.setdefault("range2", 60)
	filters.setdefault("range3", 90)
	filters.setdefault("range4", 120)

	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}

	result = ReceivablePayableReport(filters).run(args)

	columns = result[0]
	data = result[1]

	# =========================================================
	# Tambahkan Vendor Name dan Customer Name
	# =========================================================

	columns.insert(
		3,
		{
			"label": "Vendor Name",
			"fieldname": "vendor_name",
			"fieldtype": "Data",
			"width": 150,
		},
	)

	columns.insert(
		4,
		{
			"label": "Customer Name",
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 150,
		},
	)

	# =========================================================
	# Ambil semua Supplier dan Customer dari data report
	# =========================================================

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

	# =========================================================
	# Mapping Supplier
	# =========================================================

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

	# =========================================================
	# Mapping Customer
	# =========================================================

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

	# =========================================================
	# Isi Vendor Name / Customer Name
	# =========================================================

	for row in data:
		row["vendor_name"] = ""
		row["customer_name"] = ""

		party = row.get("party")
		party_type = row.get("party_type")

		if party_type == "Supplier":
			row["vendor_name"] = supplier_map.get(party, "")

		elif party_type == "Customer":
			row["customer_name"] = customer_map.get(party, "")

	# =========================================================
	# Kembalikan seluruh hasil report
	# =========================================================

	return (columns, data, *result[2:])