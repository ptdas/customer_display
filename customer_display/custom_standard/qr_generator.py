import frappe
from frappe.model.document import Document

@frappe.whitelist()
def generate_barcode_image(doc, method=None):
    if doc.barcodes:
        for row in doc.barcodes:
            if row.barcode:
                row.custom_barcode_image = row.barcode


@frappe.whitelist()
def add_to_every_pf():
    list_item = frappe.db.sql(""" SELECT name FROM `tabItem` """)
    for row in list_item:
        item_doc = frappe.get_doc("Item", row[0])

        item_doc.save()