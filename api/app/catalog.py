"""
Master category list. This is the single source of truth for the whole app —
the API seeds these into the `categories` and `budget_items` tables on first
boot. To add a category later, add it here and restart the API (the seed is
idempotent — it only inserts rows that don't already exist).
"""

# (Type, Category, Subcategory)
CATS: list[tuple[str, str, str]] = [
    ("Income", "Income", "Salary / Income 1"),
    ("Income", "Income", "Salary / Income 2"),
    ("Income", "Income", "Extra / Other Income"),

    ("Expense", "Housing", "Mortgage/Rent"),
    ("Expense", "Housing", "Electricity"),
    ("Expense", "Housing", "Water & Sewer"),
    ("Expense", "Housing", "Gas"),
    ("Expense", "Housing", "Internet/Cable"),
    ("Expense", "Housing", "Phone"),
    ("Expense", "Housing", "Waste Removal"),
    ("Expense", "Housing", "Maintenance & Repairs"),
    ("Expense", "Housing", "Supplies"),
    ("Expense", "Housing", "Other"),

    ("Expense", "Transportation", "Vehicle Payment"),
    ("Expense", "Transportation", "Fuel"),
    ("Expense", "Transportation", "Insurance"),
    ("Expense", "Transportation", "Licensing"),
    ("Expense", "Transportation", "Maintenance"),
    ("Expense", "Transportation", "Public Transport/Taxi"),
    ("Expense", "Transportation", "Parking"),
    ("Expense", "Transportation", "Other"),

    ("Expense", "Insurance", "Health"),
    ("Expense", "Insurance", "Home"),
    ("Expense", "Insurance", "Life"),
    ("Expense", "Insurance", "Other"),

    ("Expense", "Food", "Groceries"),
    ("Expense", "Food", "Dining Out"),
    ("Expense", "Food", "Other"),

    ("Expense", "Children", "Tuition"),
    ("Expense", "Children", "School Supplies"),
    ("Expense", "Children", "Medical"),
    ("Expense", "Children", "Clothing"),
    ("Expense", "Children", "Child Care"),
    ("Expense", "Children", "Activities"),
    ("Expense", "Children", "Other"),

    ("Expense", "Pets", "Food"),
    ("Expense", "Pets", "Medical"),
    ("Expense", "Pets", "Grooming"),
    ("Expense", "Pets", "Other"),

    ("Expense", "Personal Care", "Clothing"),
    ("Expense", "Personal Care", "Hair/Nails"),
    ("Expense", "Personal Care", "Health Club"),
    ("Expense", "Personal Care", "Medical"),
    ("Expense", "Personal Care", "Other"),

    ("Expense", "Entertainment", "Movies & Events"),
    ("Expense", "Entertainment", "Subscriptions"),
    ("Expense", "Entertainment", "Hobbies"),
    ("Expense", "Entertainment", "Other"),

    ("Expense", "Loans", "Credit Card"),
    ("Expense", "Loans", "Personal Loan"),
    ("Expense", "Loans", "Student Loan"),
    ("Expense", "Loans", "Other"),

    ("Expense", "Taxes", "Government/Zakat"),
    ("Expense", "Taxes", "Other"),

    ("Expense", "Gifts and Charity", "Charity"),
    ("Expense", "Gifts and Charity", "Gifts"),
    ("Expense", "Gifts and Charity", "Other"),

    ("Expense", "Miscellaneous", "Other"),

    ("Savings", "Savings", "Emergency Fund"),
    ("Savings", "Savings", "Investment Account"),
    ("Savings", "Savings", "Retirement Account"),
    ("Savings", "Savings", "Other Savings"),
]

PAYMENT_METHODS = ["Cash", "Debit Card", "Credit Card", "Bank Transfer", "Mada", "Apple Pay", "Other"]

VALID_TYPES = {"Income", "Expense", "Savings"}
