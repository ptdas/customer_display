# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint, throw 

def execute(filters=None):
	if not filters: filters = {}

	data, columns = [], []
	cs_data=[]
	columns = get_columns()
	cs_data = get_cs_data(filters)

	data = []
	for d in cs_data:
		data.append(d)

	return columns, data


def get_columns():
	return [
		{
			'fieldname': 'employee',
			'label': _('Karyawan'),
			'fieldtype': 'Link',
			'options': "Employee"
		},
		{
			'fieldname': 'employee_name',
			'label': _('Nama Karyawan'),
			'fieldtype': 'Data'
		},
		{
			'fieldname': 'total_omzet',
			'label': _('Total Omzet'),
			'fieldtype': 'Currency'
		}
	]

def get_cs_data(filters):
	
	data = frappe.db.sql("""
		SELECT si.custom_handled_by_spg as emp, SUM(si.amount) as amount, te.employee_name as emp_name
		FROM `tabSales Invoice Item` si
		JOIN `tabEmployee` te ON te.name = si.custom_handled_by_spg
		WHERE custom_handled_by_spg is NOT NULL 
		GROUP BY custom_handled_by_spg;
	""",as_dict=1)
	
	hasil = []

	for row_si in data:
		hasil.append([row_si.emp, row_si.emp_name, row_si.amount])
		
	return hasil


