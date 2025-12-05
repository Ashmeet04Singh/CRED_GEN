import pandas as pd
import joblib
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from xgboost import XGBClassifier
from sklearn.metrics import f1_score

def train_and_save_model():
    """
    Reads the dataset, trains an XGBoost classifier for underwriting, 
    and saves the complete preprocessing and modeling pipeline.
    """
    # --- 1. Setup Paths ---
    # Assuming the training script is run from the project root or the same directory as 'data'
    # The data/ directory should contain loan_history.csv
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Try common paths relative to the script location
    data_path_options = [
        os.path.join(project_root, 'data', 'loan_history.csv'), # If script is in root
        os.path.join(os.getcwd(), 'data', 'loan_history.csv'), # If script is run from root
        os.path.join(os.path.dirname(project_root), 'data', 'loan_history.csv'), # If script is in a subdirectory like 'backend'
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'loan_history.csv') # Safest bet if the script is in a nested dir
    ]
    
    data_path = None
    for path in data_path_options:
        if os.path.exists(path):
            data_path = path
            break
            
    # Output path for the model (assuming 'data' directory exists)
    model_output_dir = os.path.join(os.path.dirname(data_path), 'data') if data_path else 'data'
    os.makedirs(model_output_dir, exist_ok=True)
    model_output_path = os.path.join(model_output_dir, 'underwriting_model.pkl')

    if not data_path:
        print("ERROR: Dataset not found. Please ensure 'loan_history.csv' is in a 'data' directory relative to where you run this script.")
        return

    print(f"Reading data from: {data_path}")
    
    # --- 2. Load Data ---
    df = pd.read_csv(data_path)
    
    # --- 3. Define Features and Target (CRITICAL: Mapped to CSV headers) ---
    # Features identified from the CSV snippet that are highly predictive
    numerical_features = [
        'age', 
        'years_employed', 
        'annual_income', 
        'monthly_income', 
        'existing_loan_balance', 
        'existing_emi_monthly',
        'credit_score',
        'cibil_score', # High-impact feature
        'payment_history_default',
        'credit_inquiry_last_6m',
        'num_open_accounts',
        'num_delinquent_accounts',
        'property_value',
        'requested_loan_amount',
        'requested_loan_tenure',
        'pre_approved_limit',
        'monthly_income_after_emi',
        'debt_to_income_ratio', # High-impact feature
        'loan_to_income_ratio',
        'estimated_monthly_emi',
        'emi_to_income_ratio',
        'total_monthly_obligation',
        'obligation_to_income_ratio',
        'loan_to_asset_ratio', # High-impact feature
        'credit_age_months'
    ]

    categorical_features = [
        'gender', 
        'city', 
        'employment_type', 
        'education_level', 
        'marital_status', 
        'home_ownership', 
        'property_type',
        'rejection_reason' # Including this might help the model learn why previous similar applications failed
    ]

    target_col = 'approval_status'

    # Check for missing columns and drop records where the target is NaN
    X_cols = numerical_features + categorical_features
    missing_cols = [col for col in X_cols + [target_col] if col not in df.columns]
    if missing_cols:
        print(f"ERROR: The following columns are missing in the CSV: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        return

    df.dropna(subset=[target_col], inplace=True)
    
    # Prepare X and y
    X = df[X_cols]
    # Convert Target: 'Approved' -> 1, 'Rejected' -> 0 (Crucial for binary classification)
    y = df[target_col].map({'Approved': 1, 'Rejected': 0})
    
    # --- 4. Create the Preprocessing & Modeling Pipeline ---
    
    # Impute missing numerical data with the median and then scale
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    # Impute missing categorical data with the most frequent value and then one-hot encode
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='drop' # Drop any other columns (like customer_id, pan_number, etc.)
    )

    # XGBoost Classifier
    # NOTE: Set scale_pos_weight to handle class imbalance if necessary (e.g., if rejections > approvals)
    # scale_pos_weight = sum(y == 0) / sum(y == 1) # Example for calculating weight
    xgb_model = XGBClassifier(
        objective='binary:logistic',
        n_estimators=300, # Increased estimators for better accuracy
        learning_rate=0.05, # Slightly reduced learning rate for better convergence
        max_depth=7,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss',
        use_label_encoder=False,
        random_state=42
    )

    # Full Pipeline
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', xgb_model)
    ])

    # 5. Train the Model
    print("Training XGBoost Model...")
    # Split data to evaluate performance
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model_pipeline.fit(X_train, y_train)

    # 6. Evaluate
    # Predict probabilities for the 'Approved' class (class 1)
    y_prob = model_pipeline.predict_proba(X_test)[:, 1]
    
    # Convert probabilities to binary predictions using a default threshold (0.5)
    y_pred = (y_prob >= 0.5).astype(int)

    # Calculate F1-Score (The desired metric for balanced performance)
    f1 = f1_score(y_test, y_pred)
    
    # Note: Accuracy is not the best metric for underwriting, F1-score or AUC are better.
    accuracy = model_pipeline.score(X_test, y_test) 
    
    print(f"\n--- Model Performance Summary ---")
    print(f"Test Accuracy: {accuracy:.4f}")
    print(f"Test F1-Score: {f1:.4f} (Target: 0.85 - 0.90)")

    # 7. Save the Pipeline
    joblib.dump(model_pipeline, model_output_path)
    print(f"\nSaved complete model pipeline to: {model_output_path}")

if __name__ == "__main__":
    train_and_save_model()
