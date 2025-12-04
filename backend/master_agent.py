import re
import numpy as np
from sentence_transformers import SentenceTransformer 
# Assuming utility functions work as intended from backend.utils.preprocess
from backend.utils.preprocess import ( 
    clean_text, extract_amount, extract_tenure, extract_age,
    extract_income, extract_name, extract_pan, extract_aadhaar,
    extract_pincode, extract_employment_type, extract_purpose,
    validate_amount, validate_age, validate_tenure
)

REQUIRED_FIELDS = ["name", "loan_amount", "tenure", "age", "income", "employment_type", "purpose"]
KYC_FIELDS = ["pan", "aadhaar", "pincode", "address"]

class MasterAgent:
    
    INTENT_TEMPLATES = {
        "greeting": ["Hello", "Hi there", "Good morning", "Hey"],
        "loan_application": ["I need a loan", "I want to apply for a loan", "Can I borrow money", "Give me a loan"],
        "rate_inquiry": ["What is the interest rate", "How much interest will I pay", "Tell me about the rates"],
        "negotiate_terms": ["Can you reduce the rate", "I want a better offer", "Lower the interest"],
        "accept_offer": ["I accept the offer", "Yes I agree", "Proceed with the loan", "Approved"],
        "reject_offer": ["I reject this offer", "No thanks", "Not interested"],
        "help_general": ["I need help", "How does this work", "Explain the process"],
        "exit": ["Goodbye", "Exit", "Stop", "End chat"]
    }

    def __init__(self):
        """Initialize master agent with AI model and empty state"""
        self.state = self._initialize_state()
        
        # --- AI COMPONENT: Sentence Transformer for Intent ---
        try:
            # Use a tiny, fast model for local setup
            self.intent_model = SentenceTransformer('paraphrase-MiniLM-L6-v2') 
            self._compute_embeddings()
            print("AI Master Agent ready! ✅")
        except Exception as e:
            print(f"Failed to load SentenceTransformer: {e}. AI intent will not function.")
            self.intent_model = None
    
    def _compute_embeddings(self):
        """Pre-compute and store average embeddings for all intent templates."""
        self.intent_embeddings = {}
        for intent, templates in self.INTENT_TEMPLATES.items():
            embeddings = self.intent_model.encode(templates, convert_to_numpy=True)
            mean_embedding = np.mean(embeddings, axis=0)
            self.intent_embeddings[intent] = mean_embedding / np.linalg.norm(mean_embedding)
    
    def _initialize_state(self):
        """Create fresh state for new user session"""
        return {
            "stage": "greeting",
            "last_intent": None,
            "entities": {field: None for field in REQUIRED_FIELDS + KYC_FIELDS + ["address"]},
            "risk_score": None,
            "approval_status": None,
            "interest_rate": None,
            "offer_accepted": False,
            "missing_fields": set(REQUIRED_FIELDS).copy(),
            "current_offer": None # To hold the formatted offer message from SalesAgent
        }
    
    def detect_intent(self, text):
        """AI-powered intent detection using semantic similarity with Contextual Boosting (Rule-Based)."""
        if not self.intent_model:
            return "unclear", 0.0 # Fallback if AI failed to load
            
        text = clean_text(text)
        user_embedding_norm = self.intent_model.encode(text) / np.linalg.norm(self.intent_model.encode(text))
        
        similarities = {}
        for intent, template_embedding in self.intent_embeddings.items():
            similarity = np.dot(user_embedding_norm, template_embedding)
            similarities[intent] = similarity
        
        # --- RULE-BASED: Contextual Intent Boosting ---
        stage = self.state["stage"]
        boost_factors = {}
        if stage == "offer":
            boost_factors = {"accept_offer": 1.3, "reject_offer": 1.3, "negotiate_terms": 1.2}
            
        for intent, factor in boost_factors.items():
            if intent in similarities:
                similarities[intent] *= factor 
        
        best_intent = max(similarities, key=similarities.get)
        confidence = similarities[best_intent]
        
        # RULE: Low Confidence Threshold
        if confidence < 0.4:
            entities = self.extract_entities(text)
            if any(entities.values()):
                return "loan_application", 0.7 
            return "unclear", confidence 
        
        return best_intent, confidence
    
    def extract_entities(self, text):
        """Reliable Regex-based Entity Extraction."""
        entities = {}
        # NOTE: Using placeholder logic for brevity, assuming utility functions are robust.
        if (amount := extract_amount(text)) and validate_amount(amount): entities["loan_amount"] = amount
        if (tenure := extract_tenure(text)) and validate_tenure(tenure): entities["tenure"] = tenure
        if (age := extract_age(text)) and validate_age(age): entities["age"] = age
        if income := extract_income(text): entities["income"] = income
        if name := extract_name(text): entities["name"] = name
        if employment := extract_employment_type(text): entities["employment_type"] = employment
        if purpose := extract_purpose(text): entities["purpose"] = purpose
        if pan := extract_pan(text): entities["pan"] = pan
        if aadhaar := extract_aadhaar(text): entities["aadhaar"] = aadhaar
        if pincode := extract_pincode(text): entities["pincode"] = pincode
        if "address" in text.lower():
            address_pattern = r'address[:\s]+(.+?)(?:\.|,|$)'
            match = re.search(address_pattern, text.lower())
            if match: entities["address"] = match.group(1).strip().title()
        
        return entities
    
    def update_state(self, entities, intent):
        """Rule-Based State Transition Logic."""
        for key, value in entities.items():
            if value is not None:
                self.state["entities"][key] = value
                if key in self.state["missing_fields"]: self.state["missing_fields"].remove(key)
        
        self.state["last_intent"] = intent
        
        # State transition rules
        if self.state["stage"] == "greeting" and intent == "loan_application":
            self.state["stage"] = "collecting"
        
        elif self.state["stage"] == "collecting" and not self.state["missing_fields"]:
            self.state["stage"] = "underwriting"
        
        elif self.state["stage"] == "offer":
            if intent == "accept_offer":
                self.state["offer_accepted"] = True
                self.state["stage"] = "kyc"
            elif intent == "reject_offer":
                self.state["stage"] = "closed"
        
        elif self.state["stage"] == "rejection_counseling" and intent in ["loan_application", "negotiate_terms"]:
            self.state["stage"] = "collecting"
        
        elif self.state["stage"] == "kyc" and intent in ["accept_offer", "loan_application"]:
             # If user provides data during KYC stage, check if it's complete
             kyc_complete = all(self.state["entities"][field] for field in KYC_FIELDS)
             if kyc_complete and self.state["offer_accepted"]:
                 self.state["stage"] = "documentation"
            
    def route_to_worker(self, intent):
        """Rule-Based Routing."""
        if self.state["stage"] == "underwriting": return "underwriting"
        if self.state["stage"] == "rejection_counseling": return "sales"
        if self.state["stage"] == "offer" and intent in ["rate_inquiry", "negotiate_terms"]: return "sales"
        
        # Routing to fraud check after KYC is fully collected and offer accepted
        kyc_complete = all(self.state["entities"][field] for field in KYC_FIELDS)
        if self.state["stage"] == "kyc" and kyc_complete and self.state["offer_accepted"]:
             # Since 'documentation' is the final stage, we skip the fraud agent routing 
             # and route to documentation directly, simplifying the flow.
             self.state["stage"] = "documentation"
             return "documentation"
        
        if self.state["stage"] == "documentation": return "documentation"
            
        return "none"
    
    # --- Generate Response Logic ---
    def generate_response(self, intent, confidence):
        """Rule-Based generation of conversational text."""
        stage = self.state["stage"]
        
        # Final closure messages
        if stage == "closed":
            return {"message": "Thank you for considering CredGen. The conversation is now closed."}
        
        if stage == "documentation":
             # This message is returned just before the frontend calls the final API
             return {"message": "All set! Please proceed with the final documentation step to generate your Sanction Letter."}

        # Stage: Offer or Rejection Counseling
        if stage == "offer" or stage == "rejection_counseling":
            if self.state["current_offer"]:
                # If SalesAgent already generated a message, use it directly (this bypasses chat API)
                return self.state["current_offer"]
            
        # Stage: Collecting
        if stage == "collecting":
            if intent == "loan_application" or any(self.state["entities"].values()):
                missing_str = ", ".join([f for f in self.state["missing_fields"]])
                
                if not self.state["missing_fields"]:
                    return {"message": "Great! We have all the basic details. Please wait while we run the Underwriting check. This will only take a moment."}
                
                return {"message": f"To proceed with your application, I still need the following details: **{missing_str.title()}**."}

        # Stage: KYC Collection
        if stage == "kyc":
             missing_kyc = [f for f in KYC_FIELDS if self.state["entities"][f] is None]
             if missing_kyc:
                 missing_str = ", ".join([f for f in missing_kyc])
                 return {"message": f"Perfect! You accepted the offer. Now, please provide the remaining KYC details: **{missing_str.upper()}**."}
             else:
                 return {"message": "Thank you. All KYC details are collected. Proceeding to final documentation."}


        # General intents
        if intent == "greeting":
            return {"message": "Hello! I am CredGen, your personal loan agent. How can I help you start your application today?"}
        
        if intent == "help_general":
            return {"message": "I can guide you through the loan application, offer generation, and documentation. Just tell me what you need, or start by asking for a loan!"}
        
        # Default response
        return {"message": "I'm sorry, I didn't quite catch that. Could you please rephrase or tell me more about your loan requirements?"}

    # --- Integration Callbacks (Used by Worker Agents) ---
    def set_underwriting_result(self, risk_score, approval_status, interest_rate):
        self.state["risk_score"] = risk_score
        self.state["interest_rate"] = interest_rate
        self.state["approval_status"] = approval_status
        
        if approval_status:
            self.state["stage"] = "offer"
        else:
            self.state["stage"] = "rejection_counseling"
    
    def set_offer(self, offer_details):
        self.state["current_offer"] = offer_details
        # NOTE: Stage is usually set by underwriting, this callback just updates the content

    def handle(self, user_input):
        """
        Main handler called by backend/app.py
        """
        try:
            intent, confidence = self.detect_intent(user_input)
        except Exception:
            intent, confidence = "unclear", 0.0 
        
        entities = self.extract_entities(user_input)
        
        # Crucial step: Updates state, checks for missing fields, and handles stage transition
        self.update_state(entities, intent) 
        
        # Determine if a worker agent needs to be called
        worker = self.route_to_worker(intent)
        
        # Generate the appropriate conversational message
        response = self.generate_response(intent, confidence)
        
        # Package the response for app.py
        response["worker"] = worker
        response["intent"] = intent
        response["stage"] = self.state["stage"]
        
        return response
