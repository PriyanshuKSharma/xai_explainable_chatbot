Drop your trained loan model here as:

models/model.pkl

Recommended feature order for the built-in backend loader:
1. monthly_income
2. credit_score
3. monthly_debt_payments
4. loan_amount
5. loan_term_years
6. annual_rate
7. employment_years

If model.pkl is missing, the app falls back to the transparent rule-based loan engine so the full system still runs.
