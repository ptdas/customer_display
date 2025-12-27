frappe.ui.form.on('Payment Entry', {
    refresh:function(frm){
        hide_perm(frm);
    }
});

function hide_perm(frm) {

    let max_perm_level = frappe.boot.max_perm_level
    
    if(max_perm_level < 7 && frappe.session.user != "Administrator"){
        frm.set_df_property('naming_series', 'read_only', true);
        frm.set_df_property('party_type', 'read_only', true);
        frm.set_df_property('party', 'read_only', true);
        frm.set_df_property('party_name', 'read_only', true);
        frm.set_df_property('bank_account', 'read_only', true);
        frm.set_df_property('party_bank_account', 'read_only', true);
        frm.set_df_property('contact_person', 'read_only', true);

        frm.set_df_property('party_balance', 'read_only', true);
        frm.set_df_property('paid_from', 'read_only', true);
        frm.set_df_property('paid_from_account_currency', 'read_only', true);
        frm.set_df_property('paid_from_account_balance', 'read_only', true);
        frm.set_df_property('paid_to', 'read_only', true);
        frm.set_df_property('paid_to_account_currency', 'read_only', true);
        frm.set_df_property('paid_to_account_balance', 'read_only', true);

        frm.set_df_property('total_allocated_amount', 'read_only', true);
        frm.set_df_property('unallocated_amount', 'read_only', true);
        frm.set_df_property('difference_amount', 'read_only', true);
    }
}

