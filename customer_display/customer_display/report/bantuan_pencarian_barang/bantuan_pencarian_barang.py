import frappe

def execute(filters=None):
	if not filters or not filters.get("keyword"):
		return (
			get_columns(),
			[],
			None,
			None,
			[
				{
					"label": "Page",
					"value": 1,
					"datatype": "Int",
				},
				{
					"label": "Total Data",
					"value": 0,
					"datatype": "Int",
				},
			]
		)

	keyword = f"%{filters.get('keyword')}%"
	user = frappe.session.user

	page = int(filters.get("page") or 1)
	if page < 1:
		page = 1

	page_length = 100
	offset = (page - 1) * page_length

	allowed_companies = get_allowed_companies(user)

	if allowed_companies:
		allowed_companies = get_company_hierarchy(
			allowed_companies
		)

	company_filters = filters.get("company") or []

	if company_filters:
		if isinstance(company_filters, str):
			company_filters = [company_filters]

		company_hierarchy = get_company_hierarchy(
			company_filters
		)

		if allowed_companies:
			company_hierarchy = [
				company
				for company in company_hierarchy
				if company in allowed_companies
			]

		allowed_companies = company_hierarchy

	company_condition = ""

	query_values = [
		keyword,
		keyword,
		keyword
	]

	if allowed_companies:
		placeholders = ", ".join(
			["%s"] * len(allowed_companies)
		)

		company_condition = f"""
			AND (
				w.company IN ({placeholders})
				OR w.company IS NULL
			)
		"""

		query_values += allowed_companies

	else:
		if company_filters:
			return (
				get_columns(),
				[],
				None,
				None,
				[
					{
						"label": "Page",
						"value": page,
						"datatype": "Int",
					},
					{
						"label": "Total Data",
						"value": 0,
						"datatype": "Int",
					},
				]
			)

	price_lists = frappe.get_all(
		"Price List",
		filters={
			"selling": 1
		},
		pluck="name"
	)

	if price_lists:
		pl_select_sql = ", ".join([
			f"""
			MAX(
				CASE
					WHEN ip.price_list = '{pl}'
					THEN ip.price_list_rate
					ELSE 0
				END
			) AS `pl_{pl.lower().replace(' ', '_')}`
			"""
			for pl in price_lists
		])
	else:
		pl_select_sql = "0 AS pl_dummy"

	# ==========================================================
	# TOTAL DATA
	# ==========================================================

	count_query_values = [
		keyword,
		keyword,
		keyword
	]

	if allowed_companies:
		count_query_values += allowed_companies

	count_result = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM (
			SELECT
				i.item_code,
				i.item_name,
				i.brand,
				w.company

			FROM `tabItem` i

			LEFT JOIN `tabBin` b
				ON b.item_code = i.item_code

			LEFT JOIN `tabWarehouse` w
				ON w.name = b.warehouse

			WHERE i.disabled = 0

			AND (
				i.item_code LIKE %s
				OR i.item_name LIKE %s
				OR EXISTS (
					SELECT 1
					FROM `tabItem Barcode` ib
					WHERE ib.parent = i.name
					AND ib.barcode LIKE %s
				)
			)

			{company_condition}

			GROUP BY
				i.item_code,
				i.item_name,
				i.brand,
				w.company
		) AS total_rows
		""",
		tuple(count_query_values)
	)

	total_count = (
		count_result[0][0]
		if count_result
		else 0
	)

	# ==========================================================
	# DATA HALAMAN
	# ==========================================================

	items = frappe.db.sql(
		f"""
		SELECT
			i.item_code,
			i.item_name,
			i.brand,
			COALESCE(w.company, '-') AS company,

			SUM(
				CASE
					WHEN w.custom_tipe_warehouse = 'Toko'
					THEN b.actual_qty
					ELSE 0
				END
			) AS qty_toko,

			SUM(
				CASE
					WHEN w.custom_tipe_warehouse = 'Gudang'
					THEN b.actual_qty
					ELSE 0
				END
			) AS qty_gudang,

			SUM(
				CASE
					WHEN w.custom_tipe_warehouse = 'Waralaba'
					THEN b.actual_qty
					ELSE 0
				END
			) AS qty_waralaba,

			{pl_select_sql}

		FROM `tabItem` i

		LEFT JOIN `tabBin` b
			ON b.item_code = i.item_code

		LEFT JOIN `tabWarehouse` w
			ON w.name = b.warehouse

		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = i.item_code

		WHERE i.disabled = 0

		AND (
			i.item_code LIKE %s
			OR i.item_name LIKE %s
			OR EXISTS (
				SELECT 1
				FROM `tabItem Barcode` ib
				WHERE ib.parent = i.name
				AND ib.barcode LIKE %s
			)
		)

		{company_condition}

		GROUP BY
			i.item_code,
			i.item_name,
			i.brand,
			w.company

		ORDER BY i.item_code

		LIMIT %s OFFSET %s
		""",
		tuple(
			query_values + [
				page_length,
				offset
			]
		),
		as_dict=True
	)

	data = []

	for index, item in enumerate(
		items,
		start=offset + 1
	):
		last = get_last_pinv_item(
			item.item_code,
			item.company
		)

		bin_data = get_item_bin_info(
			item.item_code,
			company=item.company
		)

		row = {
			"no": index,
			"item_code": item.item_code,
			"item_name": item.item_name,
			"company": item.company,
			"brand": item.brand or "-",
			"vendor": last["vendor"],
			"qty_toko": bin_data["qty_toko"],
			"qty_gudang": bin_data["qty_gudang"],
			"qty_waralaba": bin_data["qty_waralaba"],
			"cogs": last["cogs"],
			"lcv": last["lcv"],
			"ppn": last["ppn"],
			"cogs_lcv": (
				last["cogs"] +
				last["lcv"]
			),
			"cogs_lcv_ppn": (
				last["cogs"] +
				last["lcv"] +
				last["ppn"]
			),
			"last_invoice": last["pinv_name"]
		}

		for pl in price_lists:
			fieldname = (
				f"pl_{pl.lower().replace(' ', '_')}"
			)

			row[fieldname] = item.get(
				fieldname,
				0
			)

		data.append(row)

	# ==========================================================
	# REPORT SUMMARY
	# ==========================================================

	if items:
		start_data = offset + 1
		end_data = offset + len(items)
	else:
		start_data = 0
		end_data = 0

	report_summary = [
		{
			"label": "Data",
			"value": f"{start_data} - {end_data}",
			"datatype": "Data",
		},
		{
			"label": "Total Data",
			"value": total_count,
			"datatype": "Int",
		},
	]

	return (
		get_columns(price_lists),
		data,
		None,
		None,
		report_summary
	)

def get_company_hierarchy(parents):
    if not parents:
        return []

    all_companies = set(parents)
    children = frappe.get_all(
        "Company",
        filters={"parent_company": ["in", parents]},
        pluck="name"
    )
    
    if children:
        all_companies.update(children)
        all_companies.update(get_company_hierarchy(children))
    
    return list(all_companies)


# def get_columns(price_lists=None):
#     columns = [
#         {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
#         {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
#         {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 160},
#         {"label": "Brand", "fieldname": "brand", "fieldtype": "Data", "width": 120},
#         {"label": "Vendor", "fieldname": "vendor", "fieldtype": "Data", "width": 150},
#         {"label": "Qty Toko", "fieldname": "qty_toko", "fieldtype": "Float", "width": 90},
#         {"label": "Qty Gudang", "fieldname": "qty_gudang", "fieldtype": "Float", "width": 110},
#     ]
#     if price_lists:
#         for pl in price_lists:
#             fieldname = f"pl_{pl.lower().replace(' ', '_')}"
#             columns.append({"label": f"PL {pl}", "fieldname": fieldname, "fieldtype": "Currency", "width": 120})

#     columns += [
#         {"label": "COGS", "fieldname": "cogs", "fieldtype": "Currency", "width": 100},
#         {"label": "LCV", "fieldname": "lcv", "fieldtype": "Currency", "width": 100},
#         {"label": "PPN", "fieldname": "ppn", "fieldtype": "Currency", "width": 100},
#         {"label": "COGS + LCV", "fieldname": "cogs_lcv", "fieldtype": "Currency", "width": 120},
#         {"label": "COGS + LCV + PPN", "fieldname": "cogs_lcv_ppn", "fieldtype": "Currency", "width": 150},
#         {"label": "Last Invoice", "fieldname": "last_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 120},  
#     ]
#     return columns

# def get_columns(price_lists=None):
#     columns = [
#         {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
#         {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},

#         {"label": "Qty Toko", "fieldname": "qty_toko", "fieldtype": "Float", "width": 90},
#         {"label": "Qty Gudang", "fieldname": "qty_gudang", "fieldtype": "Float", "width": 110},
#         {"label": "Qty Waralaba", "fieldname": "qty_waralaba", "fieldtype": "Float", "width": 110},

#         {"label": "COGS", "fieldname": "cogs", "fieldtype": "Currency", "width": 100},
#         {"label": "COGS + LCV + PPN", "fieldname": "cogs_lcv_ppn", "fieldtype": "Currency", "width": 150},
#     ]

#     # Urutan Price List sesuai permintaan (tanpa HET)
#     if price_lists:
#         price_list_order = [
#             "Retail",
#             "Grosir",
#             "MarketPlace"
#         ]

#         for pl in price_list_order:
#             if pl in price_lists:
#                 fieldname = f"pl_{pl.lower().replace(' ', '_')}"
#                 columns.append({
#                     "label": f"PL {pl}",
#                     "fieldname": fieldname,
#                     "fieldtype": "Currency",
#                     "width": 120
#                 })

#     columns += [
#         {"label": "LCV", "fieldname": "lcv", "fieldtype": "Currency", "width": 100},
#         {"label": "PPN", "fieldname": "ppn", "fieldtype": "Currency", "width": 100},
#         {"label": "COGS + LCV", "fieldname": "cogs_lcv", "fieldtype": "Currency", "width": 120},

#         {"label": "Brand", "fieldname": "brand", "fieldtype": "Data", "width": 120},
#         {"label": "Vendor", "fieldname": "vendor", "fieldtype": "Data", "width": 150},

#         {"label": "Last Invoice", "fieldname": "last_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 120},

#         {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 160},
#     ]

#     # PL HET paling akhir
#     if price_lists and "HET" in price_lists:
#         columns.append({
#             "label": "PL HET",
#             "fieldname": "pl_het",
#             "fieldtype": "Currency",
#             "width": 120
#         })

#     return columns

def get_columns(price_lists=None):
	columns = [
		{
			"label": "No",
			"fieldname": "no",
			"fieldtype": "Int",
			"width": 60
		},
		{
			"label": "Item Code",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"label": "Item Name",
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200
		},

		{
			"label": "Qty Toko",
			"fieldname": "qty_toko",
			"fieldtype": "Float",
			"width": 90
		},
		{
			"label": "Qty Gudang",
			"fieldname": "qty_gudang",
			"fieldtype": "Float",
			"width": 110
		},
		{
			"label": "Qty Waralaba",
			"fieldname": "qty_waralaba",
			"fieldtype": "Float",
			"width": 110
		},

		{
			"label": "COGS",
			"fieldname": "cogs",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": "COGS + LCV + PPN",
			"fieldname": "cogs_lcv_ppn",
			"fieldtype": "Currency",
			"width": 150
		}
	]

	if price_lists:
		price_list_order = [
			"Retail",
			"Grosir",
			"MarketPlace"
		]

		for pl in price_list_order:
			if pl in price_lists:
				fieldname = f"pl_{pl.lower().replace(' ', '_')}"

				columns.append({
					"label": f"PL {pl}",
					"fieldname": fieldname,
					"fieldtype": "Currency",
					"width": 120
				})

	columns += [
		{
			"label": "LCV",
			"fieldname": "lcv",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": "PPN",
			"fieldname": "ppn",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": "COGS + LCV",
			"fieldname": "cogs_lcv",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": "Brand",
			"fieldname": "brand",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": "Vendor",
			"fieldname": "vendor",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "Last Invoice",
			"fieldname": "last_invoice",
			"fieldtype": "Link",
			"options": "Purchase Invoice",
			"width": 120
		},
		{
			"label": "Company",
			"fieldname": "company",
			"fieldtype": "Data",
			"width": 160
		}
	]

	if price_lists and "HET" in price_lists:
		columns.append({
			"label": "PL HET",
			"fieldname": "pl_het",
			"fieldtype": "Currency",
			"width": 120
		})

	return columns

def get_item_bin_info(item_code, company=None):

    conditions = ""
    values = [item_code]

    if company:
        conditions = "AND w.company = %s"
        values.append(company)

    bin_info = frappe.db.sql(f"""
        SELECT
            w.company,
            SUM(CASE WHEN w.custom_tipe_warehouse='Toko' THEN b.actual_qty ELSE 0 END) AS qty_toko,
            SUM(CASE WHEN w.custom_tipe_warehouse='Gudang' THEN b.actual_qty ELSE 0 END) AS qty_gudang,
            SUM(CASE WHEN w.custom_tipe_warehouse='Waralaba' THEN b.actual_qty ELSE 0 END) AS qty_waralaba
        FROM `tabBin` b
        LEFT JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE b.item_code = %s
        {conditions}
        GROUP BY w.company
        LIMIT 1
    """, tuple(values), as_dict=1)

    if bin_info:
        return {
            "qty_toko": bin_info[0].qty_toko or 0,
            "qty_gudang": bin_info[0].qty_gudang or 0,
            "qty_waralaba": bin_info[0].qty_waralaba or 0,
            "company": bin_info[0].company or "-"
        }
    else:
        return {
            "qty_toko": 0,
            "qty_gudang": 0,
            "qty_waralaba": 0,
            "company": company or "-"
        }



def get_allowed_companies(user):
    companies = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Company"},
        pluck="for_value"
    )
    return companies or None

def get_last_pinv_item(item_code, company):

	item = frappe.db.get_value(
		"Item",
		item_code,
		[
			"custom_vendor",
			"custom_cogs",
			"custom_lcv",
			"custom_ppn"
		],
		as_dict=True
	)

	vendor_name = "-"
	cogs_default = 0
	lcv_default = 0
	ppn_default = 0

	if item:
		if item.custom_vendor:
			vendor_name = frappe.db.get_value(
				"Supplier",
				item.custom_vendor,
				"supplier_name"
			) or item.custom_vendor

		cogs_default = item.custom_cogs or 0
		lcv_default = item.custom_lcv or 0
		ppn_default = item.custom_ppn or 0

	last_pinv = frappe.db.sql("""
		SELECT
			pii.parent AS pinv_name,
			pii.valuation_rate,
			pii.base_rate,
			pii.net_rate,
			pii.price_list_rate,
			pii.rate

		FROM `tabPurchase Invoice Item` pii

		JOIN `tabPurchase Invoice` pi
			ON pi.name = pii.parent

		WHERE pii.item_code = %s
			AND pi.docstatus = 1
			AND pi.is_return = 0
			AND pi.company = %s

		ORDER BY
			pi.posting_date DESC,
			pi.name DESC

		LIMIT 1
	""", (item_code, company), as_dict=1)

	# Belum pernah ada PINV
	if not last_pinv:
		return {
			"pinv_name": "-",
			"cogs": cogs_default,
			"vendor": vendor_name,
			"lcv": lcv_default,
			"ppn": ppn_default
		}

	pii = last_pinv[0]

	pinv_name = pii.pinv_name

	# COGS
	cogs = pii.price_list_rate or 0

	# LCV
	lcv_res = frappe.db.sql("""
		SELECT
			SUM(applicable_charges / NULLIF(qty, 0))
		FROM `tabPINV LCV Item`
		WHERE parent = %s
			AND item_code = %s
	""", (pinv_name, item_code))

	lcv_sum = (
		lcv_res[0][0]
		if lcv_res and lcv_res[0][0]
		else 0
	)

	# PPN
	ppn_res = frappe.db.sql("""
		SELECT
			SUM(
				ROUND(
					(t.rate / 100) * pii.base_rate,
					2
				)
			)
		FROM `tabPurchase Taxes and Charges` t

		JOIN `tabPurchase Invoice Item` pii
			ON pii.parent = t.parent

		WHERE t.parent = %s
			AND pii.item_code = %s
	""", (pinv_name, item_code))

	ppn_sum = (
		ppn_res[0][0]
		if ppn_res and ppn_res[0][0]
		else 0
	)

	return {
		"pinv_name": pinv_name,
		"cogs": cogs,
		"vendor": vendor_name,
		"lcv": lcv_sum,
		"ppn": ppn_sum
	}

def test():
    test = get_company_hierarchy("BJM")
    print(test)
