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



		let pos_edit_auth = {
			item_key: null,   
			fieldname: null,
			active: false
		};

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

			// edit ghata
			async function request_authorization(req_description) {
				return await new Promise(resolve => {

					frappe.prompt(
						[{
							fieldname: "code",
							fieldtype: "Password",
							label: __("Authorization Code"),
							reqd: 1,
						}],
						values => {
							frappe.call({
								method: "customer_display.api.verify_pos_code_auth",
								args: {
									// user: frappe.session.user,
									pos_profile: cur_frm.doc.pos_profile,
                                    code: values.code,
                                    description: req_description,
								},
								callback: r => {
									if (r.message && r.message.valid === true) {
                                        let child = cur_frm.add_child("custom_auth_provider");
                                        child.auth_provider = r.message.auth_provider;
                                        child.description = __(r.message.description); 
                                        
                                        cur_frm.refresh_field("custom_auth_provider"); 

										console.log("Authenticator:", r.message.auth_provider); 
                                        resolve(true);
									} else {
										frappe.msgprint({
											title: __("Authorization Failed"),
											indicator: "red",
											message: __("Authorization code is invalid or not permitted.")
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
			}

			function attachFieldListeners(wrapper, fieldnames = [], frm, item) {

				const item_key = item.name || item.item_code;

				fieldnames.forEach(fieldname => {

					const input = wrapper.querySelector(
						`input[data-fieldname="${fieldname}"]`
					);

					if (!input || input.dataset.listenerAttached) return;

					input.addEventListener("focus", async () => {

						if (
							pos_edit_auth.active &&
							pos_edit_auth.item_key === item_key &&
							pos_edit_auth.fieldname === fieldname
						) {
							return;
						}

						const ok = await request_authorization(`Auth ${fieldname}`);
						if (ok) {
							pos_edit_auth.active = true;
							pos_edit_auth.item_key = item_key;
							pos_edit_auth.fieldname = fieldname;
							frappe.show_alert("Authorized");
						} else {
							input.blur();
						}
					});

					input.addEventListener("change", () => {
						pos_edit_auth.active = false;
						pos_edit_auth.item_key = null;
						pos_edit_auth.fieldname = null;

                        if (fieldname === "qty") {

                            const row = item;

                            if (row) {
                                row.discount_percentage = 0;
                                row.discount_amount = 0;

                                console.log("🔄 Qty changed → discount reset:", row.item_code);

                                if (cur_frm) {
                                    cur_frm.refresh_field("items");
                                }

                                reset_pos_item_discount_ui(wrapper);
                            }
                        }

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

                if (percent_input) {
                    percent_input.value = 0;
                    percent_input.dispatchEvent(new Event("input", { bubbles: true }));
                    percent_input.dispatchEvent(new Event("change", { bubbles: true }));
                }

                if (amount_input) {
                    amount_input.value = 0;
                    amount_input.dispatchEvent(new Event("input", { bubbles: true }));
                    amount_input.dispatchEvent(new Event("change", { bubbles: true }));
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

        function attachDiscountAuthMultiple() {
            const wrapper = document.querySelector('.add-discount-wrapper');
            if (!wrapper || wrapper.dataset.authAttached) return;

            wrapper.addEventListener('click', async (e) => {
                // If already authorized, allow normal interaction
                if (discountAuthorized) return;

                // Prevent the click from propagating
                e.preventDefault();
                e.stopPropagation();

                // Request authorization
                const ok = await request_pos_authorization("Auth add discounts");
                if (!ok) {
                    frappe.show_alert({
                        message: "Authorization failed",
                        indicator: "red"
                    });
                    return;
                }

                // Mark as authorized
                discountAuthorized = true;
                frappe.show_alert("Authorized! You can now add discounts.");

                // Add visual indicator (optional)
                wrapper.style.opacity = '1';
                wrapper.style.pointerEvents = 'auto';
            }, true); // Use capture phase

            // Reset authorization when discount is applied or cleared
            const resetAuth = () => {
                discountAuthorized = false;
                wrapper.style.opacity = ''; // Reset visual indicator
            };

            // Listen for discount changes to reset auth
            $(document).on('change', '.add-discount-field input', resetAuth);

            wrapper.dataset.authAttached = "true";
            
            // Optional: Add visual indicator that auth is required
            wrapper.style.opacity = '0.6';
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

			if (is_dark) {
				//DARK MODE
				new_container.css({
					background: '#171717',
					border: '1px solid rgba(255,255,255,0.08)',
					padding: '16px',
					marginBottom: '1px',
					borderRadius: '12px',
					color: '#e6e6e6'
				});
			} else {
				//LIGHT MODE
				new_container.css({
					background: '#ffffff',
					border: '1px solid #e5e7eb',
					padding: '16px',
					marginBottom: '1px',
					borderRadius: '12px',
					color: '#1f2937'
				});
			}


            customer_cart.prepend(new_container);

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

                <div id="b2b-fields" style="display:none; margin-top: 1px;">
                    <div class="form-group">
                        <label for="b2b-address">Alamat B2B</label>
                        <input type="text" class="form-control" id="b2b-address" placeholder="Masukkan alamat...">
                    </div>
                    <div class="form-check" style="margin-top: 3px;">
                        <input type="checkbox" class="form-check-input" id="invoice-checkbox">
                        <label class="form-check-label" for="invoice-checkbox">Minta Faktur?</label>
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

window.request_pos_authorization = async function (req_description) {
    return await new Promise(resolve => {
        frappe.prompt(
            [{
                fieldname: "code",
                fieldtype: "Password",
                label: __("Authorization Code"),
                reqd: 1,
            }],
            values => {
                frappe.call({
                    method: "customer_display.api.verify_pos_code_auth",
                    args: {
                        // user: frappe.session.user,
                        pos_profile: cur_frm.doc.pos_profile,
                        code: values.code,
                        description: req_description
                    },
                    callback: r => {
                        if (r.message && r.message.valid === true) {
							let child = cur_frm.add_child("custom_auth_provider");
                            child.auth_provider = r.message.auth_provider;
                            child.description = __(r.message.description); 
                            
                            cur_frm.refresh_field("custom_auth_provider"); 

                            console.log("Authenticator:", r.message.auth_provider); 
                            
                            resolve(true);
                        } else {
                            frappe.msgprint({
                                title: __("Authorization Failed"),
                                indicator: "red",
                                message: __("Authorization code is invalid or not permitted.")
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

(function () {

    let allow_remove_once = false;

    document.addEventListener(
        "click",
        async function (e) {

            const btn = e.target.closest(".remove-btn");
            if (!btn) return;

            if (allow_remove_once) {
                allow_remove_once = false;
                return;
            }

            e.preventDefault();
            e.stopImmediatePropagation();

            const ok = await window.request_pos_authorization("Auth remove item");
            if (!ok) {
                frappe.show_alert({
                    message: __("Remove item cancelled"),
                    indicator: "red"
                });
                return;
            }

            frappe.show_alert("Authorized");

            allow_remove_once = true;

            btn.dispatchEvent(
                new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    view: window
                })
            );

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
(function replace_pos_customer_name_text_only() {

    function apply() {
        if (!cur_frm || cur_frm.doctype !== "POS Invoice") return;
        if (!cur_frm.doc.customer_name) return;

        const el = document.querySelector('.customer-section .customer-name');
        if (!el) return;

        el.textContent = cur_frm.doc.customer_name;
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


function apply_pos_discount_percent(percent) {

    const input = get_pos_discount_percent_input()[0];
    if (!input) {
        console.warn("❌ POS discount input not found");
        return;
    }

    input.value = percent;

    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));

    console.log("✅ POS Discount % applied:", percent);
}

function bind_discount_amount_total_handler() {
    $(document)
        .off('change.discount_rp_total')
        .on('change.discount_rp_total', '.discount-amount-rp input', function () {

            const discount_amount = parse_discount_input(this.value);
            if (!discount_amount) return;

            const gross_total = get_pos_items_gross_total();
            if (!gross_total) return;

            const percent = flt(
                ((discount_amount / gross_total) * 100).toFixed(2)
            );

               console.log(
                    `💸 Rp → % ${discount_amount} / ${gross_total} = ${percent.toFixed(2)}% (POS=${(percent/100).toFixed(4)})`
                );

            apply_pos_discount_percent(percent / 100);
        });
}


function inject_pos_hide_net_and_tax_css() {
    if (document.getElementById("pos-hide-net-tax-css")) return;

    const style = document.createElement("style");
    style.id = "pos-hide-net-tax-css";
    style.innerHTML = `
        .cart-totals-section .net-total-container,
        .cart-totals-section .taxes-container {
            display: none !important;
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

frappe.ui.form.on("POS Invoice", {
    //agar setelah new order bisa balik tombolnya
    customer(frm) {
        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 300);
    },
    onload(frm) {
        sync_grosir_ui_from_doc(frm);

        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 300);
    },
    refresh(frm) {
        sync_grosir_ui_from_doc(frm);

        setTimeout(() => {
            sync_marketplace_resi(frm);
        }, 300);

        // Saat POS kembali ke New Order (invoice baru),
        // reload ulang cache item agar stock terbaru tampil
        // Lewati refresh pertama saat POS baru dibuka
        if (!pos_item_selector_initialized) {
            pos_item_selector_initialized = true;
            return;
        }

        // Hanya saat invoice baru (New Order)
        if (frm.is_new()) {
            setTimeout(() => {
                refresh_pos_item_selector();
            }, 300);
        }
    }
});


