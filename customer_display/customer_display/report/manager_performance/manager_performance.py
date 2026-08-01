# Copyright (c) 2026, DAS and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Manager", "fieldname": "manager_name", "fieldtype": "Data", "width": 200},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 180},
        {"label": "Total Sales", "fieldname": "total_sales", "fieldtype": "Currency", "width": 160},
        {"label": "Gross Profit", "fieldname": "gross_profit", "fieldtype": "Currency", "width": 160},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("manager"):
        conditions.append("manager_id = %(manager)s")
        values["manager"] = filters["manager"]

    if filters.get("department"):
        conditions.append("department = %(department)s")
        values["department"] = filters["department"]

    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            manager_name,
            department,
            SUM(total_sales) AS total_sales,
            SUM(gross_profit) AS gross_profit
        FROM (

            -- ATASAN 1 (reports_to)
            SELECT
                mgr.name AS manager_id,
                mgr.employee_name AS manager_name,
                emp.department,
                sii.amount AS total_sales,
                (sii.amount - COALESCE(sle.cost_amount, 0)) AS gross_profit,
                si.posting_date

            FROM `tabSales Invoice` si
            INNER JOIN `tabPOS Invoice` pi
                ON pi.custom_si_pos_no = si.custom_si_pos_no
            INNER JOIN `tabEmployee` emp
                ON emp.user_id = pi.owner
            INNER JOIN `tabEmployee` mgr
                ON (
                    emp.reports_to = mgr.name
                    OR (
                        emp.name = mgr.name
                        AND emp.reports_to = emp.name
                    )
                )
            INNER JOIN `tabSales Invoice Item` sii
                ON sii.parent = si.name
            LEFT JOIN (
                SELECT
                    voucher_no,
                    item_code,
                    SUM(actual_qty * valuation_rate * -1) AS cost_amount
                FROM `tabStock Ledger Entry`
                WHERE voucher_type = 'Sales Invoice'
                AND is_cancelled = 0
                GROUP BY voucher_no, item_code
            ) sle
                ON sle.voucher_no = si.name
                AND sle.item_code = sii.item_code
            WHERE
                si.docstatus = 1
                AND si.custom_si_pos_no IS NOT NULL

            UNION ALL

            -- ATASAN 2 (custom_report_to_spv)
            SELECT
                mgr.name AS manager_id,
                mgr.employee_name AS manager_name,
                emp.department,
                sii.amount AS total_sales,
                (sii.amount - COALESCE(sle.cost_amount, 0)) AS gross_profit,
                si.posting_date

            FROM `tabSales Invoice` si
            INNER JOIN `tabPOS Invoice` pi
                ON pi.custom_si_pos_no = si.custom_si_pos_no
            INNER JOIN `tabEmployee` emp
                ON emp.user_id = pi.owner
            INNER JOIN `tabEmployee` mgr
                ON (
                    emp.custom_report_to_spv = mgr.name
                    OR (
                        emp.name = mgr.name
                        AND emp.custom_report_to_spv = emp.name
                    )
                )
            INNER JOIN `tabSales Invoice Item` sii
                ON sii.parent = si.name
            LEFT JOIN (
                SELECT
                    voucher_no,
                    item_code,
                    SUM(actual_qty * valuation_rate * -1) AS cost_amount
                FROM `tabStock Ledger Entry`
                WHERE voucher_type = 'Sales Invoice'
                AND is_cancelled = 0
                GROUP BY voucher_no, item_code
            ) sle
                ON sle.voucher_no = si.name
                AND sle.item_code = sii.item_code
            WHERE
                si.docstatus = 1
                AND si.custom_si_pos_no IS NOT NULL

        ) base
        {where_clause}
        GROUP BY
            manager_name,
            department
        ORDER BY
            manager_name,
            department
    """

    return frappe.db.sql(query, values, as_dict=True)
