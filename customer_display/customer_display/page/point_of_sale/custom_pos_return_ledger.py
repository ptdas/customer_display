import frappe
from frappe import _
from frappe.utils import today

def get_return_balance(customer, return_pos_invoice):
    return frappe.db.sql("""
        SELECT IFNULL(SUM(amount), 0)
        FROM `tabPOS Return Ledger`
        WHERE customer = %s
          AND return_pos_invoice = %s
    """, (customer, return_pos_invoice))[0][0]


def insert_ledger(
    customer,
    return_pos_invoice,
    amount,
    used_in_pos_invoice=None,
    posting_date=None,
    remarks=None
):
    frappe.get_doc({
        "doctype": "POS Return Ledger",
        "customer": customer,
        "return_pos_invoice": return_pos_invoice,
        "used_in_pos_invoice": used_in_pos_invoice,
        "amount": amount,
        "posting_date": posting_date or today(),
        "remarks": remarks
    }).insert(ignore_permissions=True)


def before_submit_pos_invoice(doc, method):
    if doc.is_return:
        return

    #distribusi berdasarkan payment POS Return
    distribute_pos_return_usage(doc)

    if not doc.custom_pos_return_usage:
        return

    for row in doc.custom_pos_return_usage:
        if not row.pos_invoice_return or not row.amount:
            continue

        return_customer = frappe.db.get_value(
            "POS Invoice",
            row.pos_invoice_return,
            "customer"
        )
        if return_customer != doc.customer:
            frappe.throw(_("Customer retur tidak sama"))

        balance = get_return_balance(
            doc.customer,
            row.pos_invoice_return
        )

        if row.amount > balance:
            frappe.throw(_(
                f"Saldo retur {row.pos_invoice_return} tidak cukup. "
                f"Sisa saldo: {balance}"
            ))


def on_submit_pos_invoice(doc, method):
    if doc.is_return:
        handle_pos_invoice_return(doc)
    else:
        handle_pos_invoice_usage(doc)

def handle_pos_invoice_return(doc):
    insert_ledger(
        customer=doc.customer,
        return_pos_invoice=doc.name,
        amount=abs(doc.grand_total),
        posting_date=doc.posting_date,
        remarks="POS Return created"
    )


def handle_pos_invoice_usage(doc):
    if not doc.custom_pos_return_usage:
        return

    for row in doc.custom_pos_return_usage:
        if not row.pos_invoice_return or not row.amount:
            continue

        insert_ledger(
            customer=doc.customer,
            return_pos_invoice=row.pos_invoice_return,
            used_in_pos_invoice=doc.name,
            amount=-abs(row.amount),
            posting_date=doc.posting_date,
            remarks="Used in POS Invoice"
        )

def on_cancel_pos_invoice(doc, method):
    if doc.is_return:
        reverse_pos_invoice_return(doc)
    else:
        reverse_pos_invoice_usage(doc)


def reverse_pos_invoice_return(doc):
    balance = get_return_balance(doc.customer, doc.name)
    total_return = abs(doc.grand_total)

    if balance < total_return:
        usage = get_return_usage_details(doc.name)

        lines = []
        for u in usage:
            lines.append(
                f"- {u.used_in_pos_invoice}: "
                f"{frappe.format(u.used_amount, {'fieldtype': 'Currency'})}"
            )

        detail = "<br>".join(lines) if lines else "- (tidak diketahui)"

        frappe.throw(_(
            "POS Invoice Return sudah digunakan dan tidak boleh dicancel.<br>"
            "Sudah dipakai di:<br>"
            f"{detail}"
        ), title=_("Return Sudah Digunakan"))

    insert_ledger(
        customer=doc.customer,
        return_pos_invoice=doc.name,
        amount=-total_return,
        posting_date=today(),
        remarks="Reversal cancel POS Return"
    )



def reverse_pos_invoice_usage(doc):
    if not doc.custom_pos_return_usage:
        return

    for row in doc.custom_pos_return_usage:
        if not row.pos_invoice_return or not row.amount:
            continue

        insert_ledger(
            customer=doc.customer,
            return_pos_invoice=row.pos_invoice_return,
            used_in_pos_invoice=doc.name,
            amount=abs(row.amount),
            remarks="Reversal cancel POS Invoice"
        )


def get_return_usage_details(return_pos_invoice):
    return frappe.db.sql("""
        SELECT
            used_in_pos_invoice,
            SUM(amount) * -1 AS used_amount
        FROM `tabPOS Return Ledger`
        WHERE return_pos_invoice = %s
          AND used_in_pos_invoice IS NOT NULL
        GROUP BY used_in_pos_invoice
        HAVING used_amount > 0
    """, return_pos_invoice, as_dict=True)


@frappe.whitelist()
def get_available_returns(customer):
    if not customer:
        return []

    return frappe.db.sql("""
        SELECT
            return_pos_invoice AS name,
            MIN(posting_date) AS posting_date,
            SUM(amount) AS available_amount
        FROM `tabPOS Return Ledger`
        WHERE
            customer = %s
        GROUP BY return_pos_invoice
        HAVING available_amount > 0
        ORDER BY posting_date ASC
    """, customer, as_dict=True)

#######################

def get_pos_return_payment_amount(doc):
    pos_return_mop = frappe.db.get_single_value(
        "AXTRA Settings",
        "pos_retur_mode_of_payment"
    )

    if not pos_return_mop:
        return 0

    for p in doc.payments:
        if p.mode_of_payment == pos_return_mop and p.amount:
            return abs(p.amount)

    return 0


def distribute_pos_return_usage(doc):
    payment_amount = get_pos_return_payment_amount(doc)
    if not payment_amount:
        return

    if not doc.custom_pos_return_usage:
        frappe.throw(_("POS Return dipilih tapi tidak ada data retur"))

    remaining = payment_amount

    for row in doc.custom_pos_return_usage:
        if remaining <= 0:
            break

        avail = abs(row.available_amount or 0)
        if avail <= 0:
            row.amount = 0
            continue

        use_amount = min(avail, remaining)
        row.amount = use_amount
        remaining -= use_amount

    if remaining > 0:
        frappe.throw(_(
            "Saldo POS Return tidak mencukupi. Sisa: {0}"
        ).format(
            frappe.format(remaining, {"fieldtype": "Currency"})
        ))

def test():
    data = get_available_returns("ANGELINE - 1")

    print(data)
    