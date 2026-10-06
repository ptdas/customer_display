import frappe
from frappe import _

from frappe.utils import flt, today
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
	
	valuation_rate = frappe.db.get_value(
		"Bin",
		{"item_code": item.item_code, "warehouse": warehouse},
		"valuation_rate"
	) or 0

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
		"valuation_rate": valuation_rate,
		"allow_zero_valuation_rate": 1,
	})

	se.insert(ignore_permissions=True)
	se.submit()


@frappe.whitelist()
def debug_stock():
	# split_pos_invoice(frappe.get_doc("POS Invoice","BJM26A120007"),"validate")
    test = get_stock_availability("8993883950482", "TOKO - A")
    print(test)

def apply_custom_charge_to_pos_invoice(doc, method=None):
    pos = doc  
    pos_settings = frappe.get_single("AXTRA Settings")
    pos_charge_account = pos_settings.pos_charge_account

    if not pos.payments:
        return

    total_custom_charge = 0.0

    for p in pos.payments:
        if p.custom_charge_percent:
            charge_amount = flt(p.amount / 100) * flt(str(p.custom_charge_percent).replace(",","."))
            # frappe.db.set_value(p.doctype, p.name, "custom_charge_card", charge_amount)
            p.custom_charge_card = charge_amount
            p.base_amount = p.base_amount+charge_amount
            p.amount = p.amount+charge_amount
            total_custom_charge += charge_amount

    if total_custom_charge > 0 and pos_charge_account:
        company_doc = frappe.get_doc("Company", pos.company)
        account_head, cost_center = replace_account_cost_center_abbr(
            pos_charge_account,
            company_doc.cost_center,
            pos.company
        )

        pos.append("taxes", {
            "charge_type": "Actual",
            "account_head": account_head,
            "description": "POS Charge",
            "tax_amount": total_custom_charge,
            "cost_center": cost_center,
            "included_in_print_rate": 0,
        })

    pos.flags.ignore_mandatory = True
    pos.calculate_taxes_and_totals()
    pos.flags.ignore_mandatory = False

    return total_custom_charge

@frappe.whitelist()
def split_pos_invoice(doc, method):

    pos = frappe.get_doc("POS Invoice", doc.name)

    if getattr(pos, "is_return", 0) == 1:
        frappe.logger().info(f"Split POS Invoice tidak dijalankan karena ini return: {pos.name}")
        return

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

    parent_company = frappe.db.sql(""" SELECT name FROM `tabCompany` WHERE (parent_company = "" OR parent_company IS NULL) and is_group = 1 and name = "{}" """.format(pos_profile.custom_cabang))[0][0]
    children = frappe.get_all(
        "Company",
        filters={"parent_company": parent_company},
        fields=["name"],
        order_by="name asc"
    )

    order_map = {c.name: idx + 1 for idx, c in enumerate(children)}

    prefix = pos_profile.warehouse.split(" - ")[0]
    child_company_names = [c.name for c in children]

    matching_wh = frappe.get_all(
        "Warehouse",
        filters={
            "name": ["like", f"{prefix} - %"],
            "company": ["in", child_company_names]
        },
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
                
                # Harga dari POS sudah final
                "ignore_pricing_rule": 1,
                
                "redeem_loyalty_points": 1 if loyalty_used else 0,
                "loyalty_points": 0,
                "cost_center": frappe.get_doc("Company", company).cost_center,
                "discount_amount": pos.discount_amount,
                "apply_discount_on": pos.apply_discount_on,
                "set_posting_time": 1,
            })

            debit_to = replace_account_cost_center_abbr(pos.debit_to, "", si.company)
            si.debit_to = debit_to

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
                    if not template_name:
                        frappe.throw(
                            f"Sales Taxes and Charges Template tidak ditemukan untuk Company <b>{company}</b> dengan Title <b>{title}</b>.<br>"
                            f"Template asal POS: <b>{pos.taxes_and_charges}</b>"
                        )

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
                else:
                    account_head = tax.account_head
                    cost_center = tax.cost_center

                account_head, cost_center = replace_account_cost_center_abbr(account_head, cost_center, si.company)

                si.append("taxes", {
                    "charge_type": tax.charge_type,
                    "account_head": account_head,
                    "description": tax.description,
                    "rate": tax.rate,
                    "tax_amount": 0,
                    "cost_center": cost_center,
                    "included_in_print_rate": tax.included_in_print_rate
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
                "price_list_rate": item.price_list_rate,
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
                # "qty": allocate_qty,
                "qty" : remaining_qty,
                "rate": item.rate,
                "price_list_rate": item.price_list_rate,
                "uom": item.uom,
                # "warehouse": wh,
                "warehouse":  last_wh,
                "custom_handled_by_spg": item.custom_handled_by_spg
            })

    for si in invoices.values():
        if not si.items:
            continue

        for itm in si.items:
            itm_doc = frappe.get_doc("Item", itm.item_code)
            if itm_doc.is_stock_item:
                create_stock_entry_for_zero_stock(itm, itm.warehouse, si.company)

        #tambahan gata
        si.is_pos = 1
        si.flags.ignore_mandatory = True
        si.calculate_taxes_and_totals()
        si.flags.ignore_mandatory = False
        ####################

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
                        parts = base_account.rsplit(" - ", 1)

                        if len(parts) == 2:
                            new_account = f"{parts[0]} - {abbr}"
                        else:
                            new_account = base_account

                        si.set("loyalty_redemption_account", new_account)

        
        si.update_stock = 1
        si.insert(ignore_permissions=True)

    # if total_pos_amount and pos.payments:
    if total_pos_amount and pos.payments and not pos.custom_is_b2b:
        # frappe.throw("Erro1r")
        si_list = []
        for si in invoices.values():
            # si.reload()
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

                # frappe.errprint({ "mop": p.mode_of_payment, "company": si_doc.company, "account": account, "account_type": frappe.db.get_value("Account", account, "account_type") })

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
        # if si.outstanding_amount > 0 :
        # 	frappe.throw(str(si.as_json()))
        si.reload()
        # frappe.errprint(str({ "si": si.name, "customer": si.customer, "debit_to": si.debit_to, "payments": [{"mop": p.mode_of_payment, "account": p.account} for p in si.payments] }))
        si.submit()


def replace_account_cost_center_abbr(account_head, cost_center, company):
    abbr = frappe.db.get_value("Company", company, "abbr")

    if account_head:
        parts = account_head.rsplit(" - ", 1)
        if len(parts) == 2:
            account_head = f"{parts[0]} - {abbr}"

    if cost_center:
        parts = cost_center.rsplit(" - ", 1)
        if len(parts) == 2:
            cost_center = f"{parts[0]} - {abbr}"

    return account_head, cost_center

@frappe.whitelist()
def get_item_prices(item_code=None, barcode=None):
    if not item_code and not barcode:
        return None

    if barcode and not item_code:
        item_code = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
        if not item_code:
            return None

    if not frappe.db.exists("Item", item_code):
        return None

    item = frappe.get_doc("Item", item_code)

    main_barcode = frappe.db.get_value("Item Barcode", {"parent": item_code}, "barcode")
    item_group = item.item_group
    item_brand = item.brand
    posting_date = today()

    def get_price(price_list):
        return flt(
            frappe.db.get_value(
                "Item Price",
                {"item_code": item_code, "price_list": price_list, "selling": 1},
                "price_list_rate",
            ) or 0
        )

    rules = frappe.db.sql(
        """
        SELECT DISTINCT
            ic.item_code AS ic_item_code,
            pr.name AS pricing_rule,
            pr.price_or_product_discount,
            pr.priority,
            pr.discount_percentage,
            pr.discount_amount,
            pr.free_item,
            pr.min_qty,
            pr.max_qty,
            pr.valid_from,
            pr.valid_upto,
            pr.company,
            ib.brand AS brand_rule
        FROM `tabPricing Rule` pr
        LEFT JOIN `tabPricing Rule Item Code` ic ON ic.parent = pr.name
        LEFT JOIN `tabPricing Rule Item Group` ig ON ig.parent = pr.name
        LEFT JOIN `tabPricing Rule Brand` ib ON ib.parent = pr.name
        WHERE pr.disable = 0
          AND pr.selling = 1
          AND (%(posting_date)s BETWEEN IFNULL(pr.valid_from, %(posting_date)s)
                                    AND IFNULL(pr.valid_upto, %(posting_date)s))
          AND (
               ic.item_code = %(item_code)s
               OR ig.item_group = %(item_group)s
               OR ib.brand = %(brand)s
          )
        ORDER BY pr.priority ASC
        """,
        {"item_code": item_code, "item_group": item_group, "brand": item_brand, "posting_date": posting_date},
        as_dict=True,
    )

    pricing_rules = []
    for r in rules:
        row = {
            "pricing_rule": r.pricing_rule,
            "price_or_product_discount": r.price_or_product_discount,
            "priority": r.priority,
            "discount_percentage": flt(r.discount_percentage),
            "discount_amount": flt(r.discount_amount),
            "free_item": r.free_item,
            "min_qty": r.min_qty,
            "max_qty": r.max_qty,
            "valid_from": r.valid_from,
            "valid_upto": r.valid_upto,
            "company": r.company,
            "is_applied": False,
            "item_code": r.ic_item_code or item_code,  
        }
        pricing_rules.append(row)

    return {
        "item_code": item_code,
        "item_name": item.item_name,
        "barcode": main_barcode,
        "retail": get_price("Retail"),
        "grosir": get_price("Grosir"),
        "marketplace": get_price("Marketplace"),
        "pricing_rules": pricing_rules,
    }


#######################################


@frappe.whitelist()
def search_items_dialog(search, limit=10):

    search = search.strip()
    if not search:
        return []

    try:
        limit = int(limit)
    except ValueError:
        limit = 100

    items = frappe.db.sql("""
        SELECT name AS item_code, item_name, brand, item_group
        FROM `tabItem`
        WHERE disabled = 0
          AND (name LIKE %(s)s
               OR item_name LIKE %(s)s
               OR EXISTS (
                   SELECT 1 FROM `tabItem Barcode` ib
                   WHERE ib.barcode LIKE %(s)s AND ib.parent = tabItem.name
               ))
        LIMIT %(limit)s
    """, {"s": f"%{search}%", "limit": limit}, as_dict=True)

    results = []
    posting_date = today()
    for item in items:

        def get_price(price_list):
            return flt(frappe.db.get_value("Item Price",
                                           {"item_code": item.item_code, "price_list": price_list, "selling": 1},
                                           "price_list_rate") or 0)
		
        rules = frappe.db.sql("""
            SELECT DISTINCT
                ic.item_code AS ic_item_code,
                pr.name AS pricing_rule,
                pr.price_or_product_discount,
				pr.custom_sumber_pricing_rule,
                pr.priority,
                pr.discount_percentage,
                pr.discount_amount,
                pr.free_item,
                pr.min_qty,
                pr.max_qty,
                pr.valid_from,
                pr.valid_upto,
                pr.company,
                ib.brand AS brand_rule
            FROM `tabPricing Rule` pr
            LEFT JOIN `tabPricing Rule Item Code` ic ON ic.parent = pr.name
            LEFT JOIN `tabPricing Rule Item Group` ig ON ig.parent = pr.name
            LEFT JOIN `tabPricing Rule Brand` ib ON ib.parent = pr.name
            WHERE pr.disable = 0
              AND pr.selling = 1
              AND (%(posting_date)s BETWEEN IFNULL(pr.valid_from, %(posting_date)s)
                                        AND IFNULL(pr.valid_upto, %(posting_date)s))
              AND (
                   ic.item_code = %(item_code)s
                   OR ig.item_group = %(item_group)s
                   OR ib.brand = %(brand)s
              )
            ORDER BY pr.priority ASC
        """, {"item_code": item.item_code, "item_group": item.item_group, "brand": item.brand,
              "posting_date": posting_date}, as_dict=True)

        pricing_rules = []
        for r in rules:
            pricing_rules.append({
                "pricing_rule": r.pricing_rule,
				"sumber": r.custom_sumber_pricing_rule,
                "price_or_product_discount": r.price_or_product_discount,
                "priority": r.priority,
                "discount_percentage": flt(r.discount_percentage),
                "discount_amount": flt(r.discount_amount),
                "free_item": r.free_item,
                "min_qty": r.min_qty,
                "max_qty": r.max_qty,
                "valid_from": r.valid_from,
                "valid_upto": r.valid_upto,
                "company": r.company,
                "is_applied": False,
                "item_code": r.ic_item_code or item.item_code,
            })

        results.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "retail": get_price("Retail"),
            "grosir": get_price("Grosir"),
            "marketplace": get_price("Marketplace"),
            "pricing_rules": pricing_rules,
        })

    return results


def set_grosir_price_list(doc, method):
    if not doc.custom_is_grosir_mode:
        return
	
    doc.selling_price_list = "Grosir"


########### handle return invoice #####################################

def handle_pos_return(doc, method):
    if not doc.is_return:
        return

    if not doc.custom_si_pos_no or not doc.custom_si_pos_id:
        frappe.throw("POS Return tidak punya custom_si_pos_no / id")

    for item in doc.items:
        allocate_return_qty(
            pos_no=doc.custom_si_pos_no,
            pos_id=doc.custom_si_pos_id,
            item_code=item.item_code,
            return_qty=abs(flt(item.qty)),
            pos_return=doc
        )

def allocate_return_qty(pos_no, pos_id, item_code, return_qty, pos_return):

    print(item_code)
    sales_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "custom_si_pos_no": pos_no,
            "custom_si_pos_id": pos_id,
            "is_return": 0,
            "docstatus": 1
        },
        order_by="posting_date asc",
        pluck="name"
    )

    print(sales_invoices)

    remaining = return_qty
    print(remaining)
    for si_name in sales_invoices:
        if remaining <= 0:
            break

        available = get_available_qty_return(si_name, item_code)
        print(si_name)
        print(available)

        if available <= 0:
            continue

        take = min(available, remaining)

        create_return_si(
            original_si=si_name,
            item_code=item_code,
            qty=take,
            pos_return=pos_return
        )

        remaining -= take

    if remaining > 0:
        frappe.throw(
            f"Qty return item {item_code} ({return_qty}) "
            f"melebihi sisa yang bisa di-return"
        )


def get_available_qty_return(si_name, item_code):
    original = frappe.db.sql("""
        SELECT qty
        FROM `tabSales Invoice Item`
        WHERE parent=%s AND item_code=%s
    """, (si_name, item_code), as_dict=True)

    print(original)
	
    if not original:
        return 0

    original_qty = flt(original[0].qty)

    returned = frappe.db.sql("""
        SELECT ABS(SUM(sii.qty)) AS qty
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.is_return = 1
          AND si.return_against = %s
          AND sii.item_code = %s
          AND si.docstatus = 1
    """, (si_name, item_code), as_dict=True)

    returned_qty = flt(returned[0].qty) if returned and returned[0].qty else 0

    return original_qty - returned_qty

def create_return_si(original_si, item_code, qty, pos_return):
    ori = frappe.get_doc("Sales Invoice", original_si)

    si = frappe.new_doc("Sales Invoice")
    si.is_return = 1
    si.return_against = original_si

    si.company = ori.company
    si.customer = ori.customer
    si.posting_date = pos_return.posting_date
    si.set_posting_time = 1

    # carry POS identity
    si.custom_si_pos_no = ori.custom_si_pos_no
    si.custom_si_pos_id = ori.custom_si_pos_id

    ori_item = next(i for i in ori.items if i.item_code == item_code)

    print("=== RETURN SI DEBUG ===")
    print("NEW SI DEBIT TO :", si.debit_to)
    print("RETURN AGAINST  :", si.return_against)

    orig = frappe.get_doc("Sales Invoice", si.return_against)
    print("ORIG SI DEBIT TO:", orig.debit_to)

    si.append("items", {
        "item_code": item_code,
        "qty": -qty,
        "rate": ori_item.rate,
        "warehouse": ori_item.warehouse,
        "income_account": ori_item.income_account,
        "cost_center": ori_item.cost_center
    })

    si.flags.ignore_permissions = True
    si.insert()
    si.submit()

def test():
    # pos_invoice_ret = "RBJB26A260001"
    # item_code = "TPT7171"
    # hasil = get_available_qty_return(pos_invoice_ret, item_code)
    # print(hasil)

    doc = frappe.get_doc("POS Invoice", "RBJB26A260001")
	
    handle_pos_return(doc,None)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def pos_profile_query_bjb_bjm(doctype, txt, searchfield, start, page_len, filters):
    user = frappe.session.user
    company = filters.get("company") if filters else None

    companies = [company] if company else ["BJB", "BJM"]

    return frappe.db.sql(
        """
        select p.name
        from `tabPOS Profile` p
        inner join `tabPOS Profile User` u on u.parent = p.name
        where u.user = %(user)s
          and p.company in %(companies)s
          and p.name like %(txt)s
        order by p.name
        limit %(start)s, %(page_len)s
        """,
        {
            "user": user,
            "companies": tuple(companies),
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )