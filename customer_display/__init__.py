__version__ = "0.0.1"

from frappe import _
from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_program_details_with_points,validate_loyalty_points
from frappe.utils import flt, cint, getdate, add_days
import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
import erpnext.accounts.doctype.loyalty_program.loyalty_program as lp_mode
import erpnext.accounts.doctype.sales_invoice.sales_invoice as si_module
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import POSInvoiceMergeLog

from frappe.utils import flt, today

def custom_make_loyalty_point_entry(self):
	returned_amount = self.get_returned_amount()

	lp_details = get_loyalty_program_details_with_points(
		self.customer,
		company=self.company,
		current_transaction_amount=0,
		loyalty_program=self.loyalty_program,
		expiry_date=self.posting_date,
		include_expired_entry=True,
	)

	if (
		not lp_details
		or getdate(lp_details.from_date) > getdate(self.posting_date)
		or (lp_details.to_date and getdate(lp_details.to_date) < getdate(self.posting_date))
	):
		return

	# Load Loyalty Program and access custom_excluded_items
	prog = frappe.get_doc("Loyalty Program", lp_details.loyalty_program)

	# Safely access the child table even if it's empty
	excluded_items = {d.item_code for d in prog.get("custom_excluded_items", []) if d.item_code}

	# Calculate total of applicable items only
	applicable_amount = 0
	for item in self.items:
		if item.item_code in excluded_items:
			continue
		applicable_amount += flt(item.base_amount)

	eligible_amount = applicable_amount - returned_amount
	collection_factor = lp_details.collection_factor or 1.0
	points_earned = cint(eligible_amount / collection_factor)

	if self.outstanding_amount == 0:
		doc = frappe.get_doc({
			"doctype": "Loyalty Point Entry",
			"company": self.company,
			"loyalty_program": lp_details.loyalty_program,
			"loyalty_program_tier": lp_details.tier_name,
			"customer": self.customer,
			"invoice_type": self.doctype,
			"invoice": self.name,
			"loyalty_points": points_earned,
			"purchase_amount": eligible_amount,
			"expiry_date": add_days(self.posting_date, lp_details.expiry_duration),
			"posting_date": self.posting_date,
		})
		doc.flags.ignore_permissions = 1
		doc.save()

	self.set_loyalty_program_tier()

SalesInvoice.make_loyalty_point_entry = custom_make_loyalty_point_entry

def custom_validate_loyalty_points(ref_doc, points_to_redeem):
	loyalty_program = None
	posting_date = None

	if ref_doc.doctype == "Sales Invoice":
		posting_date = ref_doc.posting_date
	else:
		posting_date = today()

	if hasattr(ref_doc, "loyalty_program") and ref_doc.loyalty_program:
		loyalty_program = ref_doc.loyalty_program
	else:
		loyalty_program = frappe.db.get_value("Customer", ref_doc.customer, ["loyalty_program"])

	# custom chandra
	# if (
	# 	loyalty_program
	# 	and frappe.db.get_value("Loyalty Program", loyalty_program, ["company"]) != ref_doc.company
	# ):
	# 	frappe.throw(_("The Loyalty Program isn't valid for the selected company"))

	if loyalty_program and points_to_redeem:
		loyalty_program_details = get_loyalty_program_details_with_points(
			ref_doc.customer, loyalty_program, posting_date
		)

		if points_to_redeem > loyalty_program_details.loyalty_points:
			frappe.throw(_("You don't have enough Loyalty Points to redeem - {} - {}".format(points_to_redeem, loyalty_program_details.loyalty_points)))

		loyalty_amount = flt(points_to_redeem * loyalty_program_details.conversion_factor)
        
		# if loyalty_amount > ref_doc.rounded_total:
		# 	frappe.throw(_("You can't redeem Loyalty Points having more value than the Rounded Total.  - {} - {}".format(loyalty_amount, loyalty_program_details.rounded_total)))

		#ganti cek rounded total ke grand total
		if loyalty_amount > ref_doc.grand_total:
			frappe.throw(_("You can't redeem Loyalty Points having more value than the Grand Total.  - {} - {}".format(loyalty_amount, loyalty_program_details.grand_total)))

		if not ref_doc.loyalty_amount and ref_doc.loyalty_amount != loyalty_amount:
			ref_doc.loyalty_amount = loyalty_amount

		if ref_doc.doctype == "Sales Invoice":
			ref_doc.loyalty_program = loyalty_program
			if not ref_doc.loyalty_redemption_account:
				ref_doc.loyalty_redemption_account = loyalty_program_details.expense_account

			if not ref_doc.loyalty_redemption_cost_center:
				ref_doc.loyalty_redemption_cost_center = loyalty_program_details.cost_center

		elif ref_doc.doctype == "Sales Order":
			return loyalty_amount

lp_mode.validate_loyalty_points = custom_validate_loyalty_points
si_module.validate_loyalty_points = custom_validate_loyalty_points


def custom_on_submit(self):

	return 
	pos_invoice_docs = [frappe.get_cached_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

	returns = [d for d in pos_invoice_docs if d.get("is_return") == 1]
	sales = [d for d in pos_invoice_docs if d.get("is_return") == 0]

	sales_invoice, credit_note = "", ""
	if returns:
		credit_note = self.process_merging_into_credit_note(returns)

	if sales:
		sales_invoice = self.process_merging_into_sales_invoice(sales)

	self.save()  # save consolidated_sales_invoice & consolidated_credit_note ref in merge log
	self.update_pos_invoices(pos_invoice_docs, sales_invoice, credit_note)

POSInvoiceMergeLog.on_submit = custom_on_submit