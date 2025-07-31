import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Set seed for reproducible results
np.random.seed(42)
random.seed(42)

# Generate 500 rows of realistic employee data

# Sample data lists
first_names = [
    'John', 'Jane', 'Michael', 'Sarah', 'David', 'Lisa', 'Robert', 'Jennifer', 'William', 'Amanda',
    'James', 'Ashley', 'Christopher', 'Jessica', 'Daniel', 'Emily', 'Matthew', 'Michelle', 'Anthony', 'Kimberly',
    'Mark', 'Donna', 'Donald', 'Nancy', 'Steven', 'Karen', 'Paul', 'Betty', 'Andrew', 'Helen',
    'Joshua', 'Sandra', 'Kenneth', 'Carol', 'Kevin', 'Ruth', 'Brian', 'Sharon', 'George', 'Michelle',
    'Edward', 'Laura', 'Ronald', 'Sarah', 'Timothy', 'Kimberly', 'Jason', 'Deborah', 'Jeffrey', 'Dorothy',
    'Ryan', 'Lisa', 'Jacob', 'Nancy', 'Gary', 'Karen', 'Nicholas', 'Betty', 'Eric', 'Helen',
    'Jonathan', 'Sandra', 'Stephen', 'Donna', 'Larry', 'Carol', 'Justin', 'Ruth', 'Scott', 'Sharon',
    'Brandon', 'Michelle', 'Benjamin', 'Laura', 'Samuel', 'Sarah', 'Gregory', 'Kimberly', 'Frank', 'Deborah'
]

last_names = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
    'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson',
    'Walker', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
    'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter', 'Roberts'
]

departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations', 'IT', 'Customer Service', 'Legal', 'R&D']

positions = {
    'Engineering': ['Software Engineer', 'Senior Engineer', 'Tech Lead', 'Engineering Manager', 'DevOps Engineer'],
    'Marketing': ['Marketing Specialist', 'Marketing Manager', 'Content Creator', 'Digital Marketer', 'Brand Manager'],
    'Sales': ['Sales Representative', 'Sales Manager', 'Account Executive', 'Sales Director', 'Business Development'],
    'HR': ['HR Specialist', 'HR Manager', 'Recruiter', 'HR Director', 'Training Coordinator'],
    'Finance': ['Financial Analyst', 'Accountant', 'Finance Manager', 'Controller', 'CFO'],
    'Operations': ['Operations Analyst', 'Operations Manager', 'Process Specialist', 'Operations Director', 'Supply Chain'],
    'IT': ['IT Specialist', 'System Administrator', 'IT Manager', 'Security Analyst', 'Database Administrator'],
    'Customer Service': ['Customer Rep', 'Customer Manager', 'Support Specialist', 'Service Director', 'Client Success'],
    'Legal': ['Legal Counsel', 'Paralegal', 'Legal Manager', 'Compliance Officer', 'Contract Specialist'],
    'R&D': ['Research Scientist', 'R&D Manager', 'Product Developer', 'Innovation Lead', 'Research Director']
}

cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 
          'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville', 'Fort Worth', 'Columbus', 
          'San Francisco', 'Charlotte', 'Indianapolis', 'Seattle', 'Denver', 'Boston']

education_levels = ['High School', 'Bachelor\'s', 'Master\'s', 'PhD', 'Associate\'s']

performance_ratings = ['Excellent', 'Good', 'Average', 'Below Average', 'Poor']

# Generate the dataset
data = []

for i in range(500):
    # Basic info
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    full_name = f"{first_name} {last_name}"
    
    # Department and position
    dept = random.choice(departments)
    position = random.choice(positions[dept])
    
    # Experience and salary correlation
    experience = random.randint(0, 25)
    
    # Salary based on department and experience
    base_salaries = {
        'Engineering': 75000, 'IT': 70000, 'Finance': 65000, 'Legal': 80000, 'R&D': 72000,
        'Marketing': 60000, 'Sales': 58000, 'Operations': 62000, 'HR': 58000, 'Customer Service': 45000
    }
    
    base_salary = base_salaries[dept]
    experience_bonus = experience * random.randint(1500, 3000)
    salary = base_salary + experience_bonus + random.randint(-10000, 15000)
    salary = max(35000, salary)  # Minimum salary
    
    # Other attributes
    age = random.randint(22, 65)
    city = random.choice(cities)
    education = np.random.choice(education_levels, p=[0.1, 0.4, 0.3, 0.1, 0.1])
    performance = np.random.choice(performance_ratings, p=[0.2, 0.35, 0.3, 0.1, 0.05])
    
    # Hire date (within last 10 years)
    start_date = datetime.now() - timedelta(days=random.randint(30, 3650))
    hire_date = start_date.strftime('%Y-%m-%d')
    
    data.append({
        'Employee_Name': full_name,
        'Department': dept,
        'Position': position,
        'Salary': salary,
        'Experience_Years': experience,
        'Age': age,
        'Location': city,
        'Education_Level': education,
        'Performance_Rating': performance,
        'Hire_Date': hire_date
    })

# Create DataFrame
df = pd.DataFrame(data)

# Add some data quality issues for more realistic testing
# Add a few missing values
missing_indices = random.sample(range(500), 15)
for idx in missing_indices[:5]:
    df.loc[idx, 'Performance_Rating'] = np.nan
for idx in missing_indices[5:10]:
    df.loc[idx, 'Education_Level'] = np.nan
for idx in missing_indices[10:]:
    df.loc[idx, 'Experience_Years'] = np.nan

# Save to Excel
df.to_excel('talent_dataset_500_rows.xlsx', index=False)
print("✅ Dataset created successfully!")
print(f"📊 Shape: {df.shape}")
print(f"📋 Columns: {list(df.columns)}")
print("\n📈 Sample data:")
print(df.head())
print("\n📊 Dataset summary:")
print(df.describe())