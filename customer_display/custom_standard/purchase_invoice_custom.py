
import frappe
import json
from frappe.utils import flt
from frappe.utils.data import today
from frappe.model.mapper import get_mapped_doc

def check_po_qty(doc,method):
	if doc.workflow_state != "Draft":
		return

	doc.custom_po_harga_beda = 0  # reset

	for item in doc.items:
		if item.purchase_order and item.po_detail:
			po_item = frappe.get_doc("Purchase Order Item", item.po_detail)
			if flt(item.qty) > flt(po_item.qty):
				doc.custom_po_harga_beda = 1
				doc.workflow_state = "PO PI Harga Beda"
				break

	doc.db_update()
	
def create_lcv_on_submit(doc, method=None):
    if not doc.update_stock:
        return

    if not doc.custom_lcv_total_taxes_and_charges or doc.custom_lcv_total_taxes_and_charges <= 0:
        return

    if not doc.custom_forwarder:
        frappe.throw("Forwarder LCV wajib diisi")

    items_with_charges = [i for i in doc.custom_lcv_item if i.applicable_charges > 0]
    if not items_with_charges:
        return

    pi_item_map = {}

    for pi_item in doc.items:
        key = (pi_item.item_code, pi_item.qty)

        if key in pi_item_map:
            frappe.throw(
                f"Duplikat item_code + qty di Purchase Invoice: {pi_item.item_code} qty {pi_item.qty}"
            )

        pi_item_map[key] = pi_item

    lcv = frappe.new_doc("Landed Cost Voucher")
    lcv.company = doc.company
    lcv.posting_date = doc.posting_date

    if (doc.custom_distribute_charges_based_on or "").lower() == "constant":
        lcv.distribute_charges_based_on = "Distribute Manually"
    else:
        lcv.distribute_charges_based_on = doc.custom_distribute_charges_based_on

    lcv.append("purchase_receipts", {
        "receipt_document_type": "Purchase Invoice",
        "receipt_document": doc.name,
        "supplier": doc.supplier,
        "posting_date": doc.posting_date,
        "grand_total": doc.grand_total
    })

    for item in items_with_charges:
        key = (item.item_code, item.qty)
        pi_item = pi_item_map.get(key)

        if not pi_item:
            frappe.throw(
                f"Purchase Invoice Item tidak ditemukan untuk {item.item_code} qty {item.qty}"
            )

        lcv.append("items", {
            "item_code": pi_item.item_code,
            "description": pi_item.description,
            "qty": pi_item.qty,
            "rate": pi_item.rate,
            "amount": pi_item.amount,
            "applicable_charges": item.applicable_charges,

            "receipt_document_type": "Purchase Invoice",
            "receipt_document": doc.name,
            "purchase_receipt_item": pi_item.name,

            "cost_center": pi_item.cost_center
        })

    for tax in doc.custom_landed_cost_taxes_and_charges:
        lcv.append("taxes", {
            "expense_account": tax.expense_account,
            "account_currency": tax.account_currency,
            "amount": tax.amount,
            "exchange_rate": tax.exchange_rate,
            "description": tax.description,
            "base_amount": tax.base_amount
        })

    lcv.insert(ignore_permissions=True)
    lcv.submit()

    frappe.msgprint(
        f"Landed Cost Voucher <b>{lcv.name}</b> berhasil dibuat dari Purchase Invoice <b>{doc.name}</b>"
    )



def set_total_taxes_and_charges(doc):
	total = 0.0
	for tax in doc.custom_landed_cost_taxes_and_charges:
		total += flt(tax.amount)
	doc.custom_lcv_total_taxes_and_charges = total

def set_applicable_charges_for_item(doc):
	if not doc.custom_landed_cost_taxes_and_charges:
		return

	based_on = (doc.custom_distribute_charges_based_on or "").lower()

	if based_on == "distribute manually":
		for item in doc.custom_lcv_item:
			item.applicable_charges = 0
	else:
		total_item_cost = 0.0
		for item in doc.custom_lcv_item:
			if based_on == "constant":
				total_item_cost += flt(item.constant or 0)
			elif based_on in ["qty", "amount"]:
				total_item_cost += flt(getattr(item, based_on, 0))

		if total_item_cost <= 0:
			return

		total_charges = flt(doc.custom_lcv_total_taxes_and_charges or 0)
		charges_accum = 0.0

		for item in doc.custom_lcv_item:
			if based_on == "constant":
				item_value = flt(item.constant or 0)
			else:
				item_value = flt(getattr(item, based_on, 0))

			item.applicable_charges = (item_value / total_item_cost) * total_charges
			item.applicable_charges = flt(item.applicable_charges, 2)  
			charges_accum += item.applicable_charges

		diff = total_charges - charges_accum
		if doc.custom_lcv_item:
			doc.custom_lcv_item[-1].applicable_charges += diff

def recalc_lcv(doc, method=None):
	set_total_taxes_and_charges(doc)
	set_applicable_charges_for_item(doc)

@frappe.whitelist()
def create_forwarder_pinv(source_name):
	source = frappe.get_doc("Purchase Invoice", source_name)
	target = frappe.new_doc("Purchase Invoice")

	item_forwarder = frappe.get_single("AXTRA Settings").item_forwarder
	if not item_forwarder:
		frappe.throw("Item Forwarder belum di-set di AXTRA Settings")

	def postprocess(source, target):
		if not source.custom_forwarder:
			frappe.throw("Field Forwarder wajib diisi")

		target.supplier = source.custom_forwarder
		target.company = source.company

		target.posting_date = today()
		target.bill_date = today()
		target.supplier_invoice_date = today()
		target.due_date = today()
		target.set_posting_time = 1
		target.posting_time = None
		target.custom_is_forwarder_pinv = 1

		target.remarks = f"Forwarder dari Purchase Invoice {source.name}"
		target.custom_reference_pinv = source.name

		target.items = []
		target.taxes = []
		target.custom_lcv_item = []
		target.custom_landed_cost_taxes_and_charges = []

		row = target.append("items", {})
		row.item_code = item_forwarder
		row.item_name = frappe.get_value("Item", item_forwarder, "item_name")
		row.qty = 1
		row.uom = "Nos"
		row.stock_uom = "Nos"
		row.rate = flt(source.custom_lcv_total_taxes_and_charges or 0)
		row.amount = row.rate * row.qty
		row.cost_center = source.items[0].cost_center if source.items else None
		row.custom_pinv_forwader_reference = source.name

	doc = get_mapped_doc(
		"Purchase Invoice",
		source_name,
		{
			"Purchase Invoice": {"doctype": "Purchase Invoice"},
		},
		target_doc=target,
		postprocess=postprocess,
		ignore_permissions=True
	)

	return doc


def update_item_last_vendor(doc, method=None):
	supplier = doc.supplier
	
	if doc.custom_stock_movement_inter:
		return
	
	if not supplier:
		return

	for row in doc.items:
		if not row.item_code:
			continue

		frappe.db.set_value(
			"Item",
			row.item_code,
			"custom_vendor",
			supplier
		)

def update_items_prices(doc, method):
	for item in doc.items:
		if not item.item_code:
			continue
		
		if item.get('custom_retail_price'):
			update_or_create_item_price(
				item.item_code, 
				'Retail', 
				item.custom_retail_price
			)
		
		if item.get('custom_grosir_price'):
			update_or_create_item_price(
				item.item_code, 
				'Grosir', 
				item.custom_grosir_price
			)
		
		if item.get('custom_marketplace_price'):
			update_or_create_item_price(
				item.item_code, 
				'MarketPlace', 
				item.custom_marketplace_price
			)

def update_or_create_item_price(item_code, price_list, price):
	existing_prices = frappe.get_all(
		'Item Price',
		filters={
			'item_code': item_code,
			'price_list': price_list
		},
		fields=['name', 'price_list_rate', 'valid_from'],
		order_by='valid_from desc, creation desc'
	)
	
	if existing_prices:
		latest_price = existing_prices[0]
		
		price_with_valid_from = None
		for p in existing_prices:
			if p.valid_from:
				price_with_valid_from = p
				break
		
		if price_with_valid_from:
			item_price = frappe.get_doc('Item Price', price_with_valid_from.name)
			item_price.price_list_rate = price
			item_price.valid_from = frappe.utils.today()
			item_price.save(ignore_permissions=True)
			frappe.msgprint(f'Updated {price_list} price for {item_code} (with valid_from)')
		else:
			item_price = frappe.get_doc('Item Price', latest_price.name)
			item_price.price_list_rate = price
			item_price.valid_from = frappe.utils.today()
			item_price.save(ignore_permissions=True)
			frappe.msgprint(f'Updated {price_list} price for {item_code} (added valid_from)')
	else:
		item_price = frappe.new_doc('Item Price')
		item_price.item_code = item_code
		item_price.price_list = price_list
		item_price.price_list_rate = price
		item_price.valid_from = frappe.utils.today()
		item_price.insert(ignore_permissions=True)
		frappe.msgprint(f'Created {price_list} price for {item_code} (with valid_from)')

@frappe.whitelist()
def create_forwarder_pinv_multi(source_names):

	if isinstance(source_names, str):
		source_names = source_names.strip()
		if source_names.startswith("["):
			source_names = frappe.parse_json(source_names)
		else:
			source_names = [source_names]

	if not isinstance(source_names, (list, tuple)):
		frappe.throw("Format source Purchase Invoice tidak valid")

	if not source_names:
		frappe.throw("Tidak ada Purchase Invoice yang dipilih")

	item_forwarder = frappe.get_single("AXTRA Settings").item_forwarder
	if not item_forwarder:
		frappe.throw("Item Forwarder belum di-set di AXTRA Settings")

	item_name = frappe.get_value("Item", item_forwarder, "item_name")

	target = frappe.new_doc("Purchase Invoice")

	forwarder = None
	company = None

	target.items = []
	target.taxes = []
	target.custom_lcv_item = []
	target.custom_landed_cost_taxes_and_charges = []

	for source_name in source_names:
		src = frappe.get_doc("Purchase Invoice", source_name)

		if not src.custom_has_lcv:
			frappe.throw(f"{src.name} tidak memiliki LCV")

		if not src.custom_forwarder:
			frappe.throw(f"{src.name}: Forwarder wajib diisi")

		if forwarder is None:
			forwarder = src.custom_forwarder
			company = src.company
		elif forwarder != src.custom_forwarder:
			frappe.throw(
				"Tidak bisa menggabungkan Purchase Invoice "
				"dengan Forwarder yang berbeda"
			)

		lcv_amount = flt(src.custom_lcv_total_taxes_and_charges or 0)
		if lcv_amount <= 0:
			continue

		row = target.append("items", {})
		row.item_code = item_forwarder
		row.item_name = item_name
		row.qty = 1
		row.uom = "Nos"
		row.stock_uom = "Nos"
		row.rate = lcv_amount
		row.amount = lcv_amount
		row.cost_center = src.items[0].cost_center if src.items else None

		row.custom_pinv_forwader_reference = src.name
		row.is_free_item = 1

	if not target.items:
		frappe.throw("Tidak ada nilai LCV yang bisa dibuatkan item")

	target.supplier = forwarder
	target.company = company

	target.posting_date = today()
	target.bill_date = today()
	target.supplier_invoice_date = today()
	target.due_date = today()
	target.set_posting_time = 1
	target.posting_time = None
	target.ignore_pricing_rule = 1
	target.custom_is_forwarder_pinv = 1

	target.remarks = (
		"Forwarder dari Purchase Invoice:\n" +
		", ".join(source_names)
	)

	# target.custom_reference_pinv = ", ".join(source_names)

	return target

@frappe.whitelist()
def get_available_pinv_for_lcv(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters
):
    used_pinv = frappe.db.sql("""
        SELECT DISTINCT pii.custom_pinv_forwader_reference
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi
            ON pi.name = pii.parent
        WHERE pi.docstatus = 1
            AND pii.custom_pinv_forwader_reference IS NOT NULL
    """, as_list=True)

    used_pinv = [d[0] for d in used_pinv if d[0]]

    conditions = """
        pi.docstatus = 1
        AND pi.custom_has_lcv = 1
        AND pi.custom_forwarder IS NOT NULL
        AND pi.name LIKE %(txt)s
    """

    if used_pinv:
        conditions += " AND pi.name NOT IN %(used)s"

    return frappe.db.sql(f"""
        SELECT
            pi.name,
            pi.custom_forwarder,
            pi.custom_lcv_total_taxes_and_charges
        FROM `tabPurchase Invoice` pi
        WHERE {conditions}
        ORDER BY pi.posting_date DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """, {
        "txt": f"%{txt}%",
        "used": tuple(used_pinv) or ("",),
        "start": start,
        "page_len": page_len
    })


def update_used_forwarder_to_pinv(doc, method):

    sinvs = {
        d.custom_pinv_forwader_reference
        for d in (doc.items or [])
        if d.custom_pinv_forwader_reference
    }

    if not sinvs:
        return

    if doc.docstatus == 1:
        for sinv in sinvs:
            frappe.db.set_value(
                "Purchase Invoice",
                sinv,
                "custom_forwarded_to_pinv",
                doc.name,
                update_modified=False
            )

    elif doc.docstatus == 2:
        for sinv in sinvs:
            current = frappe.db.get_value(
                "Purchase Invoice",
                sinv,
                "custom_forwarded_to_pinv"
            )

            if current == doc.name:
                frappe.db.set_value(
                    "Purchase Invoice",
                    sinv,
                    "custom_forwarded_to_pinv",
                    None,
                	update_modified=False
                )


# def calculate_custom_lcv_per_quantity(doc, method):

#     if not hasattr(doc, "items") or not hasattr(doc, "custom_lcv_item"):
#         return

#     for row in doc.items:
#         row_lcv = next((r for r in doc.custom_lcv_item if r.item_code == row.item_code), None)
#         if row_lcv:
#             if row.rate == row.net_rate and getattr(doc, "taxes_and_charges_added", 0) > 0:
#                 value = (row_lcv.applicable_charges + row_lcv.amount) + (row.rate * 11 / 100)
#             else:
#                 value = (row_lcv.applicable_charges + row_lcv.amount) + (row.rate - row.net_rate)
            
#             row.custom_lcv_per_quantity = flt(value, 0)  

def calculate_custom_lcv_per_quantity(doc, method):

    if not hasattr(doc, "items") or not hasattr(doc, "custom_lcv_item"):
        return

    for row in doc.items:
        row_lcv = next((r for r in doc.custom_lcv_item if r.item_code == row.item_code), None)

        if row_lcv:
            applicable_charges = flt(row_lcv.applicable_charges)
            amount = flt(row_lcv.amount)
            rate = flt(row.rate)
            net_rate = flt(row.net_rate)

            if rate == net_rate and flt(doc.taxes_and_charges_added) > 0:
                value = (applicable_charges + amount) + (rate * 11 / 100)
            else:
                value = (applicable_charges + amount) + (rate - net_rate)

            row.custom_lcv_per_quantity = flt(value, 0)
