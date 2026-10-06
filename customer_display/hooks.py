app_name = "customer_display"
app_title = "Customer Display"
app_publisher = "DAS"
app_description = "Customer Display for POS"
app_email = "das@gmail.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/customer_display/css/customer_display.css"
# app_include_js = "/assets/customer_display/js/customer_display.js"

boot_session = "customer_display.custom_standard.user_custom.make_perm_level_session"

app_include_js = [
	'pos_patch.bundle.js',
	'pos_customer_display.bundle.js',
    'jquery-mask/jquery.mask.min.js'
]

web_include_context = {
	"customer_display": "customer_display.api.get_customer_display"
}

doctype_js = {
	"Customer" : "public/js/custom_customer.js",
	"Purchase Invoice" : "public/js/custom_purchase_invoice.js",
	"Purchase Order" : "public/js/custom_purchase_order.js",
	"Purchase Receipt" : "public/js/custom_purchase_receipt.js",
	"Sales Invoice" : "public/js/custom_sales_invoice.js",
	"Supplier": "public/js/custom_supplier.js",
	"Item": "public/js/custom_item.js",
	"POS Closing Entry": "public/js/custom_pos_closing_entry.js",
    "Payment Entry": "public/js/custom_payment_entry.js",
    "POS Invoice": "public/js/custom_pos_invoice.js",
    "Pricing Rule": "public/js/custom_pricing_rule.js",
    "POS Opening Entry": "public/js/custom_pos_opening_entry.js",
}

# include js, css files in header of web template
# web_include_css = "/assets/customer_display/css/customer_display.css"
# web_include_js = "/assets/customer_display/js/customer_display.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "customer_display/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# doctype_list_js = {"POS Invoice": "public/js/pos_invoice_list.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "customer_display/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "customer_display.utils.jinja_methods",
# 	"filters": "customer_display.utils.jinja_filters"
# }

jinja = {
	'filters': "customer_display.custom_standard.jinja_filters.get_tutup_kasir"
}


# Installation
# ------------

# before_install = "customer_display.install.before_install"
# after_install = "customer_display.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "customer_display.uninstall.before_uninstall"
# after_uninstall = "customer_display.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "customer_display.utils.before_app_install"
# after_app_install = "customer_display.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "customer_display.utils.before_app_uninstall"
# after_app_uninstall = "customer_display.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "customer_display.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"Sales Invoice": "customer_display.custom_standard.sales_invoice_custom.CustomSalesInvoice"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Account": {
		"after_insert": "customer_display.custom_standard.account_custom.clone_account_to_children"
	},
	# "Item" : {
	# 	"validate": "customer_display.custom_standard.item_custom.create_barcode_image_file"
	# },

#	"Customer":{
#		"after_insert": "customer_display.alan_api.execute_to_alan_server"
#	},

	# "Item": {
	#     "validate": "customer_display.custom_standard.item_custom.on_vendor_change_transfer_stock"
	# },

#	"Loyalty Point Entry":{
#		"after_insert": "customer_display.alan_api.create_poin_customer_from_api"
#	},

	# "Delivery Note": {
	# 	"validate": "customer_display.custom_standard.delivery_note_custom.set_expense"
	# },

	"Item":{
		"validate": "customer_display.custom_standard.qr_generator.create_barcode_image_file"
	},

	"Payment Entry": {
        "autoname": "customer_display.custom_standard.payment_entry_custom.custom_payment_entry_autoname",
		# "validate": "customer_display.custom_standard.payment_entry_custom.validate_ri_payment",
		"on_submit": "customer_display.custom_standard.loyalty_point_custom.payment_entry_on_submit"
	},
	"Pricing Rule": {
		"autoname": "customer_display.custom_standard.pricing_rule_custom.autoname",
        "validate": "customer_display.custom_standard.pricing_rule_custom.validate_pricing_rule_company_warehouse"
	},
	"POS Invoice": {
		"autoname": "customer_display.custom_standard.pos_invoice_custom.custom_autoname",
		"validate": ["customer_display.customer_display.page.point_of_sale.custom_pos_method.set_grosir_price_list"],
		"before_insert": "customer_display.custom_standard.pos_invoice_custom.create_si_pos_id_no",
		"before_submit": ["customer_display.customer_display.page.point_of_sale.custom_pos_method.apply_custom_charge_to_pos_invoice"
                    ,"customer_display.customer_display.page.point_of_sale.custom_pos_return_ledger.before_submit_pos_invoice"],
		"on_submit": ["customer_display.customer_display.page.point_of_sale.custom_pos_method.split_pos_invoice"
                ,"customer_display.customer_display.page.point_of_sale.custom_pos_return_ledger.on_submit_pos_invoice",
                "customer_display.customer_display.page.point_of_sale.custom_pos_method.handle_pos_return"],
        "on_cancel": "customer_display.customer_display.page.point_of_sale.custom_pos_return_ledger.on_cancel_pos_invoice",
	},
	"POS Profile": {
		"after_insert": "customer_display.custom_standard.pos_profile_custom.create_customer_display_settings"
	},

	"POS Opening Entry":{
		"validate": "customer_display.custom_standard.pos_opening_entry_custom.check_double",
        "validate": "customer_display.custom_standard.pos_opening_entry_custom.force_start_date_midnight"
	},

	"POS Closing Entry":{
		"validate": ["customer_display.custom_standard.pos_opening_entry_custom.ambil_closing_kalau_kosong",
               "customer_display.custom_standard.pos_opening_entry_custom.ambil_return_usage",
               "customer_display.custom_standard.pos_opening_entry_custom.validate_get_tutup_kasir"],
		"on_submit": [
			"customer_display.custom_standard.pos_opening_entry_custom.set_pos_invoice_consolidated"
		],
	},
	"Purchase Order": {
		"on_submit": "customer_display.custom_standard.purchase_order_custom.auto_create_purchase_invoice",
		"on_update": "customer_display.custom_standard.purchase_order_custom.mark_need_review_if_vendor_mismatch"
	},
	"Purchase Receipt": {
		"validate": ["customer_display.custom_standard.purchase_receipt_custom.check_abbr"],
		"on_update": "customer_display.custom_standard.purchase_receipt_custom.check_po_qty",
        "on_submit": "customer_display.custom_standard.purchase_invoice_custom.update_item_last_vendor"
	},
	"Purchase Invoice": {
		"autoname": "customer_display.custom_standard.autoname_custom.autoname_purchase",
        "validate": ["customer_display.custom_standard.purchase_invoice_custom.recalc_lcv",
                     "customer_display.custom_standard.purchase_invoice_custom.update_items_prices",
                     "customer_display.custom_standard.purchase_invoice_custom.calculate_custom_lcv_per_quantity",
                     "customer_display.custom_standard.purchase_invoice_custom.validate_item_cost_info",
                     "customer_display.custom_standard.purchase_invoice_custom.set_expense_account_from_item"],
		"on_submit": ["customer_display.custom_standard.purchase_invoice_custom.create_lcv_on_submit",
                "customer_display.custom_standard.purchase_invoice_custom.update_used_forwarder_to_pinv",
                "customer_display.custom_standard.purchase_invoice_custom.update_item_last_vendor"],
        "on_cancel": "customer_display.custom_standard.purchase_invoice_custom.update_used_forwarder_to_pinv"
	},
	"Sales Invoice": {
		"autoname": "customer_display.custom_standard.autoname_custom.autoname_purchase",
		"after_insert": "customer_display.custom_standard.sales_invoice_custom.approval_return"
	},
	"User":{
        "on_update": ["customer_display.custom_standard.user_custom.create_user_permission_on_save","customer_display.custom_standard.user_custom.delete_user_permission_on_delete"],
	},
	"Warehouse": {
		"after_insert": "customer_display.custom_standard.warehouse_custom.clone_warehouse_to_children"
	},"Landed Cost Voucher": {
		"on_submit": "customer_display.custom_standard.custom_landed_cost_voucher.on_lcv_submit",
		"on_cancel": "customer_display.custom_standard.custom_landed_cost_voucher.on_lcv_cancel"
	},
    "Mode of Payment": {
        "validate": ["customer_display.custom_standard.custom_mode_of_payment.validate_mdr_percent"],
	},
    "Supplier": {
        "validate": "customer_display.custom_standard.supplier.set_vendor_company"
    }
    	
	
}


override_doctype_class = {
    "Sales Invoice": "customer_display.custom_standard.sales_invoice_override.CustomSalesInvoice",
    "Purchase Invoice": "customer_display.custom_standard.purchase_invoice_override.CustomPurchaseInvoice"
}
# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"customer_display.tasks.all"
# 	],
# 	"daily": [
# 		"customer_display.tasks.daily"
# 	],
# 	"hourly": [
# 		"customer_display.tasks.hourly"
# 	],
# 	"weekly": [
# 		"customer_display.tasks.weekly"
# 	],
# 	"monthly": [
# 		"customer_display.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "customer_display.install.before_tests"

override_whitelisted_methods = {
    "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_pos_invoices":
        "customer_display.custom_standard.pos_closing_custom.get_pos_invoices",

    "erpnext.stock.get_item_details.get_item_details":
        "customer_display.custom_standard.get_item_details_override.get_item_details",

    "erpnext.stock.get_item_details.apply_price_list":
        "customer_display.custom_standard.get_item_details_override.apply_price_list"
}

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "customer_display.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "customer_display.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["customer_display.utils.before_request"]
# after_request = ["customer_display.utils.after_request"]

# Job Events
# ----------
# before_job = ["customer_display.utils.before_job"]
# after_job = ["customer_display.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"customer_display.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }



# Kiriman lintas site yang belum sampai ke seberang - lihat
# customer_display/peer.py
scheduler_events = {
	"hourly": ["customer_display.customer_display.doctype.stock_movement_inter.stock_movement_inter.sapu_belum_terkirim"],
}
