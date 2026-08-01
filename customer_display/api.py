import frappe
from frappe import _
import json
from frappe.utils import flt

@frappe.whitelist()
def get_customer_display_settings(pos_profile=None):
	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	settings = frappe.get_doc("Customer Display Settings", {"pos_profile": pos_profile})
	return {
		"customer": settings.current_customer or "",
		"points": settings.current_points or 0,
		"paid_amount": settings.paid_amount or 0,
		"change_amount": settings.change_amount or 0
	}
# @frappe.whitelist()
# def update_customer_display(items):

# 	if isinstance(items, str):
# 		items = json.loads(items)

# 	frappe.cache().set_value("customer_display_cart", items)
# 	frappe.publish_realtime("customer_display_update", items)

@frappe.whitelist()
def update_customer_display(pos_profile, items, customer=None, paid_amount=0, change_amount=0):
	doc = frappe.get_doc("Customer Display Settings", {"pos_profile": pos_profile})
	doc.current_items = []
	safe_items = frappe.parse_json(items) if items else []

	for i in safe_items:
		if isinstance(i, dict):
			doc.append("current_items", {
				"item_name": i.get("item_name"),
				"item_code": i.get("item_code"),
				"qty": flt(i.get("qty", 0)),
				"rate": flt(i.get("rate", 0))
			})
			
	doc.save(ignore_permissions=True)
	frappe.publish_realtime(f"update_customer_display_{pos_profile}", {})

@frappe.whitelist()
def update_customer_display_customer(pos_profile, customer=None, points=None):
	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	doc = frappe.get_doc("Customer Display Settings", {"pos_profile": pos_profile})
	try:
		cust = frappe.get_doc("Customer",customer)
		doc.current_customer = cust.customer_name
	except:
		doc.current_customer = customer
	
	doc.current_points = points

	doc.save(ignore_permissions=True)

	frappe.publish_realtime(f"customer_display_customer_{pos_profile}")

@frappe.whitelist()
def update_customer_display_pay_amount(pos_profile, paid=None, change=None):
	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	# Directly set the two fields, bypassing version conflicts
	frappe.db.set_value(
		"Customer Display Settings",
		{"pos_profile": pos_profile},
		{
			"paid_amount": flt(paid or 0),
			"change_amount": flt(change or 0)
		},
		update_modified=False,  # optionally avoid bumping the modified timestamp
	)

	frappe.publish_realtime(f"update_customer_display_paid_{pos_profile}", None, after_commit=True)
	
# @frappe.whitelist(allow_guest=True)
# def get_customer_display(pos_profile=None):
# 	if not pos_profile:
# 		frappe.throw(_("POS Profile is required"))

# 	doc = frappe.get_doc("Customer Display Settings", {"pos_profile": pos_profile})
# 	return doc.current_items or []

@frappe.whitelist(allow_guest=True)
def get_customer_display(pos_profile=None):
	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	doc = frappe.get_doc("Customer Display Settings", {"pos_profile": pos_profile})

	price_list = frappe.db.get_value(
		"POS Profile",
		pos_profile,
		"selling_price_list"
	)

	items = []

	for row in doc.current_items:
		item = row.as_dict()

		price_list_rate = None
		if price_list:
			price_list_rate = frappe.db.get_value(
				"Item Price",
				{
					"item_code": row.item_code,
					"price_list": price_list
				},
				"price_list_rate"
			)

		item["price_list_rate"] = price_list_rate or row.rate

		if price_list_rate and row.rate < price_list_rate:
			item["discount_percentage"] = round(
				(1 - (row.rate / price_list_rate)) * 100,
				2
			)
		else:
			item["discount_percentage"] = 0

		items.append(item)

	return items



@frappe.whitelist()
def clear_customer_display(pos_profile=None):

	user = frappe.session.user

	pos_profile_query = frappe.db.sql(""" SELECT parent FROM `tabPOS Profile User` WHERE user = "{}" """.format(user))
	if len(pos_profile_query):
		pos_profile = pos_profile_query[0][0]

	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	doc = frappe.get_doc("Customer Display Settings", {"pos_profile": pos_profile})
	doc.current_customer = ""
	doc.current_points = 0
	doc.paid_amount = 0
	doc.change_amount = 0
	doc.current_items = []
	doc.save(ignore_permissions=True)
	frappe.publish_realtime(f"customer_display_customer_{pos_profile}")
	frappe.publish_realtime(f"update_customer_display_{pos_profile}",{})
	
@frappe.whitelist()
def check_customer_display(items=None):
	user = frappe.session.user

	pos_profile_query = frappe.db.sql(""" SELECT parent FROM `tabPOS Profile User` WHERE user = "{}" """.format(user))
	if len(pos_profile_query):
		pos_profile = pos_profile_query[0][0]

	frappe.publish_realtime(f"customer_display_customer_{pos_profile}")
	frappe.publish_realtime(f"update_customer_display_{pos_profile}", {})


@frappe.whitelist()
def verify_pos_code(user, code):
	doc = frappe.get_single("POS Auth List")
	for row in doc.user_list:
		if row.user == user and row.code == code:
			return True
	return False

@frappe.whitelist()
def verify_pos_code_auth(pos_profile, code, description=""):
    pos_auth_list = frappe.get_all(
        "POS Auth",
        filters={"auth_code": code},
        fields=["name", "auth_provider"]  
    )

    if not pos_auth_list:
        return False

    for pos_auth in pos_auth_list:
        child_exist = frappe.db.exists(
            "POS Auth Profile",
            {
                "parent": pos_auth.name,
                "pos_profile": pos_profile
            }
        )

        if child_exist:
            return {
                "valid": True,
                "auth_provider": pos_auth.auth_provider,
				"description": description
            }

    return False
