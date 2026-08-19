import frappe
from frappe.model.naming import make_autoname
from datetime import datetime

# @frappe.whitelist()
# def autoname_purchase(doc, method):
# 	company = frappe.get_doc("Company", doc.company)
# 	abbr = company.custom_document_abbr or "XXXXX"
	
# 	day_of_year = datetime.now().timetuple().tm_yday
# 	ddd = f"{day_of_year:03}"

# 	yy = datetime.now().strftime("%y")

# 	if doc.doctype == "Purchase Invoice":
# 		if doc.is_return == 0:
# 			series_key = f"PI-{abbr}{ddd}{yy}."
# 		else:
# 			series_key = f"PR-{abbr}{ddd}{yy}."

# 	elif doc.doctype == "Purchase Receipt":
# 		series_key = f"PT-{abbr}{ddd}{yy}."

# 	elif doc.doctype == "Purchase Order":
# 		series_key = f"PO-{abbr}{ddd}{yy}."


# 	elif doc.doctype == "Sales Invoice":
# 		if doc.is_return == 0:
# 			series_key = f"SI-{abbr}{ddd}{yy}."
# 		else:
# 			series_key = f"SR-{abbr}{ddd}{yy}."

# 	elif doc.doctype == "Delivery Note":
# 		series_key = f"DN-{abbr}{ddd}{yy}."

# 	elif doc.doctype == "Sales Order":
# 		series_key = f"SO-{abbr}{ddd}{yy}."


# 	doc.name = make_autoname(series_key + "#####")  # 5-digit counter


@frappe.whitelist()
def autoname_purchase(doc, method):
	company = frappe.get_doc("Company", doc.company)
	abbr = company.custom_document_abbr or "XXXXX"

	yy = datetime.now().strftime("%y")
	mm = datetime.now().strftime("%m")

	series_key = None

	if doc.doctype == "Purchase Invoice":
		if doc.is_return:
			series_key = f"PR-{abbr}{yy}{mm}."
		else:
			series_key = f"PI-{abbr}{yy}{mm}."

	elif doc.doctype == "Purchase Receipt":
		series_key = f"PT-{abbr}{yy}{mm}."

	elif doc.doctype == "Purchase Order":
		series_key = f"PO-{abbr}{yy}{mm}."

	elif doc.doctype == "Sales Invoice":
		if doc.is_return:
			series_key = f"SR-{abbr}{yy}{mm}."
		else:
			series_key = f"SI-{abbr}{yy}{mm}."

	elif doc.doctype == "Delivery Note":
		series_key = f"DN-{abbr}{yy}{mm}."

	elif doc.doctype == "Sales Order":
		series_key = f"SO-{abbr}{yy}{mm}."

	if series_key:
		doc.name = make_autoname(series_key + "#####")