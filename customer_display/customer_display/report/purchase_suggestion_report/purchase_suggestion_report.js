// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Suggestion Report"] = {
  filters: [
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company",
      reqd: 1
    },
    {
      fieldname: "as_of_date",
      label: "As of Date",
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1
    }
  ]
};
