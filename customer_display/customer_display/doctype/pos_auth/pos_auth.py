# Copyright (c) 2026, DAS and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe import _

class POSAuth(Document):

    def validate(self):

        if not self.auth_code:
            return

        password = self.auth_code.strip()

        if len(password) < 10:
            frappe.throw(_("Auth Code minimal 10 karakter"))

        exists = frappe.db.exists(
            "POS Auth",
            {
                "auth_code": password,
                "name": ["!=", self.name]
            }
        )

        if exists:
            frappe.throw(_("Auth Code terlalu simple / mengandung kata2 yang sering digunakan"))

        self.auth_code = password
