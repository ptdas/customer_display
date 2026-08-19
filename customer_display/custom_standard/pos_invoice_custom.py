import frappe
import random
import string
from frappe.model.document import Document
from datetime import datetime
from frappe.model.naming import make_autoname
from frappe.utils import flt


@frappe.whitelist()
def custom_autoname(doc,method):
	pos_profile = frappe.get_doc("POS Profile", doc.pos_profile)
	cabang = pos_profile.custom_cabang or "X"
	
	posting_date = frappe.utils.getdate(doc.posting_date)
	year = str(posting_date.year)[-2:]
	
	month_letter = chr(64 + posting_date.month)
	day = str(posting_date.day).zfill(2)

	prefix = f"{cabang}{year}{month_letter}{day}"

	if doc.is_return:
		doc.name = make_autoname(f"R{prefix}.####", doc.doctype)
	else:
		doc.name = make_autoname(f"{prefix}.####", doc.doctype)

@frappe.whitelist()
def create_si_pos_id_no(self, method):
	if not self.custom_si_pos_no:
		self.custom_si_pos_no = generate_custom_si_pos_no(self)

	if not self.custom_si_pos_id:
		self.custom_si_pos_id = generate_custom_si_pos_id(self)

@frappe.whitelist()
def generate_custom_si_pos_no(self):
	prefix = "SIPOS"
	year = datetime.now().strftime("%y")
	unique_code = generate_unique_code(self, 10)

	return f"{prefix}{year}-{unique_code}"	

def generate_unique_code(self, length):
	chars = string.ascii_letters + string.digits  # a-zA-Z0-9
	while True:
		code = ''.join(random.choices(chars, k=length))
		# Check uniqueness
		exists = frappe.db.exists("POS Invoice", {"custom_si_pos_no": ("like", f"SIPOS%{code}")})
		if not exists:
			return code

@frappe.whitelist()
def generate_custom_si_pos_id(self):
	# Parts
	pos_doc = frappe.get_doc("POS Profile", self.pos_profile)

	if pos_doc.get("custom_cabang") == "BJM":
		prefix = "SIPOSM"
	else:
		prefix = "SIPOSB"

	year = datetime.now().strftime("%y")  # Last 2 digits of year
	doy = datetime.now().timetuple().tm_yday  # Day of year
	doy_str = f"{doy:03d}"

	# Get count of existing POS Invoices with same prefix in current day
	today = datetime.now().strftime("%Y-%m-%d")
	base_pattern = f"{prefix}{year}{doy_str}%"

	count = frappe.db.count(
		"POS Invoice",
		{
			"posting_date": today,
			"custom_si_pos_id": ("like", base_pattern)
		}
	)
	serial = f"{count + 1:04d}"

	return f"{prefix}{year}{doy_str}{serial}"




@frappe.whitelist()
def get_return_payment_distribution(source_invoice, grand_total):
    source = frappe.get_doc("POS Invoice", source_invoice)

    total_paid = sum(flt(p.amount) for p in source.payments)

    if not total_paid:
        return []

    # Return invoice => payment harus negatif dan tanpa desimal
    grand_total = -abs(int(round(flt(grand_total))))

    result = []
    running_total = 0

    payments = source.payments  

    for i, p in enumerate(payments, 1):
        if i == len(payments):
            amount = grand_total - running_total
        else:
            if total_paid:
                raw_amount = grand_total * flt(p.amount) / total_paid
                amount = int(round(raw_amount))
            else:
                amount = 0

            running_total += amount

        result.append({
            "mode_of_payment": p.mode_of_payment,
            "amount": amount
        })

    return result

def validate_return_payments(doc, method=None):
    if not doc.is_return or not doc.return_against:
        return

    source = frappe.get_doc("POS Invoice", doc.return_against)

    total_paid = sum(flt(p.amount) for p in source.payments)
    if not total_paid:
        return

    # Return invoice => payment harus negatif
    grand_total = -abs(flt(doc.grand_total))

    source_map = {
        p.mode_of_payment: flt(p.amount)
        for p in source.payments
    }

    running_total = 0

    for i, row in enumerate(doc.payments, 1):
        source_amount = source_map.get(row.mode_of_payment, 0)

        if i == len(doc.payments):
            amount = grand_total - running_total
        else:
            amount = flt(grand_total * source_amount / total_paid, 2)
            running_total += amount

        row.amount = amount
        row.base_amount = amount
