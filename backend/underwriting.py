import numpy as np
import pickle
import joblib
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
            # data is now a DataFrame, extract the first row for heuristic calculation
            income = data['Income'].iloc[0] if 'Income' in data else 500000
            cibil = data['CIBIL_Score'].iloc[0] if 'CIBIL_Score' in data else 700
            
            # Heuristic: Lower risk for higher income/CIBIL
            risk = 0.95 - ( (income / 1000000) * 0.1 ) - ( (cibil - 600) / 300 * 0.2)
            return np.array([[1 - risk, max(0.05, min(0.95, risk))]]) # Return format expected by scikit-learn predict_proba

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
        
        self.numerical_features = [
            'age', 'years_employed', 'annual_income', 'monthly_income',
            'existing_loan_balance', 'existing_emi_monthly', 'credit_score', 
            'cibil_score', 'payment_history_default', 'credit_inquiry_last_6m',
            'num_open_accounts', 'num_delinquent_accounts', 'property_value',
            'requested_loan_amount', 'requested_loan_tenure', 'pre_approved_limit',
            'monthly_income_after_emi', 'debt_to_income_ratio', 'loan_to_income_ratio',
            'estimated_monthly_emi', 'emi_to_income_ratio', 'total_monthly_obligation',
            'obligation_to_income_ratio', 'loan_to_asset_ratio', 'credit_age_months',
            'income_to_loan_ratio', 'emi_affordability', 'asset_coverage',
            'stability_score'
        ]

        self.categorical_features = [
            'gender', 'city', 'employment_type', 'education_level',
            'marital_status', 'home_ownership', 'property_type'
        ]

        # --- Full model features order (used in _preprocess_input) ---
        self.model_features_order = self.numerical_features + self.categorical_features

        # # --- List of all features the model expects (CRITICAL) ---
        # self.MODEL_FEATURES = [
        #     'Age', 'Income', 'Loan_Amount', 'Tenure', 'CIBIL_Score', 
        #     'Existing_EMIs', 'Debt_to_Income_Ratio', 
        #     'Employment_Type', 'Loan_Purpose', 'Residence_Type'
        # ]

        # --- AI LAYER: Load Model ---
        # self.model = load_underwriting_model('data/underwriting_model.pkl')
        self.model = load_underwriting_model('underwriting_model.pkl')
        print("Underwriting Agent ready. ✅")

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
        
    def _preprocess_input(self, entities: dict) -> pd.DataFrame:
        """
        Creates a DataFrame from the conversational entities, applying defaults
        and ensuring all model features are present in the correct order.
        Fully compatible with the trained pipeline.
        """

        # --- Numerical features ---
        numerical_defaults = {
            'age': 35,
            'years_employed': 5,
            'annual_income': 500000,
            'monthly_income': 41666,
            'existing_loan_balance': 0,
            'existing_emi_monthly': 0,
            'credit_score': 700,
            'cibil_score': 700,
            'payment_history_default': 0,
            'credit_inquiry_last_6m': 0,
            'num_open_accounts': 3,
            'num_delinquent_accounts': 0,
            'property_value': 1000000,
            'requested_loan_amount': 500000,
            'requested_loan_tenure': 36,
            'pre_approved_limit': 500000,
            'monthly_income_after_emi': 40000,
            'debt_to_income_ratio': 0.3,
            'loan_to_income_ratio': 0.2,
            'estimated_monthly_emi': 15000,
            'emi_to_income_ratio': 0.3,
            'total_monthly_obligation': 20000,
            'obligation_to_income_ratio': 0.35,
            'loan_to_asset_ratio': 0.4,
            'credit_age_months': 60,
            'income_to_loan_ratio': 1.0,
            'emi_affordability': 2.0,
            'asset_coverage': 1.5,
            'stability_score': 50
        }

        # Override defaults with provided entities
        for key in numerical_defaults:
            if key in entities:
                numerical_defaults[key] = entities[key]

        # --- Categorical features ---
        categorical_defaults = {
            'gender': 'M',
            'city': 'Bangalore',
            'employment_type': 'Salaried',
            'education_level': 'Graduate',
            'marital_status': 'Single',
            'home_ownership': 'Rented',
            'property_type': 'Apartment'
        }

        for key in categorical_defaults:
            if key in entities:
                categorical_defaults[key] = entities[key]

        # Merge all features
        model_input = {**numerical_defaults, **categorical_defaults}

        # Convert to DataFrame in correct order
        all_features_order = self.model_features_order  # should store numerical + categorical features here

        df_input = pd.DataFrame([model_input], columns=all_features_order)
        return df_input


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
        
        # CRITICAL: Preprocess the input data
        df_input = self._preprocess_input(entities)
        
        # Get risk score (probability of default for class 1)
        try:
            # Predict_proba returns probabilities for both classes [P(No Default), P(Default)]
            risk_score = self.model.predict_proba(df_input)[:, 1][0]
        except Exception as e:
            print(f"AI Model Prediction Failed: {e}")
            # Fallback score if the real model fails unexpectedly
            risk_score = 0.5 

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