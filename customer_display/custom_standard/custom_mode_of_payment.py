import frappe

def validate_mdr_percent(doc, method):

    try:
        value = float(doc.custom_mdr_percent)
    except (ValueError, TypeError):
        frappe.throw("MDR must be a number with up to 2 decimal places (e.g., 0.17)")

    if value < 0:
        frappe.throw("MDR cannot be negative")

