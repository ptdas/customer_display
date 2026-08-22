// Copyright (c) 2026, DAS and contributors
// For license information, please see license.txt

// Sesudah split, company dan gudang penerima ada di site seberang - tidak bisa
// dipilih lewat Link. Gudang tujuan diisi dari daftar yang ditarik dari sana,
// sisanya (company asal/tujuan, gudang per baris, rate) diisi server waktu
// dokumen disimpan.

const METODE = "customer_display.customer_display.doctype.stock_movement_inter.stock_movement_inter";

frappe.ui.form.on("Stock Movement Inter", {
	onload(frm) {
		if (!frm.doc.posting_time) {
			frm.set_value("posting_time", frappe.datetime.now_time());
		}
		muat_gudang_tujuan(frm);
	},

	refresh(frm) {
		muat_gudang_tujuan(frm);
		tampilkan_status(frm);
		tombol_kirim_ulang(frm);
	},
});

function muat_gudang_tujuan(frm) {
	if (frm.doc.docstatus !== 0 || frm._gudang_peer) return;

	frappe.call({
		method: `${METODE}.daftar_gudang_peer`,
		callback(r) {
			if (!r.message) return;
			frm._gudang_peer = r.message;
			frm.set_df_property("to_warehouse", "options", r.message);
			frm.refresh_field("to_warehouse");
		},
		error() {
			// Site seberang sedang tidak terjangkau. Dokumen tetap boleh
			// diketik - server yang akan menolak waktu disimpan, dengan
			// pesan yang jelas.
			frm.set_df_property(
				"to_warehouse",
				"description",
				__("Site tujuan sedang tidak terjangkau, daftar gudang tidak bisa diambil.")
			);
		},
	});
}

function tampilkan_status(frm) {
	if (frm.doc.docstatus !== 1 || !frm.doc.status) return;

	const warna = {
		Terkirim: "green",
		"Belum Terkirim": "orange",
		"Gagal Kirim": "red",
	};

	frm.dashboard.clear_headline();
	frm.dashboard.set_headline_alert(
		frm.doc.pesan_terakhir
			? `${__(frm.doc.status)}: ${frappe.utils.escape_html(frm.doc.pesan_terakhir)}`
			: __(frm.doc.status),
		warna[frm.doc.status] || "blue"
	);
}

function tombol_kirim_ulang(frm) {
	if (frm.doc.docstatus !== 1 || frm.doc.status === "Terkirim") return;

	frm.add_custom_button(__("Kirim Ulang"), () => {
		frappe.call({
			method: `${METODE}.kirim_ulang`,
			args: { nama: frm.doc.name },
			freeze: true,
			freeze_message: __("Mengirim ke site tujuan..."),
			callback() {
				frm.reload_doc();
			},
		});
	}).addClass("btn-primary");
}
