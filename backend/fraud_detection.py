from rapidfuzz import fuzz
from datetime import datetime

def fraud_score(cust_data: dict):
    """Returns a fraud-score in range 0-1. Currently on hard-checks(rule-based)."""

    #name check
    def name_score(name_list: list):
        #argument requires the name of the applicant as mentioned in the various documents he uploads.
        name_list_cleaned = [name.strip().lower() for name in name_list if name and name.strip()]

        if len(name_list_cleaned)<2:
            return {"name_score": 1.0, "flag": "LOW"}
        score_ind = []
        for i in range(len(name_list_cleaned)):
            for j in range(i+1, len(name_list_cleaned)):
                name_1, name_2 = name_list_cleaned[i], name_list_cleaned[j]
                score = fuzz.token_set_ratio(name_1, name_2) /100
                score_ind.append(score)

        if min(score_ind)<0.8:
            flag = 'HIGH'
        else:
            flag = 'LOW'
        score_cum = sum(score_ind)/len(score_ind) 
        return {'name_score': score_cum, 'flag': flag}
    
    def age_score(dob):
        "0 if any inappropriate age found. 0.5 if outside bounds. 1 in other cases"

        if not dob or not dob.strip():
            return 0
        dob = dob.strip()
        try:
            birth_date = datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            try:
                birth_date = datetime.strptime(dob, '%d-%m-%Y')
            except ValueError:
                return 0
            
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        if 18<= age <=80:
            if age<=21 or age>=60:
                return 0.5
            else:
                return 1
        else:
            return 0
        
    def income_score(declared_income: float):
        if declared_income is None or declared_income <=0:
            return {'income_score': 0, 'flag': 'HIGH'}
        if declared_income >10000000 or declared_income <10000:
            return {'income_score': 0.3, 'flag': 'MEDIUM'}
        return {'income_score': 1, 'flag': 'LOW'}
    
    fraud_score = (name_score(cust_data['name_list'])['name_score'] + age_score(cust_data['dob']) + income_score(cust_data['declared_income'])['income_score'])/3

    return fraud_score

#demo run
# cust_data = {'name_list': ['Riya Sharma', 'Riya K Sharma', 'Sharma Riya'],
#              'dob': '2012-05-20',
#              'declared_income': 50000000
#              }
# print(fraud_score(cust_data))