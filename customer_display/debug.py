import frappe

@frappe.whitelist()
def check_return_accounts(return_invoice="RBJM26H040001"):
    ret = frappe.get_doc("POS Invoice", return_invoice)
    orig = frappe.get_doc("POS Invoice", ret.return_against)

    print("=== RETURN ===")
    print(ret.name)
    print(ret.debit_to)

    print()
    print("=== ORIGINAL ===")
    print(orig.name)
    print(orig.debit_to)

    return {
        "return_debit_to": ret.debit_to,
        "original_debit_to": orig.debit_to
    }


@frappe.whitelist()
def test_pos_return_real_submit(pos_invoice="RBJM26H040001"):
    original = frappe.get_doc("POS Invoice", pos_invoice)

    print("=== ORIGINAL ===")
    print("Name:", original.name)
    print("Company:", original.company)
    print("Is Return:", original.is_return)
    print("Return Against:", original.return_against)
    print()

    try:
        # copy dokumen supaya tidak mengubah dokumen asli
        doc = frappe.copy_doc(original)
        doc.name = None
        doc.docstatus = 0

        print("=== INSERT TEST DOC ===")
        doc.insert(ignore_permissions=True)
        print("Inserted:", doc.name)

        print()
        print("=== SUBMIT TEST DOC ===")

        doc.submit()

        print("SUBMIT SUCCESS")

        # rollback supaya tidak tersimpan
        frappe.db.rollback()

        return "SUBMIT SUCCESS"

    except Exception:
        print()
        print("=== REAL ERROR ===")
        print(frappe.get_traceback())

        frappe.db.rollback()

        return "SUBMIT FAILED"

@frappe.whitelist()
def test_pos_return_coa(pos_invoice="RBJM26H040001"):
    doc = frappe.get_doc("POS Invoice", pos_invoice)

    print("=== POS INVOICE DEBUG ===")
    print("Name       :", doc.name)
    print("Company    :", doc.company)
    print("Is Return  :", doc.is_return)
    print("Return Agst:", doc.return_against)
    print()

    print("=== ITEMS ===")
    for row in doc.items:
        acc_company = None

        if row.income_account:
            acc_company = frappe.db.get_value(
                "Account",
                row.income_account,
                "company"
            )

        status = "OK" if acc_company == doc.company else "MISMATCH"

        print(
            f"ITEM={row.item_code} | ACCOUNT={row.income_account} | "
            f"ACC_COMPANY={acc_company} | STATUS={status}"
        )

    print()
    print("=== TAXES ===")
    for row in doc.taxes:
        acc_company = None

        if row.account_head:
            acc_company = frappe.db.get_value(
                "Account",
                row.account_head,
                "company"
            )

        status = "OK" if acc_company == doc.company else "MISMATCH"

        print(
            f"TAX={row.description} | ACCOUNT={row.account_head} | "
            f"ACC_COMPANY={acc_company} | STATUS={status}"
        )

    print()
    print("=== POS PROFILE ===")
    if doc.pos_profile:
        profile_company = frappe.db.get_value(
            "POS Profile",
            doc.pos_profile,
            "company"
        )

        status = "OK" if profile_company == doc.company else "MISMATCH"

        print(
            f"POS_PROFILE={doc.pos_profile} | PROFILE_COMPANY={profile_company} | STATUS={status}"
        )

    print()
    print("=== COST CENTER ===")
    if doc.cost_center:
        cc_company = frappe.db.get_value(
            "Cost Center",
            doc.cost_center,
            "company"
        )

        status = "OK" if cc_company == doc.company else "MISMATCH"

        print(
            f"COST_CENTER={doc.cost_center} | CC_COMPANY={cc_company} | STATUS={status}"
        )

    print()
    print("=== VALIDATE GL ===")

    try:
        gl_entries = doc.get_gl_entries()

        for gle in gl_entries:
            acc_company = frappe.db.get_value(
                "Account",
                gle.account,
                "company"
            )

            status = "OK" if acc_company == doc.company else "MISMATCH"

            print(
                f"GL ACCOUNT={gle.account} | DR={gle.debit} | CR={gle.credit} | "
                f"ACC_COMPANY={acc_company} | STATUS={status}"
            )

    except Exception as e:
        print("GL ERROR:", frappe.get_traceback())

    return "Done"

def test_pos_submit():
    pos = frappe.get_doc("POS Invoice", "BJB26H040004")

    print("docstatus:", pos.docstatus)

    try:
        pos.submit()
        print("SUBMIT OK")
    except Exception:
        print(frappe.get_traceback())

@frappe.whitelist()
def repair_gl_entry():	
	doctype = "Sales Invoice"
	docname = "ACC-SINV-2025-00063-1"

	docu = frappe.get_doc(doctype, docname)	
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	docu.make_gl_entries()


@frappe.whitelist()
def create_tutup_kasir():
	from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import make_closing_entry_from_opening
	closing_entry = make_closing_entry_from_opening(frappe.get_doc("POS Opening Entry","POS-OPE-2025-00009"))
	closing_entry.save()
	
def start_import():
	doc = frappe.get_doc("Data Import","Stock Entry Import on 2026-01-01 22:40:58.797076")
	doc.start_import()

def start_import2():
	doc = frappe.get_doc("Data Import","Item Price Import on 2026-01-01 05:23:08.379058")
	doc.start_import()
def rename_customer():
	data = frappe.db.sql("select name , custom_kode from `tabCustomer` where name != custom_kode", as_list=1)
	count=0
	for row in data:
		frappe.rename_doc("Customer",row[0],row[1])
		frappe.db.commit()
		count=count+1
		print(count)

def debug():
    report = frappe.get_doc("Report", "Account Receivable Summary ALAN")

    print("REPORT NAME:", report.name)
    print("REPORT TYPE:", report.report_type)
    print("MODULE:", report.module)
    print("REF DOCTYPE:", report.ref_doctype)
    print("IS STANDARD:", report.is_standard)

def upload_ste(docname="Stock Entry Import on 2026-09-02 16:22:56.860458"):
    #  Stock Entry Import on 2026-09-02 12:18:33.009419
    #  Stock Entry Import on 2026-09-02 13:08:27.484219
    #  Stock Entry Import on 2026-09-02 13:30:58.977945
    #  Stock Entry Import on 2026-09-02 13:57:18.287758
    #  Stock Entry Import on 2026-09-02 14:12:51.310292

    # Stock Entry Import on 2026-09-02 14:40:25.224303
    # Stock Entry Import on 2026-09-02 15:05:57.972782
    # Stock Entry Import on 2026-09-02 15:29:12.925658
    # Stock Entry Import on 2026-09-02 15:57:07.834753
    # Stock Entry Import on 2026-09-02 16:22:56.860458
    doc = frappe.get_doc("Data Import", docname)
    doc.start_import()


import os
import openpyxl


def split_import_backend_alan(chunk_size=50000):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    input_file = os.path.join(
        current_dir,
        "Item Price Import per 31 ags 2026.xlsx"
    )

    output_dir = current_dir

    wb = openpyxl.load_workbook(input_file, read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    header = rows[0]
    data = rows[1:]

    total = len(data)
    total_files = (total + chunk_size - 1) // chunk_size

    print(f"Total data : {total}")
    print(f"Ukuran/file: {chunk_size}")
    print(f"Total file : {total_files}")

    for i in range(total_files):
        start = i * chunk_size
        end = min(start + chunk_size, total)

        output_file = os.path.join(
            output_dir,
            f"Item Price Import per 31 ags 2026 {i + 1}.xlsx"
        )

        new_wb = openpyxl.Workbook()
        new_ws = new_wb.active

        new_ws.append(header)

        for row in data[start:end]:
            new_ws.append(row)

        new_wb.save(output_file)
        new_wb.close()

        print(
            f"File {i + 1}: "
            f"{end - start} data "
            f"({start + 1}-{end}) -> {output_file}"
        )

    print("Selesai.")


def hapus_supplier_dari_excel():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "Hapus Supplier.xlsx")

    wb = openpyxl.load_workbook(
        file_path,
        read_only=True,
        data_only=True
    )

    ws = wb.active

    # Cari kolom ID
    id_col = None

    for col in range(1, ws.max_column + 1):
        header = ws.cell(1, col).value

        if header and str(header).strip() == "ID":
            id_col = col
            break

    if not id_col:
        frappe.throw("Kolom ID tidak ditemukan")

    deleted = 0
    not_found = 0
    failed = 0

    for row in range(2, ws.max_row + 1):
        supplier_id = ws.cell(row, id_col).value

        if not supplier_id:
            continue

        supplier_id = str(supplier_id).strip()

        if not frappe.db.exists("Supplier", supplier_id):
            print(f"[NOT FOUND] {supplier_id}")
            not_found += 1
            continue

        supplier_name = frappe.db.get_value(
            "Supplier",
            supplier_id,
            "supplier_name"
        )

        try:
            frappe.delete_doc(
                "Supplier",
                supplier_id,
                force=True
            )

            print(f"[DELETED] {supplier_id} - {supplier_name}")
            deleted += 1

        except Exception as e:
            print(f"[FAILED] {supplier_id} - {supplier_name} - {e}")
            failed += 1

    wb.close()

    frappe.db.commit()

    print("")
    print("========== HASIL ==========")
    print(f"Deleted   : {deleted}")
    print(f"Not Found : {not_found}")
    print(f"Failed    : {failed}")


from difflib import get_close_matches

def check_and_fix_uom_excel(
    input_file="Item Price Import per 31 ags 2026.xlsx",
    uom_column="UOM"
):
    """
    Cek UOM di Excel terhadap UOM yang ada di ERPNext.

    - Beda huruf besar/kecil -> otomatis diperbaiki
    - Typo ringan -> otomatis diperbaiki
    - UOM yang tidak ditemukan -> tidak diubah dan ditampilkan di rekap
    - Hasil disimpan ke file _fixed.xlsx
    """

    # ============================================================
    # FILE EXCEL DI FOLDER YANG SAMA DENGAN FILE PY
    # ============================================================

    current_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    input_file = os.path.join(
        current_dir,
        input_file
    )

    if not os.path.exists(input_file):
        frappe.throw(
            f"File Excel tidak ditemukan:\n{input_file}"
        )

    # ============================================================
    # AMBIL UOM DARI ERPNext
    # ============================================================

    system_uoms = frappe.get_all(
        "UOM",
        pluck="name"
    )

    uom_map = {
        uom.strip().lower(): uom
        for uom in system_uoms
        if uom
    }

    # ============================================================
    # BUKA EXCEL
    # ============================================================

    wb = openpyxl.load_workbook(input_file)
    ws = wb.active

    # ============================================================
    # CARI KOLOM UOM
    # ============================================================

    uom_col = None

    for cell in ws[1]:

        if (
            cell.value is not None
            and str(cell.value).strip().lower() == uom_column.lower()
        ):
            uom_col = cell.column
            break

    if uom_col is None:
        frappe.throw(
            f"Kolom '{uom_column}' tidak ditemukan di Excel."
        )

    # ============================================================
    # REKAP UOM YANG TIDAK DITEMUKAN
    # ============================================================

    not_found = set()

    # ============================================================
    # CEK SETIAP ROW
    # ============================================================

    for row_number in range(2, ws.max_row + 1):

        cell = ws.cell(
            row=row_number,
            column=uom_col
        )

        if cell.value is None:
            continue

        original = str(cell.value).strip()

        if not original:
            continue

        normalized = original.lower()

        # ========================================================
        # 1. UOM ADA, TERMASUK BEDA BESAR/KECIL
        # ========================================================

        if normalized in uom_map:

            correct_uom = uom_map[normalized]

            if original != correct_uom:
                cell.value = correct_uom

            continue

        # ========================================================
        # 2. COBA TYPO RINGAN
        # ========================================================

        matches = get_close_matches(
            normalized,
            list(uom_map.keys()),
            n=1,
            cutoff=0.85
        )

        if matches:

            matched = matches[0]
            correct_uom = uom_map[matched]

            cell.value = correct_uom

        else:

            # ====================================================
            # BENAR-BENAR TIDAK ADA
            # ====================================================

            not_found.add(original)

    # ============================================================
    # SIMPAN KE FILE _FIXED
    # ============================================================

    output_file = os.path.join(
        current_dir,
        "Item Price Import per 31 ags 2026_fixed.xlsx"
    )

    wb.save(output_file)

    # ============================================================
    # REKAP SINGKAT
    # ============================================================

    print()
    print("=" * 50)
    print("UOM CHECK SELESAI")
    print("=" * 50)

    if not_found:

        print("UOM YANG TIDAK ADA DI SYSTEM:")

        for uom in sorted(not_found):
            print(f"- {uom}")

    else:

        print("Semua UOM ditemukan di system.")

    print()
    print(f"Total UOM tidak ditemukan: {len(not_found)}")
    print(f"File hasil: {output_file}")

    return {
        "not_found": sorted(not_found),
        "output_file": output_file,
    }


def patch_item_price_item_name():
    print("=" * 70)
    print("PATCH ITEM PRICE - ITEM NAME")
    print("=" * 70)

    # Cek jumlah yang perlu diperbaiki
    before = frappe.db.sql("""
        SELECT COUNT(*)
        FROM `tabItem Price` ip
        INNER JOIN `tabItem` i
            ON i.name = ip.item_code
        WHERE COALESCE(ip.item_name, '') = ''
    """)[0][0]

    print(f"[CHECK] Item Price tanpa item_name : {before}")

    if not before:
        print("[DONE] Tidak ada data yang perlu dipatch.")
        return

    # Bulk UPDATE
    frappe.db.sql("""
        UPDATE `tabItem Price` ip
        INNER JOIN `tabItem` i
            ON i.name = ip.item_code
        SET
            ip.item_name = i.item_name,
            ip.modified = NOW(),
            ip.modified_by = %(modified_by)s
        WHERE COALESCE(ip.item_name, '') = ''
    """, {
        "modified_by": frappe.session.user
    })

    frappe.db.commit()

    # Verifikasi
    after = frappe.db.sql("""
        SELECT COUNT(*)
        FROM `tabItem Price` ip
        INNER JOIN `tabItem` i
            ON i.name = ip.item_code
        WHERE COALESCE(ip.item_name, '') = ''
    """)[0][0]

    patched = before - after

    print("-" * 70)
    print(f"[PATCHED] {patched}")
    print(f"[REMAIN]  {after}")
    print("[COMMIT] Berhasil")
    print("=" * 70)



import os
import openpyxl
import frappe


def merge_item_price_excel(
    input_file="Item Price (Import per 31 ags 2026) (2).xlsx",
    output_file=None,
):
    """
    Merge seluruh sheet Excel menjadi satu sheet.

    Ketentuan:
    - Semua sheet dianggap memiliki struktur kolom yang sama.
    - Baris pertama setiap sheet dianggap sebagai header.
    - Header hanya ditulis satu kali.
    - Data dari semua sheet digabungkan.
    - Ditambahkan kolom `source_sheet` untuk mengetahui asal sheet.
    """

    # ==========================================================
    # 1. FILE PATH
    # ==========================================================

    current_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    if not os.path.isabs(input_file):
        input_file = os.path.join(
            current_dir,
            input_file
        )

    if not os.path.exists(input_file):
        frappe.throw(
            f"File Excel tidak ditemukan:\n{input_file}"
        )

    # ==========================================================
    # 2. OUTPUT FILE
    # ==========================================================

    if output_file is None:

        base_name = os.path.splitext(
            os.path.basename(input_file)
        )[0]

        output_file = os.path.join(
            current_dir,
            f"{base_name}_merged.xlsx"
        )

    elif not os.path.isabs(output_file):

        output_file = os.path.join(
            current_dir,
            output_file
        )

    # ==========================================================
    # 3. LOAD EXCEL
    # ==========================================================

    wb = openpyxl.load_workbook(
        input_file,
        read_only=True,
        data_only=True,
    )

    sheet_names = wb.sheetnames

    if not sheet_names:

        wb.close()

        frappe.throw(
            "Excel tidak memiliki sheet."
        )

    print("=" * 70)
    print("MERGE ITEM PRICE EXCEL")
    print("=" * 70)
    print(f"File       : {input_file}")
    print(f"Jumlah tab : {len(sheet_names)}")
    print()

    # ==========================================================
    # 4. BUAT WORKBOOK BARU
    # ==========================================================

    output_wb = openpyxl.Workbook()

    output_ws = output_wb.active

    output_ws.title = "Item Price"

    # ==========================================================
    # 5. HEADER
    # ==========================================================

    first_sheet = wb[sheet_names[0]]

    headers = [
        cell.value
        for cell in first_sheet[1]
    ]

    # Tambahkan source sheet
    output_ws.append([
        *headers,
        "source_sheet",
    ])

    # ==========================================================
    # 6. MERGE SEMUA SHEET
    # ==========================================================

    total_rows = 0

    for sheet_name in sheet_names:

        ws = wb[sheet_name]

        print(
            f"[PROCESS] Sheet: {sheet_name}"
        )

        sheet_rows = 0

        # ------------------------------------------------------
        # Mulai dari row 2 karena row 1 adalah header
        # ------------------------------------------------------

        for row in ws.iter_rows(
            min_row=2,
            values_only=True
        ):

            # --------------------------------------------------
            # Skip baris kosong
            # --------------------------------------------------

            if not any(
                value is not None
                for value in row
            ):
                continue

            output_ws.append([
                *row,
                sheet_name,
            ])

            sheet_rows += 1
            total_rows += 1

        print(
            f"          {sheet_rows} row"
        )

    # ==========================================================
    # 7. SAVE
    # ==========================================================

    output_wb.save(
        output_file
    )

    output_wb.close()
    wb.close()

    # ==========================================================
    # 8. SUMMARY
    # ==========================================================

    print()
    print("=" * 70)
    print("MERGE SELESAI")
    print("=" * 70)

    print(
        f"Sheet digabung : {len(sheet_names)}"
    )

    print(
        f"Total row      : {total_rows}"
    )

    print(
        f"Output         : {output_file}"
    )

    print("=" * 70)

    return {
        "input_file": input_file,
        "output_file": output_file,
        "sheet_names": sheet_names,
        "total_rows": total_rows,
    }


import os
import openpyxl
import frappe

from datetime import datetime, date


def import_item_price_from_excel(
    input_file="Item Price (Import per 31 ags 2026) (2)_merged.xlsx",
    commit=True,
    batch_size=1000,
):
    """
    Import Item Price dari Excel secara batch menggunakan direct SQL.

    Mekanisme:
    - 1000 row per batch
    - Resume berdasarkan checkpoint
    - Row yang sudah committed tidak diproses lagi
    - Item divalidasi dengan 1 query per batch
    - Item Price existing diambil dengan 1 query per batch
    - Insert / update menggunakan direct SQL
    - Tidak menggunakan frappe.get_doc().insert()
    - Error validasi per row dicatat dan proses tetap lanjut
    - Setiap batch di-commit
    - Checkpoint ditulis setelah commit berhasil
    - Failed rows disimpan ke *_not_imported.xlsx

    Aturan UOM:
    - Exact match              -> import
    - Beda case                -> sesuaikan ke UOM system
    - Typo                     -> gagal
    - UOM tidak ditemukan      -> gagal
    - Tidak menggunakan fuzzy matching
    """

    # ==========================================================
    # 1. FILE PATH
    # ==========================================================

    current_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    if not os.path.isabs(input_file):
        input_file = os.path.join(
            current_dir,
            input_file
        )

    if not os.path.exists(input_file):
        frappe.throw(
            f"File Excel tidak ditemukan:\n{input_file}"
        )

    base_name = os.path.splitext(
        os.path.basename(input_file)
    )[0]

    checkpoint_file = os.path.join(
        current_dir,
        f"{base_name}_checkpoint.txt"
    )

    not_imported_file = os.path.join(
        current_dir,
        f"{base_name}_not_imported.xlsx"
    )

    print("=" * 70)
    print("IMPORT ITEM PRICE - DIRECT SQL BATCH MODE")
    print("=" * 70)
    print(f"File       : {input_file}")
    print(f"Batch size : {batch_size}")
    print(f"Checkpoint : {checkpoint_file}")
    print("=" * 70)

    # ==========================================================
    # 2. LOAD EXCEL
    # ==========================================================

    wb = openpyxl.load_workbook(
        input_file,
        read_only=True,
        data_only=True,
    )

    ws = wb.active

    if ws.max_row < 2:
        wb.close()

        frappe.throw(
            "Excel tidak memiliki data."
        )

    total_rows = ws.max_row - 1

    # ==========================================================
    # 3. BACA HEADER
    # ==========================================================

    headers = {}

    for col in range(
        1,
        ws.max_column + 1
    ):

        value = ws.cell(
            row=1,
            column=col
        ).value

        if value:

            header = str(
                value
            ).strip().lower()

            headers[header] = col

    # ==========================================================
    # 4. HELPER CARI KOLOM
    # ==========================================================

    def find_column(*names):

        for name in names:

            name = str(
                name
            ).strip().lower()

            if name in headers:
                return headers[name]

        return None

    # ==========================================================
    # 5. CARI KOLOM
    # ==========================================================

    item_code_col = find_column(
        "item_code",
        "item code",
        "item"
    )

    uom_col = find_column(
        "uom",
        "stock_uom",
        "stock uom"
    )

    price_list_col = find_column(
        "price_list",
        "price list"
    )

    price_col = find_column(
        "price_list_rate",
        "price list rate",
        "rate",
        "price"
    )

    currency_col = find_column(
        "currency"
    )

    buying_col = find_column(
        "buying"
    )

    selling_col = find_column(
        "selling"
    )

    valid_from_col = find_column(
        "valid_from",
        "valid from"
    )

    valid_upto_col = find_column(
        "valid_upto",
        "valid upto"
    )

    # ==========================================================
    # 6. VALIDASI KOLOM WAJIB
    # ==========================================================

    if not item_code_col:
        wb.close()
        frappe.throw(
            "Kolom Item Code tidak ditemukan."
        )

    if not uom_col:
        wb.close()
        frappe.throw(
            "Kolom UOM tidak ditemukan."
        )

    if not price_list_col:
        wb.close()
        frappe.throw(
            "Kolom Price List tidak ditemukan."
        )

    if not price_col:
        wb.close()
        frappe.throw(
            "Kolom Price List Rate / Rate / Price tidak ditemukan."
        )

    # ==========================================================
    # 7. AMBIL UOM SYSTEM SEKALI SAJA
    # ==========================================================

    system_uoms = frappe.get_all(
        "UOM",
        pluck="name"
    )

    uom_map = {
        str(uom).strip().lower(): uom
        for uom in system_uoms
        if uom
    }

    # ==========================================================
    # 8. CHECKPOINT
    # ==========================================================

    last_committed_row = 1

    if os.path.exists(checkpoint_file):

        try:

            with open(
                checkpoint_file,
                "r"
            ) as f:

                value = f.read().strip()

                if value:
                    last_committed_row = int(
                        value
                    )

        except Exception as e:

            print(
                f"[WARNING] Checkpoint tidak bisa dibaca: {e}"
            )

            last_committed_row = 1

    start_row = last_committed_row + 1

    if start_row > ws.max_row:

        wb.close()

        print(
            "\nSemua row sudah pernah di-commit."
        )

        return {
            "status": "already_completed",
            "total_rows": total_rows,
            "imported": 0,
            "updated_existing": 0,
            "corrected_case": 0,
            "skipped": 0,
            "last_committed_row": last_committed_row,
            "checkpoint_file": checkpoint_file,
            "not_imported_file": (
                not_imported_file
                if os.path.exists(not_imported_file)
                else None
            ),
        }

    print(
        f"\nResume dari row Excel: {start_row}"
    )

    print(
        f"Row terakhir committed sebelumnya: "
        f"{last_committed_row}"
    )

    # ==========================================================
    # 9. COUNTER
    # ==========================================================

    imported = 0
    updated_existing = 0
    corrected_case = 0
    skipped = 0

    total_processed_this_run = 0

    # ==========================================================
    # 10. FAILED EXCEL
    # ==========================================================

    original_headers = [
        ws.cell(
            row=1,
            column=col
        ).value
        for col in range(
            1,
            ws.max_column + 1
        )
    ]

    def save_failed_excel(failed_rows):

        if not failed_rows:
            return

        existing_failed = []

        if os.path.exists(
            not_imported_file
        ):

            try:

                old_wb = openpyxl.load_workbook(
                    not_imported_file
                )

                old_ws = old_wb.active

                for row in old_ws.iter_rows(
                    min_row=2,
                    values_only=True
                ):

                    existing_failed.append(
                        list(row)
                    )

                old_wb.close()

            except Exception as e:

                print(
                    f"[WARNING] Gagal membaca failed Excel lama: {e}"
                )

        failed_wb = openpyxl.Workbook()

        failed_ws = failed_wb.active

        failed_ws.title = "Not Imported"

        failed_ws.append([
            "Original Row",
            "Reason",
            "UOM",
            *original_headers
        ])

        for row in existing_failed:

            failed_ws.append(row)

        for failed in failed_rows:

            failed_ws.append([
                failed["row_number"],
                failed["reason"],
                failed["uom"],
                *failed["data"]
            ])

        failed_wb.save(
            not_imported_file
        )

        failed_wb.close()

    # ==========================================================
    # 11. HELPER VALUE
    # ==========================================================

    def normalize_string(value):

        if value is None:
            return ""

        return str(value).strip()

    def normalize_bool(value):

        if value is None:
            return 0

        if isinstance(value, bool):
            return int(value)

        return (
            1
            if str(value).strip().lower()
            in (
                "1",
                "yes",
                "true",
                "y"
            )
            else 0
        )

    # ==========================================================
    # 12. LOOP BATCH
    # ==========================================================

    current_row = start_row

    while current_row <= ws.max_row:

        batch_start = current_row

        batch_end = min(
            current_row + batch_size - 1,
            ws.max_row
        )

        print("\n")
        print("=" * 70)
        print(
            f"PROCESS BATCH "
            f"ROW {batch_start} - {batch_end}"
        )
        print("=" * 70)

        batch_imported = 0
        batch_updated = 0
        batch_corrected_case = 0
        batch_skipped = 0

        batch_failed_rows = []

        # ======================================================
        # 13. BACA ROW EXCEL KE MEMORY
        # ======================================================

        batch_rows = []

        print(
            f"[READ EXCEL] Mulai membaca row "
            f"{batch_start} - {batch_end}"
        )

        for row_number, row_data in enumerate(
            ws.iter_rows(
                min_row=batch_start,
                max_row=batch_end,
                values_only=True,
            ),
            start=batch_start,
        ):

            batch_rows.append({
                "row_number": row_number,
                "row_data": list(row_data),
            })

            if row_number % 100 == 0:
                print(
                    f"[READ EXCEL] Sudah membaca row {row_number}"
                )

        print(
            f"[READ EXCEL] Selesai membaca "
            f"{len(batch_rows)} row"
        )

        # ======================================================
        # 14. KUMPULKAN ITEM CODE UNTUK 1 QUERY
        # ======================================================

        item_codes = []

        for row in batch_rows:

            row_number = row["row_number"]
            row_data = row["row_data"]

            item_code = normalize_string(
                row_data[item_code_col - 1]
            )

            original_uom = normalize_string(
                row_data[uom_col - 1]
            )

            price_list = normalize_string(
                row_data[price_list_col - 1]
            )

            price = row_data[
                price_col - 1
            ]

            if (
                not item_code
                and not original_uom
                and not price_list
                and not price
            ):
                continue

            if item_code:
                item_codes.append(
                    item_code
                )

        item_codes = list(
            dict.fromkeys(item_codes)
        )

        # ======================================================
        # 15. QUERY ITEM SEKALI PER BATCH
        # ======================================================

        existing_items = set()

        if item_codes:

            placeholders = ", ".join(
                ["%s"] * len(item_codes)
            )

            rows = frappe.db.sql(
                f"""
                SELECT name,
                item_name
                FROM `tabItem`
                WHERE name IN ({placeholders})
                """,
                tuple(item_codes),
                as_dict=True,
            )

            existing_items = {
                row["name"]: row["item_name"]
                for row in rows
            }

        print(
            f"[ITEM CHECK] "
            f"{len(item_codes)} Item Code "
            f"→ {len(existing_items)} ditemukan"
        )

        # ======================================================
        # 16. VALIDASI EXCEL ROW
        # ======================================================

        valid_rows = []

        for row in batch_rows:

            row_number = row["row_number"]
            row_data = row["row_data"]

            original_uom = ""

            try:

                item_code = normalize_string(
                    row_data[item_code_col - 1]
                )

                original_uom = normalize_string(
                    row_data[uom_col - 1]
                )

                price_list = normalize_string(
                    row_data[price_list_col - 1]
                )

                price = row_data[
                    price_col - 1
                ]

                # --------------------------------------------------
                # ROW KOSONG
                # --------------------------------------------------

                if (
                    not item_code
                    and not original_uom
                    and not price_list
                    and not price
                ):
                    continue

                # --------------------------------------------------
                # ITEM CODE
                # --------------------------------------------------

                if not item_code:

                    raise Exception(
                        "Item Code kosong"
                    )

                # --------------------------------------------------
                # UOM
                # --------------------------------------------------

                if not original_uom:

                    raise Exception(
                        "UOM kosong"
                    )

                normalized_uom = (
                    original_uom.lower()
                )

                correct_uom = uom_map.get(
                    normalized_uom
                )

                if not correct_uom:

                    raise Exception(
                        f"UOM '{original_uom}' "
                        f"tidak ditemukan di system"
                    )

                if original_uom != correct_uom:

                    batch_corrected_case += 1
                    corrected_case += 1

                    print(
                        f"[CASE] Row {row_number}: "
                        f"{original_uom} -> {correct_uom}"
                    )

                # --------------------------------------------------
                # ITEM EXISTENCE
                # --------------------------------------------------

                if item_code not in existing_items:

                    raise Exception(
                        f"Item '{item_code}' "
                        f"tidak ditemukan"
                    )

                # --------------------------------------------------
                # PRICE LIST
                # --------------------------------------------------

                if not price_list:

                    raise Exception(
                        "Price List kosong"
                    )

                # --------------------------------------------------
                # PRICE
                # --------------------------------------------------

                if price is None or price == "":

                    raise Exception(
                        "Price kosong"
                    )

                price = frappe.utils.flt(
                    price
                )

                # --------------------------------------------------
                # CURRENCY
                # --------------------------------------------------

                currency = None

                if currency_col:

                    value = row_data[
                        currency_col - 1
                    ]

                    if value:
                        currency = normalize_string(
                            value
                        )

                # --------------------------------------------------
                # BUYING
                # --------------------------------------------------

                buying = 0

                if buying_col:

                    buying = normalize_bool(
                        row_data[
                            buying_col - 1
                        ]
                    )

                # --------------------------------------------------
                # SELLING
                # --------------------------------------------------

                selling = 0

                if selling_col:

                    selling = normalize_bool(
                        row_data[
                            selling_col - 1
                        ]
                    )

                # --------------------------------------------------
                # VALID FROM
                # --------------------------------------------------

                valid_from = None

                if valid_from_col:

                    value = row_data[
                        valid_from_col - 1
                    ]

                    if value:

                        valid_from = normalize_date(
                            value
                        )

                # --------------------------------------------------
                # VALID UPTO
                # --------------------------------------------------

                valid_upto = None

                if valid_upto_col:

                    value = row_data[
                        valid_upto_col - 1
                    ]

                    if value:

                        valid_upto = normalize_date(
                            value
                        )

                # --------------------------------------------------
                # SIMPAN ROW VALID
                # --------------------------------------------------

                valid_rows.append({
                    "row_number": row_number,
                    "item_code": item_code,
                    "item_name": existing_items[item_code],
                    "uom": correct_uom,
                    "price_list": price_list,
                    "price": price,
                    "currency": currency,
                    "buying": buying,
                    "selling": selling,
                    "valid_from": valid_from,
                    "valid_upto": valid_upto,
                    "data": row_data,
                })

            except Exception as e:

                batch_skipped += 1
                skipped += 1

                batch_failed_rows.append({
                    "row_number": row_number,
                    "reason": str(e),
                    "uom": original_uom,
                    "data": row_data,
                })

                print(
                    f"[FAILED] Row {row_number}: "
                    f"{str(e)}"
                )

                continue

        # ======================================================
        # 17. CEK DUPLIKAT DI DALAM EXCEL
        #
        # Kalau kombinasi yang sama muncul beberapa kali dalam
        # batch, row terakhir akan dipakai.
        # ======================================================

        unique_rows = {}

        for row in valid_rows:

            key = (
                row["item_code"],
                row["price_list"],
                row["uom"],
            )

            unique_rows[key] = row

        valid_rows = list(
            unique_rows.values()
        )

        print(
            f"[VALID] "
            f"{len(valid_rows)} row siap diproses"
        )

        # ======================================================
        # 18. QUERY EXISTING ITEM PRICE SEKALI PER BATCH
        # ======================================================

        existing_prices = {}

        if valid_rows:

            item_price_conditions = []
            item_price_values = []

            for row in valid_rows:

                item_price_conditions.append(
                    """
                    (
                        item_code = %s
                        AND price_list = %s
                        AND uom = %s
                    )
                    """
                )

                item_price_values.extend([
                    row["item_code"],
                    row["price_list"],
                    row["uom"],
                ])

            where_clause = " OR ".join(
                item_price_conditions
            )

            existing_price_rows = frappe.db.sql(
                f"""
                SELECT
                    name,
                    item_code,
                    price_list,
                    uom
                FROM `tabItem Price`
                WHERE {where_clause}
                """,
                tuple(item_price_values),
                as_dict=True,
            )

            for existing in existing_price_rows:

                key = (
                    existing["item_code"],
                    existing["price_list"],
                    existing["uom"],
                )

                existing_prices[key] = (
                    existing["name"]
                )

        print(
            f"[ITEM PRICE CHECK] "
            f"{len(existing_prices)} existing"
        )

        # ======================================================
        # 19. INSERT / UPDATE DIRECT SQL
        # ======================================================

        try:

            for row in valid_rows:

                key = (
                    row["item_code"],
                    row["price_list"],
                    row["uom"],
                )

                existing_name = existing_prices.get(
                    key
                )

                # ==================================================
                # UPDATE
                # ==================================================

                if existing_name:

                    frappe.db.sql(
                        """
                        UPDATE `tabItem Price`
                        SET
                            item_name = %s,
                            price_list_rate = %s,
                            modified = NOW(),
                            modified_by = %s
                        WHERE name = %s
                        """,
                        (
                            row["item_name"],
                            row["price"],
                            frappe.session.user,
                            existing_name,
                        )
                    )

                    batch_updated += 1
                    updated_existing += 1

                    batch_imported += 1
                    imported += 1

                    print(
                        f"[UPDATE] Row {row['row_number']}: "
                        f"{row['item_code']} | "
                        f"{row['price_list']} | "
                        f"{row['uom']} | "
                        f"{row['price']}"
                    )

                # ==================================================
                # INSERT
                # ==================================================

                else:

                    item_price_name = frappe.generate_hash(
                        length=10
                    )

                    frappe.db.sql(
                        """
                        INSERT INTO `tabItem Price`
                        (
                            name,
                            creation,
                            modified,
                            modified_by,
                            owner,
                            docstatus,
                            idx,
                            item_code,
                            item_name,
                            price_list,
                            price_list_rate,
                            currency,
                            uom,
                            buying,
                            selling,
                            valid_from,
                            valid_upto
                        )
                        VALUES
                        (
                            %s,
                            NOW(),
                            NOW(),
                            %s,
                            %s,
                            0,
                            0,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            item_price_name,
                            frappe.session.user,
                            frappe.session.user,
                            row["item_code"],
                            row["item_name"],
                            row["price_list"],
                            row["price"],
                            row["currency"],
                            row["uom"],
                            row["buying"],
                            row["selling"],
                            row["valid_from"],
                            row["valid_upto"],
                        )
                    )

                    batch_imported += 1
                    imported += 1

                    print(
                        f"[INSERT] Row {row['row_number']}: "
                        f"{row['item_code']} | "
                        f"{row['price_list']} | "
                        f"{row['uom']} | "
                        f"{row['price']}"
                    )

        except Exception as e:

            # ==================================================
            # ERROR DATABASE
            # ==================================================

            frappe.db.rollback()

            print("\n" + "!" * 70)
            print("[DATABASE ERROR]")
            print(str(e))
            print(
                f"Batch row {batch_start} - {batch_end} "
                f"di-ROLLBACK."
            )
            print(
                "Checkpoint TIDAK dipindahkan."
            )
            print("!" * 70)

            wb.close()

            raise

        # ======================================================
        # 20. SIMPAN FAILED EXCEL
        # ======================================================

        if batch_failed_rows:

            try:

                save_failed_excel(
                    batch_failed_rows
                )

                print(
                    f"[FAILED EXCEL] "
                    f"{len(batch_failed_rows)} row dicatat."
                )

            except Exception as e:

                print(
                    f"[WARNING] "
                    f"Gagal membuat Excel failed: "
                    f"{str(e)}"
                )

        # ======================================================
        # 21. COMMIT BATCH
        # ======================================================

        if commit:

            try:

                frappe.db.commit()

                print("\n" + "-" * 70)
                print(
                    f"[COMMIT BERHASIL] "
                    f"Row {batch_start} - {batch_end}"
                )
                print(
                    f"Insert/Update : {batch_imported}"
                )
                print(
                    f"Failed        : {batch_skipped}"
                )
                print("-" * 70)

            except Exception as e:

                frappe.db.rollback()

                print("\n" + "!" * 70)
                print("[COMMIT ERROR]")
                print(str(e))
                print(
                    "Batch di-ROLLBACK."
                )
                print(
                    "Checkpoint tidak diubah."
                )
                print("!" * 70)

                wb.close()

                return {
                    "status": "commit_failed",
                    "failed_batch_start": batch_start,
                    "failed_batch_end": batch_end,
                    "total_rows": total_rows,
                    "imported": imported,
                    "updated_existing": updated_existing,
                    "corrected_case": corrected_case,
                    "skipped": skipped,
                    "last_committed_row": last_committed_row,
                    "not_imported_file": (
                        not_imported_file
                        if os.path.exists(
                            not_imported_file
                        )
                        else None
                    ),
                }

        # ======================================================
        # 22. CHECKPOINT
        #
        # HANYA setelah commit berhasil.
        # ======================================================

        try:

            with open(
                checkpoint_file,
                "w"
            ) as f:

                f.write(
                    str(batch_end)
                )

            last_committed_row = batch_end

            print(
                f"[CHECKPOINT] "
                f"Row {batch_end} sudah aman."
            )

        except Exception as e:

            print("\n" + "!" * 70)
            print(
                "[WARNING] Database sudah COMMIT,"
            )
            print(
                "tetapi checkpoint gagal disimpan."
            )
            print(str(e))
            print(
                "Jangan hapus database."
            )
            print(
                "Checkpoint perlu diperbaiki "
                "sebelum menjalankan ulang."
            )
            print("!" * 70)

            wb.close()

            return {
                "status": "checkpoint_failed",
                "last_committed_row": last_committed_row,
                "total_rows": total_rows,
                "imported": imported,
                "updated_existing": updated_existing,
                "corrected_case": corrected_case,
                "skipped": skipped,
                "checkpoint_file": checkpoint_file,
                "not_imported_file": (
                    not_imported_file
                    if os.path.exists(
                        not_imported_file
                    )
                    else None
                ),
            }

        # ======================================================
        # 23. NEXT BATCH
        # ======================================================

        total_processed_this_run += (
            batch_end - batch_start + 1
        )

        current_row = batch_end + 1

        print(
            f"[NEXT] Lanjut ke row {current_row}"
        )

    # ==========================================================
    # 24. SELESAI
    # ==========================================================

    wb.close()

    print("\n")
    print("=" * 70)
    print("IMPORT ITEM PRICE SELESAI")
    print("=" * 70)

    print(
        f"Total row Excel        : {total_rows}"
    )

    print(
        f"Row diproses kali ini  : "
        f"{total_processed_this_run}"
    )

    print(
        f"Berhasil dibuat/update : {imported}"
    )

    print(
        f"Existing di-update     : {updated_existing}"
    )

    print(
        f"Case UOM diperbaiki    : {corrected_case}"
    )

    print(
        f"Gagal / tidak import   : {skipped}"
    )

    print(
        f"Last committed row     : "
        f"{last_committed_row}"
    )

    if os.path.exists(
        not_imported_file
    ):

        print(
            "\nFile daftar gagal:"
        )

        print(
            not_imported_file
        )

    else:

        print(
            "\nSemua data berhasil diproses."
        )

    print("=" * 70)

    return {
        "status": "success",
        "total_rows": total_rows,
        "processed_this_run": total_processed_this_run,
        "imported": imported,
        "updated_existing": updated_existing,
        "corrected_case": corrected_case,
        "skipped": skipped,
        "last_committed_row": last_committed_row,
        "checkpoint_file": checkpoint_file,
        "not_imported_file": (
            not_imported_file
            if os.path.exists(
                not_imported_file
            )
            else None
        ),
    }


# ==============================================================
# NORMALIZE DATE
# ==============================================================

def normalize_date(value):
    """
    Normalisasi tanggal Excel menjadi YYYY-MM-DD.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.strftime(
            "%Y-%m-%d"
        )

    if isinstance(value, date):
        return value.strftime(
            "%Y-%m-%d"
        )

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%y",
        "%d/%m/%y",
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt
            ).strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            continue

    raise ValueError(
        f"Format tanggal tidak dikenali: {value}"
    )