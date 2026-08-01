import frappe
from frappe.utils import now_datetime
from frappe.model.naming import make_autoname
from frappe import _


def autoname(doc, method=None):
    current_date = now_datetime()
    year = current_date.strftime("%y")
    month = current_date.strftime("%m")
    
    prefix = f"R{year}{month}-"
    
    doc.name = make_autoname(f"{prefix}.##")

def validate_pricing_rule_company_warehouse(doc, method=None):
    if not doc.warehouse:
        return

    warehouse_company = frappe.db.get_value(
        'Warehouse',
        doc.warehouse,
        'company'
    )

    # Jika company ada tapi berbeda, throw error
    if warehouse_company != doc.company:
        frappe.throw(
            _('Company pada Warehouse ({0}) harus sama dengan Company pada Pricing Rule ({1}).').format(
                warehouse_company,
                doc.company
            )
        )


@frappe.whitelist()
def get_filtered_items(supplier=None, brand=None):

    if not supplier and not brand:
        return []

    filters = {
        'disabled': 0,
        'has_variants': 0
    }

    if supplier:
        filters['custom_vendor'] = supplier

    if brand:
        filters['brand'] = brand

    return frappe.get_all(
        'Item',
        filters=filters,
        fields=['name'],
        order_by='name'
    )
