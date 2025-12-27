frappe.ui.form.on('Item', {
    refresh:function(frm){
        hide_perm(frm)
    },
    before_save: function(frm) {
        if (!frm.doc.barcodes || frm.doc.barcodes.length === 0) {
            frappe.throw(__('You must add at least one barcode.'));
        }
    },
});



function hide_perm(frm) {

    let max_perm_level = frappe.boot.max_perm_level
    if(max_perm_level < 8 && frappe.session.user != "Administrator"){
        $('.form-tabs .nav-link:contains("Accounting")').parent().hide();
        $('.form-tabs .nav-link:contains("Purchasing")').parent().hide();
        $('.form-tabs .nav-link:contains("Sales")').parent().hide();
        $('.form-tabs .nav-link:contains("Quality")').parent().hide();
        $('.form-tabs .nav-link:contains("Manufacturing")').parent().hide();
        $('.form-tabs .nav-link:contains("Tax")').parent().hide(); 
    }
    if(max_perm_level < 7 && frappe.session.user != "Administrator"){
        frm.set_df_property('disabled', 'read_only', true);
        frm.set_df_property('allow_alternative_item', 'read_only', true);
        frm.set_df_property('is_stock_item', 'read_only', true);
        frm.set_df_property('has_variants', 'read_only', true);
        frm.set_df_property('is_fixed_asset', 'read_only', true);
        frm.set_df_property('custom_ri_required', 'read_only', true);
        frm.set_df_property('custom_auto_pi', 'read_only', true);

        frm.set_df_property('shelf_life_in_days', 'read_only', true);
        frm.set_df_property('end_of_life', 'read_only', true);
        frm.set_df_property('default_material_request_type', 'read_only', true);
        frm.set_df_property('valuation_method', 'read_only', true);
        frm.set_df_property('warranty_period', 'read_only', true);
        frm.set_df_property('weight_per_unit', 'read_only', true);
        frm.set_df_property('weight_uom', 'read_only', true);
        frm.set_df_property('allow_negative_stock', 'read_only', true);
        frm.set_df_property('reorder_levels', 'read_only', true);
        frm.set_df_property('has_batch_no', 'read_only', true);
        frm.set_df_property('create_new_batch', 'read_only', true);
        frm.set_df_property('batch_number_series', 'read_only', true);
        frm.set_df_property('has_expiry_date', 'read_only', true);
        frm.set_df_property('retain_sample', 'read_only', true);
        frm.set_df_property('sample_quantity', 'read_only', true);
        frm.set_df_property('has_serial_no', 'read_only', true);
        frm.set_df_property('serial_no_series', 'read_only', true);
    }
}

