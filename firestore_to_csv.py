import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import pandas as pd
import os
from datetime import datetime

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate('C:/Users/user/Documents/aiagent/test-e1389-firebase-adminsdk-fbsvc-5bb03be7b2.json')
        firebase_admin.initialize_app(cred)
    return firestore.client()

def format_timestamp(timestamp):
    if isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return timestamp

def get_user_data(db):
    users = db.collection("users").stream()
    user_data = []
    
    for user in users:
        user_dict = user.to_dict()
        record = {
            'userId': user.id,
            'name': user_dict.get('name'),
            'email': user_dict.get('email'),
            'role': user_dict.get('role'),
            'isAvailable': user_dict.get('isAvailable'),
            'createdAt': format_timestamp(user_dict.get('createdAt')),
            # Role-specific fields
            'place': user_dict.get('place') if user_dict.get('role') == 'chef' else None,
            'nationality': user_dict.get('nationality') if user_dict.get('role') == 'admin' else None,
            'speciality': user_dict.get('speciality') if user_dict.get('role') == 'technicien' else None,
            'chefIds': ', '.join(user_dict.get('chefIds')) if user_dict.get('role') == 'assistant' and user_dict.get('chefIds') else None,
            # Additional fields if they exist
            'currentProblem': user_dict.get('currentProblem'),
            'allProblems': user_dict.get('allProblems'),
            'lastAssigned': format_timestamp(user_dict.get('lastAssigned')),
            'longitude': user_dict.get('longitude'),
            'latitude': user_dict.get('latitude'),
            'status': user_dict.get('status'),
            'section': user_dict.get('section')
        }
        user_data.append(record)
    
    return pd.DataFrame(user_data)

def get_problem_data(db):
    problems = db.collection("problems").stream()
    problem_data = []
    
    for problem in problems:
        prob_dict = problem.to_dict()
        record = {
            'problemId': problem.id,
            'description': prob_dict.get('description'),
            'type': prob_dict.get('type'),
            'isPredefined': prob_dict.get('isPredefined'),
            'status': prob_dict.get('status'),
            'createdAt': format_timestamp(prob_dict.get('createdAt')),
            'solvedAt': format_timestamp(prob_dict.get('solvedAt')),
            'assignedTechnician': prob_dict.get('assignedTechnician'),
            'chefId': prob_dict.get('chefId')
        }
        problem_data.append(record)
    
    return pd.DataFrame(problem_data)

def export_structured_data():
    db = initialize_firebase()
    
    # Get data from both collections
    users_df = get_user_data(db)
    problems_df = get_problem_data(db)
    
    # Merge data with proper suffixes
    merged_df = pd.merge(
        problems_df,
        users_df,
        left_on='assignedTechnician',
        right_on='userId',
        how='left',
        suffixes=('_problem', '_user')
    )
    
    # Define the desired column order
    column_order = [
        # Problem info
        'problemId', 'description', 'type', 'isPredefined', 'status_problem',
        'createdAt_problem', 'solvedAt', 'chefId',
        
        # Technician info
        'assignedTechnician', 'name', 'role', 'speciality', 'isAvailable',
        
        # User info
        'email', 'createdAt_user', 'place', 'nationality', 'chefIds',
        
        # Additional location info
        'longitude', 'latitude', 'section'
    ]
    
    # Reorder columns and filter only the ones that exist
    available_columns = [col for col in column_order if col in merged_df.columns]
    merged_df = merged_df[available_columns]
    
    # Clean up description field
    if 'description' in merged_df.columns:
        merged_df['description'] = merged_df['description'].str.replace('\n', ' ').str.strip()
    
    # Ensure output directory exists
    os.makedirs("data", exist_ok=True)
    
    # Save to CSV
    output_file = "data/structured_export.csv"
    merged_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Successfully exported {len(merged_df)} records to {output_file}")
    
    # Also save separate files
    users_df.to_csv("data/structured_users.csv", index=False)
    problems_df.to_csv("data/structured_problems.csv", index=False)

if __name__ == "__main__":
    export_structured_data()