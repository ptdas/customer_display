frappe.ui.form.on("Pinjaman", {
  refresh(frm) {
    
    if (frm.doc.docstatus === 1
        && frm.doc.jumlah_pelunasan < frm.doc.jumlah_pinjaman) {

      frm.add_custom_button(__('Make Pelunasan'), () => {
        frm.call('make_pelunasan')
          .then(() => {
            frm.reload_doc(); 
          });
      }, __('Actions'));
    }
  },
  onload: function(frm) {
    frm.set_query("pos_profile", () => {
      return {
        query: "customer_display.custom_standard.queries_custom.get_pos_profiles_based_on_user"
      };
    });
  }
});