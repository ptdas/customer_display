import frappe
from frappe.utils import flt, nowdate

# sedang tidak dipakai
def on_vendor_change_transfer_stock(doc, method):
	prev_vendor = doc.get_db_value("custom_vendor")
	new_vendor = doc.custom_vendor

	if not prev_vendor or not new_vendor or prev_vendor == new_vendor:
		return

	old_company = frappe.db.get_value("Supplier", prev_vendor, "custom_vendor_company")
	new_company = frappe.db.get_value("Supplier", new_vendor, "custom_vendor_company")

	if not old_company or not new_company or old_company == new_company:
		return

	old_abbr = frappe.db.get_value("Company", old_company, "abbr")
	new_abbr = frappe.db.get_value("Company", new_company, "abbr")
	
	bin_list = frappe.get_all("Bin", 
		filters={
			"item_code": doc.name,
			"actual_qty": [">", 0],
			"warehouse": ["like", f"% - {old_abbr}"]
		},
		fields=["warehouse", "actual_qty", "valuation_rate"]
	)

	if not bin_list:
		frappe.throw(f"No stock found in any warehouse of {old_company} for item {doc.name}")

	for bin in bin_list:
		source_wh = bin.warehouse
		qty = flt(bin.actual_qty)
		rate = flt(bin.valuation_rate)

		base_wh = source_wh.rsplit(" - ", 1)[0]
		target_wh = f"{base_wh} - {new_abbr}"

		if not frappe.db.exists("Warehouse", target_wh):
			frappe.throw(f"Target warehouse {target_wh} does not exist in company {new_company}")

		# Material Issue
		issue = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": old_company,
			"posting_date": nowdate(),
			"items": [{
				"item_code": doc.name,
				"qty": qty,
				"s_warehouse": source_wh,
				"valuation_rate": rate,
			}]
		})
		issue.insert()
		issue.submit()

		# Material Receipt
		receipt = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": new_company,
			"posting_date": nowdate(),
			"items": [{
				"item_code": doc.name,
				"qty": qty,
				"t_warehouse": target_wh,
				"valuation_rate": rate,
			}]
		})
		receipt.insert()
		receipt.submit()

		frappe.msgprint(f"Transferred {qty} of {doc.name} from {source_wh} → {target_wh} at rate {rate}")