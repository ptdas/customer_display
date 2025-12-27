import frappe
from frappe import _

from frappe.utils import flt
from frappe.utils import add_to_date


@frappe.whitelist()
def get_stock_availability(item_code, warehouse):
	prefix = warehouse.split(" - ")[0]
	matching_wh = frappe.get_all(
		"Warehouse",
		filters={"name": ["like", f"{prefix} - %"]},
		pluck="name"
	)
	if warehouse not in matching_wh:
		matching_wh.append(warehouse)

	total_qty = frappe.db.sql(
		"""
		SELECT SUM(actual_qty)
		FROM `tabBin`
		WHERE item_code = %s
		  AND warehouse IN ({})
		""".format(", ".join(["%s"] * len(matching_wh))),
		[item_code] + matching_wh,
		as_list=1
	)
	total_qty = flt(total_qty[0][0]) if total_qty and total_qty[0][0] is not None else 0

	is_stock_item = frappe.get_value("Item", item_code, "is_stock_item") or 0

	return total_qty, bool(is_stock_item)


def create_stock_entry_for_zero_stock(item, warehouse, company):
	stock_qty = frappe.db.get_value("Bin", {"item_code": item.item_code, "warehouse": warehouse}, "actual_qty") or 0
	if stock_qty > 0:
		return

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Receipt"
	se.company = company
	se.set_warehouse = warehouse
	se.custom_from_pos_recon = 1

	se.posting_date = frappe.utils.nowdate()
	se.posting_time = add_to_date(frappe.utils.nowtime(), seconds=-1)

	se.append("items", {
		"item_code": item.item_code,
		"qty": item.qty,
		"t_warehouse": warehouse,
		"uom": item.uom,
		"stock_uom": item.uom,
		"conversion_factor": item.conversion_factor or 1,
	})
	se.insert(ignore_permissions=True)
	se.submit()

@frappe.whitelist()
def debug_split():
	split_pos_invoice(frappe.get_doc("POS Invoice","ACC-PSINV-2025-00105"),"validate")

@frappe.whitelist()
def split_pos_invoice(doc, method):
	pos = frappe.get_doc("POS Invoice", doc.name)
	pos_profile = frappe.get_doc("POS Profile", pos.pos_profile)

	total_pos_amount   = flt(pos.grand_total or 0.0)
	total_loyalty_amt  = flt(getattr(pos, "loyalty_amount", 0))
	loyalty_used       = total_loyalty_amt > 0

	if getattr(pos, "loyalty_program", None):
		loyalty_program_name = pos.loyalty_program
	else:
		loyalty_program_name = frappe.db.get_value(
			"Customer", pos.customer, "loyalty_program"
		)

	parent_company = frappe.db.sql(""" SELECT name FROM `tabCompany` WHERE (parent_company = "" OR parent_company IS NULL) and is_group = 1 """)[0][0]
	children = frappe.get_all(
		"Company",
		filters={"parent_company": parent_company},
		fields=["name"],
		order_by="name asc"
	)

	order_map = {c.name: idx + 1 for idx, c in enumerate(children)}

	prefix = pos_profile.warehouse.split(" - ")[0]
	matching_wh = frappe.get_all(
		"Warehouse",
		filters={"name": ["like", f"{prefix} - %"]},
		fields=["name", "company"]
	)
	matching_wh = sorted(
		matching_wh,
		key=lambda d: (
			order_map.get(d["company"], len(order_map) + 1),
			d["company"]
		)
	)
	wh_company_list = [(d.name, d.company) for d in matching_wh]

	invoices = {}
	def get_invoice(company):
		if company not in invoices:
			si = frappe.new_doc("Sales Invoice")
			si.update({
				"custom_si_pos_id": pos.custom_si_pos_id,
				"custom_si_pos_no": pos.custom_si_pos_no,
				"custom_is_b2b": pos.custom_is_b2b,
				"custom_alamat_b2b": pos.custom_alamat_b2b,
				"custom_minta_faktur": pos.custom_minta_faktur,
				"company": company,
				"customer": pos.customer,
				"posting_date": pos.posting_date,
				"due_date": pos.due_date or pos.posting_date,
				"currency": pos.currency,
				"price_list": pos.selling_price_list,
				"redeem_loyalty_points": 1 if loyalty_used else 0,
				"loyalty_points": 0,
				"cost_center": frappe.get_doc("Company", company).cost_center,
				"discount_amount": pos.discount_amount,
				"apply_discount_on": pos.apply_discount_on,
				"set_posting_time": 1
			})

			#tambahan gata
			for tax in pos.taxes:
				if pos.taxes_and_charges:
					print(pos.taxes_and_charges)
					title = frappe.get_value("Sales Taxes and Charges Template", pos.taxes_and_charges, 'title')

					template_name = frappe.db.get_value(
						"Sales Taxes and Charges Template",
						{
							"title": title,
							"company": company
						},
						"name"
					)
					print(template_name)
					stc_doc = frappe.get_doc("Sales Taxes and Charges Template", template_name)
					account_head = None
					cost_center = None
					for row in stc_doc.taxes:
						if row.charge_type == tax.charge_type and row.description == tax.description:
							account_head = row.account_head
							cost_center = row.cost_center
							break
				else:
					account_head = tax.account_head
					cost_center = tax.cost_center

				si.append("taxes", {
					"charge_type": tax.charge_type,
					"account_head": account_head,
					"description": tax.description,
					"rate": tax.rate,
					"tax_amount": 0,
					"cost_center": cost_center
				})
			################

			invoices[company] = si
		return invoices[company]

	for item in pos.items:
		remaining_qty = flt(item.qty)
		for wh, company in wh_company_list:
			if remaining_qty <= 0:
				break

			bin_qty = flt(
				frappe.db.get_value(
					"Bin",
					{"item_code": item.item_code, "warehouse": wh},
					"actual_qty"
				) or 0.0
			)
			allocate_qty = min(bin_qty, remaining_qty)
			if allocate_qty <= 0:
				continue

			si = get_invoice(company)
			si.is_pos = 1
			si.pos_profile = pos.pos_profile
			si.append("items", {
				"item_code": item.item_code,
				"qty": allocate_qty,
				"rate": item.rate,
				"uom": item.uom,
				"warehouse": wh,
				"custom_handled_by_spg": item.custom_handled_by_spg
			})
			remaining_qty -= allocate_qty

		if remaining_qty > 0 and wh_company_list:
			last_wh, last_company = wh_company_list[-1]
			si = get_invoice(last_company)
			si.append("items", {
				"item_code": item.item_code,
				"qty": remaining_qty,
				"rate": item.rate,
				"uom": item.uom,
				"warehouse": last_wh,
				"custom_handled_by_spg": item.custom_handled_by_spg
			})

	for si in invoices.values():
		if not si.items:
			continue

		for itm in si.items:
			itm_doc = frappe.get_doc("Item", itm.item_code)
			if itm_doc.is_stock_item:
				create_stock_entry_for_zero_stock(itm, itm.warehouse, si.company)

		if loyalty_used and total_pos_amount > 0:
			si.flags.ignore_mandatory = True
			si.calculate_taxes_and_totals()
			si.flags.ignore_mandatory = False

			share_pts = int(round(total_loyalty_amt * (si.grand_total / total_pos_amount)))
			if share_pts > 0:
				si.set("loyalty_amount", share_pts)

				if loyalty_program_name:
					lp = frappe.get_doc("Loyalty Program", loyalty_program_name)
					base_account = lp.expense_account  
					si.set("loyalty_points", share_pts / lp.conversion_factor)

					if base_account:
						abbr = frappe.db.get_value("Company", si.company, "abbr")
						parts = base_account.split(" - ", 1)

						if len(parts) == 2:
							new_account = f"{parts[0]} - {abbr}"
						else:
							new_account = base_account

						si.set("loyalty_redemption_account", new_account)

		#tambahan gata
		si.flags.ignore_mandatory = True
		si.calculate_taxes_and_totals()
		si.flags.ignore_mandatory = False
		####################

		si.update_stock = 1
		si.insert(ignore_permissions=True)
	
	if total_pos_amount and getattr(pos, "payments", None):
		si_list = []
		for si in invoices.values():
			si.reload()
			si_list.append({
				"doc": si,
				"grand_total": flt(si.grand_total),
				"outstanding": flt(si.outstanding_amount)
			})

		for p in pos.payments:
			orig_payment_amount = flt(p.amount)
			if orig_payment_amount <= 0:
				continue

			remaining_payment = orig_payment_amount
			for entry in si_list:
				si_doc = entry["doc"]
				si_gt = entry["grand_total"]
				si_out = entry["outstanding"]

				if si_out <= 0:
					continue

				proportion = (si_gt / total_pos_amount) if total_pos_amount else 0
				alloc = flt(orig_payment_amount * proportion, 2)
				alloc = min(alloc, si_out, remaining_payment)
				if alloc <= 0:
					continue

				account = frappe.db.get_value(
					"Mode of Payment Account",
					{
						"parent": p.mode_of_payment,
						"company": si_doc.company
					},
					"default_account"
				)
				if not account:
					frappe.throw(
						_("No Mode of Payment Account found for Mode {0} in Company {1}")
						.format(p.mode_of_payment, si_doc.company)
					)

				si_doc.append("payments", {
					"mode_of_payment": p.mode_of_payment,
					"account": frappe.db.get_value(
						"Mode of Payment Account",
						{"parent": p.mode_of_payment, "company": si_doc.company},
						"default_account"
					),
					"amount": alloc
				})
				si_doc.save()

				entry["outstanding"] = flt(si_out - alloc)
				remaining_payment = flt(remaining_payment - alloc)
				if remaining_payment <= 0:
					break

	for si in invoices.values():
		si.submit()