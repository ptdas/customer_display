import frappe
from frappe import _
from frappe.model.naming import make_autoname

def validate_ri_payment(doc, method):
	return
	for ref in doc.references or []:
		if ref.reference_doctype=="Purchase Invoice" and ref.docstatus==1:
			pi = frappe.get_doc("Purchase Invoice", ref.reference_name)
			for line in pi.items:
				if frappe.get_value("Item", line.item_code, "custom_ri_required"):
					exists = frappe.db.exists("Purchase Receipt Item", {
						"purchase_order":      line.purchase_order,
						"purchase_order_item": line.po_detail
					})
					if not exists:
						frappe.throw(
							_("Cannot pay for {0}: missing Purchase Receipt for item {1}")
							  .format(pi.name, line.item_code),
							frappe.exceptions.ValidationError
						)


def custom_payment_entry_autoname(doc, method=None):

    if not doc.company or not doc.posting_date:
        return

    company_doc = frappe.get_doc("Company", doc.company)

    parent_company = company_doc.parent_company or doc.company
    company_code = parent_company[:3].upper()

    posting_date = frappe.utils.getdate(doc.posting_date)
    year = str(posting_date.year)[-2:]
    month = str(posting_date.month).zfill(2)

    prefix = f"{company_code}PE{year}-{month}"

    doc.name = make_autoname(f"{prefix}.####")

