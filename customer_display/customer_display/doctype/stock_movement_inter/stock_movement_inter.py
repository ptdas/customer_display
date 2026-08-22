# Copyright (c) 2026, DAS and contributors
# For license information, please see license.txt

"""Kiriman barang antar grup: BJB <-> BJM, selalu lintas site.

Sebelum `erp_alan` dipecah, satu dokumen bisa membuat Sales Invoice dan
Purchase Invoice sekaligus karena kedua company ada di site yang sama.
Sesudah pecah, sisi pengirim dan sisi penerima hidup di dua site, jadi
alurnya jadi begini:

    site pengirim                          site penerima
    -------------                          -------------
    validate  -> resolve_penerimaan() ...> jawab company + gudang per item
    on_submit -> Sales Invoice lokal
              -> terima_kiriman() .......> Purchase Invoice + submit
    on_cancel -> batalkan_kiriman() .....> cancel Purchase Invoice
              -> cancel Sales Invoice lokal

Urutannya sengaja dibalik antara submit dan cancel. Waktu submit, sisi lokal
duluan: kalau seberang gagal dihubungi, barang tercatat sudah keluar tapi
belum masuk - keadaan yang memang benar untuk barang yang sedang di jalan -
dan dokumen berstatus "Belum Terkirim" lalu diulang otomatis. Waktu cancel,
seberang duluan: kalau PI di sana menolak dibatalkan (sudah kena retur atau
pembayaran), pembatalan gagal seluruhnya dan tidak ada yang setengah jalan.

Pengiriman ulang aman karena setiap PI di seberang ditandai pasangan
(site asal, nama dokumen, company). Kalau balasan hilang di tengah jalan
padahal PI sudah jadi, panggilan berikutnya mengembalikan PI yang sama -
bukan bikin yang kedua.

Company penerima TIDAK ditentukan di sini. Yang menentukan site seberang,
dari `Item.custom_vendor` -> `Supplier.custom_vendor_company` miliknya
sendiri, persis seperti sisi pengirim menentukan company-nya. Karena
`Supplier.custom_pkp_type` sama di kedua site, item PKP selalu berpasangan
PKP (EBP <-> AEP) dan non-PKP selalu non-PKP (BJB4 <-> BJM4). Pasangan yang
menyilang berarti master Supplier kedua site sudah berbeda, dan itu ditolak.
"""

import json
from collections import OrderedDict

import frappe
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from customer_display import peer
from customer_display.vendor_company import get_vendor_company

STATUS_BELUM = "Belum Terkirim"
STATUS_TERKIRIM = "Terkirim"
STATUS_GAGAL = "Gagal Kirim"

METODE_RESOLVE = (
    "customer_display.customer_display.doctype.stock_movement_inter"
    ".stock_movement_inter.resolve_penerimaan"
)
METODE_KIRIM = (
    "customer_display.customer_display.doctype.stock_movement_inter"
    ".stock_movement_inter.terima_kiriman"
)
METODE_BATAL = (
    "customer_display.customer_display.doctype.stock_movement_inter"
    ".stock_movement_inter.batalkan_kiriman"
)
METODE_GUDANG = (
    "customer_display.customer_display.doctype.stock_movement_inter"
    ".stock_movement_inter.daftar_gudang"
)


class StockMovementInter(Document):
    # ------------------------------------------------------------------
    # sisi pengirim
    # ------------------------------------------------------------------

    def before_naming(self):
        self.naming_series = "STI-{0}-.YYYY.-".format(peer.grup_lokal())

    def validate(self):
        self.source_company = peer.grup_lokal()
        self.target_company = peer.grup_peer()
        self.peer_site = peer.setelan_peer()["url"]

        if not self.status:
            self.status = STATUS_BELUM

        self.validate_items()
        self.resolve_sisi_lokal()
        self.resolve_sisi_penerima()
        self.validate_company_mapping()

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Tabel item tidak boleh kosong."))

        for row in self.items:
            if not row.item_code:
                frappe.throw(
                    _("Item Code di baris {0} tidak boleh kosong.").format(row.idx)
                )
            if flt(row.qty) <= 0:
                frappe.throw(
                    _("Qty harus lebih dari 0 untuk item {0} (baris {1}).").format(
                        row.item_code, row.idx
                    )
                )

    def resolve_sisi_lokal(self):
        salah = []
        for row in self.items:
            hasil = resolve_lokal(row.item_code, self.from_warehouse)
            if hasil.get("error"):
                salah.append(_("Baris {0}: {1}").format(row.idx, hasil["error"]))
                continue
            row.from_company = hasil["company"]
            row.s_warehouse = hasil["warehouse"]
            row.rate = hasil["rate"]

        if salah:
            frappe.throw(
                "<br>".join(salah), title=_("Sisi {0}").format(peer.grup_lokal())
            )

    def resolve_sisi_penerima(self):
        try:
            jawaban = (
                peer.panggil(
                    METODE_RESOLVE,
                    items=[row.item_code for row in self.items],
                    gudang_dasar=self.to_warehouse,
                )
                or []
            )
        except peer.PeerTidakTerjangkau:
            # submit ikut menjalankan validate, jadi tanpa jalan keluar ini
            # seberang yang mati akan memblokir submit - padahal justru itu
            # keadaan yang ingin kita layani: catat keluarnya barang sekarang,
            # susulkan PI-nya nanti. Yang belum pernah resolve tetap ditolak;
            # dokumen baru tidak boleh dibuat tanpa tahu tujuannya.
            belum = [
                row.idx
                for row in self.items
                if not (row.to_company and row.t_warehouse)
            ]
            if belum:
                raise

            frappe.msgprint(
                _(
                    "Site {0} tidak terjangkau - memakai company dan gudang "
                    "tujuan dari penyimpanan terakhir."
                ).format(peer.grup_peer()),
                indicator="orange",
            )
            return

        if len(jawaban) != len(self.items):
            frappe.throw(
                _("Jawaban site {0} tidak sepadan dengan jumlah baris item.").format(
                    peer.grup_peer()
                )
            )

        salah = []
        for row, hasil in zip(self.items, jawaban):
            if hasil.get("error"):
                salah.append(_("Baris {0}: {1}").format(row.idx, hasil["error"]))
                continue

            row.to_company = hasil["company"]
            row.t_warehouse = hasil["warehouse"]

            # Item PKP harus mendarat di company PKP juga, begitu pula
            # sebaliknya. Kalau menyilang, `custom_pkp_type` supplier di kedua
            # site sudah berbeda - jangan diteruskan diam-diam, PPN-nya akan
            # salah di salah satu sisi.
            if bool(hasil.get("pkp")) != bool(_pkp(row.from_company)):
                salah.append(
                    _(
                        "Baris {0}: {1} berangkat dari {2} tapi mendarat di {3} - "
                        "status PKP kedua sisi tidak sama. Periksa <b>Tipe PKP</b> "
                        "supplier item ini di kedua site."
                    ).format(row.idx, row.item_code, row.from_company, row.to_company)
                )

        if salah:
            frappe.throw(
                "<br>".join(salah), title=_("Sisi {0}").format(peer.grup_peer())
            )

    def validate_company_mapping(self):
        peta = _peta_mapping()
        if not peta:
            frappe.throw(
                _("Stock Movement Inter Settings belum diisi di AXTRA Settings.")
            )

        for row in self.items:
            if not row.from_company or not row.to_company:
                continue

            kunci = (row.from_company, row.to_company)
            if kunci not in peta:
                frappe.throw(
                    _(
                        "Tidak ditemukan mapping dari <b>{0}</b> ke <b>{1}</b> di "
                        "AXTRA Settings (baris item ke-{2})."
                    ).format(row.from_company, row.to_company, row.idx)
                )

            if not peta[kunci].get("customer"):
                frappe.throw(
                    _(
                        "Mapping <b>{0}</b> ke <b>{1}</b> di AXTRA Settings belum "
                        "punya Customer POS (baris item ke-{2})."
                    ).format(row.from_company, row.to_company, row.idx)
                )

    # ------------------------------------------------------------------
    # submit
    # ------------------------------------------------------------------

    def on_submit(self):
        self.buat_faktur_penjualan()
        self.kirim(diam=True)

    def buat_faktur_penjualan(self):
        peta = _peta_mapping()

        for company, baris in _kelompokkan(self.items, "from_company").items():
            si = frappe.new_doc("Sales Invoice")
            si.company = company
            si.customer = peta[(company, baris[0].to_company)]["customer"]
            si.update_stock = 1
            si.set_posting_time = 1
            si.posting_date = self.posting_date
            si.posting_time = self.posting_time
            si.custom_stock_movement_inter = self.name

            for row in baris:
                si.append(
                    "items",
                    {
                        "item_code": row.item_code,
                        "qty": row.qty,
                        "rate": row.rate,
                        "warehouse": row.s_warehouse,
                    },
                )

            _terapkan_ppn(si, company, "Sales")

            si.insert(ignore_permissions=True)
            si.submit()

            for row in baris:
                row.db_set("sales_invoice_no", si.name, update_modified=False)

    def payload_kiriman(self):
        return {
            "site_asal": peer.site_lokal(),
            "grup_asal": peer.grup_lokal(),
            "dokumen": self.name,
            "posting_date": str(self.posting_date),
            "posting_time": str(self.posting_time or "00:00:00"),
            "items": [
                {
                    "idx": row.idx,
                    "item_code": row.item_code,
                    "qty": flt(row.qty),
                    "rate": flt(row.rate),
                }
                for row in self.items
            ],
        }

    def kirim(self, diam=False):
        """Dorong kiriman ke site penerima.

        `diam=True` dipakai dari on_submit: kegagalan tidak boleh membatalkan
        submit, karena Sales Invoice lokal sudah terlanjur - dan memang harus -
        tercatat. Yang gagal ditandai lalu diulang di latar belakang.
        """
        try:
            jawaban = peer.panggil(METODE_KIRIM, payload=self.payload_kiriman())
        except peer.PeerError as e:
            self.tandai_gagal(e, diam=diam)
            return None

        self.simpan_hasil(jawaban or {})
        return jawaban

    def simpan_hasil(self, jawaban):
        per_idx = {}
        for faktur in jawaban.get("faktur") or []:
            for idx in faktur.get("idx") or []:
                per_idx[int(idx)] = faktur.get("purchase_invoice")

        for row in self.items:
            nomor = per_idx.get(row.idx)
            if nomor:
                row.db_set("purchase_invoice_no", nomor, update_modified=False)

        self.db_set(
            {
                "status": STATUS_TERKIRIM,
                "dikirim_pada": now_datetime(),
                "pesan_terakhir": None,
            },
            update_modified=False,
        )

    def tandai_gagal(self, kesalahan, diam=False):
        boleh_diulang = isinstance(kesalahan, peer.PeerTidakTerjangkau)
        status = STATUS_BELUM if boleh_diulang else STATUS_GAGAL

        self.db_set(
            {"status": status, "pesan_terakhir": str(kesalahan)[:1000]},
            update_modified=False,
        )

        if not diam:
            raise kesalahan

        frappe.msgprint(
            _(
                "Sales Invoice sudah dibuat, tapi kiriman belum sampai ke site "
                "{0}:<br>{1}<br><br>Dokumen ditandai <b>{2}</b>{3}."
            ).format(
                peer.grup_peer(),
                kesalahan,
                status,
                _(" dan akan diulang otomatis") if boleh_diulang else "",
            ),
            title=_("Belum sampai ke seberang"),
            indicator="orange",
        )

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    def on_cancel(self):
        self.batalkan_di_peer()
        self.batalkan_faktur_penjualan()

    def batalkan_di_peer(self):
        try:
            peer.panggil(METODE_BATAL, site_asal=peer.site_lokal(), dokumen=self.name)
        except peer.PeerTidakTerjangkau:
            if self.status == STATUS_TERKIRIM:
                # PI-nya ada di sana dan tidak bisa kita batalkan sekarang.
                # Membiarkan pembatalan lewat akan meninggalkan barang masuk
                # tanpa barang keluar.
                raise
            frappe.msgprint(
                _(
                    "Site {0} tidak bisa dihubungi, tapi dokumen ini memang belum "
                    "pernah terkirim - pembatalan diteruskan."
                ).format(peer.grup_peer()),
                indicator="orange",
            )

        self.db_set("status", STATUS_BELUM, update_modified=False)

    def batalkan_faktur_penjualan(self):
        nomor = {row.sales_invoice_no for row in self.items if row.sales_invoice_no}
        for si_name in sorted(nomor):
            si = frappe.get_doc("Sales Invoice", si_name)
            if si.docstatus == 1:
                si.cancel()


# ----------------------------------------------------------------------
# dipakai kedua sisi
# ----------------------------------------------------------------------


def resolve_lokal(item_code, gudang_dasar=None):
    """Company, gudang, dan valuation rate item ini DI SITE INI.

    Tidak pernah melempar - kesalahannya dikembalikan sebagai `error` supaya
    pemanggil bisa mengumpulkan semua baris yang bermasalah sekaligus, dan
    supaya jawaban ke site seberang tidak berubah jadi HTTP 417 hanya karena
    satu item belum punya vendor.
    """
    vendor = frappe.db.get_value("Item", item_code, "custom_vendor")
    if not vendor:
        return {"error": _("Item {0} belum punya Vendor.").format(item_code)}

    company = get_vendor_company(vendor, peer.grup_lokal())
    if not company:
        return {
            "error": _("Supplier {0} belum punya Company Vendor di site {1}.").format(
                vendor, frappe.local.site
            )
        }

    if gudang_dasar:
        abbr = frappe.db.get_value("Company", company, "abbr") or ""
        dasar = gudang_dasar.rsplit(" - ", 1)[0]
        kandidat = "{0} - {1}".format(dasar, abbr)
        gudang = frappe.db.get_value("Warehouse", kandidat, "name")
        if not gudang:
            return {
                "error": _("Gudang {0} tidak ada di company {1}.").format(
                    kandidat, company
                )
            }
    else:
        gudang = frappe.db.get_value(
            "Item Default",
            {"parent": item_code, "company": company},
            "default_warehouse",
        ) or frappe.db.get_value(
            "Warehouse",
            {"company": company, "is_group": 0, "disabled": 0},
            "name",
            order_by="creation asc",
        )

    if not gudang:
        return {
            "error": _("Tidak ada gudang yang cocok untuk {0} di {1}.").format(
                item_code, company
            )
        }

    return {
        "company": company,
        "warehouse": gudang,
        "rate": _valuation_rate(item_code, gudang),
        "pkp": 1 if _pkp(company) else 0,
    }


def _valuation_rate(item_code, warehouse):
    rate = frappe.db.get_value(
        "Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate"
    )
    if rate:
        return flt(rate)

    terakhir = frappe.get_all(
        "Purchase Invoice Item",
        filters={"item_code": item_code, "docstatus": 1},
        fields=["valuation_rate"],
        order_by="creation desc",
        limit_page_length=1,
    )
    return flt(terakhir[0].valuation_rate) if terakhir else 0.0


def _pkp(company):
    """True kalau `company` adalah company PKP site ini.

    Sama dengan yang dipakai POS lewat `Supplier.custom_pkp_type`: supplier
    PKP diarahkan ke `default_target_pkp_company`, yang non ke
    `default_target_pitza_company`. Jadi status PKP sebuah kiriman tidak perlu
    disetel manual - ia sudah melekat pada company tujuan barangnya.
    """
    if not company:
        return False
    return company == frappe.get_cached_value(
        "AXTRA Settings", "AXTRA Settings", "default_target_pkp_company"
    )


def _terapkan_ppn(doc, company, jenis):
    """Pasang template PPN kalau `company` memang company PKP site ini."""
    if not _pkp(company):
        return

    field = "template_ppn_penjualan" if jenis == "Sales" else "template_ppn_pembelian"
    template = frappe.get_cached_value("AXTRA Settings", "AXTRA Settings", field)
    doctype = "{0} Taxes and Charges Template".format(jenis)

    if not template:
        frappe.throw(
            _(
                "Company <b>{0}</b> itu PKP, tapi <b>{1}</b> belum diisi di "
                "AXTRA Settings."
            ).format(company, frappe.get_meta("AXTRA Settings").get_label(field))
        )

    company_template = frappe.db.get_value(doctype, template, "company")
    if company_template != company:
        frappe.throw(
            _("{0} <b>{1}</b> milik company {2}, bukan {3}.").format(
                doctype, template, company_template, company
            )
        )

    doc.taxes_and_charges = template
    for baris in get_taxes_and_charges(doctype, template):
        doc.append("taxes", baris)


def _peta_mapping():
    peta = {}
    for row in frappe.get_cached_doc("AXTRA Settings").stock_movement_inter_settings:
        if row.dikirim_dari and row.dikirim_ke:
            peta[(row.dikirim_dari, row.dikirim_ke)] = {
                "customer": row.customer_pos,
                "supplier": row.supplier_pinv,
            }
    return peta


def _kelompokkan(baris, field):
    hasil = OrderedDict()
    for row in baris:
        hasil.setdefault(row.get(field), []).append(row)
    return hasil


def _urai(nilai):
    return json.loads(nilai) if isinstance(nilai, str) else nilai


def _pastikan_dari_peer(grup_asal):
    """Payload harus mengaku datang dari grup yang memang peer kita.

    Ini bukan pengganti kunci API - itu yang sebenarnya menjaga pintu. Ini
    menjaga dari salah kabel: site BJB yang tanpa sengaja diarahkan ke dirinya
    sendiri, atau ke site ketiga.
    """
    if grup_asal != peer.grup_peer():
        frappe.throw(
            _("Kiriman mengaku dari grup {0}, padahal peer site ini {1}.").format(
                grup_asal, peer.grup_peer()
            )
        )


# ----------------------------------------------------------------------
# dipanggil site seberang
# ----------------------------------------------------------------------


@frappe.whitelist()
def resolve_penerimaan(items, gudang_dasar=None):
    """Company + gudang penerima untuk tiap item, urut sesuai yang dikirim."""
    return [resolve_lokal(kode, gudang_dasar) for kode in (_urai(items) or [])]


@frappe.whitelist()
def daftar_gudang():
    """Gudang yang bisa jadi tujuan di site ini - untuk pemilih di layar."""
    return frappe.get_all(
        "Warehouse",
        filters={"is_group": 0, "disabled": 0},
        pluck="name",
        order_by="name asc",
    )


@frappe.whitelist()
def daftar_gudang_peer():
    """Gudang di site seberang - mengisi pemilih Gudang Tujuan di layar."""
    return peer.panggil(METODE_GUDANG) or []


@frappe.whitelist()
def terima_kiriman(payload):
    """Buat Purchase Invoice untuk kiriman dari site seberang.

    Idempoten: PI ditandai pasangan (site asal, dokumen asal, company), jadi
    panggilan ulang mengembalikan PI yang sudah ada alih-alih membuat yang
    kedua.
    """
    payload = _urai(payload)
    _pastikan_dari_peer(payload.get("grup_asal"))

    site_asal = payload["site_asal"]
    dokumen = payload["dokumen"]
    peta = _peta_mapping()

    baris_per_company = OrderedDict()
    for item in payload.get("items") or []:
        hasil = resolve_lokal(item["item_code"])
        if hasil.get("error"):
            frappe.throw(_("Baris {0}: {1}").format(item["idx"], hasil["error"]))
        item = dict(item, company=hasil["company"], warehouse=hasil["warehouse"])
        baris_per_company.setdefault(hasil["company"], []).append(item)

    faktur = []
    for company, baris in baris_per_company.items():
        idx = [b["idx"] for b in baris]

        sudah_ada = frappe.db.get_value(
            "Purchase Invoice",
            {
                "custom_stock_movement_inter": dokumen,
                "custom_origin_site": site_asal,
                "company": company,
                "docstatus": ["<", 2],
            },
            "name",
        )
        if sudah_ada:
            faktur.append(
                {
                    "company": company,
                    "purchase_invoice": sudah_ada,
                    "idx": idx,
                    "sudah_ada": 1,
                }
            )
            continue

        mapping = None
        for (dari, ke), nilai in peta.items():
            if ke == company and nilai.get("supplier"):
                mapping = nilai
                break

        if not mapping:
            frappe.throw(
                _(
                    "Belum ada mapping dengan Supplier PINV untuk penerimaan di "
                    "company <b>{0}</b> di AXTRA Settings."
                ).format(company)
            )

        pi = frappe.new_doc("Purchase Invoice")
        pi.company = company
        pi.supplier = mapping["supplier"]
        pi.update_stock = 1
        pi.set_posting_time = 1
        pi.posting_date = payload["posting_date"]
        pi.posting_time = payload.get("posting_time")
        pi.bill_date = payload["posting_date"]
        pi.due_date = payload["posting_date"]
        pi.custom_stock_movement_inter = dokumen
        pi.custom_origin_site = site_asal

        for b in baris:
            pi.append(
                "items",
                {
                    "item_code": b["item_code"],
                    "qty": b["qty"],
                    "rate": b["rate"],
                    "warehouse": b["warehouse"],
                },
            )

        _terapkan_ppn(pi, company, "Purchase")

        pi.insert(ignore_permissions=True, ignore_mandatory=True)
        pi.submit()

        faktur.append(
            {
                "company": company,
                "purchase_invoice": pi.name,
                "idx": idx,
                "sudah_ada": 0,
            }
        )

    return {"dokumen": dokumen, "faktur": faktur}


@frappe.whitelist()
def batalkan_kiriman(site_asal, dokumen):
    """Batalkan PI milik satu dokumen kiriman. Aman dipanggil berulang."""
    dibatalkan = []
    for nama in frappe.get_all(
        "Purchase Invoice",
        filters={
            "custom_stock_movement_inter": dokumen,
            "custom_origin_site": site_asal,
            "docstatus": 1,
        },
        pluck="name",
    ):
        pi = frappe.get_doc("Purchase Invoice", nama)
        pi.cancel()
        dibatalkan.append(nama)

    return {"dibatalkan": dibatalkan}


# ----------------------------------------------------------------------
# pengiriman ulang
# ----------------------------------------------------------------------


@frappe.whitelist()
def kirim_ulang(nama):
    """Tombol di layar. Melempar kalau gagal supaya operator lihat sebabnya."""
    doc = frappe.get_doc("Stock Movement Inter", nama)
    doc.check_permission("submit")

    if doc.docstatus != 1:
        frappe.throw(_("Hanya dokumen yang sudah disubmit yang bisa dikirim ulang."))
    if doc.status == STATUS_TERKIRIM:
        frappe.throw(_("Dokumen ini sudah terkirim."))

    doc.kirim(diam=False)
    return doc.status


def sapu_belum_terkirim():
    """Dijalankan penjadwal tiap jam untuk yang gagal karena jaringan.

    Yang berstatus "Gagal Kirim" sengaja dilewati - itu ditolak seberang
    karena isinya, jadi mengulang tanpa perbaikan cuma menumpuk error.
    """
    if not frappe.conf.get("alan_peer"):
        return

    for nama in frappe.get_all(
        "Stock Movement Inter",
        filters={"docstatus": 1, "status": STATUS_BELUM},
        pluck="name",
        order_by="creation asc",
        limit_page_length=50,
    ):
        try:
            frappe.get_doc("Stock Movement Inter", nama).kirim(diam=True)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(
                title="Gagal kirim ulang {0}".format(nama),
                message=frappe.get_traceback(),
            )
