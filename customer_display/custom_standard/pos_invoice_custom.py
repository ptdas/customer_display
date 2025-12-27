import frappe
import random
import string
from frappe.model.document import Document
from datetime import datetime

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