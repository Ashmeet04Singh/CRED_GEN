import re
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Tuple, Optional, Set
import logging
from enum import Enum

# Assuming utility functions work as intended from backend.utils.preprocess
from .utils.preprocess import (
    clean_text, extract_amount, extract_tenure, extract_age,
    extract_income, extract_name, extract_pan, extract_aadhaar,
    extract_pincode, extract_employment_type, extract_purpose,
    validate_amount, validate_age, validate_tenure
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationStage(Enum):
    GREETING = "greeting"
    COLLECTING = "collecting"
    UNDERWRITING = "underwriting"
    OFFER = "offer"
    REJECTION_COUNSELING = "rejection_counseling"
    KYC = "kyc"
    DOCUMENTATION = "documentation"
    CLOSED = "closed"
    FRAUD_CHECK = "fraud_check"

class IntentType(Enum):
    GREETING = "greeting"
    LOAN_APPLICATION = "loan_application"
    RATE_INQUIRY = "rate_inquiry"
    NEGOTIATE_TERMS = "negotiate_terms"
    ACCEPT_OFFER = "accept_offer"
    REJECT_OFFER = "reject_offer"
    HELP_GENERAL = "help_general"
    EXIT = "exit"
    UNCLEAR = "unclear"
    PROVIDE_INFO = "provide_info"

REQUIRED_FIELDS = ["name", "loan_amount", "tenure", "age", "income", "employment_type", "purpose"]
KYC_FIELDS = ["pan", "aadhaar", "pincode", "address"]

class MasterAgent:

    INTENT_TEMPLATES = {
        IntentType.GREETING: ["Hello", "Hi there", "Good morning", "Hey", "Greetings"],
        IntentType.LOAN_APPLICATION: ["I need a loan", "I want to apply for a loan",
                                      "Can I borrow money", "Give me a loan", "Loan application",
                                      "Apply for loan", "Need financing", "Looking for loan"],
        IntentType.RATE_INQUIRY: ["What is the interest rate", "How much interest will I pay",
                                  "Tell me about the rates", "Rate of interest", "What's the rate"],
        IntentType.NEGOTIATE_TERMS: ["Can you reduce the rate", "I want a better offer",
                                     "Lower the interest", "Can we negotiate", "Better terms"],
        IntentType.ACCEPT_OFFER: ["I accept the offer", "Yes I agree", "Proceed with the loan",
                                  "Approved", "I'll take it", "Let's proceed", "Yes please"],
        IntentType.REJECT_OFFER: ["I reject this offer", "No thanks", "Not interested",
                                  "I decline", "Not now", "Maybe later", "I refuse"],
        IntentType.HELP_GENERAL: ["I need help", "How does this work", "Explain the process",
                                  "Help me", "What can you do", "Tell me more"],
        IntentType.EXIT: ["Goodbye", "Exit", "Stop", "End chat", "Bye", "Close", "Quit"],
        IntentType.PROVIDE_INFO: ["My name is", "I am", "My income is", "I want",
                                  "I need", "My age is", "Here is my", "I work as"]
    }

    # Context-aware responses for different stages
    STAGE_RESPONSES = {
        ConversationStage.GREETING: [
            "Hello! I'm CredGen, your AI-powered loan assistant. How can I help you today?",
            "Welcome to CredGen! I'm here to guide you through your loan application. What can I do for you?",
            "Hi there! Ready to find the perfect loan for you. How can I assist?"
        ],
        ConversationStage.COLLECTING: [
            "To proceed with your application, I need some basic information:",
            "Great! Let me gather some details to process your loan request:",
            "I'll help you apply. First, I need to collect some information:"
        ],
        ConversationStage.OFFER: [
            "Based on your profile, here's our offer:",
            "Great news! I have a loan offer for you:",
            "Here's what we can offer based on your application:"
        ]
    }

    def __init__(self, model_name='paraphrase-MiniLM-L6-v2'):
        """Initialize master agent with AI model and empty state"""
        self.state = self._initialize_state()
        self.conversation_history = []
        self.model_name = model_name

        try:
            # Initialize with a lighter model for better performance
            self.intent_model = SentenceTransformer(model_name)
            self._compute_embeddings()
            logger.info(f"AI Master Agent initialized with {model_name} ✅")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            self.intent_model = None

        # Initialize intent cache for faster processing
        self.intent_cache = {}

    def _initialize_state(self) -> Dict:
        """Create fresh state for new user session"""
        return {
            "stage": ConversationStage.GREETING,
            "last_intent": None,
            "entities": {field: None for field in REQUIRED_FIELDS + KYC_FIELDS},
            "risk_score": None,
            "approval_status": None,
            "interest_rate": None,
            "offer_accepted": False,
            "missing_fields": set(REQUIRED_FIELDS).copy(),
            "missing_kyc_fields": set(KYC_FIELDS).copy(),
            "current_offer": None,
            "conversation_start_time": time.time(),
            "attempts": 0,
            "fraud_check_passed": False
        }

    def _compute_embeddings(self):
        """Pre-compute and store average embeddings for all intent templates."""
        self.intent_embeddings = {}
        for intent, templates in self.INTENT_TEMPLATES.items():
            embeddings = self.intent_model.encode(templates, convert_to_numpy=True)
            mean_embedding = np.mean(embeddings, axis=0)
            self.intent_embeddings[intent] = mean_embedding / np.linalg.norm(mean_embedding)

    def detect_intent(self, text: str) -> Tuple[IntentType, float]:
        """
        AI-powered intent detection with fallback rules and context awareness.
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (intent_type, confidence_score)
        """
        # Check cache first for performance
        cache_key = hash(text.lower().strip())
        if cache_key in self.intent_cache:
            return self.intent_cache[cache_key]

        text = clean_text(text)

        # Fallback if AI model is not available
        if not self.intent_model:
            logger.warning("AI model not available, using rule-based intent detection")
            return self._rule_based_intent_detection(text), 0.6

        # 1. AI-based similarity detection
        try:
            user_embedding = self.intent_model.encode(text)
            user_embedding_norm = user_embedding / np.linalg.norm(user_embedding)

            similarities = {}
            for intent, template_embedding in self.intent_embeddings.items():
                similarity = np.dot(user_embedding_norm, template_embedding)
                similarities[intent] = similarity

            # 2. Context-aware boosting
            boosted_similarities = self._apply_context_boosting(similarities)

            # 3. Find best intent
            best_intent = max(boosted_similarities, key=boosted_similarities.get)
            confidence = boosted_similarities[best_intent]

            # 4. Validate with rules
            validated_intent, validated_confidence = self._validate_intent_with_rules(
                text, best_intent, confidence
            )

            # Cache result
            self.intent_cache[cache_key] = (validated_intent, validated_confidence)

            return validated_intent, validated_confidence

        except Exception as e:
            logger.error(f"Error in AI intent detection: {e}")
            return self._rule_based_intent_detection(text), 0.5

    def _apply_context_boosting(self, similarities: Dict[IntentType, float]) -> Dict[IntentType, float]:
        """Apply context-aware boosting to intent similarities."""
        stage = self.state["stage"]
        boosted = similarities.copy()

        # Context-specific boosting
        boost_rules = {
            ConversationStage.OFFER: {
                IntentType.ACCEPT_OFFER: 1.4,
                IntentType.REJECT_OFFER: 1.4,
                IntentType.NEGOTIATE_TERMS: 1.3
            },
            ConversationStage.REJECTION_COUNSELING: {
                IntentType.LOAN_APPLICATION: 1.3,
                IntentType.NEGOTIATE_TERMS: 1.2
            },
            ConversationStage.KYC: {
                IntentType.PROVIDE_INFO: 1.3
            }
        }

        for intent, factor in boost_rules.get(stage, {}).items():
            if intent in boosted:
                boosted[intent] *= factor

        # Boost based on previous intent
        if self.state["last_intent"] == IntentType.LOAN_APPLICATION:
            boosted[IntentType.PROVIDE_INFO] *= 1.2

        return boosted

    def _validate_intent_with_rules(self, text: str, ai_intent: IntentType,
                                   confidence: float) -> Tuple[IntentType, float]:
        """Validate AI intent with rule-based checks."""

        # Rule 1: Check for information provision
        info_keywords = ["my", "is", "I am", "I have", "I work", "income", "age", "name"]
        if any(keyword in text.lower() for keyword in info_keywords):
            entities = self.extract_entities(text)
            if any(entities.values()):
                return IntentType.PROVIDE_INFO, max(confidence, 0.7)

        # Rule 2: Low confidence threshold
        if confidence < 0.4:
            entities = self.extract_entities(text)
            if any(entities.values()):
                return IntentType.LOAN_APPLICATION, 0.7

        # Rule 3: Check for explicit exit phrases
        exit_phrases = ["goodbye", "bye", "exit", "stop", "end", "close", "quit"]
        if any(phrase in text.lower() for phrase in exit_phrases):
            return IntentType.EXIT, 0.9

        # Rule 4: Check for question patterns
        question_patterns = ["what", "how", "when", "where", "why", "can you", "could you"]
        if any(pattern in text.lower() for pattern in question_patterns):
            if "rate" in text.lower() or "interest" in text.lower():
                return IntentType.RATE_INQUIRY, max(confidence, 0.8)
            return IntentType.HELP_GENERAL, max(confidence, 0.7)

        return ai_intent, confidence

    def _rule_based_intent_detection(self, text: str) -> IntentType:
        """Fallback rule-based intent detection when AI is unavailable."""
        text_lower = text.lower()

        if any(greet in text_lower for greet in ["hello", "hi", "hey", "greetings"]):
            return IntentType.GREETING

        if any(loan_word in text_lower for loan_word in ["loan", "borrow", "apply", "need money"]):
            return IntentType.LOAN_APPLICATION

        if any(rate_word in text_lower for rate_word in ["rate", "interest", "percent"]):
            return IntentType.RATE_INQUIRY

        if any(nego_word in text_lower for nego_word in ["negotiate", "lower", "reduce", "better"]):
            return IntentType.NEGOTIATE_TERMS

        if any(accept_word in text_lower for accept_word in ["accept", "yes", "agree", "proceed"]):
            return IntentType.ACCEPT_OFFER

        if any(reject_word in text_lower for reject_word in ["reject", "no", "decline", "not interested"]):
            return IntentType.REJECT_OFFER

        if any(help_word in text_lower for help_word in ["help", "how", "explain", "what"]):
            return IntentType.HELP_GENERAL

        if any(exit_word in text_lower for exit_word in ["exit", "bye", "goodbye", "stop"]):
            return IntentType.EXIT

        # Check if user is providing information
        entities = self.extract_entities(text)
        if any(entities.values()):
            return IntentType.PROVIDE_INFO

        return IntentType.UNCLEAR

    def extract_entities(self, text: str) -> Dict[str, Optional[str]]:
        """Advanced entity extraction with validation and context awareness."""
        entities = {}
        text_lower = text.lower()

        # Extract with validation
        extraction_functions = [
            (extract_amount, "loan_amount", validate_amount),
            (extract_tenure, "tenure", validate_tenure),
            (extract_age, "age", validate_age),
            (extract_income, "income", None),
            (extract_name, "name", None),
            (extract_employment_type, "employment_type", None),
            (extract_purpose, "purpose", None),
            (extract_pan, "pan", None),
            (extract_aadhaar, "aadhaar", None),
            (extract_pincode, "pincode", None)
        ]

        for extract_func, field, validate_func in extraction_functions:
            try:
                value = extract_func(text)
                if value:
                    if validate_func:
                        if validate_func(value):
                            entities[field] = value
                    else:
                        entities[field] = value
            except Exception as e:
                logger.warning(f"Error extracting {field}: {e}")

        # Address extraction with pattern matching
        address_patterns = [
            r'address[:\s]+(.+?)(?:\.|,|$)',
            r'live[:\s]+(.+?)(?:\.|,|$)',
            r'located[:\s]+(.+?)(?:\.|,|$)',
            r'resid(?:ence|ing)[:\s]+(.+?)(?:\.|,|$)'
        ]

        for pattern in address_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["address"] = match.group(1).strip().title()
                break

        return entities

    def update_state(self, entities: Dict, intent: IntentType):
        """Advanced state management with validation and logging."""

        # Update entities
        for key, value in entities.items():
            if value is not None:
                old_value = self.state["entities"][key]
                self.state["entities"][key] = value

                # Update missing fields
                if key in self.state["missing_fields"]:
                    self.state["missing_fields"].remove(key)
                    logger.info(f"Collected required field: {key}")

                if key in self.state["missing_kyc_fields"]:
                    self.state["missing_kyc_fields"].remove(key)
                    logger.info(f"Collected KYC field: {key}")

                # Log if value changed
                if old_value != value:
                    logger.info(f"Updated {key}: {old_value} -> {value}")

        # Update last intent
        self.state["last_intent"] = intent

        # Track attempts
        self.state["attempts"] += 1

        # State machine transitions
        self._handle_state_transition(intent)

        # Log state change
        logger.info(f"State updated: {self.state['stage'].value}, intent: {intent.value}")

    def _handle_state_transition(self, intent: IntentType):
        """Handle state transitions based on intent and current state."""
        current_stage = self.state["stage"]

        # State transition rules
        transition_rules = {
            ConversationStage.GREETING: {
                IntentType.LOAN_APPLICATION: ConversationStage.COLLECTING,
                IntentType.PROVIDE_INFO: ConversationStage.COLLECTING,
            },
            ConversationStage.COLLECTING: {
                "all_fields_collected": ConversationStage.UNDERWRITING,
                IntentType.LOAN_APPLICATION: ConversationStage.COLLECTING,
                IntentType.PROVIDE_INFO: ConversationStage.COLLECTING,
            },
            ConversationStage.OFFER: {
                IntentType.ACCEPT_OFFER: ConversationStage.KYC,
                IntentType.REJECT_OFFER: ConversationStage.CLOSED,
                IntentType.NEGOTIATE_TERMS: ConversationStage.OFFER,  # Stay in offer for negotiation
            },
            ConversationStage.REJECTION_COUNSELING: {
                IntentType.LOAN_APPLICATION: ConversationStage.COLLECTING,
                IntentType.NEGOTIATE_TERMS: ConversationStage.COLLECTING,
            },
            ConversationStage.KYC: {
                "kyc_complete": ConversationStage.FRAUD_CHECK,
                IntentType.PROVIDE_INFO: ConversationStage.KYC,
            },
            ConversationStage.FRAUD_CHECK: {
                "fraud_passed": ConversationStage.DOCUMENTATION,
            },
        }

        # Check for special conditions first
        if current_stage == ConversationStage.COLLECTING and not self.state["missing_fields"]:
            self.state["stage"] = ConversationStage.UNDERWRITING
            return

        if current_stage == ConversationStage.KYC and not self.state["missing_kyc_fields"]:
            self.state["stage"] = ConversationStage.FRAUD_CHECK
            return

        # Apply intent-based transitions
        stage_rules = transition_rules.get(current_stage, {})
        if intent in stage_rules:
            self.state["stage"] = stage_rules[intent]
        elif "default" in stage_rules:
            self.state["stage"] = stage_rules["default"]

    def route_to_worker(self, intent: IntentType) -> str:
        """Intelligent routing to specialized worker agents."""
        stage = self.state["stage"]

        routing_map = {
            ConversationStage.UNDERWRITING: "underwriting",
            ConversationStage.REJECTION_COUNSELING: "sales",
            ConversationStage.OFFER: {
                IntentType.RATE_INQUIRY: "sales",
                IntentType.NEGOTIATE_TERMS: "sales",
                "default": "none"
            },
            ConversationStage.FRAUD_CHECK: "fraud",
            ConversationStage.DOCUMENTATION: "documentation",
        }

        # Get routing for current stage
        stage_routing = routing_map.get(stage, "none")

        if isinstance(stage_routing, dict):
            # Stage has intent-specific routing
            return stage_routing.get(intent, stage_routing.get("default", "none"))

        return stage_routing

    def generate_response(self, intent: IntentType, confidence: float) -> Dict:
        """Generate context-aware, natural responses."""
        stage = self.state["stage"]

        # Handle terminal states
        if stage == ConversationStage.CLOSED:
            return {
                "message": "Thank you for considering CredGen. Feel free to reach out if you need assistance in the future. Have a great day!",
                "terminate": True
            }

        if stage == ConversationStage.DOCUMENTATION:
            return {
                "message": "✅ All checks complete! Please proceed with the final documentation step to generate your Sanction Letter.",
                "terminate": False,
                "next_action": "documentation"
            }

        # Stage-specific responses
        if stage == ConversationStage.OFFER or stage == ConversationStage.REJECTION_COUNSELING:
            if self.state["current_offer"]:
                return self.state["current_offer"]

        # Generate stage-appropriate responses
        response_templates = {
            ConversationStage.GREETING: self._get_random_response(ConversationStage.GREETING),
            ConversationStage.COLLECTING: self._generate_collecting_response(),
            ConversationStage.KYC: self._generate_kyc_response(),
            ConversationStage.UNDERWRITING: {
                "message": "🔍 Processing your application... This will take just a moment.",
                "terminate": False,
                "processing": True
            },
            ConversationStage.FRAUD_CHECK: {
                "message": "🛡️ Running security verification...",
                "terminate": False,
                "processing": True
            }
        }

        # Get stage response or default
        response = response_templates.get(stage, {})
        if response:
            return response

        # Intent-specific responses
        intent_responses = {
            IntentType.HELP_GENERAL: {
                "message": "I can help you with:\n• Loan applications\n• Interest rate inquiries\n• Document collection\n• Application status\nWhat would you like to know?"
            },
            IntentType.RATE_INQUIRY: {
                "message": "Our interest rates range from 8.5% to 15% based on your credit profile. Would you like to check what rate you qualify for?"
            },
            IntentType.UNCLEAR: {
                "message": "I didn't quite understand. Could you please rephrase or tell me if you'd like to:\n1. Apply for a loan\n2. Check interest rates\n3. Get help with an existing application"
            }
        }

        return intent_responses.get(intent, {
            "message": "How can I assist you further with your loan application?",
            "terminate": False
        })

    def _generate_collecting_response(self) -> Dict:
        """Generate response for information collection stage."""
        if not self.state["missing_fields"]:
            return {
                "message": "✅ Great! I have all the basic details. Processing your application now...",
                "terminate": False,
                "processing": True
            }

        missing_list = list(self.state["missing_fields"])
        priority_fields = ["loan_amount", "income", "age"]

        missing_fields_sorted = sorted(
            missing_list,
            key=lambda x: priority_fields.index(x) if x in priority_fields else len(priority_fields)
        )

        next_field = missing_fields_sorted[0]
        prompts = {
            "loan_amount": "How much loan amount are you looking for?",
            "income": "What is your annual/monthly income?",
            "age": "What is your age?",
            "name": "What is your full name?",
            "tenure": "For how many months/years would you like the loan?",
            "employment_type": "What is your employment type? (Salaried/Self-employed/Business)",
            "purpose": "What will you use the loan for? (e.g., Home, Car, Education)"
        }

        default_msg = f"Please provide your {next_field.replace('_', ' ')}"
        return {
            "message": f"To proceed, {prompts.get(next_field, default_msg)}",
            "terminate": False,
            "missing_field": next_field
        }

    def _generate_kyc_response(self) -> Dict:
        """Generate response for KYC collection stage."""
        if not self.state["missing_kyc_fields"]:
            return {
                "message": "✅ All KYC details collected. Running final checks...",
                "terminate": False,
                "processing": True
            }

        missing_kyc = list(self.state["missing_kyc_fields"])
        kyc_prompts = {
            "pan": "Please provide your PAN card number",
            "aadhaar": "Please provide your Aadhaar number",
            "pincode": "What is your pincode?",
            "address": "Please provide your complete address"
        }

        next_kyc = missing_kyc[0]
        return {
            "message": f"For KYC verification: {kyc_prompts.get(next_kyc, f'Please provide your {next_kyc}')}",
            "terminate": False,
            "missing_field": next_kyc
        }

    def _get_random_response(self, stage: ConversationStage) -> str:
        """Get a random response from stage templates."""
        import random
        responses = self.STAGE_RESPONSES.get(stage, ["How can I help you?"])
        return random.choice(responses)

    # --- Integration Methods for Worker Agents ---

    def set_underwriting_result(self, risk_score: float, approval_status: bool,
                               interest_rate: float = None, offer_details: Dict = None):
        """Called by Underwriting Agent with results."""
        self.state["risk_score"] = risk_score
        self.state["approval_status"] = approval_status
        self.state["interest_rate"] = interest_rate

        if approval_status:
            self.state["stage"] = ConversationStage.OFFER
            if offer_details:
                self.state["current_offer"] = offer_details
        else:
            self.state["stage"] = ConversationStage.REJECTION_COUNSELING

        logger.info(f"Underwriting result: approval={approval_status}, risk={risk_score}")

    def set_fraud_check_result(self, passed: bool, details: Dict = None):
        """Called by Fraud Check Agent."""
        self.state["fraud_check_passed"] = passed
        if passed:
            self.state["stage"] = ConversationStage.DOCUMENTATION
        else:
            self.state["stage"] = ConversationStage.CLOSED
            self.state["current_offer"] = {
                "message": "⚠️ We couldn't proceed with your application due to verification issues.",
                "terminate": True
            }

        logger.info(f"Fraud check result: passed={passed}")

    def reset_conversation(self):
        """Reset the conversation for a new user."""
        self.state = self._initialize_state()
        self.conversation_history = []
        self.intent_cache.clear()
        logger.info("Conversation reset")

    def handle(self, user_input: str) -> Dict:
        """
        Main handler for user input.
        
        Args:
            user_input: User's message
            
        Returns:
            Response dictionary with message, worker routing, and metadata
        """
        try:
            # Add to conversation history
            self.conversation_history.append({"user": user_input, "timestamp": time.time()})

            # Detect intent
            intent, confidence = self.detect_intent(user_input)

            # Extract entities
            entities = self.extract_entities(user_input)

            # Update state
            self.update_state(entities, intent)

            # Determine worker routing
            worker = self.route_to_worker(intent)

            # Generate response
            response = self.generate_response(intent, confidence)

            # Prepare final response
            result = {
                "message": response.get("message", "How can I assist you?"),
                "worker": worker,
                "intent": intent.value,
                "stage": self.state["stage"].value,
                "confidence": float(confidence),
                "entities_collected": {k: v for k, v in self.state["entities"].items() if v},
                "missing_fields": list(self.state["missing_fields"]),
                "missing_kyc_fields": list(self.state["missing_kyc_fields"]),
                "terminate": response.get("terminate", False)
            }

            # Add processing flag if needed
            if response.get("processing"):
                result["processing"] = True

            # Add next action if specified
            if response.get("next_action"):
                result["next_action"] = response["next_action"]

            logger.info(f"Handled input: intent={intent.value}, stage={self.state['stage'].value}")

            return result

        except Exception as e:
            logger.error(f"Error in handle method: {e}")
            return {
                "message": "I encountered an error. Please try again or contact support.",
                "worker": "none",
                "intent": "error",
                "stage": self.state["stage"].value,
                "terminate": False
            }
