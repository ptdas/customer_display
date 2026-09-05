# =============================================================================
# split_company.py - memecah erp_alan menjadi satu site per parent company.
#
# Dijalankan SETELAH backup produksi di-restore ke site kloning:
#   bench --site bjb.local execute split_company.keep --kwargs "{'side':'BJB'}"
#   bench --site bjm.local execute split_company.keep --kwargs "{'side':'BJM'}"
#
# DRY_RUN=1 (default) hanya melaporkan, tidak menghapus apa pun.
# Jalankan dry run dulu, baca laporannya, baru DRY_RUN=0.
#
# JANGAN dijalankan di produksi sebelum lolos di kloning lokal.
#
# Field berpasangan: sesudah pecah, KEDUA site memakai
# `Supplier.custom_vendor_company` saja - Custom Field `..._bjm` dihapus di
# sini berikut kolomnya. Itu menuntut app customer_display sudah memakai
# `customer_display.vendor_company` (site gabungan `erp_alan` tetap jalan
# dengan modul yang sama). Urutannya: deploy app dulu, baru split - kalau
# terbalik, hook Supplier menulis ke field yang sudah tidak ada.
#
# Field `_bjm` di AXTRA Settings ikut app (`axtra_settings.json`), jadi di
# sini nilainya saja yang dikosongkan; field-nya hilang kalau app membuangnya.
# =============================================================================
import os

import frappe
from frappe.model.dynamic_links import get_dynamic_link_map
from frappe.utils.nestedset import rebuild_tree

# Daftar eksplisit. Tidak pakai LIKE 'BJB%' karena EBP ikut BJB dan AEP ikut BJM,
# dan tidak pakai parent_company IS NULL karena BJM menyimpan string kosong.
TREE = {
    "BJB": ["BJB", "BJB1", "BJB2", "BJB3", "BJB4", "EBP"],
    "BJM": ["BJM", "AEP", "BJM1", "BJM2", "BJM3", "BJM4"],
}
ORPHANS = ["TEST"]  # bukan milik BJB maupun BJM - dibuang dari kedua site

# Doctype pohon yang barisnya ikut tersapu. Penghapusan lewat SQL mentah tidak
# memperbarui lft/rgt, jadi pohonnya harus disusun ulang setelahnya.
NESTED = {
    "Account": "parent_account",
    "Cost Center": "parent_cost_center",
    "Warehouse": "parent_warehouse",
    "Department": "parent_department",
}

DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"


def _log(msg):
    print(("[dry-run] " if DRY_RUN else "[live]    ") + msg)


def keep(side):
    """Pertahankan subtree `side`, buang sisanya."""
    if side not in TREE:
        frappe.throw("side harus 'BJB' atau 'BJM'")

    keep_list = TREE[side]
    drop_list = [c for s, cs in TREE.items() if s != side for c in cs] + ORPHANS

    actual = set(frappe.get_all("Company", pluck="name"))
    unknown = actual - set(keep_list) - set(drop_list)
    if unknown:
        # Company baru dibuat setelah audit ini. Berhenti - jangan menebak.
        frappe.throw(f"Company tak dikenal, perbarui TREE dulu: {sorted(unknown)}")

    _log(f"pertahankan {keep_list}")
    _log(f"buang      {drop_list}")

    _delete_transactions(drop_list)
    _consolidate_paired_fields(side)
    _sweep_company_columns(drop_list)
    _null_other_company_links(drop_list)
    _null_singles(drop_list, side)
    _sweep_dynamic_links(drop_list)
    _delete_companies(drop_list)

    if not DRY_RUN:
        rebuild_tree("Company", "parent_company")
        for dt, parent_field in NESTED.items():
            _log(f"susun ulang pohon {dt}")
            rebuild_tree(dt, parent_field)
        frappe.db.commit()

    # Paling akhir, SESUDAH commit. ALTER TABLE memicu implicit commit dan
    # frappe menolaknya selama masih ada tulisan yang menggantung
    # (ImplicitCommitError). Kalau melempar di tengah, commit penutup tidak
    # pernah jalan dan SEMUA sapuan SQL mentah ikut hilang - transaksi sudah
    # lenyap lewat TDR yang commit sendiri, tapi master-nya utuh kembali.
    _drop_bjm_fields()
    if not DRY_RUN:
        frappe.db.commit()

    _log("selesai")


def _sisa_transaksi(companies):
    """Berapa baris buku besar yang masih dipegang company-company ini."""
    if not companies:
        return 0
    return frappe.db.sql(
        """
        SELECT (SELECT COUNT(*) FROM `tabGL Entry`            WHERE company IN %(c)s)
             + (SELECT COUNT(*) FROM `tabStock Ledger Entry`  WHERE company IN %(c)s)
        """,
        {"c": companies},
    )[0][0]


def _bersihkan_tdr_mandek(drop_list):
    """Buang TDR yang tersangkut Queued/Running dari percobaan sebelumnya.

    Dua alasan. Pertama, ERPNext menolak membuat TDR kedua untuk company yang
    sama selama masih ada yang Queued/Running. Kedua, hook `validate` di
    hooks.py (check_for_running_deletion_job) memblokir SEMUA dokumen
    bercompany itu selama TDR-nya dianggap berjalan.
    """
    mandek = frappe.get_all(
        "Transaction Deletion Record",
        filters={"company": ["in", drop_list], "status": ["in", ["Queued", "Running"]]},
        pluck="name",
    )
    for name in mandek:
        _log(f"TDR mandek {name} dibuang")
        if DRY_RUN:
            continue
        doc = frappe.get_doc("Transaction Deletion Record", name)
        if doc.docstatus == 1:
            doc.cancel()
        doc.delete(ignore_permissions=True)
    if mandek and not DRY_RUN:
        frappe.db.commit()


def _delete_transactions(drop_list):
    """Transaction Deletion Record bawaan ERPNext, satu per company.

    Anak dulu, grup belakangan: TDR pada grup tidak menghapus milik anaknya.

    Dijalankan SINKRON lewat process_in_single_transaction. Tanpa itu, tiap
    tugas dipecah jadi background job berantai (enqueue_after_commit) dan
    skrip ini harus menunggu dalam dua fase - rumit dan rapuh.

    `submit()` saja TIDAK memulai penghapusan: on_submit cuma menyetel status
    ke Queued. Yang menjalankan rantainya adalah start_deletion_tasks(), yang
    di UI dipicu oleh tombol. Itu harus dipanggil sendiri.
    """
    _bersihkan_tdr_mandek(drop_list)

    for company in drop_list:
        if not frappe.db.exists("Company", company):
            continue
        if not _sisa_transaksi([company]):
            _log(f"{company} sudah bersih, TDR dilewati")
            continue
        if DRY_RUN:
            _log(f"TDR untuk {company}")
            continue

        tdr = frappe.new_doc("Transaction Deletion Record")
        tdr.company = company
        tdr.process_in_single_transaction = 1
        tdr.insert(ignore_permissions=True)
        tdr.submit()
        tdr.start_deletion_tasks()
        frappe.db.commit()
        _log(f"TDR {tdr.name} selesai untuk {company} (status {tdr.reload().status})")


def _sweep_company_columns(drop_list):
    """Sapu bersih semua tabel yang punya kolom `company`.

    Ini menangkap child table dan doctype app pihak ketiga yang tidak dikenali
    TDR - TDR hanya menelusuri field Link ke Company pada doctype induk.
    Versi-agnostik: dibaca dari information_schema, bukan dari daftar doctype
    yang di-hardcode.
    """
    rows = frappe.db.sql(
        """
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = DATABASE() AND column_name = 'company'
        """,
        as_dict=True,
    )
    for r in rows:
        table = r["table_name"]
        n = frappe.db.sql(
            f"SELECT COUNT(*) FROM `{table}` WHERE company IN %(c)s", {"c": drop_list}
        )[0][0]
        if not n:
            continue
        _log(f"  {table}: {n} baris")
        if not DRY_RUN:
            frappe.db.sql(
                f"DELETE FROM `{table}` WHERE company IN %(c)s", {"c": drop_list}
            )


# Pasangan field "sisi BJB / sisi BJM" milik app customer_display. Sesudah
# pecah tiap site cuma memegang satu grup, jadi yang bersuffiks _bjm dibuang
# dan nilainya dipindah ke field polos - di KEDUA site, supaya bjb_alan dan
# bjm_alan memakai nama field yang sama.
PAIRED_SINGLES = {
    "AXTRA Settings": [
        ("default_target_pkp_company", "default_target_pkp_company_bjm"),
        ("default_target_pitza_company", "default_target_pitza_company_bjm"),
    ],
}


def _consolidate_paired_fields(side):
    """Pindahkan nilai sisi yang bertahan ke field polos SEBELUM ada yang dihapus.

    Tiap Supplier menyimpan sepasang company - satu di grup BJB, satu di grup
    BJM - tapi mana yang masuk field polos dan mana yang masuk `_bjm` tidak
    konsisten. Cacahnya dari backup produksi 19 Agt 2026:

        custom_vendor_company / custom_vendor_company_bjm
        BJB4 / BJM4  1264      BJM4 / BJB4  890
        EBP  / AEP    301      AEP  / EBP   271
                               BJM1 / BJB1  129
                               BJM2 / BJB2  129
                               BJM3 / BJB3  110
        BJB  / BJB      2      BJB  / AEP     1      NULL / NULL     1

    1566 baris ikut penamaan field, 1529 baris kebalikannya - dan cabang 1/2/3
    seragam terbalik semua. Tanpa langkah ini split akan membuang nilai yang
    BENAR untuk separuh Supplier.

    Aturannya: pakai nilai dari field mana pun yang menunjuk company yang
    bertahan, taruh di field polos. Dipakai keep_list, bukan
    `parent_company = side`, supaya company induk (`BJB`/`BJM`) sendiri ikut
    terhitung bertahan - tiga Supplier menyimpannya di field polos.
    """
    keep_list = TREE[side]
    cond = """
        WHERE `custom_vendor_company_bjm` IN %(keep)s
          AND (`custom_vendor_company` IS NULL
               OR `custom_vendor_company` NOT IN %(keep)s)
    """
    n = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabSupplier` {cond}", {"keep": keep_list}
    )[0][0]
    _log(f"  Supplier.custom_vendor_company: {n} nilai dipindah dari _bjm")
    if n and not DRY_RUN:
        frappe.db.sql(
            f"""
            UPDATE `tabSupplier`
            SET `custom_vendor_company` = `custom_vendor_company_bjm`
            {cond}
            """,
            {"keep": keep_list},
        )

    # Doctype Single - nilainya di tabSingles. Harus dibaca di sini, sebelum
    # _null_singles mengosongkan yang menunjuk company seberang.
    for dt, pairs in PAIRED_SINGLES.items():
        for plain, bjm in pairs:
            v_plain = frappe.db.get_single_value(dt, plain)
            v_bjm = frappe.db.get_single_value(dt, bjm)
            if v_plain in keep_list or v_bjm not in keep_list:
                continue
            _log(f"  {dt}.{plain} <- {bjm} ({v_bjm})")
            if not DRY_RUN:
                frappe.db.set_single_value(dt, plain, v_bjm)


def _null_other_company_links(drop_list):
    """Field Link->Company yang namanya BUKAN `company`.

    Ini rujukan, bukan kepemilikan - `tabCustomer.represents_company`,
    `tabAsset.asset_owner_company`, `tabSales Invoice.represents_company`.
    Barisnya TIDAK boleh dihapus: membuang Customer hanya karena
    represents_company menunjuk company seberang jelas salah. Yang dikosongkan
    nilainya, supaya tidak tertinggal sebagai link yatim.

    `tabCompany` dilewati - ditangani _delete_companies lalu rebuild_tree.
    Doctype Single juga terlewat dengan sendirinya karena nilainya tidak
    disimpan sebagai kolom; itu urusan _null_singles.
    """
    fields = frappe.db.sql(
        """
        SELECT DISTINCT CONCAT('tab', parent) AS tbl, fieldname AS col
        FROM tabDocField
        WHERE fieldtype = 'Link' AND options = 'Company' AND fieldname != 'company'
        UNION
        SELECT DISTINCT CONCAT('tab', dt), fieldname
        FROM `tabCustom Field`
        WHERE fieldtype = 'Link' AND options = 'Company' AND fieldname != 'company'
        """,
        as_dict=True,
    )
    for f in fields:
        tbl, col = f["tbl"], f["col"]
        # Hanya parent_company yang dilindungi - itu tulang punggung pohon,
        # diurus _delete_companies lalu rebuild_tree. Field Company lain di
        # tabCompany tetap harus dikosongkan, khususnya `existing_company`:
        # BJM menyimpan BJB di situ (dulu dibuat berdasarkan bagan akunnya),
        # dan selama itu ada, frappe.delete_doc menolak menghapus BJB.
        if tbl == "tabCompany" and col == "parent_company":
            continue
        ada = frappe.db.sql(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
            """,
            (tbl, col),
        )
        if not ada:
            continue
        n = frappe.db.sql(
            f"SELECT COUNT(*) FROM `{tbl}` WHERE `{col}` IN %(c)s", {"c": drop_list}
        )[0][0]
        if not n:
            continue
        _log(f"  {tbl}.{col}: {n} nilai dikosongkan")
        if not DRY_RUN:
            frappe.db.sql(
                f"UPDATE `{tbl}` SET `{col}` = NULL WHERE `{col}` IN %(c)s",
                {"c": drop_list},
            )


def _null_singles(drop_list, side):
    """Doctype Single menyimpan nilainya di tabSingles, bukan sebagai kolom."""
    rows = frappe.db.sql(
        "SELECT doctype, field FROM tabSingles WHERE value IN %(c)s",
        {"c": drop_list},
        as_dict=True,
    )
    for r in rows:
        # Global Defaults tidak boleh dikosongkan - site tanpa default company
        # akan menolak banyak transaksi. Diarahkan ke induk yang bertahan.
        if r.doctype == "Global Defaults" and r.field == "default_company":
            _log(f"  Global Defaults.default_company -> {side}")
            if not DRY_RUN:
                frappe.db.set_single_value("Global Defaults", "default_company", side)
            continue
        _log(f"  Singles {r.doctype}.{r.field} dikosongkan")
        if not DRY_RUN:
            frappe.db.set_single_value(r.doctype, r.field, None)


def _sweep_dynamic_links(drop_list):
    """Rujukan lewat dynamic link - sepasang kolom (doctype, nama).

    Tidak tertangkap sapuan mana pun sebelumnya: kolomnya tidak bernama
    `company` dan tipenya bukan Link ke Company. `frappe.delete_doc` memeriksa
    ini lewat check_if_doc_is_dynamically_linked, jadi kalau dibiarkan
    penghapusan Company akan ditolak dengan LinkExistsError.

    Barisnya dihapus, bukan dikosongkan: sebuah User Permission ke company
    yang sudah tidak ada tidak memberi izin apa pun, dan Comment pada dokumen
    yang lenyap tidak punya tempat menempel.

    Petanya diambil dari Frappe supaya ikut bergerak kalau ada doctype baru,
    bukan daftar tetap.
    """
    for df in get_dynamic_link_map().get("Company", []):
        tbl = "tab" + df.parent
        try:
            n = frappe.db.sql(
                f"SELECT COUNT(*) FROM `{tbl}` WHERE `{df.options}` = 'Company' "
                f"AND `{df.fieldname}` IN %(c)s",
                {"c": drop_list},
            )[0][0]
        except Exception:
            # Doctype Single atau tabel yang tidak punya kolomnya.
            continue
        if not n:
            continue
        _log(f"  {tbl}.{df.fieldname}: {n} baris")
        if not DRY_RUN:
            frappe.db.sql(
                f"DELETE FROM `{tbl}` WHERE `{df.options}` = 'Company' "
                f"AND `{df.fieldname}` IN %(c)s",
                {"c": drop_list},
            )


def _delete_companies(drop_list):
    """Hapus dokumen Company - ini yang membersihkan Account, Cost Center,
    dan Warehouse milik company tersebut lewat Company.on_trash."""
    for company in reversed(drop_list):  # anak dulu, grup terakhir
        if not frappe.db.exists("Company", company):
            continue
        if DRY_RUN:
            _log(f"delete Company {company}")
            continue
        frappe.delete_doc("Company", company, ignore_permissions=True)
        _log(f"Company {company} dihapus")


def _drop_bjm_fields():
    """Buang field bersuffiks _bjm sesudah nilainya pindah ke field polos.

    `Supplier.custom_vendor_company_bjm` cuma Custom Field - customer_display
    tidak punya fixtures - jadi penghapusannya menetap, tidak dibangkitkan
    ulang oleh `bench migrate`. frappe TIDAK ikut membuang kolomnya (on_trash
    Custom Field cuma menyapu Property Setter), jadi kolomnya di-drop manual
    supaya tidak tertinggal sebagai kolom yatim.

    AXTRA Settings beda: kedua field _bjm-nya ada di `axtra_settings.json`
    milik app, jadi di sini nilainya saja yang dikosongkan. Field-nya baru
    benar-benar hilang setelah app-nya ikut diubah - lihat kepala berkas.
    """
    cf = "Supplier-custom_vendor_company_bjm"
    if frappe.db.exists("Custom Field", cf):
        _log(f"hapus Custom Field {cf}")
        if not DRY_RUN:
            frappe.delete_doc("Custom Field", cf, ignore_permissions=True)

    ada = frappe.db.sql(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = 'tabSupplier'
          AND column_name = 'custom_vendor_company_bjm'
        """
    )
    if ada:
        _log("drop kolom tabSupplier.custom_vendor_company_bjm")
        if not DRY_RUN:
            # sql_ddl commit dulu baru jalan - itu jalur yang direstui frappe
            # untuk DDL.
            frappe.db.sql_ddl(
                "ALTER TABLE `tabSupplier` DROP COLUMN `custom_vendor_company_bjm`"
            )

    for dt, pairs in PAIRED_SINGLES.items():
        for _plain, bjm in pairs:
            _log(f"kosongkan {dt}.{bjm}")
            if not DRY_RUN:
                frappe.db.set_single_value(dt, bjm, None)
