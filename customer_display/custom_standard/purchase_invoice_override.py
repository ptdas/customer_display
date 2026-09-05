import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice


class CustomPurchaseInvoice(PurchaseInvoice):

    def make_supplier_gl_entry(self, gl_entries):

        grand_total = (
            self.rounded_total
            if (self.rounding_adjustment and self.rounded_total)
            else self.grand_total
        )

        base_grand_total = flt(
            self.base_rounded_total
            if (self.base_rounding_adjustment and self.base_rounded_total)
            else self.base_grand_total,
            self.precision("base_grand_total"),
        )

        if not grand_total or self.is_internal_transfer():
            return

        total_advance = sum(
            flt(row.allocated_amount)
            for row in self.get("advances")
            if flt(row.allocated_amount) > 0
        )

        total_advance = min(total_advance, base_grand_total)

        payable_amount = flt(base_grand_total - total_advance)

        against_voucher = self.name

        if self.is_return and self.return_against and not self.update_outstanding_for_self:
            against_voucher = self.return_against

        if payable_amount:
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": self.credit_to,
                        "party_type": "Supplier",
                        "party": self.supplier,
                        "due_date": self.due_date,
                        "against": self.against_expense_account,
                        "credit": payable_amount,
                        "credit_in_account_currency": (
                            payable_amount
                            if self.party_account_currency == self.company_currency
                            else flt(self.grand_total - total_advance)
                        ),
                        "against_voucher": against_voucher,
                        "against_voucher_type": self.doctype,
                        "project": self.project,
                        "cost_center": self.cost_center,
                    },
                    self.party_account_currency,
                    item=self,
                )
            )

        if total_advance:
            dp_account = frappe.db.get_value(
                "Company",
                self.company,
                "default_advance_paid_account",
            )

            if not dp_account:
                frappe.throw(
                    f"Default Advance Paid Account belum diset di Company {self.company}"
                )

            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": dp_account,
                        "party_type": "Supplier",
                        "party": self.supplier,
                        "against": self.credit_to,
                        "credit": total_advance,
                        "credit_in_account_currency": total_advance,
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                        "project": self.project,
                        "cost_center": self.cost_center,
                    },
                    self.party_account_currency,
                    item=self,
                )
            )