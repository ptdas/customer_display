frappe.provide("erpnext.PointOfSale");

frappe.pages["point-of-sale"].on_page_load = function (wrapper) {
	
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
        });
		/////////
		
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
			async function request_authorization() {
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
								method: "customer_display.api.verify_pos_code",
								args: {
									user: frappe.session.user,
									code: values.code
								},
								callback: r => {
									if (r.message === true) {
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

						const ok = await request_authorization();
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
					});

					input.dataset.listenerAttached = "true";
				});
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
							["qty", "discount_percentage", "rate"],
							frm,
							item
						);
					//////
	        };

	    }
	});

    if (!window._pos_spg_listener) {
        window._pos_spg_listener = true;

        function handleSPGChange(val) {
            if (!val) return;
            window.pos_spg_default = val;
            console.log("🌟 SPG default set:", val);
        }

        $(document).on("input", 'input[data-fieldname="custom_handled_by_spg"]', function () {
            handleSPGChange(this.value);
        });

        $(document).on("awesomplete-selectcomplete", 'input[data-fieldname="custom_handled_by_spg"]', function () {
            handleSPGChange(this.value);
        });
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

            //tema putih
            // new_container.css({
            //     'background': '#ffffff',
            //     'border': '1px solid #dcdcdc',
            //     'padding': '20px',
            //     'margin-bottom': '10px',
            //     'border-radius': '4px',
            //     'box-shadow': 'none'
            // });

            //tema hitam
            new_container.css({
                background: '#171717',
                border: '1px solid rgba(255,255,255,0.00)',
                padding: '16px',
                marginBottom: '12px',
                borderRadius: '12px',
                color: '#e6e6e6'
            });


            customer_cart.prepend(new_container);

            new_container.append(`
                <div class="form-check mb-2">
                    <input type="checkbox" class="form-check-input" id="b2b-checkbox">
                    <label class="form-check-label" for="b2b-checkbox">B2B</label>
                </div>
                <div id="b2b-fields" style="display:none; margin-top: 10px;">
                    <div class="form-group">
                        <label for="b2b-address">Alamat B2B</label>
                        <input type="text" class="form-control" id="b2b-address" placeholder="Masukkan alamat...">
                    </div>
                    <div class="form-check">
                        <input type="checkbox" class="form-check-input" id="invoice-checkbox">
                        <label class="form-check-label" for="invoice-checkbox">Minta Faktur?</label>
                    </div>
                </div>
            `);

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



window.request_pos_authorization = async function () {
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
                    method: "customer_display.api.verify_pos_code",
                    args: {
                        user: frappe.session.user,
                        code: values.code
                    },
                    callback: r => {
                        if (r.message === true) {
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

            const ok = await window.request_pos_authorization();
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

function inject_discount_amount_total() {

    const $field = $('.cart-totals-section .add-discount-field');
    if (!$field.length) return;

    // sudah ada → stop
    if ($field.find('.discount-amount-rp').length) return;

    // paksa vertical layout
    $field.css({
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
    });

    const html = `
        <div class="discount-amount-rp">
            <input type="text"
                class="form-control input-xs"
                placeholder="Disc Rp"
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




function bind_discount_amount_total_handler() {
    $(document)
        .off('change.discount_rp_total')
        .on('change.discount_rp_total', '.discount-amount-rp input', function () {

            const discount_amount = flt(this.value);
            if (!discount_amount) return;

            const net_total = flt(cur_frm.doc.net_total);
            if (!net_total) return;

            const discount_percentage = (discount_amount / net_total) * 100;

            cur_pos.cart.set_discount(discount_percentage);

            console.log(
                '💸 Discount Rp → %',
                discount_amount,
                '=>',
                discount_percentage.toFixed(2) + '%'
            );
        });
}
