import re

# Read the file
with open('app.py', 'r') as file:
    content = file.read()

# Replace the valid_statuses list
updated_content = re.sub(
    r"valid_statuses = \['vacant', 'pending', 'approved', 'sit-in', 'occupied'\]",
    "valid_statuses = ['vacant', 'pending', 'approved', 'sit-in', 'occupied', 'maintenance']",
    content
)

# Write the updated content back to the file
with open('app.py', 'w') as file:
    file.write(updated_content)

print("Successfully updated valid_statuses in app.py") 