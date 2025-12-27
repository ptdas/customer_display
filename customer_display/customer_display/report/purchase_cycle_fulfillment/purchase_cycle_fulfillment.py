import frappe
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    supplier = filters.get("supplier")

    # Build WHERE clause
    conditions = ["po.docstatus = 1"]
    if from_date:
        conditions.append("po.transaction_date >= %(from_date)s")
    if to_date:
        conditions.append("po.transaction_date <= %(to_date)s")
    if supplier:
        conditions.append("po.supplier = %(supplier)s")
    where_clause = " AND ".join(conditions)

    # Columns
    columns = [
        {"label":"PO No",             "fieldname":"po_no",           "fieldtype":"Link",     "options":"Purchase Order",   "width":120},
        {"label":"PO Date",           "fieldname":"po_date",         "fieldtype":"Date",                              "width":90},
        {"label":"Supplier",          "fieldname":"supplier",        "fieldtype":"Link",     "options":"Supplier",         "width":180},
        {"label":"Item Code",         "fieldname":"item_code",       "fieldtype":"Link",     "options":"Item",             "width":120},
        {"label":"Item Name",         "fieldname":"item_name",       "fieldtype":"Data",                            "width":150},
        {"label":"Ordered Qty",       "fieldname":"ordered_qty",     "fieldtype":"Data",                           "width":100},
        {"label":"PO Amount",         "fieldname":"po_amount",       "fieldtype":"Currency",                        "width":120},
        {"label":"PREC No",           "fieldname":"prec_no",         "fieldtype":"Link",     "options":"Purchase Receipt", "width":200},
        {"label":"PREC Qty",          "fieldname":"prec_qty",        "fieldtype":"Data",                           "width":100},
        {"label":"Remaining Qty",     "fieldname":"remaining_qty",   "fieldtype":"Data",                           "width":100},
        {"label":"PI No",             "fieldname":"pi_no",           "fieldtype":"Link",     "options":"Purchase Invoice",  "width":200},
        {"label":"PI Amount",         "fieldname":"pi_amount",       "fieldtype":"Currency",                        "width":120},
        {"label":"Remaining Amount",  "fieldname":"remaining_amount","fieldtype":"Currency",                        "width":120},
    ]

    # Fetch all PO-items (including amount)
    po_items = frappe.db.sql(f"""
        SELECT
            poi.parent           AS po_no,
            po.transaction_date  AS po_date,
            po.supplier,
            poi.name             AS poi_name,
            poi.item_code,
            poi.item_name,
            poi.qty              AS ordered_qty,
            poi.amount           AS po_amount
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po
          ON po.name = poi.parent
        WHERE {where_clause}
        ORDER BY poi.parent DESC, poi.idx
    """, filters, as_dict=True)

    data = []
    last_po = None

    for row in po_items:
        # Pull this item's receipts & invoices
        receipts = frappe.db.get_all("Purchase Receipt Item",
            filters={
                "purchase_order":      row.po_no,
                "purchase_order_item": row.poi_name
            },
            fields=["parent", "qty"],
            order_by="parent"
        )
        invoices = frappe.db.get_all("Purchase Invoice Item",
            filters={
                "purchase_order": row.po_no,
                "po_detail":      row.poi_name
            },
            fields=["parent", "amount"],
            order_by="parent"
        )

        # Compute Remaining Qty & Remaining Amount
        total_received = flt(sum(r.qty    for r in receipts))
        remaining_qty    = flt(row.ordered_qty) - total_received

        total_invoiced   = flt(sum(i.amount for i in invoices))
        remaining_amount = flt(row.po_amount)     - total_invoiced

        # Number of rows = max(#PR, #PI, 1)
        lines = max(len(receipts), len(invoices), 1)

        for i in range(lines):
            show_po_header = (row.po_no != last_po) and i == 0
            first_line_item = i == 0

            data.append({
                # PO header only on change of PO
                "po_no":        row.po_no    if show_po_header else "",
                "po_date":      row.po_date  if show_po_header else "",
                "supplier":     row.supplier if show_po_header else "",

                # Item info only on first line of each item
                "item_code":    row.item_code   if first_line_item else "",
                "item_name":    row.item_name   if first_line_item else "",
                "ordered_qty":  row.ordered_qty if first_line_item else "",
                "po_amount":    row.po_amount   if first_line_item else "",

                # PREC columns
                "prec_no":       receipts[i].parent if i < len(receipts) else "",
                "prec_qty":      receipts[i].qty    if i < len(receipts) else "",
                "remaining_qty": remaining_qty,

                # PI columns
                "pi_no":         invoices[i].parent if i < len(invoices) else "",
                "pi_amount":     invoices[i].amount if i < len(invoices) else "",
                "remaining_amount": (
                    remaining_amount 
                ),
            })

        last_po = row.po_no

    return columns, data
