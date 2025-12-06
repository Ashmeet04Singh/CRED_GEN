from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import time  # Added missing import
from datetime import datetime
import threading
import json

# Import the core agents
from backend.master_agent import MasterAgent
from backend.underwriting_agent import UnderwritingAgent
from backend.sales_agent import SalesAgent
from backend.fraud_detection import FraudAgent

# --- 1. Initialization ---
app = Flask(__name__)
CORS(app)

# Session management with expiration
user_sessions = {}
SESSION_TIMEOUT = 1800  # 30 minutes in seconds

# Initialize agents
master_agent = MasterAgent()
underwriting_agent = UnderwritingAgent()
sales_agent = SalesAgent()
fraud_agent = FraudAgent()

# Cleanup thread for expired sessions
def cleanup_sessions():
    """Periodically clean up expired sessions"""
    while True:
        time.sleep(300)  # Run every 5 minutes
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session_data in user_sessions.items():
            if current_time - session_data.get('last_activity', 0) > SESSION_TIMEOUT:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del user_sessions[session_id]
            print(f"Cleaned up expired session: {session_id}")

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
cleanup_thread.start()

# --- Utility Functions ---

def get_session_id(request):
    """Retrieve or create a session ID with validation."""
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id:
        # Generate new session ID
        session_id = f"session_{uuid.uuid4().hex[:16]}"
    
    return session_id

def update_session_activity(session_id):
    """Update last activity time for session."""
    if session_id in user_sessions:
        user_sessions[session_id]['last_activity'] = time.time()

def initialize_user_session(session_id):
    """Initialize a new session for a user."""
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            'master_agent': MasterAgent(),  # Create new instance per session
            'last_activity': time.time(),
            'created_at': datetime.now().isoformat(),
            'interaction_count': 0
        }
    
    update_session_activity(session_id)
    return user_sessions[session_id]

def generate_sanction_letter(state: dict) -> dict:
    """Generate the final sanction letter with all details."""
    entities = state.get('entities', {})
    current_offer = state.get('current_offer', {})
    
    # Extract data with fallbacks
    loan_amount = entities.get('loan_amount', 0)
    interest_rate = current_offer.get('interest_rate', state.get('interest_rate', 'N/A'))
    
    if isinstance(interest_rate, (int, float)):
        rate_str = f"{interest_rate:.2f}%"
        emi = current_offer.get('monthly_emi', calculate_emi(loan_amount, interest_rate, entities.get('tenure', 60)))
    else:
        rate_str = str(interest_rate)
        emi = "N/A"
    
    name = entities.get('name', 'Applicant')
    tenure = entities.get('tenure', 60)
    date_today = datetime.now().strftime("%B %d, %Y")
    
    letter_content = f"""
CREDGEN FINANCIAL SERVICES
==========================
SANCTION LETTER

Date: {date_today}
Sanction Letter No: SL-{uuid.uuid4().hex[:8].upper()}

Dear {name},

We are pleased to inform you that your loan application has been APPROVED.

Loan Details:
-------------
• Sanctioned Amount: ₹{loan_amount:,}
• Interest Rate: {rate_str}
• Loan Tenure: {tenure} months
• Monthly EMI: ₹{emi:, if isinstance(emi, (int, float)) else emi}
• Processing Fee: ₹{max(1000, loan_amount * 0.01):,}
• Disbursement Date: Within 3 working days

Terms & Conditions:
-------------------
1. This sanction is valid for 30 days from the date of issue.
2. Final disbursement is subject to document verification.
3. Rate of interest is subject to change as per market conditions.
4. Penalty for late payment: 2% per month.

Please sign and return this letter to proceed with disbursement.

For CredGen Financial Services,
[Authorized Signatory]

This is a computer-generated letter and does not require a signature.
"""
    
    return {
        'content': letter_content,
        'metadata': {
            'sanction_id': f"SL-{uuid.uuid4().hex[:8].upper()}",
            'date': date_today,
            'applicant': name,
            'amount': loan_amount,
            'interest_rate': rate_str,
            'tenure': tenure
        }
    }

def calculate_emi(principal, rate, tenure_months):
    """Calculate EMI (simplified)."""
    if tenure_months <= 0:
        return 0
    monthly_rate = rate / 12 / 100
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
    return round(emi, 2)

# --- Frontend Routes ---

@app.route('/')
def index():
    """Serve the main frontend page."""
    return send_from_directory('frontend', 'index.html')

@app.route('/widget.html')
def widget():
    """Serve the widget page for 3rd party embedding."""
    return send_from_directory('frontend', 'widget.html')

@app.route('/frontend/<path:filename>')
def frontend_files(filename):
    """Serve static frontend files (CSS, JS, etc.)."""
    return send_from_directory('frontend', filename)

# --- API Endpoints ---

@app.route('/chat', methods=['POST'])
def chat():
    """
    Primary conversational endpoint.
    """
    try:
        session_id = get_session_id(request)
        data = request.get_json()
        user_input = data.get('message', '').strip()
        
        if not user_input:
            return jsonify({
                'message': 'Please provide a message.',
                'error': 'empty_input'
            }), 400
        
        # Initialize or retrieve session
        session = initialize_user_session(session_id)
        session['interaction_count'] += 1
        
        # Get the user's master agent instance
        user_master_agent = session['master_agent']
        
        # Process the input
        response = user_master_agent.handle(user_input)
        
        # Update session state
        session['last_state'] = user_master_agent.state.copy()
        
        # Check if worker needs to be called
        worker_name = response.get('worker')
        
        # Convert worker names to actions
        action_map = {
            'underwriting': 'call_underwriting_api',
            'sales': 'call_sales_api',
            'fraud': 'call_fraud_api',
            'documentation': 'call_documentation_api'
        }
        
        if worker_name in action_map:
            response['action'] = action_map[worker_name]
            response['session_id'] = session_id
        
        # Add session info to response
        response['session_id'] = session_id
        response['interaction_count'] = session['interaction_count']
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in /chat: {e}")
        return jsonify({
            'message': 'Sorry, I encountered an error. Please try again.',
            'error': 'server_error',
            'worker': 'none'
        }), 500

@app.route('/underwrite', methods=['POST'])
def underwrite():
    """
    Worker endpoint for underwriting process.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in user_sessions:
            return jsonify({'error': 'Invalid or expired session.'}), 400
        
        session = user_sessions[session_id]
        update_session_activity(session_id)
        
        user_master_agent = session['master_agent']
        current_state = user_master_agent.state
        
        # Step 1: Run fraud check first
        fraud_result = fraud_agent.perform_fraud_check(current_state['entities'])
        
        # Update master agent with fraud result
        user_master_agent.set_fraud_result(
            fraud_score=fraud_result.get('fraud_score', 0),
            fraud_flag=fraud_result.get('fraud_flag', 'Low')
        )
        
        # Step 2: If high fraud risk, reject immediately
        if fraud_result.get('fraud_flag') == 'High':
            user_master_agent.set_underwriting_result(
                risk_score=999,
                approval_status=False,
                interest_rate=0.0
            )
            
            session['fraud_result'] = fraud_result
            session['last_state'] = user_master_agent.state.copy()
            
            return jsonify({
                'message': 'Application rejected due to verification issues.',
                'approval_status': False,
                'reason': 'fraud_detected',
                'fraud_details': fraud_result,
                'worker': 'none',
                'next_action': 'terminate'
            })
        
        # Step 3: Proceed with underwriting (only if fraud is not High)
        underwriting_result = underwriting_agent.perform_underwriting(
            current_state['entities'],
            fraud_score=fraud_result.get('fraud_score', 0)
        )
        
        # Step 4: Update master agent with underwriting result
        user_master_agent.set_underwriting_result(
            risk_score=underwriting_result['risk_score'],
            approval_status=underwriting_result['approval_status'],
            interest_rate=underwriting_result.get('interest_rate', 12.5)  # Default
        )
        
        # Step 5: Generate response based on result
        if underwriting_result['approval_status']:
            response = {
                'message': 'Your application has been pre-approved!',
                'approval_status': True,
                'risk_score': underwriting_result['risk_score'],
                'interest_rate': underwriting_result.get('interest_rate', 12.5),
                'worker': 'sales',
                'action': 'call_sales_api'
            }
        else:
            response = {
                'message': 'Unfortunately, your application was not approved at this time.',
                'approval_status': False,
                'reason': underwriting_result.get('reason', 'risk_assessment'),
                'worker': 'sales',  # Route to sales for counseling
                'action': 'call_sales_api'
            }
        
        # Update session
        session['underwriting_result'] = underwriting_result
        session['fraud_result'] = fraud_result
        session['last_state'] = user_master_agent.state.copy()
        
        response['session_id'] = session_id
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in /underwrite: {e}")
        return jsonify({
            'error': 'underwriting_failed',
            'message': 'Underwriting process failed. Please try again.'
        }), 500

@app.route('/sales', methods=['POST'])
def sales_negotiate():
    """
    Worker endpoint for sales and negotiation.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in user_sessions:
            return jsonify({'error': 'Invalid or expired session.'}), 400
        
        session = user_sessions[session_id]
        update_session_activity(session_id)
        
        user_master_agent = session['master_agent']
        current_state = user_master_agent.state
        
        # Check stage to determine what kind of sales interaction is needed
        if current_state.get('stage') == 'offer':
            # Generate loan offer
            sales_offer = sales_agent.generate_offer(
                master_agent_state=current_state,
                negotiation_request=data.get('negotiate', False)
            )
            
            # Update master agent with offer
            user_master_agent.set_offer(sales_offer)
            
            response = {
                **sales_offer,
                'session_id': session_id,
                'stage': 'offer_presented'
            }
            
        elif current_state.get('stage') == 'rejection_counseling':
            # Provide counseling for rejected application
            counseling_response = sales_agent.provide_counseling(current_state)
            
            response = {
                'message': counseling_response,
                'session_id': session_id,
                'stage': 'counseling',
                'next_steps': [
                    'Improve credit score',
                    'Reduce existing debt',
                    'Reapply in 6 months'
                ]
            }
        
        else:
            response = {
                'message': 'I need more information to provide an offer.',
                'session_id': session_id,
                'worker': 'none'
            }
        
        session['last_state'] = user_master_agent.state.copy()
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in /sales: {e}")
        return jsonify({
            'error': 'sales_processing_failed',
            'message': 'Failed to process sales request.'
        }), 500

@app.route('/fraud', methods=['POST'])
def fraud_check():
    """
    Dedicated endpoint for fraud detection.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in user_sessions:
            return jsonify({'error': 'Invalid or expired session.'}), 400
        
        session = user_sessions[session_id]
        update_session_activity(session_id)
        
        user_master_agent = session['master_agent']
        current_state = user_master_agent.state
        
        # Perform fraud check
        fraud_result = fraud_agent.perform_fraud_check(current_state['entities'])
        
        # Update master agent
        user_master_agent.set_fraud_result(
            fraud_score=fraud_result['fraud_score'],
            fraud_flag=fraud_result['fraud_flag']
        )
        
        # Store in session
        session['fraud_result'] = fraud_result
        session['last_state'] = user_master_agent.state.copy()
        
        response = {
            'fraud_check': fraud_result,
            'session_id': session_id,
            'passed': fraud_result['fraud_flag'] != 'High'
        }
        
        if fraud_result['fraud_flag'] == 'High':
            response['message'] = 'Fraud check failed. Application cannot proceed.'
            response['worker'] = 'none'
            response['next_action'] = 'terminate'
        else:
            response['message'] = 'Fraud check passed.'
            response['worker'] = 'underwriting'
            response['action'] = 'call_underwriting_api'
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in /fraud: {e}")
        return jsonify({
            'error': 'fraud_check_failed',
            'message': 'Fraud detection failed.'
        }), 500

@app.route('/documentation', methods=['POST'])
def documentation():
    """
    Final step: Generate sanction letter.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in user_sessions:
            return jsonify({'error': 'Invalid or expired session.'}), 400
        
        session = user_sessions[session_id]
        user_master_agent = session['master_agent']
        current_state = user_master_agent.state
        
        # Verify conditions
        if not current_state.get('offer_accepted', False):
            return jsonify({
                'error': 'offer_not_accepted',
                'message': 'Please accept the offer first.'
            }), 400
        
        if not all(current_state['entities'].get(field) for field in ['pan', 'aadhaar', 'address']):
            return jsonify({
                'error': 'kyc_incomplete',
                'message': 'KYC details are incomplete.'
            }), 400
        
        # Generate sanction letter
        letter_data = generate_sanction_letter(current_state)
        
        # Update final state
        user_master_agent.state['stage'] = 'closed'
        user_master_agent.state['sanction_letter'] = letter_data['metadata']['sanction_id']
        user_master_agent.state['letter_generated_at'] = datetime.now().isoformat()
        
        # Update session
        session['sanction_letter'] = letter_data
        session['last_state'] = user_master_agent.state.copy()
        session['completed_at'] = datetime.now().isoformat()
        
        return jsonify({
            'message': 'Sanction letter generated successfully!',
            'letter_content': letter_data['content'],
            'metadata': letter_data['metadata'],
            'session_id': session_id,
            'stage': 'completed',
            'download_url': f'/download/{session_id}',  # Mock download URL
            'next_action': 'download_letter'
        })
        
    except Exception as e:
        print(f"Error in /documentation: {e}")
        return jsonify({
            'error': 'documentation_failed',
            'message': 'Failed to generate sanction letter.'
        }), 500

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session status (for debugging)."""
    if session_id in user_sessions:
        session = user_sessions[session_id]
        # Don't expose full agent state, just summary
        return jsonify({
            'session_id': session_id,
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity'),
            'interaction_count': session.get('interaction_count', 0),
            'current_stage': session.get('master_agent').state.get('stage'),
            'has_offer': session.get('master_agent').state.get('offer_accepted', False)
        })
    return jsonify({'error': 'Session not found'}), 404

@app.route('/reset/<session_id>', methods=['POST'])
def reset_session(session_id):
    """Reset a session."""
    if session_id in user_sessions:
        user_sessions[session_id] = {
            'master_agent': MasterAgent(),
            'last_activity': time.time(),
            'created_at': datetime.now().isoformat(),
            'interaction_count': 0
        }
        return jsonify({'message': 'Session reset successfully.'})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(user_sessions),
        'agents': ['master', 'underwriting', 'sales', 'fraud']
    })

if __name__ == '__main__':
    print("=" * 60)
    print("CREDGEN Loan Application System")
    print("=" * 60)
    print("Server starting on http://0.0.0.0:5000")
    print("Available endpoints:")
    print("  GET  /               - Frontend page (index.html)")
    print("  GET  /frontend/*     - Frontend static files (CSS, JS)")
    print("  POST /chat           - Main conversation endpoint")
    print("  POST /underwrite     - Underwriting process")
    print("  POST /sales          - Sales and negotiation")
    print("  POST /fraud          - Fraud detection")
    print("  POST /documentation  - Generate sanction letter")
    print("  GET  /health         - Health check")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)