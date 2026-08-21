"""Company vendor per sisi (BJB / BJM), tahan di site gabungan maupun terpisah.

Sebelum site dipecah, tiap Supplier menyimpan sepasang company: sisi BJB di
`custom_vendor_company`, sisi BJM di `custom_vendor_company_bjm`. Sesudah
`erp_alan` dipecah jadi `bjb_alan` dan `bjm_alan`, tiap site cuma memegang satu
grup - field `_bjm` dibuang dan satu-satunya sisi yang tersisa disimpan di
`custom_vendor_company` di KEDUA site.

Semua kode yang dulu memilih field berdasarkan sisi harus lewat sini supaya
satu basis kode melayani ketiga site: `erp_alan` yang masih gabungan tetap
dipakai sebagai jalan mundur, dua site hasil pecah dipakai sehari-hari.
Pembeda site-nya cuma satu: ada tidaknya field `_bjm` pada Supplier.
"""

import frappe

PLAIN = "custom_vendor_company"
BJM = "custom_vendor_company_bjm"


def site_masih_gabungan():
    """True kalau site ini masih memegang BJB dan BJM sekaligus."""
    return frappe.get_meta("Supplier").has_field(BJM)


def vendor_company_field(parent_company):
    """Nama field yang menyimpan company vendor untuk sisi `parent_company`.

    Di site hasil pecah selalu `custom_vendor_company` - sisi yang tidak ada
    di site itu tidak bisa terpilih karena `parent_company` adalah Link ke
    Company, dan company seberang sudah tidak ada di sana.
    """
    if not site_masih_gabungan():
        return PLAIN
    return BJM if parent_company == "BJM" else PLAIN


def get_vendor_company(supplier, parent_company):
    """Company vendor sisi `parent_company`, atau None kalau belum diset."""
    if not supplier:
        return None
    field = vendor_company_field(parent_company)
    if isinstance(supplier, str):
        return frappe.db.get_value("Supplier", supplier, field)
    return supplier.get(field)


def set_vendor_companies(doc, sisi_bjb, sisi_bjm):
    """Isi field vendor company pada `doc` sesuai bentuk site.

    Di site gabungan keduanya diisi. Di site hasil pecah cuma ada satu field,
    dan yang benar untuk diisi adalah nilai sisi yang tersisa - yang oleh
    split_company.py sudah dipindah ke setelan berlabel polos.
    """
    doc.custom_vendor_company = sisi_bjb
    if site_masih_gabungan():
        doc.set(BJM, sisi_bjm)
