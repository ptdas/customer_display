# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_last_day, formatdate
from datetime import datetime
from dateutil.relativedelta import relativedelta

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    """Generate dynamic columns based on periodicity"""
    columns = [
        {
            "fieldname": "account_element",
            "label": _("Account Element"),
            "fieldtype": "Data",
            "width": 300
        }
    ]
    
    # Generate period columns
    periods = get_periods(filters)
    for period in periods:
        columns.append({
            "fieldname": period["key"],
            "label": period["label"],
            "fieldtype": "Currency",
            "width": 150
        })
    
    return columns

def get_periods(filters):
    """Generate periods based on from_date, to_date and periodicity"""
    periods = []
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    periodicity = filters.get("periodicity", "YEARLY")
    
    if periodicity == "MONTHLY":
        current_date = from_date
        while current_date <= to_date:
            period_end = get_last_day(current_date)
            if period_end > to_date:
                period_end = to_date
            
            periods.append({
                "key": current_date.strftime("%Y_%m"),
                "label": current_date.strftime("%b %Y"),
                "from_date": current_date.replace(day=1),
                "to_date": period_end
            })
            current_date = add_months(current_date, 1)
    
    elif periodicity == "YEARLY":
        current_date = from_date
        while current_date <= to_date:
            year_end = current_date.replace(month=12, day=31)
            if year_end > to_date:
                year_end = to_date
            
            periods.append({
                "key": str(current_date.year),
                "label": str(current_date.year),
                "from_date": current_date.replace(month=1, day=1),
                "to_date": year_end
            })
            current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
    
    return periods

def get_data(filters):
    """Generate the hierarchical report data"""
    periods = get_periods(filters)
    
    # Get account balances for each period
    period_balances = {}
    for period in periods:
        period_balances[period["key"]] = get_account_balances(period["to_date"], filters)
    
    # Build the hierarchical structure
    data = []
    
    # Define the structure mapping
    structure = get_report_structure()
    
    # Build rows
    for item in structure:
        row = build_row(item, period_balances, periods)
        data.append(row)
    
    return data

def get_account_balances(as_on_date, filters):
    """Get account balances grouped by custom_account_element_sfp"""
    
    balances = frappe.db.sql("""
        SELECT 
            acc.custom_account_element_sfp,
            SUM(gle.debit - gle.credit) as balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON gle.account = acc.name
        WHERE gle.posting_date <= %(as_on_date)s
            AND gle.is_cancelled = 0
            AND acc.custom_account_element_sfp IS NOT NULL
            AND acc.custom_account_element_sfp != ''
        GROUP BY acc.custom_account_element_sfp
    """, {"as_on_date": as_on_date}, as_dict=1)
    
    balance_dict = {}
    for b in balances:
        balance_dict[b.custom_account_element_sfp] = flt(b.balance)
    
    return balance_dict

def build_row(item, period_balances, periods):
    """Build a single row with period values"""
    row = {
        "account_element": item["label"],
        "indent": item.get("indent", 0),
        "is_header": item.get("is_header", False),
        "is_total": item.get("is_total", False)
    }
    
    # Calculate values for each period
    for period in periods:
        value = 0
        balances = period_balances.get(period["key"], {})
        
        if item.get("codes"):
            # Sum up values for specified codes
            for code in item["codes"]:
                value += flt(balances.get(code, 0))
        
        row[period["key"]] = value if value != 0 else None
    
    return row

def get_report_structure():
    """Define the complete hierarchical structure"""
    return [
        # ASSETS
        {"label": "Total Asset", "is_header": True, "is_total": True, "indent": 0, "codes": []},
        {"label": "Total Current Asset", "is_header": True, "is_total": True, "indent": 1, "codes": []},
        
        # Cash & Investment
        {"label": "Cash Investment Equivalent", "is_header": True, "indent": 2, "codes": []},
        {"label": "Cash & Cash Equivalent", "indent": 3, "codes": ["1-01 Cash & Cash Equivalent"]},
        {"label": "Investment - Short Term", "indent": 3, "codes": ["1-02 Investment - Short Term"]},
        
        # Working Capital Assets
        {"label": "Working Capital Asset", "is_header": True, "indent": 2, "codes": []},
        {"label": "Trade Receivable", "indent": 3, "codes": ["1-03 Trade Receivable"]},
        {"label": "Affiliated Receivable", "indent": 3, "codes": ["1-04 Affiliated Receivable"]},
        {"label": "Third Party Receivable", "indent": 3, "codes": ["1-05 Third Party Receivable"]},
        {"label": "Employee Receivable", "indent": 3, "codes": ["1-06 Employe Receivable"]},
        {"label": "Other Receivable", "indent": 3, "codes": ["1-07 Other Receivable"]},
        {"label": "Inventory", "indent": 3, "codes": ["1-08 Inventory"]},
        {"label": "Prepaid Expense", "indent": 3, "codes": ["1-09 Prepaid Expense"]},
        {"label": "Advance Purchase", "indent": 3, "codes": ["1-10 Advance Purchase"]},
        
        # Other Current Assets
        {"label": "Other Current Assets", "is_header": True, "indent": 2, "codes": []},
        {"label": "Other Current Assets", "indent": 3, "codes": ["1-11 Other Current Assets"]},
        
        # Non-Current Assets
        {"label": "Total Non-Current Asset", "is_header": True, "is_total": True, "indent": 1, "codes": []},
        
        # PPE & Investment
        {"label": "PPE & Investment", "is_header": True, "indent": 2, "codes": []},
        {"label": "Long Term Investment", "indent": 3, "codes": ["2-12 Long Term Investment"]},
        {"label": "Land & Building", "indent": 3, "codes": ["2-13 Land & Building"]},
        {"label": "Other Fixed Assets", "indent": 3, "codes": ["2-14 Other Fixed Assets"]},
        {"label": "Accumulated Depreciation", "indent": 3, "codes": ["2-15 Accumulated Depreciation"]},
        
        # Other Non-Current Assets
        {"label": "Other Non-Current Assets", "is_header": True, "indent": 2, "codes": []},
        {"label": "Investment in Related Party", "indent": 3, "codes": ["2-16 Investment in Related Party"]},
        {"label": "Other Long Term Investment", "indent": 3, "codes": ["2-17 Other Long Term Investment"]},
        {"label": "Intangible Assets", "indent": 3, "codes": ["2-18 Intangible Assets"]},
        {"label": "Deferred Tax Asset", "indent": 3, "codes": ["2-19 Deferred Tax Asset"]},
        {"label": "Other Long Term Assets", "indent": 3, "codes": ["2-21 Other Long Term Assets"]},
        
        # LIABILITIES AND EQUITY
        {"label": "Total Liabilities and Equity", "is_header": True, "is_total": True, "indent": 0, "codes": []},
        {"label": "Total Liabilities", "is_header": True, "is_total": True, "indent": 1, "codes": []},
        
        # Working Capital Liabilities
        {"label": "Working Capital Liabilities", "is_header": True, "indent": 2, "codes": []},
        {"label": "Trade Payable", "indent": 3, "codes": ["3-01 Trade Payable"]},
        {"label": "Affiliated Payable", "indent": 3, "codes": ["3-02 Affiliated Payable"]},
        {"label": "Interest Payable", "indent": 3, "codes": ["3-03 Interest Payable"]},
        {"label": "Tax Payable", "indent": 3, "codes": ["3-04 Tax Payable"]},
        {"label": "Dividend Payable", "indent": 3, "codes": ["3-05 Dividend Payable"]},
        {"label": "Expenses Payable", "indent": 3, "codes": ["3-06 Expenses Payable"]},
        
        # Other Liabilities
        {"label": "Other Liabilities", "is_header": True, "indent": 2, "codes": []},
        {"label": "Short Term Bank Notes", "indent": 3, "codes": ["3-07 Short Term Bank Notes"]},
        {"label": "Long Term Bank Notes that due in Short Term", "indent": 3, "codes": ["3-08 Long Term Bank Notes that due in Short Term"]},
        {"label": "Advance Sales", "indent": 3, "codes": ["3-09 Advance Sales"]},
        {"label": "Other Liabilities", "indent": 3, "codes": ["3-10 Other Liabilities"]},
        
        # Non-Current Liabilities
        {"label": "Non-Current Liabilities", "is_header": True, "indent": 2, "codes": []},
        {"label": "Long Term Bank Notes", "indent": 3, "codes": ["3-11 Long Term Bank Notes"]},
        {"label": "Long Term Trade Payable", "indent": 3, "codes": ["3-12 Long Term Trade Payable"]},
        {"label": "Long Term Affiliated Payable", "indent": 3, "codes": ["3-13 Long Term Affiliated Payable"]},
        {"label": "Deferred Tax Liabilities", "indent": 3, "codes": ["3-14 Deferred Tax Liabilities"]},
        {"label": "Other Long Term Liabilities", "indent": 3, "codes": ["3-15 Other Long Term Liabilities"]},
        
        # EQUITY
        {"label": "Total Equity", "is_header": True, "is_total": True, "indent": 1, "codes": []},
        
        # Share Equity
        {"label": "Share Equity", "is_header": True, "indent": 2, "codes": []},
        {"label": "Share Capital", "indent": 3, "codes": ["4-16 Share Capital"]},
        {"label": "Share Premium", "indent": 3, "codes": ["4-17 Share Premium"]},
        
        # Retained Equity
        {"label": "Retained Equity", "is_header": True, "indent": 2, "codes": []},
        {"label": "Retained Earnings (Current)", "indent": 3, "codes": ["4-18 Retained Earnings (Current)"]},
        {"label": "Retained Earnings", "indent": 3, "codes": ["4-19 Retained Earnings"]},
        {"label": "Other Equity", "indent": 3, "codes": ["4-20 Other Equity"]},
    ]