import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date:
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    if to_date:
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

    rows = frappe.db.sql("""
        SELECT
            mop.custom_bank_mop AS bank,
            p.mode_of_payment,
            p.parent AS invoice,
            SUM(p.amount) AS gross,
            IFNULL(mop.custom_mdr_percent, 0) AS mdr_percent,
            pi.posting_date
        FROM `tabSales Invoice Payment` p
        INNER JOIN `tabPOS Invoice` pi ON pi.name = p.parent
        INNER JOIN `tabMode of Payment` mop ON mop.name = p.mode_of_payment
        WHERE pi.docstatus = 1
          AND pi.is_return = 0
          AND mop.custom_bank_mop IS NOT NULL
        GROUP BY mop.custom_bank_mop, p.mode_of_payment, p.parent
        ORDER BY mop.custom_bank_mop, p.mode_of_payment, p.parent
    """, as_dict=True)

    grouped = {}
    for r in rows:
        posting_date = r.posting_date
        if isinstance(posting_date, datetime):
            posting_date = posting_date.date()
        if from_date and posting_date < from_date:
            continue
        if to_date and posting_date > to_date:
            continue

        bank_group = grouped.setdefault(r.bank, {})
        mode_group = bank_group.setdefault(r.mode_of_payment, {})
        mode_group[r.invoice] = {
            "gross": r.gross,
            "mdr_percent": r.mdr_percent
        }

    grand_lbr = grand_gross = grand_mdr_nominal = grand_net = 0
    no = 1

    for bank, modes in grouped.items():
        data.append({"edc_bank": bank, "_col_header": 1})

        total_lbr = total_gross = total_mdr_nominal = total_net = 0

        for mode, invoices in modes.items():
            gross = sum(inv["gross"] for inv in invoices.values())
            lbr = count_pos_invoices_for_mode_in_range(mode, from_date, to_date)

            mdr_percent = 0
            for inv in invoices.values():
                try:
                    mdr_percent = float(inv["mdr_percent"])
                except:
                    mdr_percent = 0
                break

            mdr_nominal = gross * mdr_percent / 100
            net = gross - mdr_nominal

            data.append({
                "no": no,
                "edc_bank": mode,
                "lbr": lbr,
                "gross_bank": format_number(gross),
                "mdr": format_number(mdr_percent)+"%",
                "net_bank": format_number(net)
            })

            total_lbr += lbr
            total_gross += gross
            total_mdr_nominal += mdr_nominal
            total_net += net
            no += 1

        data.append({
            "no": "",
            "edc_bank": "TOTAL",
            "lbr": total_lbr,
            "gross_bank": format_number(total_gross),
            "mdr": format_number(total_mdr_nominal),
            "net_bank": format_number(total_net)
        })
        data.append({"_spacer": 1})

        grand_lbr += total_lbr
        grand_gross += total_gross
        grand_mdr_nominal += total_mdr_nominal
        grand_net += total_net

    data.append({
        "no": "",
        "edc_bank": "GRAND TOTAL",
        "lbr": grand_lbr,
        "gross_bank": format_number(grand_gross),
        "mdr": format_number(grand_mdr_nominal),
        "net_bank": format_number(grand_net)
    })

    return columns, data

def count_pos_invoices_for_mode_in_range(mode_of_payment, from_date=None, to_date=None):
    rows = frappe.db.sql("""
        SELECT p.parent AS invoice, SUM(p.amount) AS total_amount
        FROM `tabSales Invoice Payment` p
        INNER JOIN `tabPOS Invoice` pi ON pi.name = p.parent
        WHERE pi.docstatus = 1
          AND pi.is_return = 0
          AND p.mode_of_payment = %(mode_of_payment)s
        GROUP BY p.parent
    """, {"mode_of_payment": mode_of_payment}, as_dict=True)

    lbr = 0
    for r in rows:
        posting_date = frappe.db.get_value("POS Invoice", r.invoice, "posting_date")
        if not isinstance(posting_date, datetime):
            posting_date = datetime.strptime(str(posting_date), "%Y-%m-%d").date()
        else:
            posting_date = posting_date.date()

        if from_date and posting_date < from_date:
            continue
        if to_date and posting_date > to_date:
            continue
        if r.total_amount > 0:
            lbr += 1

    return lbr

def get_columns():
    return [
        {"label": "No", "fieldname": "no", "width": 40},
        {"label": "EDC Bank", "fieldname": "edc_bank", "width": 180},
        {"label": "Lbr", "fieldname": "lbr", "width": 60},
        {"label": "Gross Bank", "fieldname": "gross_bank", "fieldtype": "Data", "width": 130},
        {"label": "MDR", "fieldname": "mdr", "fieldtype": "Data", "width": 80},
        {"label": "Net Bank", "fieldname": "net_bank", "fieldtype": "Data", "width": 130},
    ]

def format_number(value):
    try:
        return "{:,.2f}".format(float(value))
    except:
        return value
