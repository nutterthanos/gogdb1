import re

# Read the script content from the file
with open("products_builds.py", "r") as script_file:
    script = script_file.read()

# Define the increment value
increment_value = 1000000

# Define the pattern to find the start_product_id and end_product_id lines
pattern = r"(start_product_id\s*=\s*)(\d+)"
match = re.search(pattern, script)
if match:
    # Extract the original value and calculate the new value
    original_value = int(match.group(2))
    new_value = original_value + increment_value

    # Replace the original line with the updated line
    updated_line = f"{match.group(1)}{new_value}"
    script = re.sub(pattern, updated_line, script)

# Repeat the process for end_product_id
pattern = r"(end_product_id\s*=\s*)(\d+)"
match = re.search(pattern, script)
if match:
    original_value = int(match.group(2))
    new_value = original_value + increment_value
    updated_line = f"{match.group(1)}{new_value}"
    script = re.sub(pattern, updated_line, script)

# Write the updated script back to the file
with open("products_builds.py", "w") as script_file:
    script_file.write(script)