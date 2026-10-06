# =============================================================================
# hapus_transaksi_bjb.py - kosongkan semua transaksi di bjb_alan, master utuh.
#
#   bench --site $BJB execute customer_display.hapus_transaksi_bjb.jalankan
#   DRY_RUN=0 bench --site $BJB execute customer_display.hapus_transaksi_bjb.jalankan
#
# DRY_RUN=1 (default) hanya melaporkan. Baris terakhir run sungguhan HARUS
# `[live]    selesai`.
#
# Kenapa bukan Transaction Deletion Record bawaan ERPNext: TDR menghapus SEMUA
# doctype yang punya field Link ke Company kecuali daftar kecualiannya - dan
# Pricing Rule tidak ada di daftar itu. 380 Pricing Rule hasil sync master
# akan ikut lenyap. Di sini daftarnya eksplisit.
#
# Penghapusan lewat SQL mentah, sama seperti TDR: dokumen submit TIDAK
# di-cancel (cancel membuat jurnal pembalik), baris ledger-nya ikut dihapus.
# Master (Item, Customer, Supplier, Pricing Rule, Item Price, Account,
# Warehouse, POS Profile, ...) tidak disentuh - diperiksa di akhir.
# =============================================================================
import os

import frappe

DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"

# Dokumen transaksi. Child table-nya ikut terhapus lewat `parenttype`.
TRANSAKSI = [
    # Accounts
    "Journal Entry",
    "Payment Entry",
    "Purchase Invoice",
    "Sales Invoice",
    "POS Opening Entry",
    "POS Closing Entry",
    "POS Invoice Merge Log",
    "Payment Request",
    "Payment Order",
    "Bank Transaction",
    "Period Closing Voucher",
    "Exchange Rate Revaluation",
    "Dunning",
    "Invoice Discounting",
    "Cashier Closing",
    "Repost Accounting Ledger",
    "Repost Payment Ledger",
    "Unreconcile Payment",
    "Process Payment Reconciliation",
    # Buying / Selling
    "Purchase Order",
    "Supplier Quotation",
    "Request for Quotation",
    "Sales Order",
    "Quotation",
    "Installation Note",
    # Stock
    "Purchase Receipt",
    "Delivery Note",
    "Stock Entry",
    "Stock Reconciliation",
    "Material Request",
    "Landed Cost Voucher",
    "Pick List",
    "Packing Slip",
    "Repost Item Valuation",
    "Serial and Batch Bundle",
    "Stock Reservation Entry",
    "Quality Inspection",
    "Delivery Trip",
    "Shipment",
    "Closing Stock Balance",
    # customer_display
    "POS Invoice",
    "Pinjaman",
    "Stock Movement Inter",
    "Stock Movement Intra",
    "Supplier Discount Claim",
    "POS Return Ledger",
]

# Ledger & turunan transaksi - bukan dokumen yang dibuka orang, tapi isinya
# murni hasil transaksi. Bin dihapus seperti TDR; dibuat ulang otomatis oleh
# transaksi stok berikutnya.
LEDGER = [
    "GL Entry",
    "Stock Ledger Entry",
    "Payment Ledger Entry",
    "Advance Payment Ledger Entry",
    "Bin",
]

# Doctype submit yang SENGAJA dibiarkan walau berisi: master, pengaturan,
# HR/Payroll, log sistem. Hanya dilaporkan kalau ada isinya.
DIBIARKAN = {
    "Transaction Deletion Record",
    "Process Subscription",
    "Process Deferred Accounting",
    "Budget",
    "Cost Center Allocation",
}

# Master yang harus utuh. Dihitung sebelum dan sesudah.
MASTER = [
    "Company", "Account", "Cost Center", "Warehouse", "POS Profile",
    "Item", "Item Barcode", "UOM Conversion Detail", "Item Default", "Item Price",
    "Pricing Rule", "Pricing Rule Item Code", "Coupon Code", "Customer",
    "Supplier", "Contact", "Address", "Brand", "Item Group", "Customer Group",
    "Mode of Payment", "Mode of Payment Account", "User", "Employee",
    "Sales Taxes and Charges Template", "Purchase Taxes and Charges Template",
    "Item Tax Template", "POS Auth", "Custom Field", "Property Setter",
]

# Tabel yang merujuk dokumen lewat pasangan (doctype, name). Barisnya yatim
# begitu dokumennya hilang.
REFERENSI = [
    ("tabVersion", "ref_doctype"),
    ("tabComment", "reference_doctype"),
    ("tabToDo", "reference_type"),
    ("tabDocShare", "share_doctype"),
    ("tabWorkflow Action", "reference_doctype"),
    ("tabFile", "attached_to_doctype"),
    ("__global_search", "doctype"),
]


def _log(msg):
    print(("[dry-run] " if DRY_RUN else "[live]    ") + msg)


def _ada_tabel(tbl):
    return bool(
        frappe.db.sql(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s",
            tbl,
        )
    )


def _ada_kolom(tbl, col):
    return bool(
        frappe.db.sql(
            """SELECT 1 FROM information_schema.columns
               WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s""",
            (tbl, col),
        )
    )


def _sql(query, values=None):
    # frappe membungkus None menjadi (None,) - jangan dikirim kalau kosong.
    return frappe.db.sql(query, values) if values is not None else frappe.db.sql(query)


def _hitung(tbl, where="1=1", values=None):
    return _sql(f"SELECT COUNT(*) FROM `{tbl}` WHERE {where}", values)[0][0]


def _hapus(tbl, where="1=1", values=None, label=None):
    n = _hitung(tbl, where, values)
    if n:
        _log(f"  {label or tbl}: {n}")
        if not DRY_RUN:
            _sql(f"DELETE FROM `{tbl}` WHERE {where}", values)
    return n


def _pastikan_site_bjb():
    grup = frappe.conf.get("alan_grup")
    if grup and grup != "BJB":
        frappe.throw(f"alan_grup site ini '{grup}', bukan BJB. Berhenti.")
    companies = set(frappe.get_all("Company", pluck="name"))
    if "BJB" not in companies or companies & {"BJM", "AEP", "BJM1", "BJM2", "BJM3", "BJM4"}:
        frappe.throw(f"Ini bukan site BJB (company: {sorted(companies)}). Berhenti.")


def _hitung_master():
    return {dt: _hitung(f"tab{dt}") for dt in MASTER if _ada_tabel(f"tab{dt}")}


def _lapor_yang_dibiarkan():
    """Doctype submit lain yang berisi data tapi tidak ada di daftar - supaya
    tidak ada yang luput diam-diam. Tidak dihapus."""
    semua = frappe.db.sql(
        "SELECT name FROM `tabDocType` WHERE is_submittable = 1 AND istable = 0 AND issingle = 0",
        pluck=True,
    )
    for dt in sorted(set(semua) - set(TRANSAKSI)):
        tbl = f"tab{dt}"
        if not _ada_tabel(tbl):
            continue
        n = _hitung(tbl)
        if n:
            alasan = "sengaja" if dt in DIBIARKAN else "TIDAK ADA DI DAFTAR - periksa"
            _log(f"  dibiarkan {dt}: {n} ({alasan})")


def jalankan():
    _pastikan_site_bjb()
    sebelum = _hitung_master()

    doctypes = [dt for dt in TRANSAKSI if _ada_tabel(f"tab{dt}")]
    ph = ", ".join(["%s"] * len(doctypes))

    _log("== dokumen transaksi")
    total = 0
    for dt in doctypes:
        total += _hapus(f"tab{dt}", label=dt)
    _log(f"  total dokumen: {total}")

    _log("== child table (parenttype = doctype transaksi)")
    anak = frappe.db.sql(
        """SELECT table_name FROM information_schema.columns
           WHERE table_schema = DATABASE() AND column_name = 'parenttype'
             AND table_name LIKE 'tab%%'""",
        pluck=True,
    )
    for tbl in sorted(anak):
        _hapus(tbl, f"parenttype IN ({ph})", doctypes)

    _log("== ledger")
    for dt in LEDGER:
        if _ada_tabel(f"tab{dt}"):
            _hapus(f"tab{dt}", label=dt)

    _log("== referensi yatim (version, comment, lampiran, dst.)")
    # Child Workflow Action dulu, selagi induknya masih bisa ditemukan.
    if _ada_tabel("tabWorkflow Action Permitted Role"):
        _hapus(
            "tabWorkflow Action Permitted Role",
            f"""parenttype = 'Workflow Action' AND parent IN (
                    SELECT name FROM `tabWorkflow Action` WHERE reference_doctype IN ({ph}))""",
            doctypes,
        )
    for tbl, col in REFERENSI:
        if _ada_tabel(tbl) and _ada_kolom(tbl, col):
            _hapus(tbl, f"`{col}` IN ({ph})", doctypes, label=f"{tbl}.{col}")

    _log("== tidak disentuh")
    _lapor_yang_dibiarkan()

    if not DRY_RUN:
        frappe.db.commit()
        frappe.clear_cache()

    sesudah = _hitung_master()
    geser = {dt: (sebelum[dt], sesudah[dt]) for dt in sebelum if sebelum[dt] != sesudah[dt]}
    if geser:
        # Tidak mungkin terjadi lewat skrip ini - kalau muncul, ada yang
        # menulis ke site selama skrip berjalan. Laporkan, jangan diam.
        _log(f"PERINGATAN master bergeser: {geser}")
    else:
        _log(f"master utuh: {len(sebelum)} doctype, jumlah baris sama")
    _log("selesai")
