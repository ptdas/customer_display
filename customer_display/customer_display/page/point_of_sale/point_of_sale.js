frappe.provide("erpnext.PointOfSale");

window.pos_grosir_mode = false;
window._last_grosir_state = null;

frappe.pages["point-of-sale"].on_page_load = function (wrapper) {

    inject_pos_hide_net_and_tax_css();
	
	if (!sessionStorage.getItem("pos_first_load_done")) {
      // mark that we've reloaded once
      sessionStorage.setItem("pos_first_load_done", "true");
      // reload immediately
      window.location.reload();
      return; // stop further init until after reload
    }

	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Point of Sale"),
		single_column: true,
	});

	frappe.require("pos_customer_display.bundle.js", function () {
		wrapper.pos = new erpnext.PointOfSale.Controller(wrapper);
		window.cur_pos = wrapper.pos;

        // =====================================================
        // POS INVOICE OVERRIDE AUTHORIZATION
        // 1 AUTH = 1 ACTIVE POS INVOICE
        // =====================================================

        window.cur_pos.pos_authorization = {
            authorized: false,
            auth_provider: null,
            auth_in_progress: null
        };

        window.cur_pos.pos_auth_last_is_new = null;

        window.cur_pos.authorize_current_invoice = async function (
            reason = "POS Invoice Override Authorization"
        ) {

            const frm = this.frm || window.cur_frm;

            if (!frm || frm.doctype !== "POS Invoice") {
                return false;
            }

            if (this.pos_authorization?.authorized) {
                return true;
            }

            if (this.pos_authorization?.auth_in_progress) {
                return await this.pos_authorization.auth_in_progress;
            }

            this.pos_authorization.auth_in_progress =
                new Promise(resolve => {

                    let finished = false;
                    let submitted = false;
                    let dialog = null;

                    const finish = (result) => {

                        if (finished) return;

                        finished = true;

                        this.pos_authorization.auth_in_progress = null;

                        resolve(result);
                    };

                    frappe.dom.unfreeze();

                    dialog = frappe.prompt(
                        [
                            {
                                fieldname: "code",
                                fieldtype: "Password",
                                label: __("Authorization Code"),
                                reqd: 1
                            }
                        ],

                        values => {

                            submitted = true;

                            frappe.call({
                                method: "customer_display.api.verify_pos_code_auth",

                                args: {
                                    pos_profile: frm.doc.pos_profile,
                                    code: values.code,
                                    description: "POS Invoice Override Authorization"
                                },

                                callback: r => {

                                    if (
                                        r.message &&
                                        r.message.valid === true
                                    ) {

                                        const child = frm.add_child(
                                            "custom_auth_provider"
                                        );

                                        child.auth_provider =
                                            r.message.auth_provider;

                                        child.description =
                                            __("POS Invoice Override Authorization");

                                        frm.refresh_field(
                                            "custom_auth_provider"
                                        );

                                        this.pos_authorization.authorized = true;

                                        this.pos_authorization.auth_provider =
                                            r.message.auth_provider;

                                        console.log(
                                            "[POS AUTH] Authorized:",
                                            r.message.auth_provider
                                        );

                                        finish(true);

                                    } else {

                                        frappe.msgprint({
                                            title: __("Authorization Failed"),
                                            message: __(
                                                "Authorization code is invalid or not permitted."
                                            ),
                                            indicator: "red"
                                        });

                                        finish(false);
                                    }
                                },

                                error: err => {

                                    console.error(
                                        "[POS AUTH] Verification error:",
                                        err
                                    );

                                    frappe.msgprint({
                                        title: __("Authorization Failed"),
                                        message: __(
                                            "Gagal melakukan verifikasi authorization."
                                        ),
                                        indicator: "red"
                                    });

                                    finish(false);
                                }
                            });
                        },

                        __(reason),
                        __("Submit")
                    );

                    // ============================================
                    // USER CLOSE DIALOG TANPA SUBMIT
                    // ============================================

                    if (dialog) {

                        dialog.onhide = () => {

                            if (!submitted && !finished) {

                                console.log(
                                    "[POS AUTH] Authorization dialog cancelled."
                                );

                                finish(false);
                            }
                        };
                    }
                });

            const result =
                await this.pos_authorization.auth_in_progress;

            this.pos_authorization.auth_in_progress = null;

            frappe.dom.unfreeze();

            return result;
        };


        // =====================================================
        // RECORD AUTHORIZED ACTION
        // =====================================================

        window.cur_pos.record_pos_authorization_action = function (
            action,
            item_row = null,
            extra = ""
        ) {

            const frm = this.frm || window.cur_frm;

            if (!frm || frm.doctype !== "POS Invoice") {
                return;
            }

            if (!this.pos_authorization?.authorized) {
                console.warn(
                    "[POS AUTH] Action ignored - invoice not authorized"
                );
                return;
            }

            let description = action;

            if (item_row?.item_code) {
                description += ` - ${item_row.item_code}`;
            }

            if (extra) {
                description += `: ${extra}`;
            }

            const child = frm.add_child(
                "custom_auth_provider"
            );

            child.auth_provider =
                this.pos_authorization.auth_provider;

            child.description = __(description);

            frm.refresh_field(
                "custom_auth_provider"
            );

            console.log(
                "[POS AUTH ACTION]",
                child.auth_provider,
                description
            );
        };

        // ================== AUTH KHUSUS GROSIR ==================
        window.request_grosir_authorization = async function () {
            console.log("[GROSIR AUTH] called");

            return await new Promise(resolve => {
                frappe.prompt(
                    [
                        {
                            fieldname: "code",
                            fieldtype: "Password",
                            label: __("Authorization Code (Grosir)"),
                            reqd: 1,
                        }
                    ],
                    values => {
                        frappe.call({
                            method: "customer_display.api.verify_pos_code_auth",
                            args: {
                                // user: frappe.session.user,
                                pos_profile: cur_frm.doc.pos_profile,
                                code: values.code,
                                description: "Auth grosir mode",
                                purpose: "GROSIR" 
                            },
                            callback: r => {
                                if (r.message && r.message.valid === true) {
									console.log("Authenticator:", r.message.auth_provider);
                                    console.log("[GROSIR AUTH] success");
                                    resolve(true);
                                } else {
                                    frappe.msgprint({
                                        title: __("Authorization Failed"),
                                        indicator: "red",
                                        message: __("Authorization Grosir tidak valid.")
                                    });
                                    resolve(false);
                                }
                            }
                        });
                    },
                    __("Authorization Required"),
                    __("Submit")
                );
            });
        };



		// let pos_edit_auth = {
		// 	item_key: null,   
		// 	fieldname: null,
		// 	active: false
		// };

        window.pos_spg_default = null;

		// edit ghata Pasang container B2B
		add_custom_pos_container(() => {
            $('#b2b-checkbox, #b2b-address, #invoice-checkbox').on('change input', function() {
                if(cur_frm) {
                    cur_frm.set_value("custom_is_b2b", $('#b2b-checkbox').is(':checked'));
                    cur_frm.set_value("custom_alamat_b2b", $('#b2b-address').val());
                    cur_frm.set_value("custom_minta_faktur", $('#invoice-checkbox').is(':checked'));
                    console.log("B2B values updated:", {
                        is_b2b: $('#b2b-checkbox').is(':checked'),
                        alamat: $('#b2b-address').val(),
                        minta_faktur: $('#invoice-checkbox').is(':checked')
                    });
                }
            });
            
            if (cur_frm && cur_frm.doctype === "POS Invoice") {
                sync_marketplace_resi(cur_frm);
            }
        });
		/////////

        $(document).on("click", "#btn-ganti-grosir", async function () {

            if (!cur_frm.doc.customer) {
                frappe.msgprint({
                    title: __("Customer Required"),
                    indicator: "red",
                    message: __("Pilih customer dulu sebelum ganti harga Grosir")
                });
                return;
            }

            if (!cur_frm.is_new()) {
                frappe.msgprint({
                    title: __("Failed Change Price"),
                    indicator: "red",
                    message: __("Harga Grosir hanya bisa diganti sebelum item chekout")
                });
                return;
            }

            const ok = await window.request_grosir_authorization();
            if (!ok) return;

            if (!cur_frm || !window.cur_pos) {
                frappe.msgprint("POS belum siap");
                return;
            }

            try {
                await cur_frm.set_value("selling_price_list", "Grosir");
                await cur_frm.set_value("custom_is_grosir_mode", 1);

                sync_grosir_ui_from_doc(cur_frm);

                console.log("PL SET TO:", cur_frm.doc.selling_price_list);

                cur_frm.clear_table("items");
                cur_frm.refresh_field("items");

                if (cur_pos.cart) {
                    cur_pos.cart.load_invoice();
                }

                cur_pos.items = {};
                cur_pos.item_prices = {};
                cur_pos.items_by_group = {};

                if (cur_pos.item_selector) {
                    const selector = cur_pos.item_selector;

                    selector.items = [];
                    selector.search_index = {};
                    selector.item_group = selector.parent_item_group;

                    await selector.load_items_data();
                }

                setTimeout(() => {
                    const search = document.querySelector(
                        '.item-selector input.input-with-feedback'
                    );
                    if (search) {
                        search.value = "";
                        search.dispatchEvent(new Event("input", { bubbles: true }));
                        search.focus();
                    }
                }, 100);

                const btn = document.querySelector("#btn-ganti-grosir");
                if (btn) {
                    btn.textContent = "MODE GROSIR";
                    btn.disabled = true;
                    btn.classList.remove("btn-default");
                    btn.classList.add("btn-danger");
                }

                frappe.show_alert({
                    message: "Harga diganti ke GROSIR. Silakan pilih item ulang.",
                    indicator: "green"
                });

            } catch (err) {
                console.error("Gagal enable Grosir mode:", err);
                frappe.msgprint("Gagal ganti harga Grosir. Cek console.");
            }


        });


	    if (erpnext?.PointOfSale?.ItemDetails) {
	        const original_get_form_fields = erpnext.PointOfSale.ItemDetails.prototype.get_form_fields;

	        erpnext.PointOfSale.ItemDetails.prototype.get_form_fields = function(item) {
	            let fields = original_get_form_fields.call(this, item);
	            if (!fields.includes("custom_handled_by_spg")) {
	                fields.push("custom_handled_by_spg");
	            }
	            return fields;
	        };

			// // edit ghata
			// async function request_authorization(req_description) {
			// 	return await new Promise(resolve => {

			// 		frappe.prompt(
			// 			[{
			// 				fieldname: "code",
			// 				fieldtype: "Password",
			// 				label: __("Authorization Code"),
			// 				reqd: 1,
			// 			}],
			// 			values => {
			// 				frappe.call({
			// 					method: "customer_display.api.verify_pos_code_auth",
			// 					args: {
			// 						// user: frappe.session.user,
			// 						pos_profile: cur_frm.doc.pos_profile,
            //                         code: values.code,
            //                         description: req_description,
			// 					},
			// 					callback: r => {
			// 						if (r.message && r.message.valid === true) {
            //                             let child = cur_frm.add_child("custom_auth_provider");
            //                             child.auth_provider = r.message.auth_provider;
            //                             child.description = __(r.message.description); 
                                        
            //                             cur_frm.refresh_field("custom_auth_provider"); 

			// 							console.log("Authenticator:", r.message.auth_provider); 
            //                             resolve(true);
			// 						} else {
			// 							frappe.msgprint({
			// 								title: __("Authorization Failed"),
			// 								indicator: "red",
			// 								message: __("Authorization code is invalid or not permitted.")
			// 							});
			// 							resolve(false);
			// 						}
			// 					}
			// 				});
			// 			},
			// 			__("Authorization Required"),
			// 			__("Submit")
			// 		);

			// 	});
			// }

			// function attachFieldListeners(wrapper, fieldnames = [], frm, item) {

			// 	const item_key = item.name || item.item_code;

			// 	fieldnames.forEach(fieldname => {

			// 		const input = wrapper.querySelector(
			// 			`input[data-fieldname="${fieldname}"]`
			// 		);

			// 		if (!input || input.dataset.listenerAttached) return;

			// 		input.addEventListener("focus", async () => {

			// 			if (
			// 				pos_edit_auth.active &&
			// 				pos_edit_auth.item_key === item_key &&
			// 				pos_edit_auth.fieldname === fieldname
			// 			) {
			// 				return;
			// 			}

			// 			const ok = await request_authorization(`Auth ${fieldname}`);
			// 			if (ok) {
			// 				pos_edit_auth.active = true;
			// 				pos_edit_auth.item_key = item_key;
			// 				pos_edit_auth.fieldname = fieldname;
			// 				frappe.show_alert("Authorized");
			// 			} else {
			// 				input.blur();
			// 			}
			// 		});

			// 		input.addEventListener("change", () => {
			// 			pos_edit_auth.active = false;
			// 			pos_edit_auth.item_key = null;
			// 			pos_edit_auth.fieldname = null;

            //             if (fieldname === "qty") {

            //                 const row = item;

            //                 if (row) {
            //                     row.discount_percentage = 0;
            //                     row.discount_amount = 0;

            //                     console.log("🔄 Qty changed → discount reset:", row.item_code);

            //                     if (cur_frm) {
            //                         cur_frm.refresh_field("items");
            //                     }

            //                     reset_pos_item_discount_ui(wrapper);
            //                 }
            //             }

			// 		});

			// 		input.dataset.listenerAttached = "true";
			// 	});
			// }
            
            window.pos_auth_suppress_item_discount_log = false;
            // function attachFieldListeners(wrapper, fieldnames = [], frm, item) {

            //     const item_key = item.name || item.item_code;

            //     fieldnames.forEach(fieldname => {

            //         const input = wrapper.querySelector(
            //             `input[data-fieldname="${fieldname}"]`
            //         );

            //         if (!input || input.dataset.listenerAttached) {
            //             return;
            //         }

            //         // =================================================
            //         // SIMPAN NILAI SEBELUM EDIT
            //         // =================================================

            //         input.addEventListener("focus", async () => {

            //             input.dataset.authOldValue =
            //                 item[fieldname] ?? input.value ?? "";

            //             const ok =
            //                 await window.cur_pos.authorize_current_invoice();

            //             if (!ok) {
            //                 input.blur();
            //                 return;
            //             }

            //             frappe.show_alert({
            //                 message: __("Authorized"),
            //                 indicator: "green"
            //             });
            //         });


            //         // =================================================
            //         // SAAT NILAI BERUBAH
            //         // =================================================

            //         input.addEventListener("change", () => {

            //             if (
            //                 window.pos_auth_suppress_item_discount_log &&
            //                 (
            //                     fieldname === "discount_percentage" ||
            //                     fieldname === "discount_amount"
            //                 )
            //             ) {
            //                 input.dataset.authOldValue = "";
            //                 return;
            //             }

            //             const old_value =
            //                 input.dataset.authOldValue ?? "";

            //             const row = item;

            //             if (!row) {
            //                 return;
            //             }

            //             let new_value = input.value;

            //             // =============================================
            //             // QTY
            //             // =============================================

            //             if (fieldname === "qty") {

            //                 if (old_value != new_value) {

            //                     window.cur_pos.record_pos_authorization_action(
            //                         "Edit Qty",
            //                         row,
            //                         `${old_value} → ${new_value}`
            //                     );
            //                 }

            //                 row.discount_percentage = 0;
            //                 row.discount_amount = 0;

            //                 console.log(
            //                     "🔄 Qty changed → discount reset:",
            //                     row.item_code
            //                 );

            //                 if (cur_frm) {
            //                     cur_frm.refresh_field("items");
            //                 }

            //                 reset_pos_item_discount_ui(wrapper);
            //             }

            //             // =============================================
            //             // DISCOUNT %
            //             // =============================================

            //             else if (fieldname === "discount_percentage") {

            //                 if (old_value != new_value) {

            //                     window.cur_pos.record_pos_authorization_action(
            //                         "Edit Discount",
            //                         row,
            //                         `${old_value}% → ${new_value}%`
            //                     );
            //                 }
            //             }

            //             // =============================================
            //             // DISCOUNT AMOUNT
            //             // =============================================

            //             else if (fieldname === "discount_amount") {

            //                 if (old_value != new_value) {

            //                     window.cur_pos.record_pos_authorization_action(
            //                         "Edit Discount Amount",
            //                         row,
            //                         `${old_value} → ${new_value}`
            //                     );
            //                 }
            //             }

            //             // =============================================
            //             // RATE
            //             // =============================================

            //             else if (fieldname === "rate") {

            //                 if (old_value != new_value) {

            //                     window.cur_pos.record_pos_authorization_action(
            //                         "Edit Rate",
            //                         row,
            //                         `${old_value} → ${new_value}`
            //                     );
            //                 }
            //             }

            //             input.dataset.authOldValue = "";
            //         });

            //         input.dataset.listenerAttached = "true";
            //     });
            // }

            function attachFieldListeners(wrapper, fieldnames = [], frm, item) {
                if (!item) return;

                fieldnames.forEach((fieldname) => {

                    const input = wrapper.querySelector(
                        `input[data-fieldname="${fieldname}"]`
                    );

                    if (!input || input.dataset.listenerAttached) {
                        return;
                    }

                    // =====================================================
                    // FOCUS
                    // =====================================================

                    input.addEventListener("focus", async () => {

                        input.dataset.authOldValue =
                            item[fieldname] ?? input.value ?? "";

                        const authorized =
                            await window.cur_pos.authorize_current_invoice();

                        if (!authorized) {
                            input.blur();
                            return;
                        }

                        frappe.show_alert({
                            message: __("Authorized"),
                            indicator: "green"
                        });
                    });


                    // =====================================================
                    // CHANGE
                    // =====================================================

                    input.addEventListener("change", async () => {

                        const old_value =
                            input.dataset.authOldValue ?? "";

                        const new_value =
                            input.value ?? "";

                        const row = item;

                        if (!row) {
                            return;
                        }


                        // =================================================
                        // QTY
                        // =================================================

                        if (fieldname === "qty") {

                            if (String(old_value) !== String(new_value)) {

                                window.cur_pos.record_pos_authorization_action(
                                    "Edit Qty",
                                    row,
                                    `${old_value} → ${new_value}`
                                );
                            }

                            row.discount_percentage = 0;
                            row.discount_amount = 0;

                            console.log(
                                "🔄 Qty changed → discount reset:",
                                row.item_code
                            );

                            if (frm) {
                                frm.refresh_field("items");
                            }

                            reset_pos_item_discount_ui(wrapper);
                        }


                        // =================================================
                        // DISCOUNT PERCENTAGE
                        // =================================================

                        else if (fieldname === "discount_percentage") {

                            if (String(old_value) !== String(new_value)) {

                                window.cur_pos.record_pos_authorization_action(
                                    "Edit Discount",
                                    row,
                                    `${old_value}% → ${new_value}%`
                                );

                                // Tandai item sebagai manual discount
                                row.custom_manual_discount = 1;

                                // Hapus Pricing Rule dari item
                                row.pricing_rules = "";

                                // Hapus Pricing Rule dari child table POS Invoice
                                if (frm && Array.isArray(frm.doc.pricing_rules)) {

                                    frm.doc.pricing_rules = frm.doc.pricing_rules.filter(
                                        pr => pr.item_code !== row.item_code
                                    );

                                    frm.refresh_field("pricing_rules");
                                }

                                console.log(
                                    "✅ MANUAL DISCOUNT:",
                                    row.item_code,
                                    row.custom_manual_discount
                                );

                                console.log(
                                    "🧹 ITEM PRICING RULE CLEARED:",
                                    row.item_code,
                                    row.pricing_rules
                                );

                                console.log(
                                    "🧹 POS INVOICE PRICING RULE CLEARED FOR:",
                                    row.item_code
                                );

                
                                if (frm) {
                                    frm.refresh_field("items");
                                }
                            }

                            const percentage = flt(new_value);


                            // =================================================
                            // AMBIL PRICE LIST RATE
                            // =================================================

                            let price_list_rate = 0;

                            // Prioritas 1: field price_list_rate di row
                            if (row.price_list_rate) {
                                price_list_rate = flt(row.price_list_rate);
                            }

                            // Prioritas 2: field price_list_rate di input
                            if (!price_list_rate) {

                                const price_list_rate_input =
                                    wrapper.querySelector(
                                        'input[data-fieldname="price_list_rate"]'
                                    );

                                if (price_list_rate_input) {
                                    price_list_rate =
                                        flt(price_list_rate_input.value);
                                }
                            }


                            console.log(
                                "=============================="
                            );

                            console.log(
                                "DISCOUNT % CHANGE"
                            );

                            console.log(
                                "percentage:",
                                percentage
                            );

                            console.log(
                                "price_list_rate:",
                                price_list_rate
                            );

                            console.log(
                                "row.price_list_rate:",
                                row.price_list_rate
                            );

                            console.log(
                                "row.rate:",
                                row.rate
                            );


                            // =================================================
                            // HITUNG DISCOUNT AMOUNT
                            // BERDASARKAN PRICE LIST RATE
                            // =================================================

                            const discount_amount =
                                price_list_rate > 0
                                    ? (price_list_rate * percentage) / 100
                                    : 0;


                            console.log(
                                "discount amount hasil:",
                                discount_amount
                            );


                            // =================================================
                            // UPDATE ROW
                            // =================================================

                            row.discount_percentage = percentage;
                            row.discount_amount = discount_amount;


                            // =================================================
                            // UPDATE INPUT DISCOUNT AMOUNT
                            // =================================================

                            const amount_input = wrapper.querySelector(
                                'input[data-fieldname="discount_amount"]'
                            );

                            if (amount_input) {

                                amount_input.value =
                                    discount_amount;

                                console.log(
                                    "amount input updated:",
                                    amount_input.value
                                );
                            }


                            // =================================================
                            // UPDATE TOTAL POS
                            // =================================================

                            if (
                                window.cur_pos &&
                                typeof window.cur_pos.calculate_totals === "function"
                            ) {
                                window.cur_pos.calculate_totals();
                            }
                        }


                        // =================================================
                        // DISCOUNT AMOUNT
                        // =================================================

                        else if (fieldname === "discount_amount") {

                            if (String(old_value) !== String(new_value)) {

                                window.cur_pos.record_pos_authorization_action(
                                    "Edit Discount Amount",
                                    row,
                                    `${old_value} → ${new_value}`
                                );

                                row.custom_manual_discount = 1;

                                // Hapus Pricing Rule dari item
                                row.pricing_rules = "";

                                // Hapus Pricing Rule dari child table POS Invoice
                                if (frm && Array.isArray(frm.doc.pricing_rules)) {

                                    frm.doc.pricing_rules = frm.doc.pricing_rules.filter(
                                        pr => pr.item_code !== row.item_code
                                    );

                                    frm.refresh_field("pricing_rules");
                                }

                                console.log(
                                    "✅ MANUAL DISCOUNT:",
                                    row.item_code,
                                    row.custom_manual_discount
                                );

                                console.log(
                                    "🧹 ITEM PRICING RULE CLEARED:",
                                    row.item_code,
                                    row.pricing_rules
                                );

                                console.log(
                                    "🧹 POS INVOICE PRICING RULE CLEARED FOR:",
                                    row.item_code
                                );

                                if (frm) {
                                    frm.refresh_field("items");
                                }
                            }

                            const discount_amount =
                                flt(new_value);


                            // =================================================
                            // AMBIL PRICE LIST RATE
                            // =================================================

                            let price_list_rate = 0;

                            // Prioritas 1: row.price_list_rate
                            if (row.price_list_rate) {
                                price_list_rate = flt(row.price_list_rate);
                            }

                            // Prioritas 2: input price_list_rate
                            if (!price_list_rate) {

                                const price_list_rate_input =
                                    wrapper.querySelector(
                                        'input[data-fieldname="price_list_rate"]'
                                    );

                                if (price_list_rate_input) {
                                    price_list_rate =
                                        flt(price_list_rate_input.value);
                                }
                            }


                            console.log(
                                "=============================="
                            );

                            console.log(
                                "DISCOUNT AMOUNT CHANGE"
                            );

                            console.log(
                                "discount amount:",
                                discount_amount
                            );

                            console.log(
                                "price_list_rate:",
                                price_list_rate
                            );

                            console.log(
                                "row.price_list_rate:",
                                row.price_list_rate
                            );

                            console.log(
                                "row.rate:",
                                row.rate
                            );


                            // =================================================
                            // HITUNG PERCENTAGE
                            // BERDASARKAN PRICE LIST RATE
                            // =================================================

                            const percentage =
                                price_list_rate > 0
                                    ? (discount_amount / price_list_rate) * 100
                                    : 0;


                            console.log(
                                "percentage hasil:",
                                percentage
                            );


                            // =================================================
                            // UPDATE ROW
                            // =================================================

                            row.discount_amount =
                                discount_amount;

                            row.discount_percentage =
                                percentage;


                            // =================================================
                            // UPDATE INPUT PERCENTAGE
                            // =================================================

                            const percentage_input =
                                wrapper.querySelector(
                                    'input[data-fieldname="discount_percentage"]'
                                );

                            if (percentage_input) {

                                percentage_input.value =
                                    percentage;

                                console.log(
                                    "percentage input updated:",
                                    percentage_input.value
                                );
                            }


                            // =================================================
                            // UPDATE TOTAL POS
                            // =================================================

                            if (
                                window.cur_pos &&
                                typeof window.cur_pos.calculate_totals === "function"
                            ) {
                                window.cur_pos.calculate_totals();
                            }
                        }


                        // =================================================
                        // RATE
                        // =================================================

                        else if (fieldname === "rate") {

                            if (String(old_value) !== String(new_value)) {

                                window.cur_pos.record_pos_authorization_action(
                                    "Edit Rate",
                                    row,
                                    `${old_value} → ${new_value}`
                                );
                            }
                        }


                        input.dataset.authOldValue = "";
                    });


                    input.dataset.listenerAttached = "true";
                });
            }

            function reset_pos_item_discount_ui(wrapper) {
                if (!wrapper) return;

                const percent_input = wrapper.querySelector(
                    'input[data-fieldname="discount_percentage"]'
                );

                const amount_input = wrapper.querySelector(
                    'input[data-fieldname="discount_amount"]'
                );

                window.pos_auth_suppress_item_discount_log = true;

                try {

                    if (percent_input) {
                        percent_input.value = 0;

                        percent_input.dispatchEvent(
                            new Event("input", { bubbles: true })
                        );

                        percent_input.dispatchEvent(
                            new Event("change", { bubbles: true })
                        );
                    }

                    if (amount_input) {
                        amount_input.value = 0;

                        amount_input.dispatchEvent(
                            new Event("input", { bubbles: true })
                        );

                        amount_input.dispatchEvent(
                            new Event("change", { bubbles: true })
                        );
                    }

                } finally {
                    window.pos_auth_suppress_item_discount_log = false;
                }
            }


            const original_render_form = erpnext.PointOfSale.ItemDetails.prototype.render_form;
	        erpnext.PointOfSale.ItemDetails.prototype.render_form = function(item) {
	            original_render_form.call(this, item);
                
	            if (this.custom_handled_by_spg_control) {
	                this.custom_handled_by_spg_control.df.label = __("Handled by SPG");
	                this.custom_handled_by_spg_control.refresh();
	            }

                
					// edit ghata
					const frm = this.frm || cur_frm;
					    attachFieldListeners(
							this.wrapper[0],
							["qty", "discount_percentage", "rate", "discount_amount"],
							frm,
							item
						);
					//////
	        };

	    }

        ////
        let fromScript = false;

        // UPDATE AUTH CHANDRA

        let discountAuthorized = false;

        // function attachDiscountAuthMultiple() {
        //     const wrapper = document.querySelector('.add-discount-wrapper');
        //     if (!wrapper || wrapper.dataset.authAttached) return;

        //     wrapper.addEventListener('click', async (e) => {
        //         // If already authorized, allow normal interaction
        //         if (discountAuthorized) return;

        //         // Prevent the click from propagating
        //         e.preventDefault();
        //         e.stopPropagation();

        //         // Request authorization
        //         const ok = await request_pos_authorization("Auth add discounts");
        //         if (!ok) {
        //             frappe.show_alert({
        //                 message: "Authorization failed",
        //                 indicator: "red"
        //             });
        //             return;
        //         }

        //         // Mark as authorized
        //         discountAuthorized = true;
        //         frappe.show_alert("Authorized! You can now add discounts.");

        //         // Add visual indicator (optional)
        //         wrapper.style.opacity = '1';
        //         wrapper.style.pointerEvents = 'auto';
        //     }, true); // Use capture phase

        //     // Reset authorization when discount is applied or cleared
        //     const resetAuth = () => {
        //         discountAuthorized = false;
        //         wrapper.style.opacity = ''; // Reset visual indicator
        //     };

        //     // Listen for discount changes to reset auth
        //     $(document).on('change', '.add-discount-field input', resetAuth);

        //     wrapper.dataset.authAttached = "true";
            
        //     // Optional: Add visual indicator that auth is required
        //     wrapper.style.opacity = '0.6';
        // }

        function attachDiscountAuthMultiple() {

            const wrapper =
                document.querySelector(".add-discount-wrapper");

            if (!wrapper || wrapper.dataset.authAttached) {
                return;
            }

            let allow_discount_once = false;
            let discount_auth_in_progress = false;

            wrapper.addEventListener(
                "click",
                async function(e) {

                    // =============================================
                    // CLICK HASIL REPLAY SETELAH AUTH
                    // =============================================

                    if (allow_discount_once) {
                        allow_discount_once = false;
                        return;
                    }

                    // =============================================
                    // AUTH SEDANG BERJALAN
                    // JANGAN BIARKAN CLICK ASLI LEWAT
                    // =============================================

                    if (discount_auth_in_progress) {
                        e.preventDefault();
                        e.stopImmediatePropagation();
                        return;
                    }

                    // =============================================
                    // SUDAH AUTH UNTUK INVOICE INI
                    // =============================================

                    if (
                        window.cur_pos?.pos_authorization?.authorized
                    ) {
                        return;
                    }

                    // =============================================
                    // STOP CLICK ASLI
                    // =============================================

                    e.preventDefault();
                    e.stopImmediatePropagation();

                    discount_auth_in_progress = true;

                    try {

                        const ok =
                            await window.cur_pos.authorize_current_invoice();

                        if (!ok) {

                            frappe.show_alert({
                                message: __("Authorization failed"),
                                indicator: "red"
                            });

                            return;
                        }

                        frappe.show_alert({
                            message: __("Authorized"),
                            indicator: "green"
                        });

                        // =============================================
                        // REPLAY CLICK ASLI
                        // =============================================

                        allow_discount_once = true;

                        wrapper.dispatchEvent(
                            new MouseEvent("click", {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            })
                        );

                    } finally {
                        discount_auth_in_progress = false;
                    }

                },
                true
            );

            wrapper.dataset.authAttached = "true";
        }

        setInterval(attachDiscountAuthMultiple, 300);

	});

    if (!window._pos_spg_listener) {
        window._pos_spg_listener = true;

        function handleSPGChange(val) {
            if (!val) return;
            window.pos_spg_default = val;
            console.log("🌟 SPG default set:", val);
        }
    }


};


frappe.pages["point-of-sale"].refresh = function (wrapper) {
	if (document.scannerDetectionData) {
		onScan.detachFrom(document);
		wrapper.pos.wrapper.html("");
		wrapper.pos.check_opening_entry();
	}
};


function add_custom_pos_container(callback) {
    const customer_cart = $('.customer-cart-container');
    if (customer_cart.length) {
        if ($('#custom-menu-container').length === 0) {
            const new_container = $(`
                <div id="custom-menu-container"></div>
            `);

            const desk_theme = frappe.boot?.user?.desk_theme || "Light";
            const is_dark = desk_theme === "Dark";

			// if (is_dark) {
			// 	//DARK MODE
			// 	new_container.css({
			// 		background: '#171717',
			// 		border: '1px solid rgba(255,255,255,0.08)',
			// 		padding: '16px',
			// 		marginBottom: '1px',
			// 		borderRadius: '12px',
			// 		color: '#e6e6e6'
			// 	});
			// } else {
			// 	//LIGHT MODE
			// 	new_container.css({
			// 		background: '#ffffff',
			// 		border: '1px solid #e5e7eb',
			// 		padding: '16px',
			// 		marginBottom: '1px',
			// 		borderRadius: '12px',
			// 		color: '#1f2937'
			// 	});
			// }

            if (is_dark) {
                new_container.css({
                    background: '#171717',
                    border: '1px solid rgba(255,255,255,0.08)',
                    padding: '6px 10px',
                    marginBottom: '1px',
                    borderRadius: '8px',
                    color: '#e6e6e6'
                });
            } else {
                new_container.css({
                    background: '#ffffff',
                    border: '1px solid #e5e7eb',
                    padding: '6px 10px',
                    marginBottom: '1px',
                    borderRadius: '8px',
                    color: '#1f2937'
                });
            }


            customer_cart.prepend(new_container);

            new_container.css({
                lineHeight: '1.2'
            });

            new_container.find('.form-group').css({
                marginBottom: '2px'
            });

            new_container.find('.form-check').css({
                marginBottom: '2px'
            });

            new_container.find('label').css({
                marginBottom: '2px'
            });

            new_container.find('.form-control').css({
                minHeight: '30px',
                height: '30px',
                paddingTop: '4px',
                paddingBottom: '4px'
            });


            new_container.append(`
                
                <div class="form-check mb-2" style="display:flex; align-items:center; gap:8px;">
                    <input type="checkbox" class="form-check-input" id="b2b-checkbox">
                    <label class="form-check-label" for="b2b-checkbox">B2B</label>

                    <button
                        class="btn btn-xs"
                        id="btn-ganti-grosir"
                        style="margin-left:auto;"
                    >
                        Ganti Harga Grosir
                    </button>
                </div>

                <div id="b2b-fields" style="display:none; margin-top:2px;">
                    <div class="form-group" style="margin-bottom:2px;">
                        <label for="b2b-address" style="margin-bottom:2px;">Alamat B2B</label>
                        <input
                            type="text"
                            class="form-control"
                            id="b2b-address"
                            placeholder="Masukkan alamat..."
                        >
                    </div>

                    <div class="form-check" style="margin-top:2px; margin-bottom:2px;">
                        <input
                            type="checkbox"
                            class="form-check-input"
                            id="invoice-checkbox"
                        >
                        <label
                            class="form-check-label"
                            for="invoice-checkbox"
                            style="margin-bottom:0;"
                        >
                            Minta Faktur?
                        </label>
                    </div>
                </div>

                <!-- CUSTOMER POINT -->
                <div
                    id="customer-point-section"
                    style="display:none; margin:4px 0;"
                >
                    <div
                        id="customer-point-info"
                        style="
                            padding:6px 8px;
                            border-radius:6px;
                            background:rgba(127,127,127,0.08);
                            display:flex;
                            align-items:center;
                            justify-content:space-between;
                            gap:12px;
                        "
                    >
                        <strong style="white-space:nowrap;">
                            Point
                        </strong>

                        <span id="customer-point-value">
                            0 Point
                        </span>

                        <strong style="white-space:nowrap;">
                            Max Discount
                        </strong>

                        <span id="customer-max-discount">
                            Rp0
                        </span>
                    </div>
                </div>

                <!-- SPG DEFAULT -->
                <div class="form-group" style="margin-bottom:1px;">
                    <div id="pos-spg-section" class="spg-section">

                        <!-- SPG PICKER (STATE 1) -->
                        <div id="spg-picker"></div>

                        <!-- SPG DETAILS (STATE 2) -->
                        <div id="spg-details" style="display:none"></div>

                    </div>
                </div>

               <!-- RESI MARKETPLACE -->
                <div
                    id="pos-resi-section"
                    class="form-group"
                    style="display:none; margin-bottom:1px; margin-top:8px;"
                >
                    <div id="resi-picker">
                        <input
                            type="text"
                            class="form-control"
                            id="pos-resi"
                            placeholder="Resi Marketplace"
                        >
                    </div>

                    <div id="resi-details" style="display:none;"></div>
                </div>
            `);

            window.pos_custom_resi = null;

            function render_resi_details(resi) {
                $('#resi-picker').hide();

                $('#resi-details')
                    .html(`
                        <div class="resi-details">
                            <div
                                class="resi-display"
                                style="
                                    display:flex;
                                    align-items:center;
                                    justify-content:space-between;
                                    padding:8px 0;
                                "
                            >
                                <div style="flex:1;">
                                    <div class="resi-name">
                                        ${frappe.utils.escape_html(resi)}
                                    </div>
                                </div>

                                <div
                                    class="reset-resi-btn"
                                    style="cursor:pointer;"
                                >
                                    <svg width="32" height="32" viewBox="0 0 14 14" fill="none">
                                        <path
                                            d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759"
                                            stroke="#8D99A6"
                                        ></path>
                                    </svg>
                                </div>
                            </div>
                        </div>
                    `)
                    .show();
            }

            $('#pos-resi').on('change', function() {
                const resi = $(this).val().trim();

                if (!resi) {
                    return;
                }

                window.pos_custom_resi = resi;

                if (window.cur_frm && cur_frm.doctype === "POS Invoice") {
                    cur_frm.set_value("custom_resi_marketplace", resi);
                }

                render_resi_details(resi);
            });

            $(document).on('click', '#resi-details .reset-resi-btn', function() {
                window.pos_custom_resi = null;

                if (window.cur_frm && cur_frm.doctype === "POS Invoice") {
                    cur_frm.set_value("custom_resi_marketplace", "");
                }

                $('#resi-details').hide().empty();
                $('#resi-picker').show();
                $('#pos-resi').val('');
            });

            window.pos_spg_control = frappe.ui.form.make_control({
                parent: $('#spg-picker'),
                df: {
                    fieldtype: "Link",
                    fieldname: "pos_spg_default",
                    options: "Employee",
                    placeholder: "Handled by SPG",
                    change() {
                        const emp = this.get_value();
                        if (!emp) return;

                        window.pos_spg_default = emp;
                        render_spg_details(emp);
                    }
                },
                render_input: true
            });

            window.pos_spg_control.refresh();

            function render_spg_details(emp) {
                frappe.db.get_value(
                    "Employee",
                    emp,
                    ["employee_name"]
                ).then(r => {
                    const d = r.message;
                    if (!d) return;

                    $('#spg-picker').hide();

                    $('#spg-details')
                        .html(`
                            <div class="spg-details">
                                <div class="spg-display" style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0;">

                                    <div class="spg-name-desc" style="flex: 1;">
                                        <div class="spg-name">${d.employee_name}</div>
                                    </div>

                                    <div class="reset-spg-btn" style="cursor: pointer;">
                                        <svg width="32" height="32" viewBox="0 0 14 14" fill="none">
                                            <path d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759" stroke="#8D99A6"></path>
                                        </svg>
                                    </div>

                                </div>
                            </div>
                        `)
                        .show();
                });
            }


            $(document).on('click', '#spg-details .reset-spg-btn', function () {
                window.pos_spg_default = null;

                if (window.pos_spg_control) {
                    window.pos_spg_control.set_value('');
                }

                $('#spg-details').hide().empty();
                $('#spg-picker').show();
            });

            $('#b2b-checkbox').on('change', function() {
                if ($(this).is(':checked')) {
                    $('#b2b-fields').slideDown();
                } else {
                    $('#b2b-fields').slideUp();
                    $('#b2b-address').val('');
                    $('#invoice-checkbox').prop('checked', false);
                }
            });

            if(typeof callback === "function") callback();

        } else {
            if(typeof callback === "function") callback();
        }

    } else {
        setTimeout(() => add_custom_pos_container(callback), 200);
    }
}

// window.request_pos_authorization = async function (req_description) {
//     return await new Promise(resolve => {
//         frappe.prompt(
//             [{
//                 fieldname: "code",
//                 fieldtype: "Password",
//                 label: __("Authorization Code"),
//                 reqd: 1,
//             }],
//             values => {
//                 frappe.call({
//                     method: "customer_display.api.verify_pos_code_auth",
//                     args: {
//                         // user: frappe.session.user,
//                         pos_profile: cur_frm.doc.pos_profile,
//                         code: values.code,
//                         description: req_description
//                     },
//                     callback: r => {
//                         if (r.message && r.message.valid === true) {
// 							let child = cur_frm.add_child("custom_auth_provider");
//                             child.auth_provider = r.message.auth_provider;
//                             child.description = __(r.message.description); 
                            
//                             cur_frm.refresh_field("custom_auth_provider"); 

//                             console.log("Authenticator:", r.message.auth_provider); 
                            
//                             resolve(true);
//                         } else {
//                             frappe.msgprint({
//                                 title: __("Authorization Failed"),
//                                 indicator: "red",
//                                 message: __("Authorization code is invalid or not permitted.")
//                             });
//                             resolve(false);
//                         }
//                     }
//                 });
//             },
//             __("Authorization Required"),
//             __("Submit")
//         );
//     });
// };

// (function () {

//     let allow_remove_once = false;

//     document.addEventListener(
//         "click",
//         async function (e) {

//             const btn = e.target.closest(".remove-btn");
//             if (!btn) return;

//             if (allow_remove_once) {
//                 allow_remove_once = false;
//                 return;
//             }

//             e.preventDefault();
//             e.stopImmediatePropagation();

//             const ok = await window.request_pos_authorization("Auth remove item");
//             if (!ok) {
//                 frappe.show_alert({
//                     message: __("Remove item cancelled"),
//                     indicator: "red"
//                 });
//                 return;
//             }

//             frappe.show_alert("Authorized");

//             allow_remove_once = true;

//             btn.dispatchEvent(
//                 new MouseEvent("click", {
//                     bubbles: true,
//                     cancelable: true,
//                     view: window
//                 })
//             );

//         },
//         true 
//     );

// })();

(function () {
    let allow_remove_once = false;
    let remove_auth_in_progress = false;

    document.addEventListener(
        "click",
        async function (e) {
            const btn = e.target.closest(".remove-btn");
            if (!btn) return;

            if (allow_remove_once) {
                allow_remove_once = false;
                return;
            }

            if (remove_auth_in_progress) {
                e.preventDefault();
                e.stopImmediatePropagation();
                return;
            }

            e.preventDefault();
            e.stopImmediatePropagation();

            remove_auth_in_progress = true;

            try {
                const wrapper = btn.closest(".cart-item-wrapper");

                let item_row = null;

                // Cari item berdasarkan data DOM
                if (wrapper && window.cur_frm?.doc?.items) {
                    const possible_item_codes = [
                        wrapper.dataset.itemCode,
                        wrapper.getAttribute("data-item-code"),
                        wrapper.querySelector("[data-item-code]")?.dataset.itemCode
                    ].filter(Boolean);

                    for (const item_code of possible_item_codes) {
                        item_row = window.cur_frm.doc.items.find(
                            row => row.item_code === item_code
                        );

                        if (item_row) break;
                    }
                }

                // Fallback: coba dari current_item
                if (!item_row && window.cur_pos?.current_item) {
                    item_row = window.cur_pos.current_item;
                }

                // Fallback terakhir: ambil item berdasarkan index DOM
                if (!item_row && wrapper && window.cur_frm?.doc?.items) {
                    const wrappers = Array.from(
                        document.querySelectorAll(".cart-item-wrapper")
                    );

                    const wrapper_index = wrappers.indexOf(wrapper);

                    if (
                        wrapper_index >= 0 &&
                        window.cur_frm.doc.items[wrapper_index]
                    ) {
                        item_row =
                            window.cur_frm.doc.items[wrapper_index];
                    }
                }

                const item_code = item_row?.item_code || "";
                const qty = item_row?.qty ?? "";

                console.log("[POS AUTH REMOVE]", {
                    item_row,
                    item_code,
                    qty
                });

                const ok =
                    await window.cur_pos.authorize_current_invoice();

                if (!ok) {
                    frappe.show_alert({
                        message: __("Remove item cancelled"),
                        indicator: "red"
                    });
                    return;
                }

                window.cur_pos.record_pos_authorization_action(
                    "Remove Item",
                    item_row,
                    item_code
                        ? `Qty ${qty}`
                        : ""
                );

                frappe.show_alert({
                    message: __("Authorized"),
                    indicator: "green"
                });

                allow_remove_once = true;

                btn.dispatchEvent(
                    new MouseEvent("click", {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    })
                );

            } finally {
                remove_auth_in_progress = false;
            }
        },
        true
    );
})();

(function watch_pos_items() {
    let last_len = 0;

    function tick() {
        if (!window.cur_frm || cur_frm.doctype !== "POS Invoice") {
            setTimeout(tick, 300);
            return;
        }

        const items = cur_frm.doc.items || [];

        inject_discount_amount_total();
        bind_discount_amount_total_handler();
        // bind_discount_percentage_to_rp();

        if (items.length > last_len) {
            const row = items[items.length - 1];

            if (row && window.pos_spg_default && !row.custom_handled_by_spg) {
                row.custom_handled_by_spg = window.pos_spg_default;

                console.log(
                    "✅ SPG AUTO SET (LENGTH WATCHER):",
                    row.item_code,
                    window.pos_spg_default
                );

                cur_frm.refresh_field("items");
            }
        }

        last_len = items.length;
        setTimeout(tick, 200);
    }

    tick();
})();

//ganti customer_name
//ganti customer_name + compact customer section
(function replace_pos_customer_name_text_only() {

    function apply() {
        if (!cur_frm || cur_frm.doctype !== "POS Invoice") return;
        if (!cur_frm.doc.customer_name) return;

        const el = document.querySelector('.customer-section .customer-name');
        if (!el) return;

        el.textContent = cur_frm.doc.customer_name;

        // Compact customer name
        el.style.margin = "0";
        el.style.padding = "0";
        el.style.lineHeight = "1.2";
        el.style.fontSize = "13px";
        el.style.maxHeight = "18px";
        el.style.overflow = "hidden";
        el.style.textOverflow = "ellipsis";
        el.style.whiteSpace = "nowrap";

        // Compact parent customer section
        const section = el.closest(".customer-section");

        if (section) {
            section.style.margin = "0";
            section.style.padding = "4px 8px";
            section.style.minHeight = "0";
        }
    }

    setInterval(apply, 300);

})();


function inject_discount_amount_total() {

    const $field = $('.cart-totals-section .add-discount-field');
    if (!$field.length) return;

    if ($field.find('.discount-amount-rp').length) return;

    $field.css({
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
    });

    const html = `
        <div class="discount-amount-rp">
            <input type="text"
                class="form-control input-xs"
                placeholder="Enter discount amount."
                style="
                    width:100%;
                    background:#111315;
                    color:#e5e7eb;
                    border:1px solid rgba(255,255,255,.15);
                    border-radius:6px;
                "
            />
        </div>
    `;

    $field.append(html);
}


function get_pos_discount_percent_input() {
    return $('.add-discount-field .frappe-control').filter(function() {
        const label = $(this).find('label.control-label').text().trim().toLowerCase();
        return label === 'discount';
    }).find('input').first();
}


function get_pos_items_gross_total() {
    if (!cur_frm?.doc?.items) return 0;

    let total = 0;

    cur_frm.doc.items.forEach(row => {
        const qty  = parse_pos_qty(row.qty);
        const rate = parse_pos_amount(row.rate);

        const line_total = qty * rate;

        console.log(
            '🧾 ITEM',
            row.item_code,
            'qty=', qty,
            'rate=', rate,
            'total=', line_total
        );

        total += line_total;
    });

    console.log('🧮 GROSS TOTAL:', total);
    return total;
}


function parse_pos_qty(val) {
    if (!val) return 0;
    if (typeof val === 'number') return val;

    return flt(
        val
            .toString()
            .replace(/,/g, '.')
    );
}

function parse_discount_input(val) {
    if (!val) return 0;

    return flt(val.toString().replace(/[^\d]/g, ''));
}


function parse_pos_amount(val) {
    if (!val) return 0;
    if (typeof val === 'number') return val;

    return flt(
        val
            .toString()
            .replace(/\./g, '')
            .replace(/,/g, '.')
    );
}


// function apply_pos_discount_percent(percent) {

//     const input = get_pos_discount_percent_input()[0];
//     if (!input) {
//         console.warn("❌ POS discount input not found");
//         return;
//     }

//     input.value = percent;

//     input.dispatchEvent(new Event('input', { bubbles: true }));
//     input.dispatchEvent(new Event('change', { bubbles: true }));

//     console.log("✅ POS Discount % applied:", percent);
// }

function apply_pos_discount_percent(percent, discount_amount) {
    const input = get_pos_discount_percent_input()[0];
    const field = cur_frm?.fields_dict?.additional_discount_percentage;

    if (!input || !field) {
        console.warn("❌ POS discount field not found");
        return;
    }

    const numeric_percent = Number(percent);
    const numeric_amount = Number(discount_amount);

    if (!Number.isFinite(numeric_percent) || !Number.isFinite(numeric_amount)) {
        console.warn("❌ Invalid discount:", {
            percent,
            discount_amount
        });
        return;
    }

    // Simpan FULL PRECISION ke document
    cur_frm.doc.additional_discount_percentage = numeric_percent;
    cur_frm.doc.discount_amount = numeric_amount;

    // Tampilan tetap 2 angka desimal
    input.value = numeric_percent.toFixed(2);

    // Trigger recalculation POS
    if (cur_pos && typeof cur_pos.calculate_totals === "function") {
        cur_pos.calculate_totals();
    } else if (cur_frm && typeof cur_frm.cscript?.calculate_taxes_and_totals === "function") {
        cur_frm.cscript.calculate_taxes_and_totals();
    }

    cur_frm.refresh_field("discount_amount");
    cur_frm.refresh_field("additional_discount_percentage");

    console.log("✅ POS Discount Applied:", {
        percentage_display: input.value,
        percentage_internal: numeric_percent,
        discount_amount: numeric_amount,
        doc_percentage: cur_frm.doc.additional_discount_percentage,
        doc_amount: cur_frm.doc.discount_amount
    });
}

// function bind_discount_amount_total_handler() {
//     $(document)
//         .off('change.discount_rp_total')
//         .on('change.discount_rp_total', '.discount-amount-rp input', function () {

//             const discount_amount = parse_discount_input(this.value);
//             if (!discount_amount) return;

//             const gross_total = get_pos_items_gross_total();
//             if (!gross_total) return;

//             const percent = flt(
//                 ((discount_amount / gross_total) * 100).toFixed(2)
//             );

//                console.log(
//                     `💸 Rp → % ${discount_amount} / ${gross_total} = ${percent.toFixed(2)}% (POS=${(percent/100).toFixed(4)})`
//                 );

//             apply_pos_discount_percent(percent / 100);
//         });
// }

function bind_discount_amount_total_handler() {
    $(document)
        .off('change.discount_rp_total')
        .on('change.discount_rp_total', '.discount-amount-rp input', function () {
            const discount_amount = parse_discount_input(this.value);

            if (!discount_amount) return;

            const gross_total = get_pos_items_gross_total();

            if (!gross_total) return;

            // JANGAN dibulatkan.
            // Nilai ini dipakai ERPNext untuk menghitung discount_amount.
            const exact_percent = (discount_amount / gross_total) * 100;

            console.log(
                `💸 Rp → % ${discount_amount} / ${gross_total} =`,
                exact_percent
            );

            apply_pos_discount_percent(
                exact_percent,
                discount_amount
            );
        });
}


// function inject_pos_hide_net_and_tax_css() {
//     if (document.getElementById("pos-hide-net-tax-css")) return;

//     const style = document.createElement("style");
//     style.id = "pos-hide-net-tax-css";
//     style.innerHTML = `
//         .cart-totals-section .net-total-container,
//         .cart-totals-section .taxes-container {
//             display: none !important;
//         }
//     `;

//     document.head.appendChild(style);
// }

function inject_pos_hide_net_and_tax_css() {
    if (document.getElementById("pos-hide-net-tax-css")) return;

    const style = document.createElement("style");
    style.id = "pos-hide-net-tax-css";

    style.innerHTML = `
        .cart-totals-section .net-total-container,
        .cart-totals-section .taxes-container {
            display: none !important;
        }

        /* Compact cart item - tanpa merusak layout/scroll */
        .cart-item-wrapper {
            padding: 2px 4px !important;
        }

        .cart-item-wrapper .item-image {
            width: 28px !important;
            height: 28px !important;
        }

        .cart-item-wrapper .item-name {
            font-size: 12px !important;
            line-height: 18px !important;
        }

        .cart-item-wrapper .item-qty,
        .cart-item-wrapper .item-rate {
            font-size: 12px !important;
            line-height: 18px !important;
        }
    `;

    document.head.appendChild(style);
}

(function POS_ALT_SHORTCUTS_HARD() {

    let last_trigger = 0;
    let block_until = 0;

    let alt_c_active = false;
    let alt_i_active = false;
    let alt_j_active = false;   

    let current_item_index = -1; 
    let modal_open_state = false; // track modal Item Price List

    function is_alt(e, key) {
        return (
            e.altKey &&
            !e.ctrlKey &&
            !e.shiftKey &&
            (
                e.key === key ||
                e.key === key.toUpperCase() ||
                e.code === "Key" + key.toUpperCase()
            )
        );
    }

    function hard_block(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        return false;
    }

    function focus_and_select(input, label) {
        if (!input) return;
        requestAnimationFrame(() => {
            input.focus();
            input.select?.();
            frappe.show_alert({ message: label, indicator: "blue" });
        });
    }

    function get_customer_input() {
        return document.querySelector('.customer-section input[data-target="Customer"]');
    }

    function get_item_search_input() {
        const inputs = document.querySelectorAll('input.input-with-feedback[data-fieldtype="Data"]');
        for (const el of inputs) {
            if (el.dataset.target === "Customer") continue;
            if (el.closest('.customer-section')) continue;
            return el;
        }
        return null;
    }

    function get_cart_items() {
        return Array.from(document.querySelectorAll('.cart-items-section .cart-item-wrapper'));
    }

    function close_item_cart_if_open() {
        const close_btn = document.querySelector('.close-btn');
        if (close_btn) { close_btn.click(); return true; }
        return false;
    }

    function select_cart_item(item) {
        if (!item) return;
        item.scrollIntoView({behavior: "smooth", block: "center"});
        ['pointerdown','pointerup','mousedown','mouseup','click'].forEach(evName => {
            const ev = new MouseEvent(evName, { view: window, bubbles: true, cancelable: true });
            item.dispatchEvent(ev);
        });
        item.style.outline = "2px solid blue";
        setTimeout(() => { item.style.outline = ""; }, 500);
    }

    function click_item_price_list_if_exists() {
        const btn = document.querySelector('button[data-label="Item%20Price%20List"]');
        if (btn) { btn.click(); frappe.show_alert({ message: "Item Price List", indicator: "blue" }); return true; }
        return false;
    }

    function close_modal_if_open() {
        const close_btn = document.querySelector('.modal-actions .btn-modal-close');
        if (close_btn) { close_btn.click(); return true; }
        return false;
    }

    function toggle_item_price_modal() {
        const modal = document.querySelector('.modal-dialog'); 
        const modal_close_btn = modal?.querySelector('.modal-actions .btn-modal-close');
        const item_price_btn = document.querySelector('button[data-label="Item%20Price%20List"]');

        if (modal && modal.classList.contains('show')) {
            if (modal_close_btn) modal_close_btn.click();
        } else {
            if (item_price_btn) item_price_btn.click();
        }
    }


    function is_focused(el) {
        return el && document.activeElement === el;
    }

    document.addEventListener("keydown", function(e) {

        // === ALT + C ===
        if (is_alt(e, "c")) {
            if (alt_c_active || e.repeat) { hard_block(e); return; }
            alt_c_active = true;
            const now = Date.now();
            if (now - last_trigger < 300) { hard_block(e); return; }
            last_trigger = now;
            block_until = now + 500;
            hard_block(e);

            close_item_cart_if_open();
            close_modal_if_open();

            const customer = get_customer_input();
            if (!is_focused(customer)) focus_and_select(customer, "Customer");
            return;
        }

        // === ALT + I ===
        if (is_alt(e, "i")) {
            if (alt_i_active || e.repeat) { hard_block(e); return; }
            alt_i_active = true;
            const now = Date.now();
            if (now - last_trigger < 300) { hard_block(e); return; }
            last_trigger = now;
            block_until = now + 500;
            hard_block(e);

            close_item_cart_if_open();
            if (modal_open_state) toggle_item_price_modal();

            const item = get_item_search_input();
            if (!is_focused(item)) focus_and_select(item, "Item Search");
            return;
        }

        // === ALT + J ===
        if (is_alt(e, "j")) {
            if (e.repeat) { hard_block(e); return; }
            const now = Date.now();
            if (now - last_trigger < 150) { hard_block(e); return; }
            last_trigger = now;
            block_until = now + 300;
            hard_block(e);

            close_item_cart_if_open();
            if (modal_open_state) toggle_item_price_modal();

            const items = get_cart_items();
            if (items.length === 0) return;

            current_item_index++;
            if (current_item_index >= items.length) current_item_index = 0;

            select_cart_item(items[current_item_index]);
            return;
        }

        // === ALT + P ===
        if (is_alt(e, "p")) {
            if (e.repeat) { hard_block(e); return; }
            const now = Date.now();
            if (now - last_trigger < 200) { hard_block(e); return; }
            last_trigger = now;
            block_until = now + 300;
            hard_block(e);

            close_item_cart_if_open();
            toggle_item_price_modal(); 
            return;
        }


    }, true);

    document.addEventListener("keyup", function(e) {
        if (e.key === "Alt") {
            alt_c_active = false;
            alt_i_active = false;
            alt_j_active = false;
            hard_block(e);
            return;
        }
        if (is_alt(e, "c") || is_alt(e, "i") || is_alt(e, "j")) {
            if (Date.now() < block_until) hard_block(e);
        }
    }, true);

})();

function sync_marketplace_resi(frm) {
    if (!frm || frm.doctype !== "POS Invoice") return;

    const customer = frm.doc.customer;

    const is_marketplace =
        customer === "Shopee Market Place" ||
        customer === "TikTok Marketplace";

    const section = $('#pos-resi-section');

    // POS masih render ulang → tunggu sampai container tersedia
    if (!section.length) {
        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 200);
        return;
    }

    if (!is_marketplace) {
        section.hide();

        // kosongkan state JS
        window.pos_custom_resi = null;

        // kosongkan UI
        $('#resi-details').hide().empty();
        $('#resi-picker').show();
        $('#pos-resi').val('');

        // kosongkan field invoice
        if (frm.doc.custom_resi_marketplace) {
            frm.set_value("custom_resi_marketplace", "");
        }

        return;
    }

    section.show();

    const resi = (frm.doc.custom_resi_marketplace || "").trim();

    if (!resi) {
        window.pos_custom_resi = null;

        $('#resi-details').hide().empty();
        $('#resi-picker').show();
        $('#pos-resi').val('');

        return;
    }

    window.pos_custom_resi = resi;

    $('#resi-picker').hide();

    $('#resi-details')
        .html(`
            <div class="resi-details">
                <div
                    class="resi-display"
                    style="
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        padding:8px 0;
                    "
                >
                    <div style="flex:1;">
                        <div class="resi-name">
                            ${frappe.utils.escape_html(resi)}
                        </div>
                    </div>

                    <div
                        class="reset-resi-btn"
                        style="cursor:pointer;"
                        title="Ganti Resi"
                    >
                        <svg width="32" height="32" viewBox="0 0 14 14" fill="none">
                            <path
                                d="M4.93764 4.93759L7.00003 6.99998M9.06243 9.06238L7.00003 6.99998M7.00003 6.99998L4.93764 9.06238L9.06243 4.93759"
                                stroke="#8D99A6"
                            ></path>
                        </svg>
                    </div>
                </div>
            </div>
        `)
        .show();
}


async function sync_grosir_ui_from_doc(frm) {
    const is_grosir = cint(frm.doc.custom_is_grosir_mode) === 1;

    const prev = window._last_grosir_state;
    window._last_grosir_state = is_grosir;

    window.pos_grosir_mode = is_grosir;

    const btn = document.querySelector("#btn-ganti-grosir");
    if (!btn) return;

    if (is_grosir) {
        btn.textContent = "MODE GROSIR";
        btn.disabled = true;
        btn.classList.remove("btn-default");
        btn.classList.add("btn-danger");
    } else {
        btn.textContent = "Ganti Harga Grosir";
        btn.disabled = false;
        btn.classList.remove("btn-danger");
        btn.classList.add("btn-default");
    }

    if (prev === true && is_grosir === false) {
        await reset_item_selector_price_context();
    }
}

let pos_item_selector_initialized = false;
async function refresh_pos_item_selector() {
    if (!window.cur_pos?.item_selector) return;

    const selector = cur_pos.item_selector;

    selector.items = [];
    selector.search_index = {};
    selector.item_group = selector.parent_item_group;

    await selector.load_items_data();
    selector.render_item_list(selector.items);
}

async function refresh_pos_item_selector() {
    if (!window.cur_pos?.item_selector) return;

    const selector = cur_pos.item_selector;

    selector.items = [];
    selector.search_index = {};
    selector.item_group = selector.parent_item_group;

    await selector.load_items_data();

    // render ulang item yang tampil
    selector.render_item_list(selector.items);
}

async function set_b2b_default_from_pos_profile(frm) {
    if (!frm || frm.doctype !== "POS Invoice") return;
    if (!frm.is_new()) return;

    const pos_profile = frm.doc.pos_profile;
    if (!pos_profile) return;

    try {
        const r = await frappe.db.get_value(
            "POS Profile",
            pos_profile,
            ["custom_is_b2b", "custom_alamat_b2b"]
        );

        if (!r.message) return;

        const is_b2b = cint(r.message.custom_is_b2b) === 1;
        const alamat_b2b = r.message.custom_alamat_b2b || "";

        await frm.set_value("custom_is_b2b", is_b2b ? 1 : 0);
        await frm.set_value("custom_alamat_b2b", alamat_b2b);

        $('#b2b-checkbox').prop('checked', is_b2b);

        if (is_b2b) {
            $('#b2b-fields').show();
            $('#b2b-address').val(alamat_b2b);
        } else {
            $('#b2b-fields').hide();
            $('#b2b-address').val('');
            $('#invoice-checkbox').prop('checked', false);
        }

        console.log("B2B DEFAULT FROM POS PROFILE:", {
            pos_profile: pos_profile,
            is_b2b: is_b2b,
            alamat_b2b: alamat_b2b
        });

    } catch (err) {
        console.error("Gagal mengambil default B2B dari POS Profile:", err);
    }
}


window.pos_customer_point = 0;
window.pos_customer_max_discount = 0;
window.pos_customer_point_customer = null;
window.pos_customer_point_request_id = 0;


function format_rupiah(value) {
    return 'Rp' + Number(value || 0).toLocaleString('id-ID');
}


function load_customer_point(customer_id) {

    const section = $('#customer-point-section');


    // =====================================================
    // CUSTOMER KOSONG
    // =====================================================
    if (!customer_id) {

        window.pos_customer_point = 0;
        window.pos_customer_max_discount = 0;
        window.pos_customer_point_customer = null;

        if (section.length) {
            section.show();

            $('#customer-point-value').text('0 Point');

            $('#customer-max-discount').text(
                format_rupiah(0)
            );
        }

        console.log('CUSTOMER KOSONG → POINT RESET 0');

        return;
    }


    // =====================================================
    // CONTAINER BELUM ADA
    // =====================================================
    if (!section.length) {

        setTimeout(() => {
            load_customer_point(customer_id);
        }, 300);

        return;
    }


    // =====================================================
    // CUSTOMER SAMA
    // Jangan request API lagi
    // =====================================================
    if (
        window.pos_customer_point_customer === customer_id
    ) {

        section.show();

        console.log(
            'CUSTOMER SAMA → TIDAK REQUEST ULANG:',
            customer_id
        );

        return;
    }


    // =====================================================
    // CUSTOMER BARU
    // =====================================================

    window.pos_customer_point_request_id++;

    const request_id =
        window.pos_customer_point_request_id;

    // Simpan customer yang sedang diminta
    window.pos_customer_point_customer = customer_id;

    section.show();

    $('#customer-point-value').text('Loading...');
    $('#customer-max-discount').text('Loading...');


    console.log(
        'GET CUSTOMER POINT:',
        customer_id,
        'request:',
        request_id
    );


    $.ajax({

        url: 'https://alan.digitalasiasolusindo.com/api/method/alan.api.get_customer_point',

        method: 'GET',

        data: {
            customer_id: customer_id
        },


        success: function (r) {

            // =================================================
            // Kalau ada request baru, abaikan response lama
            // =================================================

            if (
                request_id !==
                window.pos_customer_point_request_id
            ) {

                console.log(
                    'RESPONSE LAMA DIABAIKAN:',
                    customer_id
                );

                return;
            }


            console.log(
                'CUSTOMER POINT RESPONSE:',
                r
            );


            const data = r.message;


            // =================================================
            // API GAGAL / CUSTOMER TIDAK ADA
            // =================================================

            if (!data || !data.success) {

                window.pos_customer_point = 0;
                window.pos_customer_max_discount = 0;

                $('#customer-point-value').text(
                    '0 Point'
                );

                $('#customer-max-discount').text(
                    format_rupiah(0)
                );

                console.log(
                    'API TIDAK MENEMUKAN CUSTOMER:',
                    customer_id
                );

                return;
            }


            // =================================================
            // DATA BERHASIL
            // =================================================

            const point =
                parseFloat(data.jmlpoint) || 0;

            const max_discount =
                point * 2500;


            window.pos_customer_point =
                point;

            window.pos_customer_max_discount =
                max_discount;


            // Pastikan customer masih sama
            window.pos_customer_point_customer =
                customer_id;


            // =================================================
            // UPDATE UI
            // =================================================

            $('#customer-point-value').text(
                `${point.toLocaleString('id-ID')} Point`
            );

            $('#customer-max-discount').text(
                format_rupiah(max_discount)
            );


            console.log(
                'POINT:',
                point
            );

            console.log(
                'MAX DISCOUNT:',
                max_discount
            );
        },


        error: function (xhr, status, error) {

            // Jangan proses response request lama
            if (
                request_id !==
                window.pos_customer_point_request_id
            ) {
                return;
            }


            console.error(
                'GAGAL MENGAMBIL POINT CUSTOMER:',
                error,
                xhr.responseText
            );


            window.pos_customer_point = 0;
            window.pos_customer_max_discount = 0;


            $('#customer-point-value').text(
                '0 Point'
            );

            $('#customer-max-discount').text(
                format_rupiah(0)
            );
        }
    });
}

// frappe.ui.form.on("POS Invoice", {
//     customer(frm) {
//         setTimeout(() => {
//             sync_marketplace_resi(frm);
//         }, 300);

//         // Ambil point customer dari alan.digital
//         setTimeout(() => {
//             load_customer_point(frm.doc.customer);
//         }, 300);
//     },

//     onload(frm) {
//         sync_grosir_ui_from_doc(frm);

//         setTimeout(() => {
//             sync_marketplace_resi(frm);
//         }, 300);

//         // Default B2B dari POS Profile
//         setTimeout(() => {
//             set_b2b_default_from_pos_profile(frm);
//         }, 500);

//         setTimeout(() => {
//             load_customer_point(frm.doc.customer);
//         }, 500);
//     },
//     refresh(frm) {
//         sync_grosir_ui_from_doc(frm);

//         setTimeout(() => {
//             sync_marketplace_resi(frm);
//         }, 300);

//         setTimeout(() => {
//             load_customer_point(frm.doc.customer);
//         }, 300);

//         // Saat POS kembali ke New Order (invoice baru),
//         // reload ulang cache item agar stock terbaru tampil
//         // Lewati refresh pertama saat POS baru dibuka
//         if (!pos_item_selector_initialized) {
//             pos_item_selector_initialized = true;
//             return;
//         }

//         // Hanya saat invoice baru (New Order)
//         if (frm.is_new()) {
//             setTimeout(() => {
//                 refresh_pos_item_selector();
//             }, 300);
//         }
//     }
// });


frappe.ui.form.on("POS Invoice", {

    customer(frm) {

        const customer_id = frm.doc.customer || null;

        // Simpan customer yang sedang aktif
        window.pos_active_customer = customer_id;

        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 300);

        setTimeout(() => {
            load_customer_point(customer_id);
        }, 500);
    },

    onload(frm) {

        sync_grosir_ui_from_doc(frm);

        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 300);

        setTimeout(() => {
            set_b2b_default_from_pos_profile(frm);
        }, 500);

        setTimeout(() => {
            load_customer_point(frm.doc.customer);
        }, 700);
    },

    refresh(frm) {

        sync_grosir_ui_from_doc(frm);

        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 300);

        setTimeout(() => {
            load_customer_point(frm.doc.customer);
        }, 500);

        const current_is_new = !!frm.is_new();
        const previous_is_new = window.cur_pos.pos_auth_last_is_new;

        console.log(
            "[POS AUTH STATE]",
            "previous_is_new =", previous_is_new,
            "current_is_new =", current_is_new,
            "authorized =", window.cur_pos.pos_authorization?.authorized
        );

        window.cur_pos.pos_auth_last_is_new = current_is_new;

        if (
            previous_is_new === false &&
            current_is_new === true
        ) {
            window.cur_pos.pos_authorization = {
                authorized: false,
                auth_provider: null,
                auth_in_progress: null
            };

            console.log("[POS AUTH] New Order detected - authorization reset");
        }

        // =====================================================
        // NEW ORDER TERDETEKSI
        // Hanya reset ketika:
        // saved/submitted invoice → New Order
        // =====================================================

        if (
            previous_is_new === false &&
            current_is_new === true
        ) {
            window.cur_pos.pos_authorization = {
                authorized: false,
                auth_provider: null,
                auth_in_progress: null
            };

            console.log(
                "[POS AUTH] New Order detected - authorization reset"
            );
        }

        // =====================================================
        // REFRESH ITEM SELECTOR
        // =====================================================

        if (!pos_item_selector_initialized) {
            pos_item_selector_initialized = true;
            return;
        }

        if (current_is_new) {
            setTimeout(() => {
                refresh_pos_item_selector();
            }, 300);
        }
    }
});