
import frappe

def recompute_has_lcv(purchase_invoice):
    has_lcv = frappe.db.exists(
        "Landed Cost Purchase Receipt",
        {
            "receipt_document_type": "Purchase Invoice",
            "receipt_document": purchase_invoice,
            "docstatus": 1
        }
    )

    frappe.db.set_value(
        "Purchase Invoice",
        purchase_invoice,
        "custom_has_lcv",
        1 if has_lcv else 0,
        update_modified=False
    )

def on_lcv_submit(doc, method=None):
    for pr in doc.purchase_receipts:
        if pr.receipt_document_type == "Purchase Invoice":
            recompute_has_lcv(pr.receipt_document)

def on_lcv_cancel(doc, method=None):
    for pr in doc.purchase_receipts:
        if pr.receipt_document_type == "Purchase Invoice":
            recompute_has_lcv(pr.receipt_document)




def patch_recompute_has_lcv():
    """
    Backfill custom_has_lcv untuk semua Purchase Invoice
    berdasarkan LCV aktif (docstatus = 1)
    """

    print("Start patch: recompute custom_has_lcv")

    purchase_invoices = frappe.get_all(
        "Purchase Invoice",
        pluck="name"
    )

    for pi in purchase_invoices:
        print(pi)
        has_lcv = frappe.db.exists(
            "Landed Cost Purchase Receipt",
            {
                "receipt_document_type": "Purchase Invoice",
                "receipt_document": pi,
                "docstatus": 1
            }
        )

        frappe.db.set_value(
            "Purchase Invoice",
            pi,
            "custom_has_lcv",
            1 if has_lcv else 0,
            update_modified=False
        )

    frappe.db.commit()
    print("Finish patch: recompute custom_has_lcv")
