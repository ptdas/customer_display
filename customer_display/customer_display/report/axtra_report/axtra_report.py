# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

def get_banks():
    return frappe.get_all(
        "Bank",
        fields=["name", "bank_name"],
        order_by="bank_name"
    )


def get_mops_with_bank():
    return frappe.get_all(
        "Mode of Payment",
        fields=["name", "custom_bank_mop"],
        filters={"custom_bank_mop": ["is", "set"]}
    )


def get_mop_company_map(mop_names):
    rows = frappe.get_all(
        "Mode of Payment Account",
        fields=["parent as mop", "company"],
        filters={"parent": ["in", mop_names]}
    )

    mop_company_map = {}
    for r in rows:
        mop_company_map.setdefault(r.mop, set()).add(r.company)

    return mop_company_map


def build_bank_mop_map(mops, mop_company_map):
    """
    Result:
    {
        bank: [
            {"mop": mop_name, "companies": set([...])}
        ]
    }
    """
    bank_mop_map = {}

    for mop in mops:
        companies = mop_company_map.get(mop.name)
        if not companies:
            continue

        bank_mop_map.setdefault(mop.custom_bank_mop, []).append({
            "mop": mop.name,
            "companies": companies
        })

    for bank in bank_mop_map:
        bank_mop_map[bank] = sorted(
            bank_mop_map[bank],
            key=lambda x: x["mop"]
        )

    return bank_mop_map

def build_columns(max_mop):
    columns = [
        {"label": "CV", "fieldname": "cv", "fieldtype": "Data", "width": 180},
        {"label": "Sales", "fieldname": "sales", "fieldtype": "Currency", "width": 120},
    ]

    for i in range(1, max_mop + 1):
        columns.append({
            "label": f"C{i}",
            "fieldname": f"c{i}",
            "fieldtype": "Currency",
            "width": 120
        })

    return columns

def build_bank_block(bank, bank_mops, max_mop, grand_total, payment_matrix):
    data = []

    bank_name = bank.bank_name or bank.name

    companies = sorted({
        company
        for m in bank_mops
        for company in m["companies"]
    })

    block_total = {"sales": 0, **{f"c{i}": 0 for i in range(1, max_mop + 1)}}

    # ---------- HEADER ----------
    header = {
        "cv": f"CV ({bank_name})",
        "sales": "Sales",
        "_col_header": 1
    }

    for idx, mop in enumerate(bank_mops, start=1):
        header[f"c{idx}"] = mop["mop"]

    data.append(header)

    # ---------- ROWS ----------
    for company in companies:

        bank_name = bank.name
        company_payments = payment_matrix.get(bank_name, {}).get(company, {})

        sales_value = sum(company_payments.values())

        row = {
            "cv": company,
            "sales": sales_value
        }


        block_total["sales"] += sales_value
        grand_total["sales"] += sales_value


        for i in range(1, max_mop + 1):
            row[f"c{i}"] = None

        for idx, mop in enumerate(bank_mops, start=1):
            if company in mop["companies"]:
                raw_value = company_payments.get(mop["mop"])
                value = flt(raw_value)  

                row[f"c{idx}"] = value  

                block_total[f"c{idx}"] += value
                grand_total[f"c{idx}"] += value


        data.append(row)

    # ---------- TOTAL ----------
    total = {"cv": "TOTAL", "sales": block_total["sales"]}
    for i in range(1, max_mop + 1):
        total[f"c{i}"] = block_total[f"c{i}"]

    data.append(total)
    data.append({"_spacer": 1})

    return data

def get_payment_matrix(from_date=None, to_date=None, customer_type=None):

    """
    return:
    {
        bank: {
            company: {
                mop: amount
            }
        }
    }
    """

    conditions = "pi.docstatus = 1"

    if from_date:
        conditions += " AND pi.posting_date >= %(from_date)s"
    if to_date:
        conditions += " AND pi.posting_date <= %(to_date)s"

    if customer_type == "B2B":
        conditions += " AND pi.custom_is_b2b = 1"
    elif customer_type == "B2C":
        conditions += " AND (pi.custom_is_b2b = 0 OR pi.custom_is_b2b IS NULL)"


    rows = frappe.db.sql(f"""
        SELECT
            mop.custom_bank_mop AS bank,
            pi.company,
            pip.mode_of_payment AS mop,
            SUM(pip.amount) AS amount
        FROM `tabSales Invoice Payment` pip
        INNER JOIN `tabSales Invoice` pi ON pi.name = pip.parent
        INNER JOIN `tabMode of Payment` mop ON mop.name = pip.mode_of_payment
        WHERE {conditions}
        GROUP BY mop.custom_bank_mop, pi.company, pip.mode_of_payment
    """, {
        "from_date": from_date,
        "to_date": to_date
    }, as_dict=True)

    matrix = {}
    for r in rows:
        matrix\
            .setdefault(r.bank, {})\
            .setdefault(r.company, {})[r.mop] = flt(r.amount)

    return matrix


def execute(filters=None):
    filters = filters or {}

    banks = get_banks()
    mops = get_mops_with_bank()

    mop_names = [m.name for m in mops]
    mop_company_map = get_mop_company_map(mop_names)
    bank_mop_map = build_bank_mop_map(mops, mop_company_map)

    max_mop = max([len(v) for v in bank_mop_map.values()] or [0])

    columns = build_columns(max_mop)

    data = []
    grand_total = {"sales": 0, **{f"c{i}": 0 for i in range(1, max_mop + 1)}}

    payment_matrix = get_payment_matrix(
        filters.get("from_date"),
        filters.get("to_date"),
        filters.get("customer_type")
    )



    for bank in banks:
        bank_mops = bank_mop_map.get(bank.name)
        if not bank_mops:
            continue

        data.extend(
            build_bank_block(
                bank,
                bank_mops,
                max_mop,
                grand_total,
                payment_matrix
            )
        )


    # ---------- GRAND TOTAL ----------
    grand = {"cv": "GRAND TOTAL", "sales": grand_total["sales"]}
    for i in range(1, max_mop + 1):
        grand[f"c{i}"] = grand_total[f"c{i}"]

    data.append(grand)

    return columns, data
