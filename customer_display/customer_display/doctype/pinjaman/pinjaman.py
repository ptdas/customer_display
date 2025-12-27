# pinjaman.py

import frappe
from frappe.model.document import Document
from frappe import _
class Pinjaman(Document):
	def on_submit(self):
		"""When a Pinjaman is submitted, create matching Journal Entry."""
		self.create_journal_entry()
		if self.jumlah_pelunasan is None:
			self.db_set("jumlah_pelunasan", 0)
			
	def create_journal_entry(self):
		# fixed company
		company = "ABKG"

		# loan amount & date from this doc
		amount = self.jumlah_pinjaman
		posting_date = self.posting_date

		# fetch company’s custom accounts
		comp = frappe.get_doc("Company", company)
		pinjaman_acc = comp.custom_pinjaman_account
		receivable_acc = comp.default_receivable_account
		cash_acc       = comp.default_cash_account

		# build JE
		je = frappe.new_doc("Journal Entry")
		je.company = company
		je.posting_date = posting_date

		# 1) Debit the loan account
		je.append("accounts", {
			"account": pinjaman_acc,
			"debit": amount,
			"debit_in_account_currency": amount,
			"credit": 0.0,
			"party_type": "Customer",
			"party": "Pinjaman"
		})

		# 2) Credit the receivable account, and assign it to the Customer “Pinjaman”
		#    (make sure you have a Customer record with name “Pinjaman”)
		je.append("accounts", {
			"account": cash_acc,
			"debit": 0.0,
			"credit": amount,
			"credit_in_account_currency": amount
		})

		je.insert()
		je.submit()

	@frappe.whitelist()
	def make_pelunasan(self):
		"""Called from the client: create JE and mark pelunasan done."""
		# guard
		if self.jumlah_pelunasan >= self.jumlah_pinjaman:
			frappe.throw(_("Pelunasan already completed"), title=_("Nothing to do"))

		company = "ABKG"
		amount = self.jumlah_pinjaman

		# fetch company settings
		comp = frappe.get_doc("Company", company)
		pinjaman_acc = comp.custom_pinjaman_account
		receivable_acc = comp.default_receivable_account
		cash_acc       = comp.default_cash_account

		# build the Journal Entry
		je = frappe.new_doc("Journal Entry")
		je.company      = company
		je.posting_date = self.posting_date

		# Debit Receivable
		je.append("accounts", {
			"account": cash_acc,
			"debit": amount,
			"debit_in_account_currency": amount,
			"credit": 0.0
		})
		# Credit Cash/Bank
		je.append("accounts", {
			"account": pinjaman_acc,
			"debit": 0.0,
			"credit": amount,
			"credit_in_account_currency": amount,
			"party_type": "Customer",
			"party": "Pinjaman"
		})

		je.insert()
		je.submit()

		# update pelunasan
		self.db_set("jumlah_pelunasan", self.jumlah_pinjaman)

		frappe.msgprint(
			_("Pelunasan processed: Journal Entry {0}").format(je.name),
			title=_("Success")
		)

		return je.name
