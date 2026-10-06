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

@frappe.whitelist()
def get_item_from_scan(scan_value):
    """Terjemahkan isi kolom scan_item_code jadi nama Item.

    Barcode scanner mengirim isi barcode, yang belum tentu sama dengan nama
    Item - jadi dicoba dulu sebagai nama Item, baru sebagai barcode.
    """
    scan_value = (scan_value or '').strip()

    if not scan_value:
        return None

    item_code = frappe.db.get_value('Item', scan_value, 'name')

    if not item_code:
        item_code = frappe.db.get_value(
            'Item Barcode',
            {'barcode': scan_value},
            'parent'
        )

    return item_code


@frappe.whitelist()
def search_items_for_pricing_rule(
    txt=None,
    start=0,
    page_length=20,
    supplier=None,
    brand=None
):
    txt = txt or ""
    start = int(start or 0)
    page_length = int(page_length or 20)

    filters = {
        "disabled": 0,
        "has_variants": 0,
    }

    if supplier:
        filters["custom_vendor"] = supplier

    if brand:
        filters["brand"] = brand

    or_filters = []

    if txt:
        if "%" in txt:
            pattern = txt
        else:
            pattern = f"{txt}%"

        or_filters = [
            ["Item", "name", "like", pattern],
            ["Item", "item_name", "like", pattern],
        ]

    return frappe.get_list(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "item_name",
            "stock_uom",
            "item_group",
            "brand",
        ],
        order_by="name asc",
        start=start,
        page_length=page_length,
    )