import re

# Example text that might come from a file or directly as a string
sample_text = """
Create 167: vehicle.tesla.cybertruck (1) at (-2433.68, -5778.56, 60)
Id: 167 Location: (-2433.68, -5778.56, 60)
Create 168: sensor.other.collision (5) at (0, 0, 0)
Id: 168 Location: (0, 0, 0)
Create 169: sensor.other.lane_invasion (5) at (0, 0, 0)
Id: 169 Location: (0, 0, 0)
"""

def do_match(text):
    # Regex pattern to find lines with 'Create xxx: vehicle.yyy'
    pattern = r"(Create \d+: vehicle\.\S+.*$)"

    # Use re.findall to find all occurrences that match the pattern
    matches = re.findall(pattern, text, re.MULTILINE)

    # Print out the results
    results = []
    for line in matches:
        # Extract the vehicle ID and type from the matched line
        id_and_type = re.search(r"Create (\d+): vehicle\.(\S+)", line)
        if id_and_type:
            vehicle_id, vehicle_type = id_and_type.groups()
            print(f"Line: {line.strip()}")
            print(f"Vehicle ID: {vehicle_id}, Vehicle Type: {vehicle_type}\n")
            results.append((vehicle_id, line))
    return results

def do_match_full(text, vehicle_id):
    # Dynamic pattern based on provided vehicle_id
    pattern = rf"Id: {vehicle_id} Location.*$"

    # Use re.findall to find all occurrences that match the pattern
    matches = re.findall(pattern, text, re.MULTILINE)

    # Print and return the results
    results = []
    for line in matches:
        print(f"Matching Line: {line.strip()}")
        results.append(line)
    return results

if __name__ == "__main__":
    vehicle_matches = do_match(sample_text)
    if vehicle_matches:
        # Assuming we want to further search based on the first vehicle ID found
        first_vehicle_id = vehicle_matches[0][0]
        do_match_full(sample_text, first_vehicle_id)
