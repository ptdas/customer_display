import frappe
from frappe.core.doctype.data_import.data_import import DataImport


def create_fast_data_import(doctype_name, file_url_or_id, import_type="Insert New Records"):
    """Membuat dokumen Data Import secara cepat tanpa validasi berlebih.

    :param doctype_name: Target DocType yang ingin di-import (misal: 'Item',
    'Customer')
    :param file_url_or_id: URL File atau File ID (misal: '/files/my_import.csv')
    :param import_type: 'Insert New Records' atau 'Update Existing Records'
    """
    # 1. Pastikan path/URL file valid
    file_doc = None
    if file_url_or_id.startswith("/files/"):
        file_url = file_url_or_id
    else:
        # Jika yang dimasukkan adalah nama/ID File DocType
        file_doc = frappe.get_doc("File", file_url_or_id)
        file_url = file_doc.file_url

    # 2. Buat dokumen Data Import baru
    doc = frappe.new_doc("Data Import")
    doc.reference_doctype = doctype_name
    doc.import_type = import_type
    doc.import_file = file_url
    doc.status = "Pending"
    doc.submit_after_import=1
    # 3. Bypass validasi bawaan saat save menggunakan flags
    doc.flags.ignore_validate = True
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True

    # Simpan langsung ke database
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    print(
        f"Data Import berhasil dibuat dengan ID: {doc.name} untuk DocType: {doctype_name}"
    )
    return doc.name


def run_data_import_now(data_import_id):
    """Menjalankan proses import secara background/langsung via CLI."""
    doc = frappe.get_doc("Data Import", data_import_id)
    # Menjalankan pemrosesan data import
    doc.start_import()
    frappe.db.commit()
    print(f"Proses import untuk {data_import_id} telah dimulai di background.")
