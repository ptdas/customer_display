# =============================================================================
# sync_master_bjm.py - salin master data bjm_alan ke bjb_alan.
#
# Sumbernya tabel staging `_bjm_*` yang dimuat dari buat_staging.py ke
# database bjb_alan. Dijalankan di site BJB:
#
#   bench --site $BJB execute customer_display.sync_master_bjm.jalankan
#   DRY_RUN=0 bench --site $BJB execute customer_display.sync_master_bjm.jalankan
#   bench --site $BJB execute customer_display.sync_master_bjm.bersihkan
#
# DRY_RUN=1 (default) hanya melaporkan. Baris terakhir run sungguhan HARUS
# `[live]    selesai`.
#
# Aturannya:
#   - BJM yang benar. Baris yang sudah ada di BJB ditimpa nilai BJM.
#   - Tidak pernah menghapus apa pun di BJB. Yang hanya ada di BJB dibiarkan.
#   - Yang terkait company TIDAK disalin: Item Default, akun/pajak per company,
#     harga pokok & PINV terakhir di Item (hasil transaksi BJM), POS Profile,
#     Mode of Payment Account, Warehouse, user & kasir BJM.
#   - Item Price TIDAK menimpa: hanya harga yang belum ada di BJB yang masuk.
#   - Pricing Rule menimpa, company/warehouse diterjemahkan ke sisi BJB.
#   - Supplier.custom_vendor_company diterjemahkan ke pasangannya di BJB.
# =============================================================================
import os

import frappe
from frappe.utils.nestedset import rebuild_tree

DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"
P = "_bjm_"

# Pasangan company, sama dengan split_company.TREE.
PETA_COMPANY = {
    "BJM": "BJB",
    "AEP": "EBP",
    "BJM1": "BJB1",
    "BJM2": "BJB2",
    "BJM3": "BJB3",
    "BJM4": "BJB4",
}

# Kolom yang tidak pernah ditimpa pada baris yang sudah ada.
KOLOM_IDENTITAS = {"name", "creation", "owner", "idx", "docstatus"}
KOLOM_UI = {"_user_tags", "_comments", "_assign", "_liked_by"}

# Kolom Item yang isinya hasil transaksi/akun company BJM - tidak disalin.
ITEM_KOLOM_COMPANY = {
    "valuation_rate",
    "last_purchase_rate",
    "custom_cogs",
    "custom_lcv",
    "custom_ppn",
    "custom_last_pinv",
    "custom_last_pinv_date",
    "custom_sales_template",  # Sales Taxes and Charges Template milik company
}

CUSTOMER_KOLOM_COMPANY = {"represents_company", "loyalty_program", "loyalty_program_tier"}
SUPPLIER_KOLOM_COMPANY = {"represents_company"}


def _log(msg):
    print(("[dry-run] " if DRY_RUN else "[live]    ") + msg)


# -----------------------------------------------------------------------------
# helper
# -----------------------------------------------------------------------------
def _kolom(tbl):
    return [
        r[0]
        for r in frappe.db.sql(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = %s
            ORDER BY ordinal_position
            """,
            tbl,
        )
    ]


def _kolom_bersama(dt, kecuali=()):
    tgt = set(_kolom(f"tab{dt}"))
    return [c for c in _kolom(f"{P}tab{dt}") if c in tgt and c not in kecuali]


def _names_baru(dt, syarat=""):
    """Nama di staging yang belum ada di BJB (perbandingan ikut collation DB,
    jadi `D66I` dan `d66i` dianggap sama - persis seperti MariaDB)."""
    where = f"AND ({syarat})" if syarat else ""
    return [
        r[0]
        for r in frappe.db.sql(
            f"""
            SELECT s.name FROM `{P}tab{dt}` s
            WHERE NOT EXISTS (SELECT 1 FROM `tab{dt}` t WHERE t.name = s.name) {where}
            """
        )
    ]


def _sisip_baru(dt, kecuali=(), syarat="", ekspr=None):
    """INSERT baris staging yang `name`-nya belum ada di BJB."""
    ekspr = ekspr or {}
    cols = _kolom_bersama(dt, kecuali)
    where = f"NOT EXISTS (SELECT 1 FROM `tab{dt}` t WHERE t.name = s.name)"
    if syarat:
        where += f" AND ({syarat})"
    n = frappe.db.sql(f"SELECT COUNT(*) FROM `{P}tab{dt}` s WHERE {where}")[0][0]
    _log(f"  {dt}: {n} baris baru")
    if n and not DRY_RUN:
        sel = ", ".join(ekspr.get(c, f"s.`{c}`") for c in cols)
        frappe.db.sql(
            f"""
            INSERT INTO `tab{dt}` ({", ".join(f"`{c}`" for c in cols)})
            SELECT {sel} FROM `{P}tab{dt}` s WHERE {where}
            """
        )
    return n


def _perbarui(dt, kecuali=(), syarat="", ekspr=None):
    """UPDATE baris yang sudah ada di BJB dengan nilai BJM, hanya yang beda.

    Pembandingan pakai BINARY supaya perubahan huruf besar/kecil
    (item_name "Velvet" -> "VELVET") ikut terbawa; collation bawaan
    menganggapnya sama.
    """
    ekspr = ekspr or {}
    cols = _kolom_bersama(dt, set(kecuali) | KOLOM_IDENTITAS | KOLOM_UI)
    if not cols:
        return 0

    def e(c):
        return ekspr.get(c, f"s.`{c}`")

    # `modified`/`modified_by` ikut disalin, tapi tidak dihitung sebagai
    # alasan untuk menyentuh baris - kalau cuma itu yang beda, lewati.
    pembanding = [c for c in cols if c not in ("modified", "modified_by")]
    beda = " OR ".join(f"NOT (BINARY t.`{c}` <=> BINARY {e(c)})" for c in pembanding)
    where = f"({beda})" + (f" AND ({syarat})" if syarat else "")
    base = f"FROM `tab{dt}` t JOIN `{P}tab{dt}` s ON t.name = s.name"

    n = frappe.db.sql(f"SELECT COUNT(*) {base} WHERE {where}")[0][0]
    _log(f"  {dt}: {n} baris diperbarui")
    if n:
        # Rincian per kolom - ini yang dibaca sebelum DRY_RUN=0.
        rinci = frappe.db.sql(
            "SELECT "
            + ", ".join(f"SUM(NOT (BINARY t.`{c}` <=> BINARY {e(c)}))" for c in pembanding)
            + f" {base} WHERE {where}"
        )[0]
        for c, k in zip(pembanding, rinci):
            if k:
                _log(f"      {c}: {int(k)}")
    if n and not DRY_RUN:
        frappe.db.sql(
            f"UPDATE `tab{dt}` t JOIN `{P}tab{dt}` s ON t.name = s.name "
            f"SET {', '.join(f't.`{c}` = {e(c)}' for c in cols)} WHERE {where}"
        )
    return n


def _sisip_anak(dt, parenttype, parents_sql, kunci):
    """Tambah baris child yang belum ada di BJB untuk parent terpilih.

    `kunci` = kolom yang menentukan "baris yang sama" selain parent, mis.
    ("barcode",) untuk Item Barcode. Tidak ada yang dihapus: baris child yang
    hanya ada di BJB tetap tinggal.
    """
    cols = _kolom_bersama(dt, KOLOM_UI)
    sama = " AND ".join(f"t.`{k}` = s.`{k}`" for k in kunci)
    where = f"""
        s.parenttype = '{parenttype}'
        AND s.parent IN ({parents_sql})
        AND NOT EXISTS (SELECT 1 FROM `tab{dt}` t
                        WHERE t.parent = s.parent AND t.parenttype = s.parenttype AND {sama})
        AND NOT EXISTS (SELECT 1 FROM `tab{dt}` t WHERE t.name = s.name)
    """
    n = frappe.db.sql(f"SELECT COUNT(*) FROM `{P}tab{dt}` s WHERE {where}")[0][0]
    _log(f"  {dt}: {n} baris child baru")
    if n and not DRY_RUN:
        frappe.db.sql(
            f"""
            INSERT INTO `tab{dt}` ({", ".join(f"`{c}`" for c in cols)})
            SELECT {", ".join(f"s.`{c}`" for c in cols)} FROM `{P}tab{dt}` s WHERE {where}
            """
        )
    return n


def _daftar_sql(names):
    if not names:
        return "NULL"
    return ", ".join(frappe.db.escape(n) for n in names)


# -----------------------------------------------------------------------------
# pengaman
# -----------------------------------------------------------------------------
def _pastikan_site_bjb():
    grup = frappe.conf.get("alan_grup")
    if grup and grup != "BJB":
        frappe.throw(f"alan_grup site ini '{grup}', bukan BJB. Berhenti.")
    companies = set(frappe.get_all("Company", pluck="name"))
    salah = companies & set(PETA_COMPANY)
    if salah or "BJB" not in companies:
        frappe.throw(f"Ini bukan site BJB (company: {sorted(companies)}). Berhenti.")
    if not frappe.db.sql("SHOW TABLES LIKE %s", f"{P}tabItem"):
        frappe.throw("Tabel staging _bjm_* belum dimuat. Muat bjm_master_staging.sql.gz dulu.")
    sumber = frappe.db.sql(f"SELECT sumber, dibuat FROM `{P}meta`")
    _log(f"sumber staging: {sumber[0][0] if sumber else '?'} (dimuat {sumber[0][1] if sumber else '?'})")


def _cek_konflik_nama():
    """Nama yang sama tapi isinya jelas beda dokumen - misalnya BJB sudah
    membuat Supplier V26-3222 atau Pricing Rule R2609-01 sendiri sejak backup.
    Menimpanya berarti mengganti dokumen orang lain. Berhenti, jangan menebak.

    Dokumen yang sama-sama berasal dari erp_alan (sebelum split) punya
    `creation` yang identik di kedua site; kalau beda, itu dua dokumen lain.
    """
    konflik = []
    for dt in ("Supplier", "Pricing Rule", "Coupon Code"):
        for name, bjb, bjm in frappe.db.sql(
            f"""
            SELECT t.name, t.creation, s.creation
            FROM `tab{dt}` t JOIN `{P}tab{dt}` s ON t.name = s.name
            WHERE t.creation <> s.creation
            """
        ):
            konflik.append(name)
            _log(f"  KONFLIK {dt} {name}: dibuat BJB {bjb} vs BJM {bjm} - dokumen berbeda")

    gudang = frappe.db.sql(
        f"""
        SELECT name, warehouse FROM `{P}tabPricing Rule`
        WHERE IFNULL(warehouse, '') <> '' AND warehouse NOT LIKE 'All Warehouses - %'
        """
    )
    for name, wh in gudang:
        _log(f"  KONFLIK Pricing Rule {name}: warehouse {wh} bukan gudang induk, tak bisa dipetakan")
    konflik += gudang

    tak_dikenal = frappe.db.sql(
        f"""
        SELECT DISTINCT custom_vendor_company FROM `{P}tabSupplier`
        WHERE IFNULL(custom_vendor_company, '') <> ''
          AND custom_vendor_company NOT IN ({_daftar_sql(PETA_COMPANY)})
        """
    )
    for (c,) in tak_dikenal:
        _log(f"  KONFLIK vendor company tanpa pasangan: {c}")

    barcode = frappe.db.sql(
        f"""
        SELECT s.barcode, s.parent, t.parent
        FROM `{P}tabItem Barcode` s JOIN `tabItem Barcode` t ON t.barcode = s.barcode
        WHERE t.parent <> s.parent
        """
    )
    for bc, bjm, bjb in barcode:
        _log(f"  KONFLIK barcode {bc}: di BJM milik {bjm}, di BJB milik {bjb}")

    n = len(konflik) + len(tak_dikenal) + len(barcode)
    if n and not DRY_RUN:
        frappe.throw(f"{n} konflik - lihat log di atas. Tidak ada yang diubah.")
    return n


# -----------------------------------------------------------------------------
# langkah
# -----------------------------------------------------------------------------
def _kustomisasi():
    _log("== kustomisasi")
    cf_baru = _names_baru("Custom Field")
    dts = sorted(
        {
            r[0]
            for r in frappe.db.sql(
                f"SELECT DISTINCT dt FROM `{P}tabCustom Field` WHERE name IN ({_daftar_sql(cf_baru)})"
            )
        }
    )
    report_baru = _names_baru("Report")

    _sisip_baru("Custom Field")
    _sisip_baru("Property Setter")
    _sisip_baru("Custom DocPerm")
    _sisip_baru("Report")
    _sisip_anak("Has Role", "Report", _daftar_sql(report_baru), ("role",))
    _sisip_baru("Print Format")

    # Custom Field yang dimasukkan lewat SQL belum punya kolom di tabel.
    # updatedb membaca meta (termasuk Custom Field) lalu ALTER TABLE; itu DDL,
    # jadi commit dulu (lihat ImplicitCommitError di split_company.py).
    for dt in dts:
        _log(f"  sinkron kolom tab{dt}")
        if not DRY_RUN:
            frappe.db.commit()
            frappe.clear_cache(doctype=dt)
            frappe.db.updatedb(dt)
    if not DRY_RUN:
        frappe.db.commit()
        frappe.clear_cache()


def _master_kecil():
    _log("== master kecil")
    _sisip_baru("UOM")
    _sisip_baru("Brand")
    _sisip_baru("Bank")

    # Pohon: parent harus sudah ada sebelum anaknya. Grup (is_group=1) dulu.
    for dt, parent_field in (("Item Group", "parent_item_group"), ("Customer Group", "parent_customer_group")):
        kecuali = {"lft", "rgt", "old_parent"}
        _sisip_baru(dt, kecuali, syarat="s.is_group = 1")
        _sisip_baru(dt, kecuali)
        if not DRY_RUN:
            _log(f"  susun ulang pohon {dt}")
            rebuild_tree(dt, parent_field)


def _supplier():
    _log("== supplier")
    peta = "CASE s.custom_vendor_company " + " ".join(
        f"WHEN {frappe.db.escape(a)} THEN {frappe.db.escape(b)}" for a, b in PETA_COMPANY.items()
    ) + " ELSE NULL END"
    ada_kolom = "custom_vendor_company" in _kolom("tabSupplier")
    _sisip_baru(
        "Supplier",
        SUPPLIER_KOLOM_COMPANY | KOLOM_UI,
        ekspr={"custom_vendor_company": peta} if ada_kolom else {},
    )

    # Supplier lama: vendor company milik BJB dipertahankan. Hanya kalau
    # status PKP-nya berubah di BJM, vendor company ikut pindah ke pasangannya
    # - persis yang dilakukan hook Supplier saat disimpan (PKP -> EBP,
    # Non -> BJB4). Tidak pernah dikosongkan.
    ekspr_lama = {}
    if ada_kolom:
        ekspr_lama["custom_vendor_company"] = f"""
            CASE WHEN BINARY t.custom_pkp_type <=> BINARY s.custom_pkp_type
                 THEN t.custom_vendor_company
                 ELSE COALESCE({peta}, t.custom_vendor_company) END"""
    _perbarui(
        "Supplier",
        SUPPLIER_KOLOM_COMPANY,
        syarat="t.supplier_name = s.supplier_name",
        ekspr=ekspr_lama,
    )

    # Supplier dinamai `format:V{YY}-{###}` - counternya tersimpan di
    # tabSeries dengan name kosong. Naikkan supaya supplier baru di BJB tidak
    # bertabrakan dengan V26-xxxx yang baru disalin.
    _naikkan_series("")


def _naikkan_series(key):
    """Counter BJB = max(BJB, BJM), supaya dokumen berikutnya yang dibuat di
    BJB tidak memakai nama yang baru saja disalin dari BJM."""
    bjm = frappe.db.sql(f"SELECT current FROM `{P}tabSeries` WHERE name = %s", key)
    if not bjm:
        return
    bjb = frappe.db.sql("SELECT current FROM `tabSeries` WHERE name = %s", key)
    lama = bjb[0][0] if bjb else None
    if lama is not None and lama >= bjm[0][0]:
        return
    _log(f"  tabSeries '{key}': {lama} -> {bjm[0][0]}")
    if DRY_RUN:
        return
    if bjb:
        frappe.db.sql("UPDATE `tabSeries` SET current = %s WHERE name = %s", (bjm[0][0], key))
    else:
        frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", (key, bjm[0][0]))


def _pricing_rule():
    _log("== pricing rule")
    peta_co = "CASE s.company " + " ".join(
        f"WHEN {frappe.db.escape(a)} THEN {frappe.db.escape(b)}" for a, b in PETA_COMPANY.items()
    ) + " ELSE NULL END"
    # Warehouse di BJM selalu gudang induk company-nya (All Warehouses - B /
    # - BJM4). Diganti gudang induk company pasangannya di BJB.
    peta_wh = f"""
        CASE WHEN IFNULL(s.warehouse, '') = '' THEN s.warehouse ELSE (
            SELECT w.name FROM `tabWarehouse` w
            WHERE w.company = ({peta_co}) AND w.is_group = 1
              AND IFNULL(w.parent_warehouse, '') = ''
            LIMIT 1) END
    """
    ekspr = {"company": peta_co, "warehouse": peta_wh}

    _sisip_baru("Pricing Rule", KOLOM_UI, ekspr=ekspr)
    _perbarui("Pricing Rule", ekspr=ekspr)

    # Child disamakan persis dengan BJM untuk rule yang ada di staging:
    # "ditimpa" berarti item yang dicabut dari promo di BJM juga dicabut di
    # BJB. Rule yang hanya ada di BJB tidak tersentuh.
    for child in ("Pricing Rule Item Code", "Pricing Rule Item Group", "Pricing Rule Brand"):
        cols = _kolom_bersama(child, KOLOM_UI)
        where = f"""t.parenttype = 'Pricing Rule'
            AND t.parent IN (SELECT name FROM `{P}tabPricing Rule`)"""
        lama = frappe.db.sql(f"SELECT COUNT(*) FROM `tab{child}` t WHERE {where}")[0][0]
        baru = frappe.db.sql(
            f"SELECT COUNT(*) FROM `{P}tab{child}` WHERE parenttype = 'Pricing Rule'"
        )[0][0]
        _log(f"  {child}: {lama} baris lama diganti {baru} baris BJM")
        if not DRY_RUN:
            frappe.db.sql(f"DELETE t FROM `tab{child}` t WHERE {where}")
            frappe.db.sql(
                f"""
                INSERT INTO `tab{child}` ({", ".join(f"`{c}`" for c in cols)})
                SELECT {", ".join(f"s.`{c}`" for c in cols)} FROM `{P}tab{child}` s
                WHERE s.parenttype = 'Pricing Rule'
                """
            )

    _sisip_baru("Coupon Code", KOLOM_UI)
    _perbarui("Coupon Code")

    for (key,) in frappe.db.sql(f"SELECT name FROM `{P}tabSeries` WHERE name LIKE 'R26%-'"):
        _naikkan_series(key)


def _item_price():
    """Tambah saja, TIDAK menimpa. Harga yang sudah ada di BJB - termasuk yang
    nilainya beda dengan BJM - dibiarkan.

    "Sudah ada" dinilai dari kunci yang dipakai ERPNext untuk menolak Item
    Price ganda: item, price list, UOM, customer, supplier, batch.
    """
    _log("== item price")
    cols = _kolom_bersama("Item Price", KOLOM_UI)
    where = """
        NOT EXISTS (
            SELECT 1 FROM `tabItem Price` t
            WHERE t.item_code = s.item_code AND t.price_list = s.price_list
              AND IFNULL(t.uom, '') = IFNULL(s.uom, '')
              AND IFNULL(t.customer, '') = IFNULL(s.customer, '')
              AND IFNULL(t.supplier, '') = IFNULL(s.supplier, '')
              AND IFNULL(t.batch_no, '') = IFNULL(s.batch_no, ''))
        AND NOT EXISTS (SELECT 1 FROM `tabItem Price` t WHERE t.name = s.name)
        AND EXISTS (SELECT 1 FROM `tabPrice List` p WHERE p.name = s.price_list)
    """
    # Saat dry-run item baru belum masuk, jadi syarat "item ada" dicek ke
    # staging juga - supaya angkanya sama dengan run sungguhan.
    where_item = f"""AND (EXISTS (SELECT 1 FROM `tabItem` i WHERE i.name = s.item_code)
                         OR EXISTS (SELECT 1 FROM `{P}tabItem` i WHERE i.name = s.item_code))"""
    rinci = frappe.db.sql(
        f"""SELECT s.price_list, COUNT(*) FROM `{P}tabItem Price` s
            WHERE {where} {where_item} GROUP BY s.price_list"""
    )
    for pl, n in rinci:
        _log(f"  Item Price {pl}: {n} harga baru")
    beda = frappe.db.sql(
        f"""
        SELECT COUNT(*) FROM `{P}tabItem Price` s JOIN `tabItem Price` t
          ON t.item_code = s.item_code AND t.price_list = s.price_list
         AND IFNULL(t.uom, '') = IFNULL(s.uom, '')
        WHERE t.price_list_rate <> s.price_list_rate
        """
    )[0][0]
    _log(f"  Item Price: {beda} harga beda nilai dengan BJM - DIBIARKAN nilai BJB")
    if not DRY_RUN and rinci:
        frappe.db.sql(
            f"""
            INSERT INTO `tabItem Price` ({", ".join(f"`{c}`" for c in cols)})
            SELECT {", ".join(f"s.`{c}`" for c in cols)} FROM `{P}tabItem Price` s
            WHERE {where} {where_item}
            """
        )


def _customer():
    _log("== customer")
    _sisip_baru("Customer", CUSTOMER_KOLOM_COMPANY | KOLOM_UI)
    _perbarui("Customer", CUSTOMER_KOLOM_COMPANY)


def _contact():
    _log("== contact")
    # Contact milik user yang tidak ada di BJB (kasir BJM) tidak ikut.
    syarat = "IFNULL(s.user, '') = '' OR EXISTS (SELECT 1 FROM `tabUser` u WHERE u.name = s.user)"
    baru = _names_baru("Contact", syarat)
    _sisip_baru("Contact", KOLOM_UI, syarat=syarat)
    daftar = _daftar_sql(baru)
    _sisip_anak("Contact Email", "Contact", daftar, ("email_id",))
    _sisip_anak("Contact Phone", "Contact", daftar, ("phone",))
    _sisip_anak("Dynamic Link", "Contact", daftar, ("link_doctype", "link_name"))


def _item():
    _log("== item")
    _sisip_baru("Item", ITEM_KOLOM_COMPANY | KOLOM_UI)
    # item_code tidak ditimpa: dua item di BJM cuma diganti huruf besarnya
    # (d66i -> D66I). `name` tidak ikut berubah, jadi item_code harus tetap
    # sama persis dengan name-nya.
    _perbarui("Item", ITEM_KOLOM_COMPANY | {"item_code"})

    semua_item = f"SELECT name FROM `{P}tabItem`"
    _sisip_anak("Item Barcode", "Item", semua_item, ("barcode",))
    _sisip_anak("UOM Conversion Detail", "Item", semua_item, ("uom",))

    # Faktor konversi yang berubah di BJM untuk UOM yang sama.
    n = frappe.db.sql(
        f"""
        SELECT COUNT(*) FROM `tabUOM Conversion Detail` t
        JOIN `{P}tabUOM Conversion Detail` s
          ON t.parent = s.parent AND t.parenttype = s.parenttype AND t.uom = s.uom
        WHERE s.parenttype = 'Item' AND t.conversion_factor <> s.conversion_factor
        """
    )[0][0]
    _log(f"  UOM Conversion Detail: {n} faktor konversi diperbarui")
    if n and not DRY_RUN:
        frappe.db.sql(
            f"""
            UPDATE `tabUOM Conversion Detail` t
            JOIN `{P}tabUOM Conversion Detail` s
              ON t.parent = s.parent AND t.parenttype = s.parenttype AND t.uom = s.uom
            SET t.conversion_factor = s.conversion_factor
            WHERE s.parenttype = 'Item' AND t.conversion_factor <> s.conversion_factor
            """
        )


def jalankan():
    _pastikan_site_bjb()
    _cek_konflik_nama()

    _kustomisasi()
    _master_kecil()
    _supplier()
    _customer()
    _contact()
    _item()
    _item_price()
    _pricing_rule()

    if not DRY_RUN:
        frappe.db.commit()
        frappe.clear_cache()
    _log("selesai")


def bersihkan():
    """Buang tabel staging sesudah sinkron lolos diperiksa."""
    tabel = [r[0] for r in frappe.db.sql("SHOW TABLES LIKE '\\_bjm\\_%'")]
    for t in tabel:
        print(f"drop {t}")
        frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `{t}`")
