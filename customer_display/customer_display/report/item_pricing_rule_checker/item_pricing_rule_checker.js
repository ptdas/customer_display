frappe.query_reports["Item Pricing Rule Checker"] = {
    "filters": [
        {
            "fieldname": "item",
            "label": "Item",
            "fieldtype": "Link",
            "options": "Item",
            "reqd": 1
        },
        {
            "fieldname": "date",
            "label": "Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        }
    ],

    "onload": function(report) {
        frappe.show_alert({
            message: "Pilih item untuk melihat pricing rule yang valid",
            indicator: "blue"
        });
    },
	
};
