# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
    return [
        {"label": _("Nama User"), "fieldname": "nama_user", "fieldtype": "Data", "width": 150},
        {"label": _("Online Partai"), "fieldname": "online_partai", "fieldtype": "Currency", "width": 120},
        {"label": _("Online"), "fieldname": "online", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Online"), "fieldname": "total_online", "fieldtype": "Currency", "width": 120},
        {"label": _("Kas Awal"), "fieldname": "kas_awal", "fieldtype": "Currency", "width": 120},
        {"label": _("Jual Cash"), "fieldname": "jual_cash", "fieldtype": "Currency", "width": 120},
        {"label": _("Jual Kartu"), "fieldname": "jual_kartu", "fieldtype": "Currency", "width": 120},
        {"label": _("Jumlah Jual"), "fieldname": "jumlah_jual", "fieldtype": "Currency", "width": 120},
        {"label": _("Voucher"), "fieldname": "vch", "fieldtype": "Currency", "width": 100},
        {"label": _("Retur Cash"), "fieldname": "retur_cash", "fieldtype": "Currency", "width": 120},
        {"label": _("Retur Kartu"), "fieldname": "retur_kartu", "fieldtype": "Currency", "width": 120},
        {"label": _("Discount Item"), "fieldname": "discount_item", "fieldtype": "Currency", "width": 120},
        {"label": _("Discount Nota"), "fieldname": "discount_nota", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Jual"), "fieldname": "byk", "fieldtype": "Int", "width": 80},
        {"label": _("Kas Akhir"), "fieldname": "kas_akhir", "fieldtype": "Currency", "width": 120},
        {"label": _("Member Free"), "fieldname": "member_free", "fieldtype": "Currency", "width": 120},
        {"label": _("Member Non Free"), "fieldname": "member_non_free", "fieldtype": "Currency", "width": 120},
        {"label": _("Biaya Member"), "fieldname": "biaya_member", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Kas Akhir"), "fieldname": "total_kas_akhir", "fieldtype": "Currency", "width": 120},
        {"label": _("Pinjaman"), "fieldname": "pinjaman", "fieldtype": "Currency", "width": 120},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 120},
        {"label": _("Uang Charge Kredit"), "fieldname": "uang_charge_kredit", "fieldtype": "Currency", "width": 120},
        {"label": _("Total Tutup"), "fieldname": "total_tutup", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    if not filters.get("date"):
        return []

    pos_invoices = frappe.db.sql("""
        SELECT
            si.name,
            si.owner,
            si.is_return,
            si.pos_profile,
            si.change_amount,
            si.discount_amount AS discount_nota
        FROM `tabPOS Invoice` si
        WHERE
            si.docstatus = 1
            AND si.is_pos = 1
            AND si.posting_date = %(date)s
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPOS Invoice Reference` ref
                INNER JOIN `tabPOS Closing Entry` pc
                    ON pc.name = ref.parent
                WHERE
                    ref.pos_invoice = si.name
                    AND pc.docstatus = 1
            )
    """, filters, as_dict=1)

    if not pos_invoices:
        return []

    invoice_names = [inv.name for inv in pos_invoices]

    item_discount_rows = frappe.db.sql("""
        SELECT
            parent,
            SUM(discount_amount) AS total_discount_item
        FROM `tabPOS Invoice Item`
        WHERE parent IN %(invoices)s
        GROUP BY parent
    """, {"invoices": invoice_names}, as_dict=1)

    item_discount_map = {
        r.parent: r.total_discount_item or 0
        for r in item_discount_rows
    }

    payments = frappe.db.sql("""
        SELECT
            parent,
            mode_of_payment,
            amount
        FROM `tabSales Invoice Payment`
        WHERE parent IN %(invoices)s
    """, {"invoices": invoice_names}, as_dict=1)

    payments_map = {}
    mop_list = set()

    for p in payments:
        payments_map.setdefault(p.parent, []).append(p)
        if p.mode_of_payment:
            mop_list.add(p.mode_of_payment)

    mop_type_map = {}

    if mop_list:
        mop_rows = frappe.db.sql("""
            SELECT
                name,
                custom_mop_type
            FROM `tabMode of Payment`
            WHERE name IN %(mops)s
        """, {"mops": tuple(mop_list)}, as_dict=1)

        mop_type_map = {r.name: r.custom_mop_type for r in mop_rows}

    tax_rows = frappe.db.sql("""
        SELECT
            parent,
            SUM(tax_amount) AS total_charge
        FROM `tabSales Taxes and Charges`
        WHERE
            parent IN %(invoices)s
            AND description = 'POS Charge'
        GROUP BY parent
    """, {"invoices": invoice_names}, as_dict=1)

    tax_map = {
        r.parent: r.total_charge or 0
        for r in tax_rows
    }

    pos_profiles = list(set([
        inv.pos_profile for inv in pos_invoices if inv.pos_profile
    ]))

    kas_awal_map = {}

    if pos_profiles:
        kas_awal_rows = frappe.db.sql("""
            SELECT
                poe.pos_profile,
                SUM(pod.opening_amount) AS kas_awal
            FROM `tabPOS Opening Entry` poe
            INNER JOIN `tabPOS Opening Entry Detail` pod
                ON pod.parent = poe.name
            WHERE
                poe.status = 'Open'
                AND poe.pos_profile IN %(profiles)s
            GROUP BY poe.pos_profile
        """, {"profiles": tuple(pos_profiles)}, as_dict=1)

        kas_awal_map = {
            r.pos_profile: r.kas_awal or 0
            for r in kas_awal_rows
        }

    summary = {}

    for inv in pos_invoices:

        user = inv.owner
        pos_profile = inv.pos_profile

        summary.setdefault(user, {
            "jual_cash": 0,
            "jual_kartu": 0,
            "jumlah_jual": 0,
            "retur_cash": 0,
            "retur_kartu": 0,
            "online_partai": 0,
            "online": 0,
            "total_online": 0,
            "total_change": 0,
            "jumlah_jual": 0,
            "total_jual": 0,
            "byk": 0,
            "vch": 0,
            "kas_awal": kas_awal_map.get(pos_profile, 0),
            "kas_akhir": 0,
            "discount_item": 0,
            "discount_nota": 0,
            "member_free": 0,
            "member_non_free": 0,
            "biaya_member": 0,
            "total_kas_akhir": 0,
            "pinjaman": 0,
            "total": 0,
            "uang_charge_kredit": 0,
            "total_tutup": 0
        })

        summary[user]["discount_nota"] += abs(inv.discount_nota or 0)
        # summary[user]["discount_item"] += abs(item_discount_map.get(inv.name, 0))

        summary[user]["total_change"] += inv.change_amount or 0
        summary[user]["uang_charge_kredit"] += tax_map.get(inv.name, 0)

        inv_payments = payments_map.get(inv.name, [])

        for p in inv_payments:

            mop_type = mop_type_map.get(p.mode_of_payment)

            if inv.is_return:
                if mop_type == "Cash":
                    summary[user]["retur_cash"] += abs(p.amount)
                else:
                    summary[user]["retur_kartu"] += abs(p.amount)

            else:
                if mop_type == "Cash":
                    summary[user]["jual_cash"] += p.amount
                elif mop_type == "Bank":
                    summary[user]["jual_kartu"] += p.amount
                elif mop_type == "Online Partai":
                    summary[user]["online_partai"] += p.amount
                elif mop_type == "Online":
                    summary[user]["online"] += p.amount

        if not inv.is_return:
            summary[user]["byk"] += 1

    for user in summary:

        val = summary[user]

        val["total_online"] = val["online_partai"] + val["online"]

        val["jumlah_jual"] = (
            val["jual_cash"] +
            val["jual_kartu"] -
            val["uang_charge_kredit"]
        )

        val["total_jual"] = (
            val["jumlah_jual"] -
            val["retur_cash"] -
            val["retur_kartu"]
        )

        val["jual_cash"] = val["jual_cash"] - val["total_change"]

        val["kas_akhir"] = (
            val["kas_awal"] +
            val["jual_cash"] -
            val["retur_cash"]
        )

        val["total_kas_akhir"] = val["kas_akhir"]

        val["total"] = val["kas_akhir"] - val["pinjaman"]

        val["total_tutup"] = val["total"] - val["uang_charge_kredit"]

    data = []

    for user, val in summary.items():

        row = {"nama_user": user}

        for key in [
            "online_partai","online","total_online","kas_awal","jual_cash","jual_kartu","jumlah_jual",
            "vch","retur_cash","retur_kartu","discount_item","discount_nota","byk",
            "kas_akhir","member_free","member_non_free","biaya_member","total_kas_akhir",
            "pinjaman","total","uang_charge_kredit","total_tutup"
        ]:
            row[key] = val.get(key, 0)

        data.append(row)

    data.sort(key=lambda x: x["nama_user"].lower())

    return data



# kode lama
# def get_data(filters):
# 	if not filters.get("date"):
# 		return []

# 	# 1. Ambil semua POS Invoice pada tanggal terpilih
# 	pos_invoices = frappe.db.sql("""
# 		SELECT
# 			si.name,
# 			si.owner,
# 			si.is_return
# 		FROM `tabPOS Invoice` si
# 		WHERE
# 			si.docstatus = 1
# 			AND si.is_pos = 1
# 			AND si.posting_date = %(date)s
# 	""", filters, as_dict=1)

# 	if not pos_invoices:
# 		return []

# 	invoice_names = [inv.name for inv in pos_invoices]

# 	# 2. Ambil semua payment dari invoice tersebut
# 	payments = frappe.db.sql("""
# 		SELECT
# 			parent,
# 			mode_of_payment,
# 			amount
# 		FROM `tabSales Invoice Payment`
# 		WHERE parent IN %(invoices)s
# 	""", {"invoices": invoice_names}, as_dict=1)

# 	# 3. Group payment per invoice
# 	payments_map = {}
# 	for p in payments:
# 		payments_map.setdefault(p.parent, []).append(p)

# 	# 4. Rekap per user (cashier)
# 	summary = {}

# 	for inv in pos_invoices:
# 		user = inv.owner
# 		summary.setdefault(user, {
# 			"jual_cash": 0,
# 			"jual_kartu": 0,
# 			"retur_cash": 0,
# 			"retur_kartu": 0,
# 			"byk": 0
# 		})

# 		inv_payments = payments_map.get(inv.name, [])

# 		for p in inv_payments:
# 			if inv.is_return:
# 				# Return invoice
# 				if p.mode_of_payment == "Cash":
# 					summary[user]["retur_cash"] += abs(p.amount)
# 				else:
# 					summary[user]["retur_kartu"] += abs(p.amount)
# 			else:
# 				# Normal sales
# 				if p.mode_of_payment == "Cash":
# 					summary[user]["jual_cash"] += p.amount
# 				else:
# 					summary[user]["jual_kartu"] += p.amount

# 		if not inv.is_return:
# 			summary[user]["byk"] += 1

# 	# 5. Convert ke format report
# 	data = []
# 	for user, val in summary.items():
# 		data.append({
# 			"nama_user": user,
# 			"jual_cash": val["jual_cash"],
# 			"jual_kartu": val["jual_kartu"],
# 			"retur_cash": val["retur_cash"],
# 			"retur_kartu": val["retur_kartu"],
# 			"byk": val["byk"]
# 		})

# 	# Optional: sort by nama_user
# 	data.sort(key=lambda x: x["nama_user"].lower())

# 	return data

# def get_columns():
# 	return [
# 		{
# 			"label": _("Nama User"),
# 			"fieldname": "nama_user",
# 			"fieldtype": "Data",
# 			"width": 150
# 		},
# 		{
# 			"label": _("Jual Cash"),
# 			"fieldname": "jual_cash",
# 			"fieldtype": "Currency",
# 			"width": 120
# 		},
# 		{
# 			"label": _("Jual Kartu"),
# 			"fieldname": "jual_kartu",
# 			"fieldtype": "Currency",
# 			"width": 120
# 		},
# 		{
# 			"label": _("Vch"),
# 			"fieldname": "vch",
# 			"fieldtype": "Currency",
# 			"width": 100
# 		},
# 		{
# 			"label": _("Retur Cash"),
# 			"fieldname": "retur_cash",
# 			"fieldtype": "Currency",
# 			"width": 120
# 		},
# 		{
# 			"label": _("Retur Kartu"),
# 			"fieldname": "retur_kartu",
# 			"fieldtype": "Currency",
# 			"width": 120
# 		},
# 		{
# 			"label": _("Byk"),
# 			"fieldname": "byk",
# 			"fieldtype": "Int",
# 			"width": 80
# 		},
# 	]



def debug_charge_kredit(date):
    """
    Debug POS Invoice yang berkontribusi ke
    Uang Charge Kredit untuk tanggal tertentu.
    """

    if not date:
        print("DEBUG: tanggal belum diisi.")
        return

    filters = {
        "date": date
    }

    pos_invoices = frappe.db.sql("""
        SELECT
            si.name,
            si.owner,
            si.is_return,
            si.pos_profile
        FROM `tabPOS Invoice` si
        WHERE
            si.docstatus = 1
            AND si.is_pos = 1
            AND si.posting_date = %(date)s
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPOS Invoice Reference` ref
                INNER JOIN `tabPOS Closing Entry` pc
                    ON pc.name = ref.parent
                WHERE
                    ref.pos_invoice = si.name
                    AND pc.docstatus = 1
            )
    """, filters, as_dict=1)

    if not pos_invoices:
        print("Tidak ada POS Invoice yang masuk report.")
        return

    invoice_names = [inv.name for inv in pos_invoices]

    tax_rows = frappe.db.sql("""
        SELECT
            parent,
            SUM(tax_amount) AS total_charge
        FROM `tabSales Taxes and Charges`
        WHERE
            parent IN %(invoices)s
            AND description = 'POS Charge'
        GROUP BY parent
    """, {
        "invoices": invoice_names
    }, as_dict=1)

    tax_map = {
        row.parent: row.total_charge or 0
        for row in tax_rows
    }

    print("\n" + "=" * 100)
    print("DEBUG UANG CHARGE KREDIT")
    print("Tanggal:", date)
    print("=" * 100)

    total = 0
    jumlah_invoice = 0

    for inv in pos_invoices:

        charge = tax_map.get(inv.name, 0)

        if charge:
            print(
                "Invoice:", inv.name,
                "| Owner:", inv.owner,
                "| Return:", inv.is_return,
                "| POS Profile:", inv.pos_profile,
                "| Charge Kredit:", charge
            )

            total += charge
            jumlah_invoice += 1

    print("-" * 100)
    print("TOTAL UANG CHARGE KREDIT:", total)
    print("JUMLAH INVOICE:", jumlah_invoice)
    print("=" * 100)