# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class POSAds(Document):
	def validate(self):
		self.validate_images()

	def validate_images(self):
		allowed_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")

		for ad in self.table_ads:
			if ad.attach:
				if not ad.attach.lower().endswith(allowed_extensions):
					frappe.throw(
						f"Attachment '{ad.attach}' is not a valid image file. Only JPG, PNG, GIF, and WEBP are allowed.",
						title="Invalid Attachment"
					)

@frappe.whitelist()
def get_pos_ads():
	ads = []
	ad_doc = frappe.get_single("POS Ads")  # POS Ads is a single doctype

	for ad in sorted(ad_doc.table_ads, key=lambda x: x.idx):
		if ad.attach:
			ads.append({
				"image": ad.attach
			})

	return ads