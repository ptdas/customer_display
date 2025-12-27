
frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        hide_perm(frm)
        let ktp_field = frm.fields_dict.custom_ktp.$input;
        
        if (ktp_field) {
            ktp_field.on('keypress', function(e) {
                let current_value = ktp_field.val() || '';
                let char = String.fromCharCode(e.which);
                
                if (current_value.length >= 16 && e.which !== 8) {
                    e.preventDefault();
                    return false;
                }
                
                if (!/[0-9]/.test(char) && e.which !== 8) {
                    e.preventDefault();
                    return false;
                }
            });
            
            ktp_field.on('paste', function(e) {
                setTimeout(function() {
                    let value = ktp_field.val();
                    let cleaned = value.replace(/\D/g, '').substring(0, 16);
                    ktp_field.val(cleaned);
                    frm.set_value('custom_ktp', cleaned);
                }, 10);
            });
            
            ktp_field.on('input', function(e) {
                let value = ktp_field.val();
                let cleaned = value.replace(/\D/g, '').substring(0, 16);
                if (value !== cleaned) {
                    ktp_field.val(cleaned);
                    frm.set_value('custom_ktp', cleaned);
                }
            });
        }
    }
});

function hide_perm(frm) {

    let max_perm_level = frappe.boot.max_perm_level
    if(max_perm_level < 8 && frappe.session.user != "Administrator"){
        $('.form-tabs .nav-link:contains("Dashboard")').parent().hide();
        $('.form-tabs .nav-link:contains("Tax")').parent().hide();
        $('.form-tabs .nav-link:contains("Settings")').parent().hide();
        $('.form-tabs .nav-link:contains("Portal Users")').parent().hide();
        $('.form-tabs .nav-link:contains("Sales Team")').parent().hide();
    }
    if(max_perm_level < 7){
        frm.set_df_property('payment_terms', 'read_only', true);
        frm.set_df_property('credit_limits', 'read_only', true);
        frm.set_df_property('accounts', 'read_only', true);
        frm.set_df_property('loyalty_program', 'read_only', true);
        frm.set_df_property('loyalty_program_tier', 'read_only', true);
    }
}

