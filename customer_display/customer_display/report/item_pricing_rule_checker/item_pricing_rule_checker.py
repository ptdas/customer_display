# Copyright (c) 2026
# Report: Item Pricing Rule Checker

import frappe
from frappe.utils import today

def execute(filters=None):
    if not filters:
        filters = {}

    item_code = filters.get("item")
    if not item_code:
        frappe.throw("Filter 'Item' wajib diisi")

    posting_date = filters.get("date") or today()

    item_group = frappe.db.get_value("Item", item_code, "item_group")

    rules = frappe.db.sql("""
        SELECT DISTINCT
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
            pr.company
        FROM `tabPricing Rule` pr
        LEFT JOIN `tabPricing Rule Item Code` ic ON ic.parent = pr.name
        LEFT JOIN `tabPricing Rule Item Group` ig ON ig.parent = pr.name
        WHERE pr.disable = 0
          AND (%(posting_date)s BETWEEN IFNULL(pr.valid_from, %(posting_date)s)
                                    AND IFNULL(pr.valid_upto, %(posting_date)s))
          AND (
               ic.item_code = %(item_code)s
               OR ig.item_group = %(item_group)s
          )
        ORDER BY pr.priority ASC
    """, {
        "item_code": item_code,
        "item_group": item_group,
        "posting_date": posting_date
    }, as_dict=True)

    columns = [
        "Pricing Rule:Link/Pricing Rule:200",
        "Type:Data:80",
        "Priority:Int:60",
        "Discount %:Percent:80",
        "Discount Amount:Currency:120",
        "Free Item:Link/Item:120",
        "Min Qty:Int:70",
        "Max Qty:Int:70",
        "Valid From:Date:100",
        "Valid Upto:Date:100",
        "Company:Link/Company:120"
    ]

    data = []
    for r in rules:
        data.append([
            r.pricing_rule,
            r.price_or_product_discount,
            r.priority,
            r.discount_percentage,
            r.discount_amount,
            r.free_item,
            r.min_qty,
            r.max_qty,
            r.valid_from,
            r.valid_upto,
            r.company
        ])

    return columns, data
