let POS_RETURN_MOP = null;
let POS_RETURN_MOP_LOADED = false;

function load_pos_return_mop(callback) {
	if (POS_RETURN_MOP_LOADED) {
		callback();
		return;
	}

	frappe.db.get_single_value("AXTRA Settings", "pos_retur_mode_of_payment")
		.then(value => {
			POS_RETURN_MOP = value || null;
			POS_RETURN_MOP_LOADED = true;
			callback();
		});
}

/* eslint-disable no-unused-vars */
erpnext.PointOfSale.Payment = class {
	constructor({ events, wrapper }) {
		console.log("TEST")
		this.wrapper = wrapper;
		this.events = events;

		this.checkoutClicked = false;

		this.init_component();
	}

	init_component() {
		this.prepare_dom();
		this.initialize_numpad();
		this.bind_events();
		this.attach_shortcuts();
	}

	prepare_dom() {
		this.wrapper.append(
			`<section class="payment-container">
				<div class="section-label payment-section">${__("Payment Method")}</div>
				<div class="payment-modes"></div>
				<div class="fields-numpad-container">
					<div class="fields-section">
						<div class="section-label">${__("Additional Information")}</div>
						<div class="invoice-fields"></div>
					</div>
					<div class="number-pad"></div>
				</div>
				<div class="totals-section">
					<div class="totals"></div>
				</div>
				<div class="submit-order-btn">${__("Complete Order")}</div>
			</section>`
		);
		this.$component = this.wrapper.find(".payment-container");
		this.$payment_modes = this.$component.find(".payment-modes");
		this.$totals_section = this.$component.find(".totals-section");
		this.$totals = this.$component.find(".totals");
		this.$numpad = this.$component.find(".number-pad");
		this.$invoice_fields_section = this.$component.find(".fields-section");
	}

	make_invoice_fields_control() {
		frappe.db.get_doc("POS Settings", undefined).then((doc) => {
			const fields = doc.invoice_fields;
			if (!fields.length) return;

			this.$invoice_fields = this.$invoice_fields_section.find(".invoice-fields");
			this.$invoice_fields.html("");
			const frm = this.events.get_frm();

			fields.forEach((df) => {
				this.$invoice_fields.append(
					`<div class="invoice_detail_field ${df.fieldname}-field" data-fieldname="${df.fieldname}"></div>`
				);
				let df_events = {
					onchange: function () {
						frm.set_value(this.df.fieldname, this.get_value());
					},
				};
				if (df.fieldtype == "Button") {
					df_events = {
						click: function () {
							if (frm.script_manager.has_handlers(df.fieldname, frm.doc.doctype)) {
								frm.script_manager.trigger(df.fieldname, frm.doc.doctype, frm.doc.docname);
							}
						},
					};
				}

				this[`${df.fieldname}_field`] = frappe.ui.form.make_control({
					df: {
						...df,
						...df_events,
					},
					parent: this.$invoice_fields.find(`.${df.fieldname}-field`),
					render_input: true,
				});
				this[`${df.fieldname}_field`].set_value(frm.doc[df.fieldname]);
			});
		});
	}

	initialize_numpad() {
		const me = this;
		this.number_pad = new erpnext.PointOfSale.NumberPad({
			wrapper: this.$numpad,
			events: {
				numpad_event: function ($btn) {
					me.on_numpad_clicked($btn);
				},
			},
			cols: 3,
			keys: [
				[1, 2, 3],
				[4, 5, 6],
				[7, 8, 9],
				[".", 0, "Delete"],
			],
		});

		this.numpad_value = "";
	}

	on_numpad_clicked($btn) {
		const button_value = $btn.attr("data-button-value");

		highlight_numpad_btn($btn);
		this.numpad_value =
			button_value === "delete" ? this.numpad_value.slice(0, -1) : this.numpad_value + button_value;
		this.selected_mode.$input.get(0).focus();
		this.selected_mode.set_value(this.numpad_value);

		function highlight_numpad_btn($btn) {
			$btn.addClass("shadow-base-inner bg-selected");
			setTimeout(() => {
				$btn.removeClass("shadow-base-inner bg-selected");
			}, 100);
		}
	}

	bind_events() {
		const me = this;

		this.$payment_modes.on("click", ".mode-of-payment", function (e) {
			const mode_clicked = $(this);
			// if clicked element doesn't have .mode-of-payment class then return
			if (!$(e.target).is(mode_clicked)) return;

			const scrollLeft =
				mode_clicked.offset().left - me.$payment_modes.offset().left + me.$payment_modes.scrollLeft();
			me.$payment_modes.animate({ scrollLeft });

			const mode = mode_clicked.attr("data-mode");

			// hide all control fields and shortcuts
			$(`.mode-of-payment-control`).css("display", "none");
			$(`.cash-shortcuts`).css("display", "none");
			me.$payment_modes.find(`.pay-amount`).css("display", "inline");
			me.$payment_modes.find(`.loyalty-amount-name`).css("display", "none");

			// remove highlight from all mode-of-payments
			$(".mode-of-payment").removeClass("border-primary");

			if (mode_clicked.hasClass("border-primary")) {
				// clicked one is selected then unselect it
				mode_clicked.removeClass("border-primary");
				me.selected_mode = "";
			} else {
				// clicked one is not selected then select it
				mode_clicked.addClass("border-primary");
				mode_clicked.find(".mode-of-payment-control").css("display", "flex");
				mode_clicked.find(".cash-shortcuts").css("display", "grid");
				me.$payment_modes.find(`.${mode}-amount`).css("display", "none");
				me.$payment_modes.find(`.${mode}-name`).css("display", "inline");

				me.selected_mode = me[`${mode}_control`];
				me.selected_mode && me.selected_mode.$input.get(0).focus();
				me.auto_set_remaining_amount();
			}
		});

		frappe.ui.form.on("POS Invoice", "contact_mobile", (frm) => {
			const contact = frm.doc.contact_mobile;
			const request_button = $(this.request_for_payment_field?.$input[0]);
			if (contact) {
				request_button.removeClass("btn-default").addClass("btn-primary");
			} else {
				request_button.removeClass("btn-primary").addClass("btn-default");
			}
		});

		frappe.ui.form.on("POS Invoice", "coupon_code", (frm) => {
			if (frm.doc.coupon_code && !frm.applying_pos_coupon_code) {
				if (!frm.doc.ignore_pricing_rule) {
					frm.applying_pos_coupon_code = true;
					frappe.run_serially([
						() => (frm.doc.ignore_pricing_rule = 1),
						() => frm.trigger("ignore_pricing_rule"),
						() => (frm.doc.ignore_pricing_rule = 0),
						() => frm.trigger("apply_pricing_rule"),
						() => frm.save(),
						() => this.update_totals_section(frm.doc),
						() => (frm.applying_pos_coupon_code = false),
					]);
				} else if (frm.doc.ignore_pricing_rule) {
					frappe.show_alert({
						message: __("Ignore Pricing Rule is enabled. Cannot apply coupon code."),
						indicator: "orange",
					});
				}
			}
		});

		this.setup_listener_for_payments();

		this.$payment_modes.on("click", ".shortcut", function () {
			const value = $(this).attr("data-value");
			me.selected_mode.set_value(value);
		});

		this.$component.on("click", ".submit-order-btn", () => {
			const doc = this.events.get_frm().doc;
			const paid_amount = doc.paid_amount;
			const items = doc.items;

			if (paid_amount == 0 || !items.length) {
				const message = items.length
					? __("You cannot submit the order without payment.")
					: __("You cannot submit empty order.");
				frappe.show_alert({ message, indicator: "orange" });
				frappe.utils.play_sound("error");
				return;
			}

			if (paid_amount < doc.grand_total) {
				const message = __("You cannot submit the order with payment less than grand total.");
				frappe.show_alert({ message, indicator: "orange" });
				frappe.utils.play_sound("error");
				return;
			}

			this.events.submit_invoice();
		});

		frappe.ui.form.on("POS Invoice", "paid_amount", (frm) => {
			this.update_totals_section(frm.doc);

			// need to re calculate cash shortcuts after discount is applied
			const is_cash_shortcuts_invisible = !this.$payment_modes.find(".cash-shortcuts").is(":visible");
			this.attach_cash_shortcuts(frm.doc);
			!is_cash_shortcuts_invisible &&
				this.$payment_modes.find(".cash-shortcuts").css("display", "grid");
			this.custom_render_payment_mode_dom();
		});

		frappe.ui.form.on("POS Invoice", "loyalty_amount", (frm) => {
			const formatted_currency = format_currency(frm.doc.loyalty_amount, frm.doc.currency);
			this.$payment_modes.find(`.loyalty-amount-amount`).html(formatted_currency);
		});

		frappe.ui.form.on("Sales Invoice Payment", "amount", (frm, cdt, cdn) => {
			// for setting correct amount after loyalty points are redeemed
			const default_mop = locals[cdt][cdn];
			const mode = default_mop.mode_of_payment.replace(/ +/g, "_").toLowerCase();
			if (this[`${mode}_control`] && this[`${mode}_control`].get_value() != default_mop.amount) {
				this[`${mode}_control`].set_value(default_mop.amount);
			}
		});
	}

	setup_listener_for_payments() {
		frappe.realtime.on("process_phone_payment", (data) => {
			const doc = this.events.get_frm().doc;
			const { response, amount, success, failure_message } = data;
			let message, title;

			if (success) {
				title = __("Payment Received");
				const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
					? doc.grand_total
					: doc.rounded_total;
				if (amount >= grand_total) {
					frappe.dom.unfreeze();
					message = __("Payment of {0} received successfully.", [
						format_currency(amount, doc.currency, 0),
					]);
					this.events.submit_invoice();
					cur_frm.reload_doc();
				} else {
					message = __(
						"Payment of {0} received successfully. Waiting for other requests to complete...",
						[format_currency(amount, doc.currency, 0)]
					);
				}
			} else if (failure_message) {
				message = failure_message;
				title = __("Payment Failed");
			}

			frappe.msgprint({ message: message, title: title });
		});
	}

	auto_set_remaining_amount() {
		const doc = this.events.get_frm().doc;
		const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
			? doc.grand_total
			: doc.rounded_total;
		const remaining_amount = grand_total - doc.paid_amount;
		const current_value = this.selected_mode ? this.selected_mode.get_value() : undefined;
		if (!current_value && remaining_amount > 0 && this.selected_mode) {
			this.selected_mode.set_value(remaining_amount);
		}
	}

	attach_shortcuts() {
		const ctrl_label = frappe.utils.is_mac() ? "⌘" : "Ctrl";
		this.$component.find(".submit-order-btn").attr("title", `${ctrl_label}+Enter`);
		frappe.ui.keys.on("ctrl+enter", () => {
			const payment_is_visible = this.$component.is(":visible");
			const active_mode = this.$payment_modes.find(".border-primary");
			if (payment_is_visible && active_mode.length) {
				this.$component.find(".submit-order-btn").click();
			}
		});

		frappe.ui.keys.add_shortcut({
			shortcut: "tab",
			action: () => {
				const payment_is_visible = this.$component.is(":visible");
				let active_mode = this.$payment_modes.find(".border-primary");
				active_mode = active_mode.length ? active_mode.attr("data-mode") : undefined;

				if (!active_mode) return;

				const mode_of_payments = Array.from(this.$payment_modes.find(".mode-of-payment")).map((m) =>
					$(m).attr("data-mode")
				);
				const mode_index = mode_of_payments.indexOf(active_mode);
				const next_mode_index = (mode_index + 1) % mode_of_payments.length;
				const next_mode_to_be_clicked = this.$payment_modes.find(
					`.mode-of-payment[data-mode="${mode_of_payments[next_mode_index]}"]`
				);

				if (payment_is_visible && mode_index != next_mode_index) {
					next_mode_to_be_clicked.click();
				}
			},
			condition: () =>
				this.$component.is(":visible") && this.$payment_modes.find(".border-primary").length,
			description: __("Switch Between Payment Modes"),
			ignore_inputs: true,
			page: cur_page.page.page,
		});
	}

	toggle_numpad() {
		// pass
	}

	render_payment_section() {
		this.custom_render_payment_mode_dom();
		this.make_invoice_fields_control();
		this.update_totals_section();
		this.focus_on_default_mop();
	}

	after_render() {
		const frm = this.events.get_frm();
		frm.script_manager.trigger("after_payment_render", frm.doc.doctype, frm.doc.docname);
	}

	edit_cart() {

		this.events.toggle_other_sections(false);
		this.toggle_component(false);
	}

	checkout() {

		this.checkoutClicked = true;

		this.events.toggle_other_sections(true);
		this.toggle_component(true);

		this.render_payment_section();
		this.after_render();
	}

	toggle_remarks_control() {
		if (this.$remarks.find(".frappe-control").length) {
			this.$remarks.html("+ Add Remark");
		} else {
			this.$remarks.html("");
			this[`remark_control`] = frappe.ui.form.make_control({
				df: {
					label: __("Remark"),
					fieldtype: "Data",
					onchange: function () {},
				},
				parent: this.$totals_section.find(`.remarks`),
				render_input: true,
			});
			this[`remark_control`].set_value("");
		}
	}

	// custom_render_payment_mode_dom() {

	// 	console.log("test test test");
		
	// 	const doc = this.events.get_frm().doc;
	// 	const payments = doc.payments;
	// 	const currency = doc.currency;

	// 	this.$payment_modes.html(
	// 		`${payments
	// 			.map((p, i) => {
	// 				const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
	// 				const payment_type = p.type;
	// 				const margin = i % 2 === 0 ? "pr-2" : "pl-2";
	// 				const amount = p.amount > 0 ? format_currency(p.amount, currency) : "";

	// 			// return `
	// 			// 	<div class="payment-mode-wrapper">
	// 			// 		<div class="mode-of-payment" data-mode="${mode}" data-payment-type="${payment_type}">
	// 			// 			${p.mode_of_payment}
	// 			// 			<div class="${mode}-amount pay-amount">${amount}</div>
	// 			// 			<div class="${mode} mode-of-payment-control"></div>
	// 			// 		</div>
	// 			// 	</div>
	// 			// `;

	// 			return `
	// 				<div class="payment-mode-wrapper">
	// 					<div class="mode-of-payment" data-mode="${mode}" data-payment-type="${payment_type}">
	// 						${p.mode_of_payment}
	// 						<div class="${mode}-amount pay-amount">${amount}</div>
	// 						<div class="${mode} mode-of-payment-control payment-control-stack"></div>
	// 					</div>
	// 				</div>
	// 			`;

	// 			})
	// 			.join("")}`
	// 	);

	// 	///
	// 	this.$payment_modes
	// 	.find(".payment-control-stack")
	// 	.css({
	// 		display: "flex",
	// 		flexDirection: "column",
	// 		gap: "6px"
	// 	});
	// 	///

	// 	payments.forEach((p) => {
	// 		const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
	// 		const me = this;
	// 		this[`${mode}_control`] = frappe.ui.form.make_control({
	// 			df: {
	// 				label: p.mode_of_payment,
	// 				fieldtype: "Currency",
	// 				placeholder: __("Enter {0} amount.", [p.mode_of_payment]),
	// 				onchange: function () {
	// 					const current_value = frappe.model.get_value(p.doctype, p.name, "amount");
	// 					if (current_value != this.value) {
	// 						frappe.model
	// 							.set_value(p.doctype, p.name, "amount", flt(this.value))
	// 							.then(() => me.update_totals_section());

	// 						const formatted_currency = format_currency(this.value, currency);
	// 						me.$payment_modes.find(`.${mode}-amount`).html(formatted_currency);
	// 					}
	// 				},
	// 			},
	// 			parent: this.$payment_modes.find(`.${mode}.mode-of-payment-control`),
	// 			render_input: true,
	// 		});
	// 		this[`${mode}_control`].toggle_label(false);
	// 		this[`${mode}_control`].set_value(p.amount);

	// 		///////////////////////////////////////////////

	// 		const parent = this.$payment_modes.find(
	// 			`.${mode}.mode-of-payment-control`
	// 		);

	// 		parent.css({
	// 			display: "flex",
	// 			flexDirection: "column",
	// 			gap: "6px"
	// 		});

	// 		const checkbox = $(`
	// 			<label style="
	// 				display: flex;
	// 				align-items: center; /* sebelumnya 'left', diganti center */
	// 				gap: 6px;
	// 				font-size: 12px;
	// 				cursor: pointer;
	// 			">
	// 				<input type="checkbox" class="charge-toggle">
	// 				Charge
	// 			</label>
	// 		`);

	// 		parent.append(checkbox);


	// 		const charge_control = frappe.ui.form.make_control({
	// 			df: {
	// 				label: "Charge Amount",
	// 				fieldtype: "Currency",
	// 				placeholder: __("Enter charge amount."),
	// 				onchange: function () {
	// 					const charge_val = flt(this.value);
	// 					frappe.model.set_value(p.doctype, p.name, "custom_charge_card", charge_val)
	// 						.then(() => {
	// 							const doc = me.events.get_frm().doc;

	// 							// Hitung total charge semua mode
	// 							const total_charge = flt(doc.payments.reduce((sum, x) => sum + flt(x.custom_charge_card || 0), 0));

	// 							// Update grand total sementara
	// 							doc.grand_total = flt(doc.grand_total_original || doc.grand_total) + total_charge;

	// 							// Update display
	// 							me.update_totals_section(doc);

	// 							// Update mode-of-payment display
	// 							const base_payment = flt(p.amount) - flt(p.custom_charge_card || 0);
	// 							const new_payment = base_payment + charge_val;
	// 							me[`${mode}_control`].set_value(new_payment);
	// 							me.$payment_modes.find(`.${mode}-amount`).html(format_currency(new_payment, doc.currency));
	// 						});
	// 				}

	// 			},
	// 			parent: parent,
	// 			render_input: true
	// 		});




	// 		charge_control.$wrapper.hide();

	// 		charge_control.set_value(p.custom_charge_card || 0);

	// 		if (p.custom_charge_card && p.custom_charge_card > 0) {
	// 			checkbox.find("input").prop("checked", true);
	// 			charge_control.$wrapper.show();
	// 		} else {
	// 			checkbox.find("input").prop("checked", false);
	// 			charge_control.$wrapper.hide();
	// 		}

	// 		checkbox.find("input").on("change", function () {
	// 			if (this.checked) {
	// 				charge_control.$wrapper.show();
	// 				charge_control.set_value(p.custom_charge_card || 0);
	// 			} else {
	// 				charge_control.$wrapper.hide();
	// 				frappe.model.set_value(
	// 					p.doctype,
	// 					p.name,
	// 					"custom_charge_card",
	// 					0
	// 				);
	// 				charge_control.set_value(0);
	// 			}
	// 		});

	// 	});
		
	// 	// this.$payment_modes.empty();

	//     //   const frm = this.events.get_frm();
	//     //   const parent = this.$payment_modes;

	//     //   // create one searchable Link to Mode of Payment
	//     //   this.payment_method_control = frappe.ui.form.make_control({
	//     //     df: {
	//     //       fieldname: "single_mode_of_payment",
	//     //       label: __("Payment Method"),
	//     //       fieldtype: "Link",
	//     //       options: "Mode of Payment",
	//     //       reqd: 1,
	//     //     },
	//     //     parent: parent,
	//     //     render_input: true,
	//     //   });

	//     //   // when selection changes, overwrite the payments child table
	//     //   this.payment_method_control.$input.on("change", () => {
	//     //     const method = this.payment_method_control.get_value();
	//     //     const total = frm.doc.rounded_total || frm.doc.grand_total;

	//     //     // reset the payments table to exactly one row
	//     //     frm.doc.payments = [{
	//     //       doctype: "Sales Invoice Payment",
	//     //       mode_of_payment: method,
	//     //       amount: total,
	//     //     }];

	//     //     frm.refresh_field("payments");
	//     //     // update the totals display (Paid / Change)
	//     //     this.update_totals_section(frm.doc);
	//     //   });

	//     //   // prefill with whatever default the invoice had
	//     //   const existing = frm.doc.payments[0]?.mode_of_payment;
	//     //   if (existing) {
	//     //     this.payment_method_control.set_value(existing);
	//     //   }


	// 	this.render_loyalty_points_payment_mode();

	// 	this.attach_cash_shortcuts(doc);
	// }

	custom_render_payment_mode_dom() {
		load_pos_return_mop(() => {
			this._render_payment_mode_dom_internal();
		});
	}


	_render_payment_mode_dom_internal() {
		const doc = this.events.get_frm().doc;
		const payments = doc.payments;
		const currency = doc.currency;

		this.$payment_modes.html(
			`${payments.map((p) => {
				const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
				const amount = p.amount > 0 ? format_currency(p.amount, currency) : "";
				return `
					<div class="payment-mode-wrapper">
						<div class="mode-of-payment" data-mode="${mode}">
							${p.mode_of_payment}
							<div class="${mode}-amount pay-amount">${amount}</div>
							<div class="${mode} mode-of-payment-control payment-control-stack"></div>
						</div>
					</div>
				`;
			}).join("")}`
		);

		this.$payment_modes.find(".payment-control-stack").css({
			display: "flex",
			flexDirection: "column",
			gap: "6px"
		});

		payments.forEach((p) => {
			const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
			const me = this;

			const is_pos_return_mode =
				POS_RETURN_MOP && p.mode_of_payment === POS_RETURN_MOP;

			this[`${mode}_control`] = frappe.ui.form.make_control({
				df: {
					label: p.mode_of_payment,
					fieldtype: "Currency",
					placeholder: __("Enter {0} amount.", [p.mode_of_payment]),
					onchange: function () {
						const current_value = frappe.model.get_value(p.doctype, p.name, "amount");
						if (current_value != this.value) {
							frappe.model
								.set_value(p.doctype, p.name, "amount", flt(this.value))
								.then(() => me.update_totals_section());
							me.$payment_modes
								.find(`.${mode}-amount`)
								.html(format_currency(this.value, currency));
						}
					},
				},
				parent: this.$payment_modes.find(`.${mode}.mode-of-payment-control`),
				render_input: true,
			});

			this[`${mode}_control`].toggle_label(false);
			this[`${mode}_control`].set_value(p.amount);

			const parent = this.$payment_modes.find(`.${mode}.mode-of-payment-control`);
			parent.css({ display: "flex", flexDirection: "column", gap: "6px" });

			if (is_pos_return_mode) {
				const btn = $(`
					<button type="button" class="btn btn-sm btn-primary">
						POS Return
					</button>
				`);

				btn.on("click", () => {
					me.open_pos_return_dialog(p);
				});

				parent.append(btn);

				return;
			}


			const checkbox = $(`
				<label style="display: flex; align-items: center; gap: 6px; font-size: 12px; cursor: pointer;">
					<input type="checkbox" class="charge-toggle"> Charge
				</label>
			`);
			parent.append(checkbox);

			const charge_percent_control = frappe.ui.form.make_control({
				df: {
					label: "Charge %",
					fieldtype: "Data",
					placeholder: __("Enter charge percent."),
					onchange: function () {
						update_charge(this.value);
					},
				},
				parent: parent,
				render_input: true,
			});

			charge_percent_control.$wrapper.hide();
			charge_percent_control.set_value(parseFloat(p.custom_charge_percent.toString().replace(",",".")) || 0);

			if (p.custom_charge_percent && parseFloat(p.custom_charge_percent.toString().replace(",",".")) > 0) {
				checkbox.find("input").prop("checked", true);
				charge_percent_control.$wrapper.show();
			}

			checkbox.find("input").on("change", function () {
				if (this.checked) {
					charge_percent_control.$wrapper.show();
					charge_percent_control.set_value(p.custom_charge_percent || 0);
				} else {
					charge_percent_control.$wrapper.hide();
					frappe.model.set_value(p.doctype, p.name, "custom_charge_percent", 0);
					charge_percent_control.set_value(0);
					update_charge(0);
				}
			});

			function update_charge(percent) {
				const base_payment = flt(p.amount);

				frappe.model.set_value(
					p.doctype,
					p.name,
					"custom_charge_percent",
					percent || 0
				);

				const doc = me.events.get_frm().doc;

				const total_charge = flt(
					doc.payments.reduce((sum, x) => {
						var charge_bob = parseFloat(x.custom_charge_percent.toString().replace(",","."))
						return (
							sum +
							(flt(
								charge_bob
									? flt(x.amount * charge_bob / 100)
									: 0
							))
						);
					}, 0)
				);

				me.update_totals_section(doc);
				update_paid_with_charge_display(doc, total_charge);

				me[`${mode}_control`].set_value(base_payment);
				me.$payment_modes
					.find(`.${mode}-amount`)
					.html(format_currency(base_payment, doc.currency));
			}
		});

		function update_paid_with_charge_display(doc, charge_total) {
			const $totals_section = $(".totals-section");
			const $paid_col = $totals_section.find(".col").eq(1);

			let base_paid = flt(doc.paid_amount || 0);
			let total_with_charge = base_paid + flt(charge_total);

			$paid_col.find(".paid-with-charge").remove();

			$paid_col.append(`
				<div class="paid-with-charge" style="font-size: 12px; color: #555;">
					(+Charge: ${format_currency(flt(charge_total), doc.currency)})
					Total: ${format_currency(total_with_charge, doc.currency)}
				</div>
			`);
		}

		this.render_loyalty_points_payment_mode();
		this.attach_cash_shortcuts(doc);
	}

	open_pos_return_dialog(payment_row) {
		const me = this;
		const doc = this.events.get_frm().doc;

		frappe.call({
			method: "customer_display.customer_display.page.point_of_sale.custom_pos_return_ledger.get_available_returns",
			args: {
				customer: doc.customer,
				pos_invoice: doc.name
			}
		}).then(r => {
			const data = r.message || [];
			me.render_pos_return_dialog(data, payment_row);
		});
	}

	render_pos_return_dialog(returns, payment_row) {
		const me = this;
		const frm = this.events.get_frm();
		const doc = frm.doc;

		let selected = {};

		const dialog = new frappe.ui.Dialog({
			title: __("POS Invoice Return"),
			size: "large",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "return_table"
				}
			],
			primary_action_label: __("Apply"),
			primary_action() {

				let total_amount = 0;
				const selected_rows = Object.values(selected);

				if (!selected_rows.length) {
					frappe.msgprint(__("Pilih minimal satu POS Return"));
					return;
				}

				frappe.model.clear_table(doc, "custom_pos_return_usage");

				selected_rows.forEach(r => {
					total_amount += flt(r.available_amount);

					const child = frappe.model.add_child(
						doc,
						"custom_pos_return_usage"
					);

					child.pos_invoice_return = r.name;
					child.available_amount = flt(r.available_amount);
				});

				frm.refresh_field("custom_pos_return_usage");

				frappe.model.set_value(
					payment_row.doctype,
					payment_row.name,
					"amount",
					total_amount
				);

				const mode = payment_row.mode_of_payment
					.replace(/ +/g, "_")
					.toLowerCase();

				me.$payment_modes
					.find(`.${mode}-amount`)
					.html(format_currency(total_amount, doc.currency))
					.show();

				me.update_totals_section(doc);

				dialog.hide();
			}
		});

		const $wrapper = $(dialog.fields_dict.return_table.wrapper);

		if (!returns.length) {
			$wrapper.html(
				`<div class="text-muted">Tidak ada POS Return yang tersedia.</div>`
			);
			dialog.show();
			return;
		}

		const table = $(`
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th style="width:40px"></th>
						<th>Return Invoice</th>
						<th class="text-right">Available Amount</th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		`);

		returns.forEach(r => {
			const row = $(`
				<tr>
					<td>
						<input type="checkbox" class="return-check">
					</td>
					<td>${r.name}</td>
					<td class="text-right">
						${format_currency(r.available_amount, doc.currency)}
					</td>
				</tr>
			`);

			row.find(".return-check").on("change", function () {
				if (this.checked) {
					selected[r.name] = r;
				} else {
					delete selected[r.name];
				}
			});

			table.find("tbody").append(row);
		});

		$wrapper.append(table);
		dialog.show();
	}

	focus_on_default_mop() {
		const doc = this.events.get_frm().doc;
		const payments = doc.payments;
		payments.forEach((p) => {
			const mode = p.mode_of_payment.replace(/ +/g, "_").toLowerCase();
			if (p.default) {
				setTimeout(() => {
					this.$payment_modes.find(`.${mode}.mode-of-payment-control`).parent().click();
				}, 500);
			}
		});
	}

	attach_cash_shortcuts(doc) {
		const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
			? doc.grand_total
			: doc.rounded_total;
		const currency = doc.currency;

		const shortcuts = this.get_cash_shortcuts(flt(grand_total));

		this.$payment_modes.find(".cash-shortcuts").remove();
		let shortcuts_html = shortcuts
			.map((s) => {
				return `<div class="shortcut" data-value="${s}">${format_currency(s, currency, 0)}</div>`;
			})
			.join("");

		this.$payment_modes
			.find('[data-payment-type="Cash"]')
			.find(".mode-of-payment-control")
			.after(`<div class="cash-shortcuts">${shortcuts_html}</div>`);
	}

	get_cash_shortcuts(grand_total) {
		let steps = [1, 5, 10];
		const digits = String(Math.round(grand_total)).length;

		steps = steps.map((x) => x * 10 ** (digits - 2));

		const get_nearest = (amount, x) => {
			let nearest_x = Math.ceil(amount / x) * x;
			return nearest_x === amount ? nearest_x + x : nearest_x;
		};

		return steps.reduce((finalArr, x) => {
			let nearest_x = get_nearest(grand_total, x);
			nearest_x = finalArr.indexOf(nearest_x) != -1 ? nearest_x + x : nearest_x;
			return [...finalArr, nearest_x];
		}, []);
	}

	render_loyalty_points_payment_mode() {
		const me = this;
		const doc = this.events.get_frm().doc;
		const { loyalty_program, loyalty_points, conversion_factor } = this.events.get_customer_details();

		this.$payment_modes.find(`.mode-of-payment[data-mode="loyalty-amount"]`).parent().remove();

		if (!loyalty_program) return;

		let description, read_only, max_redeemable_amount;
		if (!loyalty_points) {
			description = __("You don't have enough points to redeem.");
			read_only = true;
		} else {
			max_redeemable_amount = flt(
				flt(loyalty_points) * flt(conversion_factor),
				precision("loyalty_amount", doc)
			);
			description = __("You can redeem upto {0}.", [format_currency(max_redeemable_amount)]);
			read_only = false;
		}

		const margin = this.$payment_modes.children().length % 2 === 0 ? "pr-2" : "pl-2";
		const amount = doc.loyalty_amount > 0 ? format_currency(doc.loyalty_amount, doc.currency) : "";
		this.$payment_modes.append(
			`<div class="payment-mode-wrapper">
				<div class="mode-of-payment loyalty-card" data-mode="loyalty-amount" data-payment-type="loyalty-amount">
					Redeem Loyalty Points
					<div class="loyalty-amount-amount pay-amount">${amount}</div>
					<div class="loyalty-amount-name">${loyalty_program}</div>
					<div class="loyalty-amount mode-of-payment-control"></div>
				</div>
			</div>`
		);

		this["loyalty-amount_control"] = frappe.ui.form.make_control({
			df: {
				label: __("Redeem Loyalty Points"),
				fieldtype: "Currency",
				placeholder: __("Enter amount to be redeemed."),
				options: "company:currency",
				read_only,
				onchange: async function () {
					if (!loyalty_points) return;

					if (this.value > max_redeemable_amount) {
						frappe.show_alert({
							message: __("You cannot redeem more than {0}.", [
								format_currency(max_redeemable_amount),
							]),
							indicator: "red",
						});
						frappe.utils.play_sound("submit");
						me["loyalty-amount_control"].set_value(0);
						return;
					}
					const redeem_loyalty_points = this.value > 0 ? 1 : 0;
					await frappe.model.set_value(
						doc.doctype,
						doc.name,
						"redeem_loyalty_points",
						redeem_loyalty_points
					);
					frappe.model.set_value(
						doc.doctype,
						doc.name,
						"loyalty_points",
						parseInt(this.value / conversion_factor)
					);
				},
				description,
			},
			parent: this.$payment_modes.find(`.loyalty-amount.mode-of-payment-control`),
			render_input: true,
		});
		this["loyalty-amount_control"].toggle_label(false);

		// this.render_add_payment_method_dom();
	}

	render_add_payment_method_dom() {
		const docstatus = this.events.get_frm().doc.docstatus;
		if (docstatus === 0)
			this.$payment_modes.append(
				`<div class="w-full pr-2">
					<div class="add-mode-of-payment w-half text-grey mb-4 no-select pointer">+ Add Payment Method</div>
				</div>`
			);
	}

	// update_totals_section(doc) {
	// 	if (!doc) doc = this.events.get_frm().doc;
	// 	const paid_amount = doc.paid_amount;
	// 	const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
	// 		? doc.grand_total
	// 		: doc.rounded_total;
	// 	const remaining = grand_total - doc.paid_amount;
	// 	const change = doc.change_amount || remaining <= 0 ? -1 * remaining : undefined;
	// 	const currency = doc.currency;
	// 	const label = change ? __("Change") : __("To Be Paid");

	// 	this.$totals.html(
	// 		`<div class="col">
	// 			<div class="total-label">${__("Grand Total")}</div>
	// 			<div class="value">${format_currency(grand_total, currency)}</div>
	// 		</div>
	// 		<div class="seperator-y"></div>
	// 		<div class="col">
	// 			<div class="total-label">${__("Paid Amount")}</div>
	// 			<div class="value">${format_currency(paid_amount, currency)}</div>
	// 		</div>
	// 		<div class="seperator-y"></div>
	// 		<div class="col">
	// 			<div class="total-label">${label}</div>
	// 			<div class="value">${format_currency(change || remaining, currency)}</div>
	// 		</div>`
	// 	);

	// 	if (this.checkoutClicked) {

	// 		frappe.call({
	// 			method: "customer_display.api.update_customer_display_pay_amount",
	// 			args: {
	// 				pos_profile: doc.pos_profile,
	// 				paid:        flt(paid_amount),
	// 				change:      flt(change)
	// 			},
	// 			freeze: false
	// 		}).catch(err => {
	// 			console.warn("Failed to push paid/change to display:", err);
	// 		}); 
	// 	}
	// }

	update_totals_section(doc) {
		if (!doc) doc = this.events.get_frm().doc;

		const total_charge = flt(doc.payments.reduce((sum, x) => {
			var charge_bob = parseFloat(x.custom_charge_percent.toString().replace(",",".")) //x.custom_charge_percent
			if (charge_bob) {
				return sum + flt(x.amount * charge_bob / 100);
			} else if (x.custom_charge_card) {
				return sum + flt(x.custom_charge_card);
			}
			return sum;
		}, 0));

		const paid_amount_with_charge = flt(doc.paid_amount || 0) + total_charge;

		const grand_total = cint(frappe.sys_defaults.disable_rounded_total)
			? doc.grand_total
			: doc.rounded_total;

		const grand_total_with_charge = grand_total + total_charge;

		const remaining = grand_total_with_charge - flt(paid_amount_with_charge);
		const change = doc.change_amount || remaining <= 0 ? -1 * remaining : undefined;
		const currency = doc.currency;
		const label = change ? __("Change") : __("To Be Paid");

		this.$totals.html(
			`<div class="col">
				<div class="total-label">${__("Grand Total + Charge")}</div>
				<div class="value">${format_currency(grand_total_with_charge, currency)}</div>
			</div>
			<div class="seperator-y"></div>
			<div class="col">
				<div class="total-label">${__("Paid Amount")}</div>
				<div class="value">${format_currency(paid_amount_with_charge, currency)}</div>
			</div>
			<div class="seperator-y"></div>
			<div class="col">
				<div class="total-label">${label}</div>
				<div class="value">${format_currency(change || remaining, currency)}</div>
			</div>`
		);

		if (this.checkoutClicked) {
			frappe.call({
				method: "customer_display.api.update_customer_display_pay_amount",
				args: {
					pos_profile: doc.pos_profile,
					paid:        flt(paid_amount_with_charge),
					change:      flt(change)
				},
				freeze: false
			}).catch(err => {
				console.warn("Failed to push paid/change to display:", err);
			}); 
		}
	}


	toggle_component(show) {
		show ? this.$component.css("display", "flex") : this.$component.css("display", "none");
	}
};
