frappe.ui.form.on("Stock Movement Intra", {
    onload(frm) {
        frm.set_query("parent_company", () => {
            return {
                filters: {
                    parent_company: ["is", "not set"]
                }
            };
        });

        if (!frm.doc.posting_time) {
            frm.set_value("posting_time", frappe.datetime.now_time());
        }

        toggle_warehouse_fields(frm);
        set_parent_warehouse_query(frm);
        set_child_warehouse_query(frm); 
    },

    parent_company(frm) {
        set_parent_warehouse_query(frm);
        set_child_warehouse_query(frm);
    },

    stock_entry_type(frm) {
        toggle_warehouse_fields(frm);
    }
});

function toggle_warehouse_fields(frm) {
    const type = frm.doc.stock_entry_type;

    frm.set_df_property("from_warehouse", "reqd", 0);
    frm.set_df_property("to_warehouse", "reqd", 0);

    if (type === "Material Transfer") {
        frm.toggle_display("from_warehouse", true);
        frm.toggle_display("to_warehouse", true);

        frm.set_df_property("from_warehouse", "reqd", 1);
        frm.set_df_property("to_warehouse", "reqd", 1);

    } else if (type === "Material Issue") {
        frm.toggle_display("from_warehouse", true);
        frm.toggle_display("to_warehouse", false);

        frm.set_value("to_warehouse", null);
        frm.set_df_property("from_warehouse", "reqd", 1);

    } else if (type === "Material Receipt") {
        frm.toggle_display("from_warehouse", false);
        frm.toggle_display("to_warehouse", true);

        frm.set_value("from_warehouse", null);
        frm.set_df_property("to_warehouse", "reqd", 1);

    } else {
        frm.toggle_display("from_warehouse", false);
        frm.toggle_display("to_warehouse", false);

        frm.set_value("from_warehouse", null);
        frm.set_value("to_warehouse", null);
    }
}

function set_parent_warehouse_query(frm) {
    if (!frm.doc.parent_company) return;

    frm.set_query("from_warehouse", () => {
        return {
            filters: {
                company: frm.doc.parent_company
            }
        };
    });

    frm.set_query("to_warehouse", () => {
        return {
            filters: {
                company: frm.doc.parent_company
            }
        };
    });
}

function set_child_warehouse_query(frm) {
    if (!frm.doc.parent_company) return;
    
    const child_table = "items";

    const s_field = frm.fields_dict[child_table].grid.get_field("s_warehouse");
    s_field.get_query = function() {
        return {
            filters: {
                company: frm.doc.parent_company
            }
        };
    };

    const t_field = frm.fields_dict[child_table].grid.get_field("t_warehouse");
    t_field.get_query = function() {
        return {
            filters: {
                company: frm.doc.parent_company
            }
        };
    };
}
