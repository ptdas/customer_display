
import frappe
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

    items_with_charges = [i for i in doc.custom_lcv_item if i.applicable_charges > 0]
    if not items_with_charges:
        return
    
    if not doc.custom_forwarder:
        frappe.throw("Forwader LCV wajib di isi")

    lcv = frappe.new_doc("Landed Cost Voucher")
    lcv.company = doc.company
    lcv.posting_date = doc.posting_date

    if (doc.custom_distribute_charges_based_on or "").lower() == "constant":
        lcv.distribute_charges_based_on = "Distribute Manually"
    else:
        lcv.distribute_charges_based_on = doc.custom_distribute_charges_based_on

    lcv.purchase_receipts = []
    lcv.items = []

    lcv.append("purchase_receipts", {
        "receipt_document_type": "Purchase Invoice",
        "receipt_document": doc.name,
        "supplier": doc.supplier,
        "posting_date": doc.posting_date,
        "grand_total": doc.grand_total
    })

    for item in items_with_charges:
        lcv.append("items", {
            "item_code": item.item_code,
            "description": item.description,
            "qty": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "applicable_charges": item.applicable_charges,
            "receipt_document_type": "Purchase Invoice",  
            "receipt_document": doc.name,                 
            "cost_center": item.cost_center               
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

    lcv.insert()
    lcv.submit()

    frappe.msgprint(f"Landed Cost Voucher {lcv.name} berhasil dibuat dari {doc.name}")


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
