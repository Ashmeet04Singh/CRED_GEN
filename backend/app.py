from flask import Flask, request, jsonify
from flask_cors import CORS 
import os
import uuid
from datetime import datetime

# Import the core agents we have developed
from backend.master_agent import MasterAgent
from backend.underwriting_agent import UnderwritingAgent
from backend.sales_agent import SalesAgent

# --- 1. Initialization ---
app = Flask(__name__)
# CRITICAL: Allows your frontend (running on a different port/IP) to talk to this backend
CORS(app) 

# In a real app, this would be a database (Redis/Postgres)
user_sessions = {}

# Initialize all agents once when the server starts
master_agent = MasterAgent()
underwriting_agent = UnderwritingAgent()
sales_agent = SalesAgent()

# --- Utility Function Mocks ---

def get_session_id(request):
    """Retrieves or creates a session ID."""
    # For simplicity, we use a mock unique ID or a value from the request header/cookie
    # In a hackathon, using a fixed ID or generating one per request is common.
    # We'll use a simple header/mock fallback for testing.
    session_id = request.headers.get('X-Session-ID', 'default_user_123')
    if session_id == 'default_user_123' and request.method == 'POST':
        # Generate a new ID if it's the first chat message
        session_id = str(uuid.uuid4())
    return session_id

def generate_sanction_letter(state: dict) -> str:
    """Mocks the final step: generating a PDF sanction letter content."""
    entities = state.get('entities', {})
    loan_amount = entities.get('loan_amount', 0)
    interest_rate = state.get('interest_rate', 'N/A')
    name = entities.get('name', 'Applicant')
    date_today = datetime.now().strftime("%B %d, %Y")
    
    letter_details = (
        f"\n\n*** CREDGEN SANCTION LETTER (MOCK) ***\n"
        f"Date: {date_today}\n"
        f"Applicant: {name}\n"
        f"Loan Amount Sanctioned: ₹{loan_amount:,}\n"
        f"Final Interest Rate: {interest_rate:.2f}%\n"
        f"Status: APPROVED FOR DISBURSEMENT\n"
        f"--------------------------------------\n"
    )
    return letter_details

# --- 2. API Endpoints (The Routes) ---

@app.route('/chat', methods=['POST'])
def chat():
    """
    Primary conversational endpoint. Receives user input and routes it to the MasterAgent.
    The response includes an 'action' flag if a worker agent needs to be called.
    """
    session_id = get_session_id(request)
    data = request.get_json()
    user_input = data.get('message', '')

    # Initialize or retrieve session state
    if session_id not in user_sessions:
        user_sessions[session_id] = master_agent._initialize_state()

    # Set the MasterAgent's internal state to the current session state
    master_agent.state = user_sessions[session_id] 

    # Process the user input through the Master Agent
    response = master_agent.handle(user_input)
    
    # Update the global session state with the Master Agent's latest state
    user_sessions[session_id] = master_agent.state

    # Check the worker flag set by the MasterAgent
    worker_name = response.get('worker')
    
    # IMPORTANT: app.py converts the worker name into a specific frontend action flag
    if worker_name == "underwriting":
        return jsonify({"message": response['message'], "action": "call_underwriting_api"})
    
    # Sales agent is called for negotiation or rejection counseling
    if worker_name == "sales": 
        return jsonify({"message": response['message'], "action": "call_sales_api"})
    
    # Documentation is the final step after KYC is accepted
    if worker_name == "documentation":
        return jsonify({"message": response['message'], "action": "call_documentation_api"})

    # Default conversational response
    return jsonify(response)


@app.route('/underwrite', methods=['POST'])
def underwrite():
    """
    Worker Agent Call: Executes the Underwriting Agent's AI + Rule-Based logic.
    """
    session_id = get_session_id(request)
    current_state = user_sessions.get(session_id)
    
    if not current_state:
        return jsonify({"error": "No active session."}), 400

    # 1. Execute the AI + Rule-Based Underwriting Logic
    underwriting_result = underwriting_agent.perform_underwriting(current_state['entities'])
    
    # 2. Update Master Agent's State with the result (must set its state first)
    master_agent.state = current_state
    master_agent.set_underwriting_result(
        risk_score=underwriting_result['risk_score'],
        approval_status=underwriting_result['approval_status'],
        # Use the rate calculated by the Underwriting Agent (or Sales Agent logic)
        interest_rate=underwriting_agent._mock_interest_rate(underwriting_result['risk_score']) 
    )
    
    # 3. Get the next conversational response (the offer or rejection message)
    final_response = master_agent.generate_response(intent=master_agent.state["last_intent"], confidence=1.0)
    
    # Update global state
    user_sessions[session_id] = master_agent.state
    
    # NOTE: We intentionally set the worker to 'sales' here to get the Sales Agent's formatted offer message next
    final_response["worker"] = "sales" 
    final_response["action"] = "call_sales_api"
    
    return jsonify(final_response)


@app.route('/sales', methods=['POST'])
def sales_negotiate():
    """
    Worker Agent Call: Executes the Sales Agent's logic for negotiation or counseling.
    """
    session_id = get_session_id(request)
    current_state = user_sessions.get(session_id)
    
    if not current_state:
        return jsonify({"error": "No active session."}), 400
        
    # Check if the user is asking for negotiation or if the MasterAgent is routing to counseling
    is_negotiation = current_state["stage"] == "offer"
    
    # 1. Execute the AI + Rule-Based Sales Logic
    sales_offer = sales_agent.generate_offer(
        master_agent_state=current_state,
        negotiation_request=is_negotiation
    )
    
    # 2. Update Master Agent's State (set its state first)
    master_agent.state = current_state
    master_agent.set_offer(sales_offer) # This updates the current_offer details
    
    # 3. Return the offer message directly (Sales Agent formats the final message)
    user_sessions[session_id] = master_agent.state
    return jsonify(sales_offer)


@app.route('/generate-letter', methods=['POST'])
def documentation():
    """
    FINAL ACTION: Generates the Sanction Letter content.
    """
    session_id = get_session_id(request)
    current_state = user_sessions.get(session_id)
    
    # CRITICAL RULE: Check for offer acceptance
    if not current_state or not current_state.get("offer_accepted", False):
        return jsonify({"message": "Error: Offer not accepted or missing data."}), 400
        
    # Execute the mock documentation generation
    letter_content = generate_sanction_letter(current_state)
    
    # Master Agent sets stage to 'closed'
    master_agent.state = current_state
    master_agent.state["stage"] = "closed"
    
    # Update global state
    user_sessions[session_id] = master_agent.state
    
    return jsonify({
        "message": f"Sanction Letter is ready for download! {letter_content}",
        "action": "download_letter" # Frontend uses this to trigger a final download/display
    })


if __name__ == '__main__':
    # CRITICAL for team collaboration: host='0.0.0.0' allows access from other machines on the network
    # Make sure you know the host machine's IP address (e.g., 192.168.1.5)
    print("Starting Flask server...")
    print("Access the server via the host machine's IP address on port 5000.")
    app.run(host='0.0.0.0', port=5000, debug=True)
