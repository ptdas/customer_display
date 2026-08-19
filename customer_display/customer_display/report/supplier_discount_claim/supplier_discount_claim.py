import frappe


def execute(filters=None):
	filters = filters or {}

	columns = [
		{
			"label": "No.Nota",
			"fieldname": "no_nota",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
		{
			"label": "Tanggal",
			"fieldname": "tanggal",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": "Kode Barang",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": "Nama Barang",
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": "Byk",
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 80,
		},
		{
			"label": "Harga Jual",
			"fieldname": "harga_jual",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": "Disk Spl Rp",
			"fieldname": "diskon",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": "Jumlah",
			"fieldname": "jumlah",
			"fieldtype": "Currency",
			"width": 120,
		},
	]

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw("From Date dan To Date wajib diisi.")

	if filters.get("from_date") > filters.get("to_date"):
		frappe.throw(
			"From Date tidak boleh lebih besar dari To Date."
		)

	if not filters.get("company"):
		frappe.throw("Company wajib diisi.")

	company = frappe.db.get_value(
		"Company",
		filters.get("company"),
		["name", "lft", "rgt"],
		as_dict=True
	)

	if not company:
		frappe.throw("Company tidak ditemukan.")

	companies = frappe.get_all(
		"Company",
		filters={
			"lft": [">=", company.lft],
			"rgt": ["<=", company.rgt],
		},
		pluck="name"
	)

	if not companies:
		companies = [company.name]

	data = frappe.db.sql("""
		SELECT
			child.no_nota,
			child.tanggal,
			child.item_code,
			child.item_name,
			child.qty,
			child.harga_jual,
			child.diskon,
			child.jumlah
		FROM `tabSupplier Discount Claim Item` child
		INNER JOIN `tabSupplier Discount Claim` parent
			ON parent.name = child.parent
		INNER JOIN `tabSales Invoice` si
			ON si.name = child.no_nota
		WHERE
			parent.docstatus = 1
			AND child.tanggal BETWEEN %(from_date)s
				AND %(to_date)s
			AND si.company IN %(companies)s
		ORDER BY
			child.tanggal,
			child.no_nota,
			child.idx
	""", {
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"companies": tuple(companies),
	}, as_dict=True)

	return columns, data