# CREDGEN - AI-Powered Loan Application System

CREDGEN is an intelligent, conversational loan application system that automates the entire loan processing workflow using multiple AI agents. The system guides users through loan applications via natural language conversations, performs automated underwriting, fraud detection, and generates sanction letters.

## 🚀 Features

- **Conversational Interface**: Natural language chat-based loan application process
- **Multi-Agent Architecture**: Specialized AI agents for different stages of loan processing
  - **Master Agent**: Orchestrates the conversation flow and intent recognition
  - **Underwriting Agent**: AI-powered risk assessment and loan approval decisions
  - **Fraud Detection Agent**: Real-time fraud risk analysis using anomaly detection
  - **Sales Agent**: Handles loan offers, negotiations, and counseling
- **Automated Workflows**: Streamlined loan processing from application to sanction letter generation
- **Session Management**: Secure, session-based user interactions with automatic cleanup
- **KYC Verification**: Automated Know Your Customer (KYC) document collection and validation
- **Dynamic Interest Rate Calculation**: Risk-based interest rate determination (8.5% - 15%)
- **Sanction Letter Generation**: Automated generation of loan sanction letters with all terms

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🔧 Installation

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd CRED_GEN
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify model files** are present in the `backend/` directory:
   - `underwriting_model.pkl` (underwriting AI model)
   - `lof_pipeline.pkl` (fraud detection model)

## 🎯 Usage

### Starting the Server

Run the Flask application:

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000` (accessible at `http://localhost:5000`).

### Accessing the Application

- **Main Application**: Open `http://localhost:5000` in your web browser
- **Widget Mode**: Access `http://localhost:5000/widget.html` for embedded usage

### Application Flow

1. **Initial Greeting**: User starts a conversation about loan application
2. **Information Collection**: Master Agent collects required details:
   - Personal information (name, age)
   - Loan requirements (amount, tenure, purpose)
   - Financial information (income, employment type)
   - KYC details (PAN, Aadhaar, address)
3. **Fraud Detection**: Automatic fraud risk assessment
4. **Underwriting**: AI-powered risk scoring and approval decision
5. **Offer Generation**: Dynamic loan offer with interest rate and EMI calculation
6. **Negotiation**: Optional negotiation of loan terms
7. **Documentation**: Final sanction letter generation

## 📡 API Endpoints

### Conversation Endpoints

- **`POST /chat`**: Main conversational endpoint for user interactions
  ```json
  {
    "message": "I need a loan of ₹500000"
  }
  ```

- **`POST /underwrite`**: Triggers underwriting process
  ```json
  {
    "session_id": "session_abc123"
  }
  ```

- **`POST /sales`**: Sales negotiation and offer generation
  ```json
  {
    "session_id": "session_abc123",
    "negotiate": false
  }
  ```

- **`POST /fraud`**: Fraud detection check
  ```json
  {
    "session_id": "session_abc123"
  }
  ```

- **`POST /documentation`**: Generate sanction letter
  ```json
  {
    "session_id": "session_abc123"
  }
  ```

### Utility Endpoints

- **`GET /health`**: Health check endpoint
- **`GET /session/<session_id>`**: Get session status
- **`POST /reset/<session_id>`**: Reset a user session
- **`GET /`**: Frontend main page
- **`GET /widget.html`**: Embedded widget page

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)                │
│                  Chat Interface + Widget                 │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Flask API Server (app.py)                   │
│         Session Management + Route Handlers              │
└─────┬──────────┬──────────┬──────────┬──────────────────┘
      │          │          │          │
┌─────▼─────┐ ┌─▼──────┐ ┌─▼─────┐ ┌─▼──────────┐
│   Master  │ │Under-  │ │ Sales │ │   Fraud    │
│   Agent   │ │writing │ │ Agent │ │   Agent    │
│           │ │ Agent  │ │       │ │            │
└───────────┘ └────────┘ └───────┘ └────────────┘
                  │                      │
            ┌─────▼──────────────┐  ┌───▼─────────┐
            │   ML Models        │  │ Anomaly     │
            │   (XGBoost)        │  │ Detection   │
            │   underwriting_    │  │ (LOF)       │
            │   model.pkl        │  │ lof_        │
            └────────────────────┘  │ pipeline.pkl│
                                    └─────────────┘
```

### Agent Responsibilities

- **Master Agent**: Manages conversation state, intent classification, and routes to specialized agents
- **Underwriting Agent**: Uses ML model to assess credit risk and determine approval
- **Fraud Agent**: Detects anomalies and potential fraud using Isolation Forest/LOF
- **Sales Agent**: Generates offers, handles negotiations, and provides counseling

## 📁 Project Structure

```
CRED_GEN/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── backend/
│   ├── master_agent.py        # Master orchestrator agent
│   ├── underwriting_agent.py  # Credit risk assessment agent
│   ├── sales_agent.py         # Sales and negotiation agent
│   ├── fraud_detection.py     # Fraud detection agent
│   ├── pdf_generator.py       # Sanction letter PDF generation
│   ├── underwriting_model.pkl # Trained underwriting ML model
│   ├── lof_pipeline.pkl       # Fraud detection model
│   └── utils/
│       ├── config.py          # Configuration constants
│       ├── preprocess.py      # Data preprocessing utilities
│       ├── underwriting_modelling.py  # Model training code
│       └── fraud_detection_model.py   # Fraud model training
├── frontend/
│   ├── index.html             # Main application page
│   ├── widget.html            # Embeddable widget version
│   ├── chat.js                # Chat interface logic
│   ├── embed.js               # Widget embedding script
│   └── styles.css             # Styling
├── data/
│   ├── kyc_sample.csv         # Sample KYC data
│   └── loan_history.csv       # Historical loan data
└── demo/
    └── API_Testing.md         # API documentation
```

## 🔑 Configuration

Key configuration parameters can be modified in `backend/utils/config.py`:

- **Loan Constraints**:
  - Minimum loan amount: ₹50,000
  - Maximum loan amount: ₹5,000,000
  - Tenure range: 12-60 months
  - Age range: 21-65 years
  - Minimum annual income: ₹300,000

- **Interest Rate Bands**:
  - Low risk (0.0-0.3): 8.5% - 9.5%
  - Medium risk (0.3-0.7): 9.5% - 12.0%
  - High risk (0.7-1.0): 12.0% - 15.0%

- **Session Management**:
  - Session timeout: 30 minutes (1800 seconds)
  - Automatic cleanup: Every 5 minutes

## 🛠️ Technologies Used

- **Backend Framework**: Flask 3.0.0
- **NLP**: sentence-transformers, transformers
- **Machine Learning**: 
  - scikit-learn 1.4.1
  - XGBoost 2.0.3 (underwriting model)
  - PyOD 1.1.0 (fraud detection)
- **Data Processing**: pandas, numpy
- **PDF Generation**: reportlab
- **CORS**: Flask-CORS for cross-origin requests

## 🔒 Security Features

- Session-based authentication with expiration
- Automatic session cleanup for expired sessions
- Fraud detection before underwriting approval
- KYC verification requirements

## 📝 Example Conversation

```
User: Hi, I need a loan
Agent: Hello! I'd be happy to help you with a loan application. 
       To get started, could you please tell me your name?

User: My name is John Doe
Agent: Nice to meet you, John! What loan amount are you looking for?

User: ₹500000
Agent: Great! For how many months would you like to repay this loan?

[... continues through information collection ...]

Agent: Your application has been pre-approved! 
       Loan Amount: ₹500,000
       Interest Rate: 10.5% p.a.
       Monthly EMI: ₹10,845
       Would you like to proceed?
```

## 🚦 Status Codes

- `200`: Success
- `400`: Bad request (missing/invalid data)
- `404`: Session not found
- `500`: Server error

## 🐛 Troubleshooting

### Common Issues

1. **Model files not found**: Ensure `underwriting_model.pkl` and `lof_pipeline.pkl` are in the `backend/` directory
2. **Port already in use**: Change the port in `app.py` (line 563) or stop the process using port 5000
3. **Dependencies error**: Make sure all packages in `requirements.txt` are installed correctly
4. **Session expired**: Sessions expire after 30 minutes of inactivity. Start a new conversation if needed

## 📄 License

[Add your license information here]

## 👥 Contributing

[Add contribution guidelines if applicable]

## 📧 Contact

[Add contact information if applicable]

---

**Note**: This is a demonstration system. For production use, ensure proper security measures, database integration, and compliance with financial regulations.

