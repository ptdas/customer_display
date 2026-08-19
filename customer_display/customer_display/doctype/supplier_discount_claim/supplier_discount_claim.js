frappe.ui.form.on("Supplier Discount Claim", {
	onload(frm) {
		if (!frm.doc.from_date) {
			frm.set_value(
				"from_date",
				frappe.datetime.month_start()
			);
		}

		if (!frm.doc.to_date) {
			frm.set_value(
				"to_date",
				frappe.datetime.month_end()
			);
		}
	},

	get_data(frm) {
		if (!frm.doc.from_date || !frm.doc.to_date) {
			frappe.msgprint(
				__("From Date dan To Date wajib diisi.")
			);
			return;
		}

		if (frm.doc.from_date > frm.doc.to_date) {
			frappe.msgprint(
				__("From Date tidak boleh lebih besar dari To Date.")
			);
			return;
		}

		frappe.call({
			method: "get_data",
			doc: frm.doc,
			freeze: true,
			freeze_message: __(
				"Sedang mengambil data, mohon tunggu..."
			),

			callback(r) {
				if (!r.message) {
					return;
				}

				frm.clear_table("claim_items");

				r.message.forEach(row => {
					let child = frm.add_child("claim_items");

					child.no_nota = row.no_nota;
					child.tanggal = row.tanggal;

					child.pricing_rule = row.pricing_rule;
					child.price_list = row.price_list;

					child.customer = row.customer;
					child.nama_customer = row.nama_customer;
					child.nama_user_penjual = row.nama_user_penjual;
					child.nama_creator = row.nama_creator;

					child.brand = row.brand;

					child.item_code = row.item_code;
					child.item_name = row.item_name;
					child.sales_invoice_item = row.sales_invoice_item;

					child.qty = row.qty;

					child.harga_jual = row.harga_jual;
					child.harga_setelah_diskon =
						row.harga_setelah_diskon;

					child.diskon = row.diskon;
					child.discount_percentage =
						row.discount_percentage;

					child.jumlah = row.jumlah;
				});

				frm.refresh_field("claim_items");

				frappe.show_alert({
					message: __(
						`${r.message.length} item berhasil diambil.`
					),
					indicator: "green"
				});
			}
		});
	}
});