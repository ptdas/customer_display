# Copyright (c) 2024, das and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, cstr, flt, formatdate, get_first_day, getdate
import math
import re

def get_columns(periodicity, period_list, accumulated_values=1, company=None):
	columns = [
		{
			"fieldname": "account",
			"label": _("ACCOUNT"),
			"fieldtype": "Data",
			"width": 300,
		}
	]
	if company:
		columns.append(
			{
				"fieldname": "currency",
				"label": _("CURRENCY"),
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
			}
		)
	for period in period_list:
		columns.append(
			{
				"fieldname": period.key,
				"label": period.label,
				"fieldtype": "Data",
				"width": 150,
			}
		)
	if periodicity != "YEARLY":
		if not accumulated_values:
			columns.append(
				{
					"fieldname": "total",
					"label": _("TOTAL"),
					"fieldtype": "Data",
					"width": 150,
				}
			)

	return columns

def execute(filters=None):
	columns, data = [], []

	cash_flow_accounts = get_cash_flow_accounts()

	data = []
	summary_data = {}
	temp_total = {}

	green_array = ["GROSS PROFIT","EBITDA","OPERATING INCOME","EARNINGS BEFORE TAX","NET INCOME","NET INCOME CORE"]
	head_array = ["SALES NET", "TOTAL COGS", "OPERATING EXPENSES", "BUSINESS RELATED EXPENSES", "NON-OPERATING PROFIT","EXTRAORDINARY PROFIT"]

	for cash_flow_account in cash_flow_accounts:
		section_data = []

		if cash_flow_account["section_header"] in green_array:
			data.append(
				{
					"account_name": """<span style ="font-size:135%"> <b>{}</b> </span>""".format(cash_flow_account["section_header"]),
					"account":  """<span style ="font-size:135%"> <b>{}</b> </span>""".format(cash_flow_account["section_header"]),
					"indent": 0,
					"parent_account": None,
					"text_account_name": cash_flow_account["section_header"]
				}
			)
		else:
			data.append(
				{
					"account_name": "<b>{}</b>".format(cash_flow_account["section_header"]),
					"account":  "<b>{}</b>".format(cash_flow_account["section_header"]),
					"indent": 0,
					"parent_account": None,
					"text_account_name": cash_flow_account["section_header"]
				}
			)

		for account in cash_flow_account["account_types"]:
			
			account_data = {
					"account_name": account["label"],
					"account": account["label"],
					"indent": 1,
					"parent_account": cash_flow_account["section_header"],
					"currency": "IDR",
					"text_account_name": account["label"]
				}
			
			data.append(account_data)
			section_data.append(account_data)

		data.append(
			{
				
			}
		)
	
	period_list = get_period_list(
		
		filters.get("from_date"),
		filters.get("to_date"),
		filters.get("periodicity")
	)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values
	)

	# frappe.throw(str(period_list))

	hasil = data_olah(data, filters, period_list)

	for satu_period in period_list:
		for row in hasil:
			if row.get("account_name"):

				nama_text_account_name = str(row.get("text_account_name"))
				if filters.get("periodicity") == "YEARLY":
					if nama_text_account_name not in green_array and nama_text_account_name not in head_array:
						row[satu_period.key] = """<a href="https://agress.digitalasiasolusindo.com/app/query-report/General%20Ledger?company=AGRES+X&from_date={}&to_date={}&group_by=Group+by+Voucher+%28Consolidated%29&account_element_is={}&include_dimensions=1&include_default_book_entries=1">{}""".format(filters.get("from_date"),filters.get("to_date"),nama_text_account_name.replace(" ","+"),row[satu_period.key])
				elif filters.get("periodicity") == "MONTHLY":
					if nama_text_account_name not in green_array and nama_text_account_name not in head_array:
						row[satu_period.key] = """<a href="https://agress.digitalasiasolusindo.com/app/query-report/General%20Ledger?company=AGRES+X&from_date={}&to_date={}&group_by=Group+by+Voucher+%28Consolidated%29&account_element_is={}&include_dimensions=1&include_default_book_entries=1">{}""".format(satu_period.from_date,satu_period.to_date,nama_text_account_name.replace(" ","+"),row[satu_period.key])


	return columns, hasil

def data_olah(data, filters, period_list):

	get_all_account = get_account(filters)
	notal = 0

	for satu_period in period_list:

		dari = satu_period.from_date
		sampai = satu_period.to_date

		# frappe.throw("{}-{}".format(dari,sampai))

		sales_revenue = calculate_per_account("SALES REVENUE", dari, sampai, get_all_account)
		sales_return = calculate_per_account("SALES RETURN", dari, sampai, get_all_account)
		sales_discount = calculate_per_account("SALES DISCOUNT", dari, sampai, get_all_account)

		cogs  = calculate_per_account("COGS", dari, sampai, get_all_account)
		other_cogs  = calculate_per_account("OTHER COGS", dari, sampai, get_all_account)

		selling_expense = calculate_per_account("SELLING EXPENSE", dari, sampai, get_all_account)
		distribution_expense = calculate_per_account("DISTRIBUTION EXPENSE", dari, sampai, get_all_account)
		other_operation_expense = calculate_per_account("OTHER OPERATION EXPENSE", dari, sampai, get_all_account)

		depamor_expenses = calculate_per_account("DEPAMOR EXPENSES", dari, sampai, get_all_account)
		financing_expenses = calculate_per_account("FINANCING EXPENSES", dari, sampai, get_all_account)

		other_income = calculate_per_account("OTHER INCOME", dari, sampai, get_all_account)
		other_expense = calculate_per_account("OTHER EXPENSE", dari, sampai, get_all_account)

		extraordinary_income = calculate_per_account("EXTRAORDINARY INCOME", dari, sampai, get_all_account)
		extraordinary_expense = calculate_per_account("EXTRAORDINARY EXPENSE", dari, sampai, get_all_account)

		tax_expense = calculate_per_account("TAX EXPENSES", dari, sampai, get_all_account)

		sales_net = sales_revenue - sales_return - sales_discount
		total_cogs = cogs + other_cogs
		gross_profit = sales_net - total_cogs
		operating_expenses = selling_expense + distribution_expense + other_operation_expense
		ebitda = gross_profit - operating_expenses
		business_related_expenses = depamor_expenses + financing_expenses
		operating_income = ebitda - business_related_expenses
		non_operating_profit = other_income - other_expense
		extraordinary_profit = extraordinary_income - extraordinary_expense
		earnings_before_tax = operating_income + non_operating_profit + extraordinary_profit
		net_income = earnings_before_tax - tax_expense
		net_income_core = net_income - extraordinary_profit

		for row in data:
			if row.get("account_name") == "SALES REVENUE":
				row[satu_period.key] = f""" <div style="text-align:right">RP {sales_revenue:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "SALES RETURN":
				row[satu_period.key] = f""" <div style="text-align:right">RP {sales_return:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "SALES DISCOUNT":
				row[satu_period.key] = f""" <div style="text-align:right">RP {sales_discount:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

			elif row.get("account_name") == "COGS":
				row[satu_period.key] = f""" <div style="text-align:right">RP {cogs:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "OTHER COGS":
				row[satu_period.key] = f""" <div style="text-align:right">RP {other_cogs:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

			elif row.get("account_name") == "SELLING EXPENSE":
				row[satu_period.key] = f""" <div style="text-align:right">RP {selling_expense:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "DISTRIBUTION EXPENSE":
				row[satu_period.key] = f""" <div style="text-align:right">RP {distribution_expense:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "OTHER OPERATION EXPENSE":
				row[satu_period.key] = f""" <div style="text-align:right">RP {other_operation_expense:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

			elif row.get("account_name") == "DEPAMOR EXPENSES":
				row[satu_period.key] = f""" <div style="text-align:right">RP {depamor_expenses:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "FINANCING EXPENSES":
				row[satu_period.key] = f""" <div style="text-align:right">RP {financing_expenses:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

			elif row.get("account_name") == "OTHER INCOME":
				row[satu_period.key] = f""" <div style="text-align:right">RP {other_income:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "OTHER EXPENSE":
				row[satu_period.key] = f""" <div style="text-align:right">RP {other_expense:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

			elif row.get("account_name") == "EXTRAORDINARY INCOME":
				row[satu_period.key] = f""" <div style="text-align:right">RP {extraordinary_income:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
			elif row.get("account_name") == "EXTRAORDINARY EXPENSE":
				row[satu_period.key] = f""" <div style="text-align:right">RP {extraordinary_expense:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

			elif row.get("account_name"):
				if "TAX EXPENSES" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {tax_expense:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "SALES NET" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {sales_net:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "TOTAL COGS" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {total_cogs:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "GROSS PROFIT" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {gross_profit:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "OPERATING EXPENSES" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {operating_expenses:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "EBITDA" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {ebitda:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "BUSINESS RELATED EXPENSES" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {business_related_expenses:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "OPERATING INCOME" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {operating_income:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "NON-OPERATING PROFIT" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {non_operating_profit:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "EXTRAORDINARY PROFIT" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {extraordinary_profit:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "EARNINGS BEFORE TAX" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {earnings_before_tax:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "NET INCOME" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {net_income:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")
				elif "NET INCOME CORE" in str(row.get("account_name")):
					row[satu_period.key] = f""" <div style="text-align:right">RP {net_income_core:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

	if filters.get("periodicity") == "MONTHLY":
		for baris_data in data:
			if baris_data.get("account_name"):
				total_per_baris = 0
				for baris_period in period_list:
					get_angka = str(baris_data[baris_period.key]).replace(' <div style="text-align:right">RP ','').replace('.','').replace(',','.').replace(" </div>","")
					angka = float(get_angka)
				
					total_per_baris += frappe.utils.flt(angka)

				baris_data['total']	= f""" <div style="text-align:right">RP {total_per_baris:,.2f} </div>""".replace(",", "X").replace(".", ",").replace("X", ".")

				

	# if filters.get("periodicity" == "YEARLY"):
	# 	for baris in get_all_account:

	# for row in data:
	# 	if row.get("account_name"):
	# 		row['total'] = "RP. 0,00"

	return data

def calculate_per_account(account, dari, sampai, get_all_account):
	hasil = 0

	for satu_account in get_all_account:
		if satu_account.account == account and satu_account.tanggal >= dari and satu_account.tanggal <= sampai:
			hasil += frappe.utils.flt(satu_account.total)

	return hasil

def get_account(filters):
	
	list_account = frappe.db.sql(""" 

		SELECT SUM(gl.debit-gl.credit) as total, ta.custom_account_element_is as account, gl.posting_date as tanggal
		FROM `tabGL Entry` gl 
		JOIN `tabAccount` ta ON ta.name = gl.account
		WHERE gl.posting_date >= "{}" AND gl.posting_date <= "{}"
		AND ta.custom_account_element_is IS NOT NULL
		AND ta.custom_account_element_is != ""
		GROUP BY ta.custom_account_element_is, gl.posting_date

	""".format(filters.get("from_date"), filters.get("to_date")), as_dict=1)

	return list_account



def get_months(start_date, end_date):
	diff = (12 * end_date.year + end_date.month) - (12 * start_date.year + start_date.month)
	return diff + 1


def get_label(periodicity, from_date, to_date):
	if periodicity == "YEARLY":
		if formatdate(from_date, "YYYY") == formatdate(to_date, "YYYY"):
			label = formatdate(from_date, "YYYY")
		else:
			label = formatdate(from_date, "YYYY") + "-" + formatdate(to_date, "YYYY")
	else:
		label = formatdate(from_date, "MMM YY") + "-" + formatdate(to_date, "MMM YY")

	return str(label).upper()


def get_period_list(
	period_start_date,
	period_end_date,
	periodicity,
	accumulated_values=False,
):
	"""Get a list of dict {"from_date": from_date, "to_date": to_date, "key": key, "label": label}
	Periodicity can be (YEARLY, Quarterly, MONTHLY)"""

	year_start_date = getdate(period_start_date)
	year_end_date = getdate(period_end_date)

	months_to_add = {"YEARLY": 12, "MONTHLY": 1}[periodicity]

	period_list = []

	start_date = year_start_date
	months = get_months(year_start_date, year_end_date)

	# frappe.throw("{}-{}-{}".format(str(months),year_end_date, year_start_date))

	for i in range(cint(math.ceil(months / months_to_add))):
		period = frappe._dict({"from_date": start_date})

		to_date = add_months(get_first_day(start_date), months_to_add)

		start_date = to_date

		# Subtract one day from to_date, as it may be first day in next fiscal year or month
		to_date = add_days(to_date, -1)

		if to_date <= year_end_date:
			# the normal case
			period.to_date = to_date
		else:
			# if a fiscal year ends before a 12 month period
			period.to_date = year_end_date

		period_list.append(period)

		if period.to_date == year_end_date:
			break

	# common processing
	for opts in period_list:
		key = opts["to_date"].strftime("%b_%Y").lower()
		if periodicity == "MONTHLY" and not accumulated_values:
			label = formatdate(opts["to_date"], "MMM YYYY")
		else:
			if not accumulated_values:
				label = get_label(periodicity, opts["from_date"], opts["to_date"])
			else:
				if reset_period_on_fy_change:
					label = get_label(periodicity, opts.from_date_fiscal_year_start_date, opts["to_date"])
				else:
					label = get_label(periodicity, period_list[0].from_date, opts["to_date"])
		opts.update(
			{
				"key": key.replace(" ", "_").replace("-", "_"),
				"label": label,
				"year_start_date": year_start_date,
				"year_end_date": year_end_date,
			}
		)

	return period_list

def get_cash_flow_accounts():
	sales_net = {
		"section_name": "SALES NET",
		"section_header": _("SALES NET"),
		"account_types": [
			{"account_type": "SALES REVENUE", "label": _("SALES REVENUE")},
			{"account_type": "SALES RETURN", "label": _("SALES RETURN")},
			{"account_type": "SALES DISCOUNT", "label": _("SALES DISCOUNT")},
			
		],
	}

	total_cogs = {
		"section_name": "TOTAL COGS",
		"section_header": _("TOTAL COGS"),
		"account_types": [
			{"account_type": "COGS", "label": _("COGS")},
			{"account_type": "OTHER COGS", "label": _("OTHER COGS")}
		],
	}

	gross_profit = {
		"section_name": "GROSS PROFIT",
		"section_header": _("GROSS PROFIT"),
		"account_types": [
		],
	}

	operating_expenses = {
		"section_name": "OPERATING EXPENSES",
		"section_header": _("OPERATING EXPENSES"),
		"account_types": [
			{"account_type": "SELLING EXPENSE", "label": _("SELLING EXPENSE")},
			{"account_type": "DISTRIBUTION EXPENSE", "label": _("DISTRIBUTION EXPENSE")},
			{"account_type": "OTHER OPERATION EXPENSE", "label": _("OTHER OPERATION EXPENSE")},
		],
	}

	ebitda = {
		"section_name": "EBITDA",
		"section_header": _("EBITDA"),
		"account_types": [
		],
	}

	business_related_expenses = {
		"section_name": "BUSINESS RELATED EXPENSES",
		"section_header": _("BUSINESS RELATED EXPENSES"),
		"account_types": [
			{"account_type": "DEPAMOR EXPENSES", "label": _("DEPAMOR EXPENSES")},
			{"account_type": "FINANCING EXPENSES", "label": _("FINANCING EXPENSES")}
		],
	}

	operating_income = {
		"section_name": "OPERATING INCOME",
		"section_header": _("OPERATING INCOME"),
		"account_types": [
		],
	}

	non_operating_profit = {
		"section_name": "NON-OPERATING PROFIT",
		"section_header": _("NON-OPERATING PROFIT"),
		"account_types": [
			{"account_type": "OTHER INCOME", "label": _("OTHER INCOME")},
			{"account_type": "OTHER EXPENSE", "label": _("OTHER EXPENSE")}
		],
	}

	extraordinary_profit = {
		"section_name": "EXTRAORDINARY PROFIT",
		"section_header": _("EXTRAORDINARY PROFIT"),
		"account_types": [
			{"account_type": "EXTRAORDINARY INCOME", "label": _("EXTRAORDINARY INCOME")},
			{"account_type": "EXTRAORDINARY EXPENSE", "label": _("EXTRAORDINARY EXPENSE")}
		],
	}

	earnings_before_tax = {
		"section_name": "EARNINGS BEFORE TAX",
		"section_header": _("EARNINGS BEFORE TAX"),
		"account_types": [
		],
	}

	tax_expenses = {
		"section_name": "TAX EXPENSES",
		"section_header": _("TAX EXPENSES"),
		"account_types": [
		],
	}

	net_income = {
		"section_name": "NET INCOME",
		"section_header": _("NET INCOME"),
		"account_types": [
		],
	}

	net_income_core = {
		"section_name": "NET INCOME CORE",
		"section_header": _("NET INCOME CORE"),
		"account_types": [
		],
	}

	return [
		sales_net, 
		total_cogs, 
		gross_profit, 
		operating_expenses, 
		ebitda, 
		business_related_expenses,
		operating_income,
		non_operating_profit, 
		extraordinary_profit,
		earnings_before_tax, 
		tax_expenses, 
		net_income, 
		net_income_core
	]


