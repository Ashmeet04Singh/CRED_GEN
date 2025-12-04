import numpy as np
import pickle
import os
import pandas as pd # <-- REQUIRED for model pipeline input

# --- AI MODEL TRAINING AND LOADING ---
def load_underwriting_model(filepath: str):
    # ... (Model loading logic remains the same) ...
    if os.path.exists(filepath):
        print(f"Loading REAL AI Model from {filepath}...")
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Failed to load REAL model: {e}. Falling back to MOCK.")
    
    # --- MOCK AI MODEL (Fallback/Development) ---
    class MockModel:
        def predict_proba(self, data: dict):
            """Simulates the model output (risk score)."""
            income = data.get('income', 500000)
            cibil = data.get('CIBIL_Score', 700)
            
            # Heuristic: Lower risk for higher income/CIBIL
            risk = 0.95 - ( (income / 1000000) * 0.1 ) - ( (cibil - 600) / 300 * 0.2)
            return max(0.05, min(0.95, risk)) # Risk between 0.05 (best) and 0.95 (worst)

    print("Using MOCK AI Model for Underwriting.")
    return MockModel()


class UnderwritingAgent:
    
    def __init__(self):
        """Initializes agent and loads the AI predictive model."""
        # --- RULE-BASED LAYER: Hard Business Policy Constants ---
        self.MIN_AGE = 21
        self.MAX_AGE = 60
        self.MIN_INCOME = 300000 
        self.MAX_LOAN = 2000000 
        self.RISK_THRESHOLD_REJECT = 0.80 # AI Score > 0.80 is Auto-Reject Rule
        
        # --- AI LAYER: Load Model ---
        self.model = load_underwriting_model('data/underwriting_model.pkl')
        print("Underwriting Agent ready. ✅")

    def perform_underwriting(self, entities: dict) -> dict:
        """
        Executes the AI + Rule-Based underwriting process.
        """
        # --- PHASE 1: RULE-BASED CHECK (Hard Stops) ---
        age = entities.get('age', 0)
        income = entities.get('income', 0)
        loan_amount = entities.get('loan_amount', 0)
        
        if age < self.MIN_AGE or age > self.MAX_AGE:
            return self._hard_reject(reason=f"Age outside policy: {self.MIN_AGE}-{self.MAX_AGE}")

        if income < self.MIN_INCOME:
            return self._hard_reject(reason=f"Income below minimum policy of ₹{self.MIN_INCOME:,}")
            
        if loan_amount > self.MAX_LOAN or loan_amount < 50000:
            return self._hard_reject(reason=f"Loan amount outside policy range")

        # --- PHASE 2: AI MODEL SCORING ---
        
        # CRITICAL: Input must match the training features exactly!
        # Use placeholders (e.g., 700, 0.3) if the Master Agent doesn't collect them yet.
        model_input = {
            'Age': age,
            'Income': income,
            'Loan_Amount': loan_amount,
            'Tenure': entities.get('tenure', 36),
            'CIBIL_Score': entities.get('CIBIL_Score', 700), # <-- NEW HIGH-IMPACT FEATURE
            'Existing_EMIs': entities.get('Existing_EMIs', 5000), # <-- NEW HIGH-IMPACT FEATURE
            'Debt_to_Income_Ratio': entities.get('Debt_to_Income_Ratio', 0.35), # <-- NEW HIGH-IMPACT FEATURE
            'Employment_Type': entities.get('employment_type', 'Salaried'),
            'Loan_Purpose': entities.get('purpose', 'Consolidation'),
            'Residence_Type': entities.get('Residence_Type', 'Rented')
        }
        
        # Convert to a DataFrame, which the scikit-learn Pipeline expects.
        df_input = pd.DataFrame([model_input])
        
        # Get risk score (probability of default for class 1)
        # Note: We must call predict_proba() on the DataFrame
        try:
             risk_score = self.model.predict_proba(df_input)[:, 1][0]
        except Exception as e:
             print(f"AI Model Prediction Failed (Likely feature mismatch): {e}")
             # Fallback to a mid-range risk score if the real model fails
             risk_score = self.model.predict_proba({'age': age, 'income': income}) if not isinstance(self.model, pd.DataFrame) else 0.5 

        # --- PHASE 3: AI SCORE THRESHOLD RULE ---
        if risk_score > self.RISK_THRESHOLD_REJECT:
            return self._hard_reject(
                reason=f"AI Risk Score ({risk_score:.2f}) exceeds policy threshold ({self.RISK_THRESHOLD_REJECT})"
            )
            
        # --- PHASE 4: FINAL APPROVAL ---
        interest_rate = self._mock_interest_rate(risk_score) 
        
        return {
            "approval_status": True,
            "risk_score": round(risk_score, 3),
            "interest_rate": interest_rate,
            "reason": "Approved based on policy and low AI risk score."
        }

    def _hard_reject(self, reason: str) -> dict:
        """Helper to format a standardized rejection response."""
        return {
            "approval_status": False,
            "risk_score": 1.0, 
            "interest_rate": None,
            "reason": f"HARD REJECTED: {reason}"
        }

    def _mock_interest_rate(self, risk_score: float) -> float:
        """Simplified pricing rule based on the AI Risk Score."""
        BASE_RATE = 9.5
        MAX_RATE = 18.0
        rate = BASE_RATE + (risk_score * (MAX_RATE - BASE_RATE))
        return round(min(rate, MAX_RATE), 2)
