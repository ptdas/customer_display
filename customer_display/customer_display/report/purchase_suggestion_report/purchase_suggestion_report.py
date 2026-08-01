# # Copyright (c) 2025, DAS and contributors
# # For license information, please see license.txt

# import frappe
# from frappe.utils import add_days

# def execute(filters=None):
#     columns = get_columns()
#     data = []

#     as_of_date = filters.get("as_of_date")

#     items = get_candidate_items(filters)

#     for item in items:
#         dsi_target = get_dsi_target(item.item_code)
#         stock_qty = get_stock_qty(item.item_code)

#         avg_sales = 0
#         sd_sales = 0
#         dsi_actual = None

#         reorder_point = 0
#         reorder_point_high = 0
#         suggested_order = 0
#         suggested_order_high = 0

#         if dsi_target and dsi_target > 0:
#             avg_sales = get_avg_sales(item.item_code, dsi_target, as_of_date)

#             sd_sales = get_sales_sd(item.item_code, dsi_target, as_of_date)

#             if avg_sales > 0:
#                 dsi_actual = stock_qty / avg_sales

#                 reorder_point = dsi_target * avg_sales
#                 reorder_point_high = dsi_target * (avg_sales + sd_sales)

#                 suggested_order = max(reorder_point - stock_qty, 0)
#                 suggested_order_high = max(reorder_point_high - stock_qty, 0)

#         data.append({
#             "item_group": item.item_group,
#             "item_code": item.item_code,
#             "item_name": item.item_name,

#             "dsi_target": dsi_target,
#             "dsi_actual": dsi_actual,

#             "stock_qty": stock_qty,

#             "reorder_point": reorder_point,
#             "reorder_point_high": reorder_point_high,

#             "suggested_order": suggested_order,
#             "suggested_order_high": suggested_order_high,

#             "avg_sales": avg_sales,
#             "sd_sales": sd_sales,

#             "avg_sales_1w": get_avg_sales_period(item.item_code, 7, as_of_date),
#             "avg_sales_3d": get_avg_sales_period(item.item_code, 3, as_of_date),
#             "today_sales": get_today_sales(item.item_code, as_of_date),
#         })

#     data.sort(key=lambda x: x["dsi_actual"] if x["dsi_actual"] is not None else float('inf'))
#     return columns, data


# def get_today_sales(item_code, as_of_date):
#     rows = frappe.db.sql("""
#         SELECT SUM(qty) qty
#         FROM `tabSales Invoice Item` sii
#         JOIN `tabSales Invoice` si ON si.name = sii.parent
#         WHERE si.docstatus = 1
#           AND sii.item_code = %s
#           AND si.posting_date = %s
#     """, (item_code, as_of_date), as_dict=1)

#     return rows[0].qty or 0

# def get_avg_sales_period(item_code, days, as_of_date):
#     from_date = add_days(as_of_date, -days)
#     to_date = add_days(as_of_date, -1)

#     rows = frappe.db.sql("""
#         SELECT SUM(qty) qty
#         FROM `tabSales Invoice Item` sii
#         JOIN `tabSales Invoice` si ON si.name = sii.parent
#         WHERE si.docstatus = 1
#           AND sii.item_code = %s
#           AND si.posting_date BETWEEN %s AND %s
#     """, (item_code, from_date, to_date), as_dict=1)

#     return (rows[0].qty or 0) / days

# def get_sales_sd(item_code, dsi_target, as_of_date):
#     from_date = add_days(as_of_date, -dsi_target)
#     to_date = add_days(as_of_date, -1)

#     sales = frappe.db.sql("""
#         SELECT posting_date, SUM(qty) qty
#         FROM `tabSales Invoice Item` sii
#         JOIN `tabSales Invoice` si ON si.name = sii.parent
#         WHERE si.docstatus = 1
#           AND sii.item_code = %s
#           AND si.posting_date BETWEEN %s AND %s
#         GROUP BY posting_date
#     """, (item_code, from_date, to_date), as_dict=1)

#     valid_days = 0

#     for row in sales:
#         stock = get_stock_qty_on_date(item_code, row.posting_date)
#         if stock > 0:
#             valid_days += 1

#     if valid_days == 0:
#         return 0

#     return valid_days


# def get_candidate_items(filters):
#     return frappe.db.sql("""
#         SELECT i.name AS item_code, i.item_name, i.item_group
#         FROM `tabItem` i
#         WHERE i.is_purchase_item = 1
#           AND i.disabled = 0
#     """, as_dict=1)

# def get_dsi_target(item_code):
#     vendor = frappe.db.get_value("Item", item_code, "custom_vendor")

#     if not vendor:
#         return None

#     return frappe.db.get_value(
#         "Supplier",
#         vendor,
#         "custom_dsi_target"
#     )


# def get_stock_qty(item_code):
#     result = frappe.db.sql("""
#         SELECT SUM(actual_qty)
#         FROM `tabBin`
#         WHERE item_code = %s
#     """, item_code)
#     return result[0][0] or 0

# def get_avg_sales(item_code, dsi_target, as_of_date):
#     from_date = add_days(as_of_date, -dsi_target)
#     to_date = add_days(as_of_date, -1)

#     sales = frappe.db.sql("""
#         SELECT posting_date, SUM(qty) qty
#         FROM `tabSales Invoice Item` sii
#         JOIN `tabSales Invoice` si ON si.name = sii.parent
#         WHERE si.docstatus = 1
#           AND sii.item_code = %s
#           AND si.posting_date BETWEEN %s AND %s
#         GROUP BY posting_date
#     """, (item_code, from_date, to_date), as_dict=1)

#     valid_days = 0
#     total_qty = 0

#     for row in sales:
#         stock = get_stock_qty_on_date(item_code, row.posting_date)
#         if stock > 0:
#             valid_days += 1
#             total_qty += row.qty

#     if valid_days == 0:
#         return 0

#     return total_qty / valid_days

# def get_stock_qty_on_date(item_code, posting_date):
#     result = frappe.db.sql("""
#         SELECT qty_after_transaction
#         FROM `tabStock Ledger Entry`
#         WHERE item_code = %s
#           AND posting_date <= %s
#           AND is_cancelled = 0
#         ORDER BY posting_date DESC, posting_time DESC, creation DESC
#         LIMIT 1
#     """, (item_code, posting_date))

#     if result:
#         return result[0][0] or 0

#     return 0

# def get_columns():
#     return [
#         {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 120},
#         {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
#         {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},

#         {"label": "DSI Target", "fieldname": "dsi_target", "fieldtype": "Int", "width": 90},
#         {"label": "DSI Actual", "fieldname": "dsi_actual", "fieldtype": "Float", "precision": 2, "width": 90},

#         {"label": "Stock", "fieldname": "stock_qty", "fieldtype": "Float", "width": 90},
#         {"label": "Reorder Point", "fieldname": "reorder_point", "fieldtype": "Float", "width": 110},

#         {"label": "Reorder Point", "fieldname": "reorder_point", "fieldtype": "Float", "width": 110},
#         {"label": "Reorder Point - High", "fieldname": "reorder_point_high", "fieldtype": "Float", "width": 140},

#         {"label": "Suggested Order", "fieldname": "suggested_order", "fieldtype": "Float", "width": 120},
#         {"label": "Suggested Order High", "fieldname": "suggested_order_high", "fieldtype": "Float", "width": 150},

#         {"label": "Avg Sales", "fieldname": "avg_sales", "fieldtype": "Float", "precision": 2, "width": 90},
#         {"label": "SD", "fieldname": "sd_sales", "fieldtype": "Float", "precision": 2, "width": 80},

#         {"label": "Avg Sales 1W", "fieldname": "avg_sales_1w", "fieldtype": "Float", "precision": 2, "width": 110},
#         {"label": "Avg Sales 3D", "fieldname": "avg_sales_3d", "fieldtype": "Float", "precision": 2, "width": 110},
#         {"label": "Today Sales", "fieldname": "today_sales", "fieldtype": "Float", "width": 100},

#     ]

############################ test refactor untuk speed bisa dikembalikan di atas kalau keliru

import frappe
from frappe.utils import add_days
from collections import defaultdict

def execute(filters=None):
    from frappe.utils import getdate
    columns = get_columns()
    data = []

    as_of_date = getdate(filters.get("as_of_date"))

    items = get_candidate_items(filters)

    all_stock_qty = get_all_stock_qty()

    item_dsi_target_map = get_all_dsi_target([i['item_code'] for i in items])

    sales_by_item = get_all_sales([i['item_code'] for i in items], as_of_date)

    stock_on_date_map = get_stock_on_date([i['item_code'] for i in items], as_of_date)

    for item in items:
        item_code = item['item_code']
        dsi_target = item_dsi_target_map.get(item_code)
        stock_qty = all_stock_qty.get(item_code, 0)

        avg_sales = 0
        sd_sales = 0
        dsi_actual = None

        reorder_point = 0
        reorder_point_high = 0
        suggested_order = 0
        suggested_order_high = 0

        if dsi_target and dsi_target > 0:
            avg_sales = calculate_avg_sales(item_code, dsi_target, as_of_date, sales_by_item, stock_on_date_map)
            sd_sales = calculate_sd_sales(item_code, dsi_target, as_of_date, sales_by_item, stock_on_date_map)

            if avg_sales > 0:
                dsi_actual = stock_qty / avg_sales
                reorder_point = dsi_target * avg_sales
                reorder_point_high = dsi_target * (avg_sales + sd_sales)
                suggested_order = max(reorder_point - stock_qty, 0)
                suggested_order_high = max(reorder_point_high - stock_qty, 0)

        avg_sales_1w = calculate_avg_sales_period(item_code, 7, as_of_date, sales_by_item, stock_on_date_map)
        avg_sales_3d = calculate_avg_sales_period(item_code, 3, as_of_date, sales_by_item, stock_on_date_map)
        today_sales = calculate_today_sales(item_code, as_of_date, sales_by_item, stock_on_date_map)

        data.append({
            "item_group": item['item_group'],
            "item_code": item_code,
            "item_name": item['item_name'],
            "dsi_target": dsi_target,
            "dsi_actual": dsi_actual,
            "stock_qty": stock_qty,
            "reorder_point": reorder_point,
            "reorder_point_high": reorder_point_high,
            "suggested_order": suggested_order,
            "suggested_order_high": suggested_order_high,
            "avg_sales": avg_sales,
            "sd_sales": sd_sales,
            "avg_sales_1w": avg_sales_1w,
            "avg_sales_3d": avg_sales_3d,
            "today_sales": today_sales,
        })

    data.sort(key=lambda x: x["dsi_actual"] if x["dsi_actual"] is not None else float('inf'))
    return columns, data

def get_columns():
    return [
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 120},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "DSI Target", "fieldname": "dsi_target", "fieldtype": "Int", "width": 90},
        {"label": "DSI Actual", "fieldname": "dsi_actual", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "Stock", "fieldname": "stock_qty", "fieldtype": "Float", "width": 90},
        {"label": "Reorder Point", "fieldname": "reorder_point", "fieldtype": "Float", "width": 110},
        {"label": "Reorder Point - High", "fieldname": "reorder_point_high", "fieldtype": "Float", "width": 140},
        {"label": "Suggested Order", "fieldname": "suggested_order", "fieldtype": "Float", "width": 120},
        {"label": "Suggested Order High", "fieldname": "suggested_order_high", "fieldtype": "Float", "width": 150},
        {"label": "Avg Sales", "fieldname": "avg_sales", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "SD", "fieldname": "sd_sales", "fieldtype": "Float", "precision": 2, "width": 80},
        {"label": "Avg Sales 1W", "fieldname": "avg_sales_1w", "fieldtype": "Float", "precision": 2, "width": 110},
        {"label": "Avg Sales 3D", "fieldname": "avg_sales_3d", "fieldtype": "Float", "precision": 2, "width": 110},
        {"label": "Today Sales", "fieldname": "today_sales", "fieldtype": "Float", "width": 100},
    ]

def get_candidate_items(filters):
    return frappe.db.sql("""
        SELECT i.name AS item_code, i.item_name, i.item_group
        FROM `tabItem` i
        WHERE i.is_purchase_item = 1
          AND i.disabled = 0
    """, as_dict=1)

def get_all_stock_qty():
    rows = frappe.db.sql("""
        SELECT item_code, SUM(actual_qty) as stock_qty
        FROM `tabBin`
        GROUP BY item_code
    """, as_dict=1)
    return {r['item_code']: r['stock_qty'] for r in rows}

def get_all_dsi_target(item_codes):
    item_vendor_map = frappe.db.get_all("Item", filters={"name": ["in", item_codes]}, fields=["name", "custom_vendor"])
    vendors = list(set(i['custom_vendor'] for i in item_vendor_map if i['custom_vendor']))
    supplier_targets = frappe.db.get_all("Supplier", filters={"name": ["in", vendors]}, fields=["name", "custom_dsi_target"])
    supplier_target_map = {s['name']: s['custom_dsi_target'] for s in supplier_targets}
    return {i['name']: supplier_target_map.get(i['custom_vendor']) for i in item_vendor_map}

def get_all_sales(item_codes, as_of_date):
    sales = frappe.db.sql("""
        SELECT sii.item_code, si.posting_date, SUM(sii.qty) as qty
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
          AND sii.item_code IN %(items)s
          AND si.posting_date <= %(as_of_date)s
        GROUP BY sii.item_code, si.posting_date
    """, {"items": tuple(item_codes), "as_of_date": as_of_date}, as_dict=1)
    result = defaultdict(list)
    for row in sales:
        result[row['item_code']].append(row)
    return result

def get_stock_on_date(item_codes, as_of_date):
    sle = frappe.db.sql("""
        SELECT item_code, posting_date, qty_after_transaction
        FROM `tabStock Ledger Entry`
        WHERE item_code IN %(items)s
          AND posting_date <= %(as_of_date)s
          AND is_cancelled = 0
        ORDER BY posting_date DESC, posting_time DESC, creation DESC
    """, {"items": tuple(item_codes), "as_of_date": as_of_date}, as_dict=1)
    result = defaultdict(list)
    for row in sle:
        result[row['item_code']].append(row)
    return result

def calculate_avg_sales(item_code, dsi_target, as_of_date, sales_by_item, stock_on_date_map):
    from_date = add_days(as_of_date, -dsi_target)
    to_date = add_days(as_of_date, -1)
    sales = [r for r in sales_by_item.get(item_code, []) if from_date <= r['posting_date'] <= to_date]
    total_qty = valid_days = 0
    stock_map = {r['posting_date']: r['qty_after_transaction'] for r in stock_on_date_map.get(item_code, [])}
    for r in sales:
        stock = stock_map.get(r['posting_date'], 0)
        if stock > 0:
            total_qty += r['qty']
            valid_days += 1
    return total_qty / valid_days if valid_days else 0

def calculate_sd_sales(item_code, dsi_target, as_of_date, sales_by_item, stock_on_date_map):
    return calculate_avg_sales(item_code, dsi_target, as_of_date, sales_by_item, stock_on_date_map)

def calculate_avg_sales_period(item_code, days, as_of_date, sales_by_item, stock_on_date_map):
    from_date = add_days(as_of_date, -days)
    to_date = add_days(as_of_date, -1)
    sales = [r for r in sales_by_item.get(item_code, []) if from_date <= r['posting_date'] <= to_date]
    total_qty = valid_days = 0
    stock_map = {r['posting_date']: r['qty_after_transaction'] for r in stock_on_date_map.get(item_code, [])}
    for r in sales:
        stock = stock_map.get(r['posting_date'], 0)
        if stock > 0:
            total_qty += r['qty']
            valid_days += 1
    return total_qty / valid_days if valid_days else 0


def calculate_today_sales(item_code, as_of_date, sales_by_item, stock_on_date_map):
    sales = [r for r in sales_by_item.get(item_code, []) if r['posting_date'] == as_of_date]
    total_qty = 0
    stock_map = {r['posting_date']: r['qty_after_transaction'] for r in stock_on_date_map.get(item_code, [])}
    for r in sales:
        stock = stock_map.get(r['posting_date'], 0)
        if stock > 0:
            total_qty += r['qty']
    return total_qty
