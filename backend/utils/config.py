# Paths
MODEL_PATH = "../data/"
UNDERWRITING_MODEL = "underwriting_model.pkl"
FRAUD_MODEL = "fraud_model.pkl"

# Loan constraints
MIN_LOAN_AMOUNT = 50000
MAX_LOAN_AMOUNT = 5000000
MIN_TENURE = 12  # months
MAX_TENURE = 60  # months
MIN_AGE = 21
MAX_AGE = 65
MIN_INCOME = 300000  # annual

# Interest rate bands (based on risk_score 0-1)
INTEREST_BANDS = {
    "low": (0.0, 0.3, 8.5, 9.5),      # risk 0-0.3 → 8.5-9.5%
    "medium": (0.3, 0.7, 9.5, 12.0),  # risk 0.3-0.7 → 9.5-12%
    "high": (0.7, 1.0, 12.0, 15.0)    # risk 0.7-1.0 → 12-15%
}

# Required fields for underwriting
REQUIRED_FIELDS = [
    "loan_amount", "tenure", "age", "income", 
    "employment_type", "name", "purpose"
]

# Required fields for KYC
KYC_FIELDS = ["pan", "aadhaar", "address", "pincode"]

# Intent keywords mapping
INTENT_KEYWORDS = {
    "greeting": ["hi", "hello", "hey", "good morning", "good evening", "namaste"],
    "loan_application": ["loan", "borrow", "need money", "apply", "credit"],
    "rate_inquiry": ["interest", "rate", "percentage", "roi", "apr"],
    "negotiate_terms": ["reduce", "lower", "discount", "better rate", "negotiate"],
    "accept_offer": ["accept", "yes", "proceed", "ok", "agree", "confirm"],
    "reject_offer": ["reject", "no", "cancel", "not interested", "decline"],
    "status_check": ["status", "where", "pending", "approved", "check application"],
    "kyc_query": ["documents", "kyc", "papers", "id proof", "verification"],
    "help_general": ["help", "how", "what", "explain", "process"],
    "complaint": ["slow", "poor", "bad", "complaint", "unsatisfied"],
    "exit": ["bye", "exit", "quit", "stop", "end"]
}
