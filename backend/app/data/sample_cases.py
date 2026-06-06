SAMPLE_CASES = [
    {
        "company_name":"Northstar Logistics", "monthly_revenue":240000, "monthly_spend":162000, "planned_budget":170000, "cash_reserve":98000, "budget_variance_ratio":0.08,
        "anomalous_transactions_30d":1, "runway_months":8, "late_payments_90d":0, "invoice_match_rate":0.97, "books_verified":True,
        "documents":["general_ledger_jan.csv","vendor_aging_jan.csv","budget_plan_q1.json"]
    },
    {
        "company_name":"Bluebyte Commerce", "monthly_revenue":175000, "monthly_spend":151000, "planned_budget":145000, "cash_reserve":42000, "budget_variance_ratio":0.26,
        "anomalous_transactions_30d":5, "runway_months":4, "late_payments_90d":2, "invoice_match_rate":0.89, "books_verified":True,
        "documents":["general_ledger_jan.csv","expenses_breakdown_jan.csv","budget_plan_q1.json"]
    },
    {
        "company_name":"Vertex Creative Labs", "monthly_revenue":98000, "monthly_spend":112000, "planned_budget":89000, "cash_reserve":12000, "budget_variance_ratio":0.43,
        "anomalous_transactions_30d":11, "runway_months":2, "late_payments_90d":5, "invoice_match_rate":0.72, "books_verified":False,
        "documents":["expenses_dump.csv"]
    }
]
