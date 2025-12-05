import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from xgboost import XGBClassifier

def train_and_save_model():
    """
    Reads the dataset, trains an XGBoost classifier, and saves the pipeline.
    """
    # 1. Setup Paths (Relative to this file in backend/utils/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir)) # Go up to CredGen/
    
    data_path = os.path.join(project_root, 'data', 'loan_history.csv')
    model_output_path = os.path.join(project_root, 'data', 'underwriting_model.pkl')

    print(f"Reading data from: {data_path}")
    
    if not os.path.exists(data_path):
        print(f"ERROR: Dataset not found at {data_path}")
        return

    # 2. Load Data
    df = pd.read_csv(data_path)

    # 3. Define Features and Target
    # NOTE: Adjust these column names if your CSV headers are slightly different (e.g., capitals)
    
    # Numerical Features (will be Scaled)
    numerical_features = [
        'age', 
        'years_employed', 
        'monthly_income', 
        'annual_income', 
        'existing_loan_balance', 
        'existing_emi_monthly'
    ]

    # Categorical Features (will be One-Hot Encoded)
    categorical_features = [
        'gender', 
        'city', 
        'employment_type', 
        'education_level', 
        'marital_status', 
        'loan_purpose'
    ]

    # Target Column
    target_col = 'approval_status'

    # Check if columns exist
    missing_cols = [col for col in numerical_features + categorical_features + [target_col] if col not in df.columns]
    if missing_cols:
        print(f"ERROR: The following columns are missing in the CSV: {missing_cols}")
        print(f"Available columns: {list(df.columns)}")
        return

    # Prepare X and y
    X = df[numerical_features + categorical_features]
    # Convert Target: 'Approved' -> 1, 'Rejected' -> 0
    y = df[target_col].map({'Approved': 1, 'Rejected': 0})

    # 4. Create the Preprocessing & Modeling Pipeline
    # We use a Pipeline so the Agent doesn't need to manually encode data later.
    
    numerical_transformer = Pipeline(steps=[
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )

    # XGBoost Classifier
    xgb_model = XGBClassifier(
        objective='binary:logistic',
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
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
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model_pipeline.fit(X_train, y_train)

    # 6. Evaluate
    score = model_pipeline.score(X_test, y_test)
    print(f"Model trained successfully! Test Accuracy: {score:.4f}")

    # 7. Save the Pipeline
    joblib.dump(model_pipeline, model_output_path)
    print(f"Saved model to: {model_output_path}")

if __name__ == "__main__":

    train_and_save_model()
