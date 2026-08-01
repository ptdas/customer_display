



frappe.ui.form.on("Purchase Invoice", {
	onload: function(frm) {
		if (frm.doc.docstatus == 0 && frm.doc.items) {
			frm.doc.items.forEach(function(item) {
				if (item.item_code) {
					fill_item_price(frm, item.doctype, item.name);
				}
			});
		}
		if (frm.doc.supplier) {
			set_company_filter(frm);
		}
	},
	supplier: function(frm) {
		if (frm.doc.supplier) {
			set_company_filter(frm);
		}
	},
	custom_get_items_from_invoice(frm){
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
	custom_distribute_charges_based_on(frm) {
		set_applicable_charges_for_item(frm);
	},
	refresh(frm){

		hide_perm(frm);

		custom_get_item_from_pinv_with_lcv(frm);

		/////pinv forwader
		 if (frm.doc.docstatus === 1 &&
			flt(frm.doc.custom_lcv_total_taxes_and_charges) > 0 &&
			frm.doc.custom_forwarder) {

				frm.add_custom_button(__('PINV Forwarder'), function() {
						frappe.model.open_mapped_doc({
							method: "customer_display.custom_standard.purchase_invoice_custom.create_forwarder_pinv",
							frm: frm
						});
				}, __('Create'));

		}
			
		////

		frm.fields_dict['custom_landed_cost_taxes_and_charges'].grid.get_field('expense_account').get_query = function(doc, cdt, cdn) {
			return {
				filters: {
					company: doc.company
				}
			};
		};

		var help_content = `<br><br>
			<table class="table table-bordered" style="background-color: var(--scrollbar-track-color);">
				<tr><td>
					<h4>
						<i class="fa fa-hand-right"></i>
						${__("Notes")}:
					</h4>
					<ul>
						<li>
							${__("Charges will be distributed proportionately based on item qty or amount, as per your selection")}
						</li>
						<li>
							${__("Remove item if charges is not applicable to that item")}
						</li>
						<li>
							${__("Charges are updated in Purchase Receipt against each item")}
						</li>
						<li>
							${__("Item valuation rate is recalculated considering landed cost voucher amount")}
						</li>
						<li>
							${__("Stock Ledger Entries and GL Entries are reposted for the selected Purchase Receipts")}
						</li>
					</ul>
				</td></tr>
			</table>`;

		set_field_options("custom_landed_cost_help", help_content);
	}


});

frappe.ui.form.on("Purchase Invoice Item", {
	item_code(frm, cdt, cdn) {
		fill_item_price(frm,cdt,cdn)
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
	qty(frm, cdt, cdn) {
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
	rate(frm, cdt, cdn) {
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
	amount(frm, cdt, cdn) {
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
	custom_lcv_item_remove(frm, cdt, cdn) {
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
	remove(frm, cdt, cdn) {
		sync_items_to_lcv(frm);
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	}
});

frappe.ui.form.on("PINV LCV Taxes and Charges", {
	expense_account(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.db.get_value('Account', row.expense_account, 'account_currency')
			.then(r => {
				if (r && r.message) {
					frappe.model.set_value(cdt, cdn, 'account_currency', r.message.account_currency);
				}
			});
	},
	amount(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'base_amount', flt(row.amount) * flt(frm.doc.conversion_rate || 1));

		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
});

frappe.ui.form.on("PINV LCV Item", {
	constant(frm, cdt, cdn) {
		set_total_taxes_and_charges(frm);
		set_applicable_charges_for_item(frm);
	},
});

function sync_items_to_lcv(frm) {
	if (frm.doc.docstatus !== 0) return;

	const existing_map = {};
	frm.doc.custom_lcv_item.forEach(row => {
		existing_map[row.reference_detail] = row;
	});

	const active_refs = new Set(); 

	frm.doc.items.forEach(src => {
		let target = existing_map[src.name];

		if (target) {
			let keep_constant = target.constant;

			target.item_code = src.item_code;
			target.item_name = src.item_name;
			target.qty = src.qty;
			target.rate = src.rate;
			// target.amount = src.amount;
			target.amount = flt(src.qty) * flt(src.rate);
			target.cost_center = src.cost_center;
			target.description = src.description;

			if (keep_constant !== undefined && keep_constant !== null) {
				target.constant = keep_constant;
			}

		} else {
			target = frm.add_child("custom_lcv_item");
			target.reference_detail = src.name;
			target.item_code = src.item_code;
			target.item_name = src.item_name;
			target.qty = src.qty;
			target.rate = src.rate;
			// target.amount = src.amount;
			target.amount = flt(src.qty) * flt(src.rate);
			target.cost_center = src.cost_center;
			target.description = src.description;
			target.receipt_document = frm.doc.name;
		}

		active_refs.add(src.name); 
	});

	frm.doc.custom_lcv_item = frm.doc.custom_lcv_item.filter(row => {
		return active_refs.has(row.reference_detail);
	});

	frm.refresh_field("custom_lcv_item");
}

function custom_get_item_from_pinv_with_lcv(frm) {
	if (frm.doc.docstatus !== 0) return;

	frm.add_custom_button(
		__("Purchase Invoice (LCV)"),
		function () {

			const dialog = new frappe.ui.form.MultiSelectDialog({
				doctype: "Purchase Invoice",
				target: frm,

				setters: {
					custom_forwarder: undefined,
					custom_lcv_total_taxes_and_charges: undefined,
				},

				get_query() {
					const values = this.dialog?.get_values?.() || {};

					let filters = [
						["Purchase Invoice", "docstatus", "=", 1],
						["Purchase Invoice", "custom_has_lcv", "=", 1],
						["Purchase Invoice", "custom_forwarder", "is", "set"],
						["Purchase Invoice", "custom_forwarder", "!=", ""],
						["Purchase Invoice", "custom_forwarded_to_pinv", "is", "not set"],
					];

					if (values.custom_forwarder) {
						filters.push([
							"Purchase Invoice",
							"custom_forwarder",
							"=",
							values.custom_forwarder
						]);
					}

					if (values.custom_lcv_total_taxes_and_charges) {
						filters.push([
							"Purchase Invoice",
							"custom_lcv_total_taxes_and_charges",
							">=",
							values.custom_lcv_total_taxes_and_charges
						]);
					}

					return { filters };
				},

				action(selections) {
					if (!selections || !selections.length) {
						frappe.msgprint("Pilih minimal satu Purchase Invoice");
						return;
					}

					frappe.call({
						method: "customer_display.custom_standard.purchase_invoice_custom.create_forwarder_pinv_multi",
						args: {
							source_names: selections
						},
						freeze: true,
						freeze_message: __("Creating Forwarder Purchase Invoice..."),
						callback(r) {
							if (!r.message) return;

							frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					});
				}
			});

			dialog.$wrapper.on("change", "input, select", () => {
				dialog.refresh();
			});

		},
		__("Get Items From")
	);
}



function set_applicable_charges_for_item(frm) {
	if (!frm.doc.custom_landed_cost_taxes_and_charges.length) return;

	let based_on = (frm.doc.custom_distribute_charges_based_on || "").toLowerCase();

	if (based_on === "distribute manually") {
		(frm.doc.custom_lcv_item || []).forEach(item => {
			item.applicable_charges = 0;
		});
	} else {
		let total_item_cost = 0.0;

		(frm.doc.custom_lcv_item || []).forEach(d => {
			if (based_on === "constant") {
				total_item_cost += flt(d.constant || 0);
			} else {
				total_item_cost += flt(d[based_on] || 0);
			}
		});

		let total_charges = 0.0;

		if (total_item_cost <= 0) return;

		(frm.doc.custom_lcv_item || []).forEach(item => {
			let item_value = based_on === "constant" ? flt(item.constant || 0) : flt(item[based_on] || 0);

			item.applicable_charges = (item_value * flt(frm.doc.custom_lcv_total_taxes_and_charges)) / flt(total_item_cost);

			item.applicable_charges = flt(
				item.applicable_charges,
				precision("applicable_charges", item)
			);

			total_charges += item.applicable_charges;
		});

		if (Math.abs(total_charges - frm.doc.custom_lcv_total_taxes_and_charges) > 0.001) {
			let diff = flt(frm.doc.custom_lcv_total_taxes_and_charges) - flt(total_charges);
			let last_item = frm.doc.custom_lcv_item.slice(-1)[0];
			if (last_item) {
				last_item.applicable_charges += diff;
			}
		}
	}

	frm.refresh_field("custom_lcv_item");
}


function set_total_taxes_and_charges(frm) {
	let total = 0;

	(frm.doc.custom_landed_cost_taxes_and_charges || []).forEach(d => {
		total += flt(d.amount);
	});

	frm.set_value("custom_lcv_total_taxes_and_charges", total);
}

function hide_perm(frm) {

	let max_perm_level = frappe.boot.max_perm_level

	if(max_perm_level < 7 && frappe.session.user != "Administrator"){
		frm.set_df_property('naming_series', 'read_only', true);
		frm.set_df_property('tax_id', 'read_only', true);
		frm.set_df_property('posting_date', 'read_only', true);
		frm.set_df_property('posting_time', 'read_only', true);
		frm.set_df_property('set_posting_time', 'read_only', true);
		frm.set_df_property('is_paid', 'read_only', true);
		frm.set_df_property('apply_tds', 'read_only', true);
		frm.set_df_property('update_stock', 'read_only', true);
		frm.set_df_property('taxes_and_charges_added', 'read_only', true);
		frm.set_df_property('taxes_and_charges_deducted', 'read_only', true);
		frm.set_df_property('total_taxes_and_charges', 'read_only', true);
		frm.set_df_property('use_company_roundoff_cost_center', 'read_only', true);
		frm.set_df_property('other_charges_calculation', 'read_only', true);
		frm.set_df_property('pricing_rules', 'read_only', true);
	}

}

function fill_item_price(frm,cdt,cdn){
	let row = locals[cdt][cdn];

	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Item Price',
			filters: {
				item_code: row.item_code
			},
			fields: ['name', 'price_list', 'price_list_rate', 'valid_from'],
			order_by: 'valid_from desc, creation desc'
		},
		callback: function(r) {
			if (r.message) {
				let latest_prices = {};
				r.message.forEach(function(price) {
					if (!latest_prices[price.price_list]) {
						latest_prices[price.price_list] = price;
					}
				});
				
				if (latest_prices['Retail']) {
					frappe.model.set_value(cdt, cdn, 'custom_retail_price', latest_prices['Retail'].price_list_rate);
				}
				if (latest_prices['Grosir']) {
					frappe.model.set_value(cdt, cdn, 'custom_grosir_price', latest_prices['Grosir'].price_list_rate);
				}
				if (latest_prices['MarketPlace']) {
					frappe.model.set_value(cdt, cdn, 'custom_marketplace_price', latest_prices['MarketPlace'].price_list_rate);
				}
			}
		}
	});
}


function set_company_filter(frm) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Supplier',
			name: frm.doc.supplier
		},
		callback: function(r) {
			if (r.message) {
				let supplier = r.message;
				let vendor_companies = [];
				
				if (supplier.custom_vendor_company) {
					vendor_companies.push(supplier.custom_vendor_company);
				}
				
				if (supplier.custom_vendor_company_bjm) {
					vendor_companies.push(supplier.custom_vendor_company_bjm);
				}
				
				vendor_companies = [...new Set(vendor_companies)];
				
				frappe.call({
					method: 'frappe.client.get',
					args: {
						doctype: 'User',
						name: frappe.session.user
					},
					callback: function(user_data) {
						if (user_data.message && user_data.message.cabang_user) {
							let user_companies = user_data.message.cabang_user;
							
							if (!user_companies || user_companies.length === 0) {
								set_filter(frm, vendor_companies);
							} else {
								let allowed_companies = user_companies.map(row => row.company);
								
								let filtered_companies = vendor_companies.filter(company => 
									allowed_companies.includes(company)
								);
								
								if (filtered_companies.length === 0) {
									frappe.msgprint(__('No matching companies found between supplier and your access rights'));
									frm.set_value('company', '');
								}
								
								set_filter(frm, filtered_companies);
							}
						} else {
							set_filter(frm, vendor_companies);
						}
					}
				});
			}
		}
	});
}

function set_filter(frm, companies) {
	if (companies && companies.length > 0) {
		frm.set_query('company', function() {
			return {
				filters: {
					name: ['in', companies]
				}
			};
		});
		
		if (companies.length === 1) {
			frm.set_value('company', companies[0]);
		} else if (companies.length > 1) {
			if (!companies.includes(frm.doc.company)) {
				frm.set_value('company', companies[0]);
			}
		}
	} else {
		frm.set_query('company', function() {
			return {
				filters: {
					name: ['in', []]
				}
			};
		});
		frm.set_value('company', '');
	}
}