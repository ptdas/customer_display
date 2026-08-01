import frappe
from frappe.utils import get_first_day, get_last_day, today

def execute(filters=None):
	if not filters:
		filters = {}
	
	parent_company = filters.get("parent_company")
	from_date = filters.get("from_date") or get_first_day(today())
	to_date = filters.get("to_date") or get_last_day(today())
	
	allowed_companies = []
	if parent_company:
		allowed_companies = frappe.get_all(
			"Company",
			filters={"parent_company": parent_company},
			pluck="name"
		)
		allowed_companies.append(parent_company)
	
	conditions = "1=1"
	values = []
	
	if allowed_companies:
		placeholders = ", ".join(["%s"] * len(allowed_companies))
		conditions += f" AND si.company IN ({placeholders})"
		values.extend(allowed_companies)
	
	conditions += " AND si.posting_date BETWEEN %s AND %s"
	values.extend([from_date, to_date])
	
	data = frappe.db.sql(f"""
		SELECT
			sii.item_code,
			sii.item_name,
			SUM(sii.qty) AS qty_sales,
			SUM(sii.amount) AS amount,
			ts.supplier_name AS vendor
		FROM `tabSales Invoice Item` sii
		JOIN `tabSales Invoice` si ON si.name = sii.parent
		LEFT JOIN `tabItem` i ON i.item_code = sii.item_code
		LEFT JOIN `tabSupplier` ts on ts.name = i.custom_vendor
		WHERE si.docstatus = 1
		AND {conditions}
		GROUP BY sii.item_code, sii.item_name, i.custom_vendor
		ORDER BY sii.item_code
	""", tuple(values), as_dict=1)
	
	# Calculate total amount
	total_amount = sum(row.get("amount", 0) for row in data)
	total_qty_sales = sum(row.get("qty_sales", 0) for row in data)
	
	# Insert total row at the top
	total_row = {
		"item_code": "",
		"item_name": "<b>Total</b>",
		"qty_sales": total_qty_sales,
		"amount": total_amount,
		"vendor": ""
	}
	
	data.insert(0, total_row)
	
	return get_columns(), data

def get_columns():
	return [
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": "Qty Sales", "fieldname": "qty_sales", "fieldtype": "Float", "width": 100},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": "Vendor", "fieldname": "vendor", "fieldtype": "Data", "width": 150},
	]