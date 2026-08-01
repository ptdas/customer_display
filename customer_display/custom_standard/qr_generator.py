
import frappe
from frappe.model.document import Document
import barcode
from barcode.writer import ImageWriter
import io
import base64
import os
from PIL import Image
import re

@frappe.whitelist()
def generate_barcode_image(doc, method=None):
	pass
	# if doc.barcodes:
	# 	for row in doc.barcodes:
	# 		if row.barcode:
	# 			row.custom_barcode_image = row.barcode


@frappe.whitelist()
def add_to_every_pf():
	list_item = frappe.db.sql(""" SELECT name FROM `tabItem` """)
	for row in list_item:
		item_doc = frappe.get_doc("Item", row[0])

		item_doc.save()


@frappe.whitelist()
def create_barcode_image_file(self, method):
	# Generate barcodes for each barcode row
	if self.barcodes:
		for row in self.barcodes:
			if row.barcode and not row.custom_item_barcode_image_file:
				# Generate Code128 barcode
				code128 = barcode.get('code128', row.barcode, writer=ImageWriter())
				
				# Define the path in the public files folder
				site_path = frappe.get_site_path()
				public_path = os.path.join(site_path, 'public', 'files', 'barcodes')
				
				# Create directory if it doesn't exist
				if not os.path.exists(public_path):
					os.makedirs(public_path)
				
				# Sanitize filename - remove invalid characters
				safe_barcode = re.sub(r'[^\w\-_]', '_', row.barcode)
				filename = f"barcode_{safe_barcode}"
				filepath = os.path.join(public_path, filename)
				
				# Save without extension (python-barcode adds .png automatically)
				code128.save(filepath)
				
				# Set the file URL
				row.custom_item_barcode_image_file = f"/files/barcodes/{filename}.png"

@frappe.whitelist()
def patch_image():
	list_item = frappe.db.sql(""" SELECT ti.name 
		FROM `tabItem` ti 
		GROUP BY ti.name
		  """)
	for satu_item in list_item:
		print(satu_item[0])
		item_doc = frappe.get_doc("Item", satu_item[0])
		if not item_doc.barcodes[0].custom_item_barcode_image_file:
			item_doc.save()
			frappe.db.commit()
