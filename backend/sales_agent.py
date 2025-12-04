import numpy as np
import copy # Used for safely updating state dictionary

class SalesAgent:
    
    def __init__(self, config=None):
        """Initializes the Sales Agent with business rules (Rule-Based Layer)."""
        # Hard Rule Limits (Policy Rules)
        self.BASE_RATE = 9.5         # Absolute minimum interest rate
        self.MAX_RATE = 18.0
        self.NEGOTIATION_DECREMENT = 0.5 # How much the rate drops upon negotiation
        self.DEFAULT_ALTERNATIVE_OFFER_FACTOR = 0.6 # Rule: 60% of original amount if rejected
        self.DEFAULT_TENURE_MONTHS = 36
        
        # --- AI MAPPING: Rule-Based Mapping of AI Risk Score ---
        # The AI risk score (0.0 to 1.0) maps directly to rate tiers.
        self.RISK_TIERS = {
            "low": 0.2,    # Score <= 0.2: Best rate
            "medium": 0.5, # Score <= 0.5: Standard rate
            "high": 0.8    # Score <= 0.8: High rate
        }

    def calculate_interest(self, risk_score: float) -> float:
        """
        AI + Rule-Based Interest Calculation. 
        Uses the AI-generated risk_score to determine the price tier.
        """
        # RULE: Check against risk tiers
        if risk_score <= self.RISK_TIERS["low"]:
            rate = self.BASE_RATE
        elif risk_score <= self.RISK_TIERS["medium"]:
            rate = self.BASE_RATE + 2.5 # E.g., 9.5 + 2.5 = 12.0%
        elif risk_score <= self.RISK_TIERS["high"]:
            rate = self.BASE_RATE + 5.5 # E.g., 9.5 + 5.5 = 15.0%
        else:
            rate = self.MAX_RATE
            
        # RULE: Final rate cannot exceed MAX_RATE
        return min(rate, self.MAX_RATE)

    def _calculate_emi(self, principal, rate_annual, tenure_months):
        """Helper function to calculate the Equated Monthly Installment (EMI)."""
        rate_monthly = (rate_annual / 12) / 100
        # Formula: P * r * (1+r)^n / ((1+r)^n - 1)
        if rate_monthly == 0: 
            return principal / tenure_months
        power_term = (1 + rate_monthly) ** tenure_months
        emi = principal * rate_monthly * power_term / (power_term - 1)
        return round(emi, 0)
    
    def format_offer_message(self, offer_type: str, **kwargs) -> dict:
        """
        Generates the final human-readable message and sets the action flag.
        """
        principal_formatted = f"₹{kwargs.get('principal', 0):,}"
        
        if offer_type == "approved":
            message = (
                f"Congratulations, {kwargs.get('name', 'Applicant')}! 🎉 Your loan for **{principal_formatted}** is pre-approved! "
                f"We are happy to offer you an interest rate of **{kwargs['rate']:.2f}%** per annum "
                f"for a tenure of **{kwargs['tenure']} years**. "
                f"Your estimated EMI is **₹{kwargs['emi']:,}**."
                f"\n\nDo you accept this offer to proceed to KYC?"
            )
            return {"message": message, "action": "wait_for_offer_decision", "interest_rate": kwargs['rate']}

        elif offer_type == "negotiated":
            message = (
                f"Great news! We have applied a policy discount. Your revised rate is **{kwargs['rate']:.2f}%** for a {kwargs['tenure']} year tenure, "
                f"which is the lowest we can offer you! "
                f"\n\nAccept this revised offer now?"
            )
            return {"message": message, "action": "wait_for_offer_decision", "interest_rate": kwargs['rate']}

        elif offer_type == "rejected_alternative":
            new_principal_formatted = f"₹{kwargs.get('new_principal', 0):,}"
            message = (
                f"Hello {kwargs.get('name', 'Applicant')}. While we couldn't approve your request for {principal_formatted}, "
                f"our Sales Agent has generated an **alternative offer** for you: "
                f"We can offer **{new_principal_formatted}** at **{kwargs['rate']:.2f}%** per annum. "
                f"\n\nWould you like to proceed with this alternative, lower amount?"
            )
            return {"message": message, "action": "wait_for_offer_decision", "interest_rate": kwargs['rate'], "new_amount": kwargs.get('new_principal')}
            
        elif offer_type == "rejected_final":
             message = (
                 f"We sincerely apologize, but based on your current financial profile and credit policy, "
                 f"we are unable to offer you a loan at this time, even with a reduced amount."
                 f"Thank you for considering CredGen. Goodbye."
             )
             return {"message": message, "action": "end_session", "interest_rate": kwargs['rate']}

        return {"message": "I'm having trouble calculating the offer. Please try again later.", "action": "end_session"}


    def generate_offer(self, master_agent_state: dict, negotiation_request: bool = False) -> dict:
        """Handles approval, negotiation, and rejection counseling."""
        # Use a copy to ensure we are working with the latest data, not directly mutating state
        entities = master_agent_state['entities']
        risk_score = master_agent_state['risk_score']
        principal = entities.get('loan_amount', 0)
        tenure = entities.get('tenure', self.DEFAULT_TENURE_MONTHS)
        underwriting_approved = master_agent_state.get('approval_status', False)

        # 1. Handle Hard Rejection (Rejection Counseling Logic)
        if not underwriting_approved:
            # Rule: Calculate the alternative offer amount (60% of original)
            new_principal = int(principal * self.DEFAULT_ALTERNATIVE_OFFER_FACTOR)
            interest_rate = self.calculate_interest(risk_score) 
            
            # Rule: Hard floor for alternative loan amount
            if new_principal < 50000: 
                return self.format_offer_message("rejected_final", principal=principal, rate=interest_rate)

            emi = self._calculate_emi(new_principal, interest_rate, tenure)

            return self.format_offer_message(
                offer_type="rejected_alternative",
                name=entities.get('name', 'Applicant'),
                principal=principal,
                new_principal=new_principal,
                tenure=tenure // 12,
                rate=interest_rate,
                emi=emi
            )

        # 2. Handle Standard Offer / Negotiation
        interest_rate = master_agent_state.get('interest_rate') # Use the rate set by UnderwritingAgent first
        
        # Rule: Negotiation Logic
        if negotiation_request:
            # Rule: Reduce rate by fixed decrement, but never below BASE_RATE
            negotiated_rate = interest_rate - self.NEGOTIATION_DECREMENT
            interest_rate = max(self.BASE_RATE, negotiated_rate) 
        
        emi = self._calculate_emi(principal, interest_rate, tenure)
        
        offer_type = "negotiated" if negotiation_request else "approved"
        
        # IMPORTANT: The Sales Agent updates the state (rate) for the Master Agent to use later
        if negotiation_request:
             master_agent_state['interest_rate'] = interest_rate
             
        return self.format_offer_message(
            offer_type=offer_type,
            name=entities.get('name', 'Applicant'),
            principal=principal,
            tenure=tenure // 12,
            rate=interest_rate,
            emi=emi
        )
