import os
import json
import re

def clean_json(json_text):
    """Fix common JSON issues like missing commas and unescaped characters."""
    try:
        # Replace bad backslashes (e.g., \') with properly escaped versions
        json_text = json_text.replace("\\", "\\\\")
        
        # Ensure all keys are properly quoted
        json_text = re.sub(r'(?<!")(\b[A-Za-z0-9_ ]+\b)(?=\s*:)', r'"\1"', json_text)
        
        # Attempt to parse JSON
        return json.loads(json_text)
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format. {e}")
        return None

def main():
    index_file_path = "txt/index.txt"
    txt_folder = "txt"

    if not os.path.exists(txt_folder):
        print(f"Error: The folder '{txt_folder}' does not exist.")
        return

    if not os.path.isfile(index_file_path):
        print(f"Error: The file '{index_file_path}' does not exist.")
        return

    try:
        with open(index_file_path, "r", encoding="utf-8") as file:
            json_text = file.read().strip()
        
        # Attempt to clean and load the JSON
        data = clean_json(json_text)
        if data is None:
            return

    except Exception as e:
        print(f"Error: Failed to read '{index_file_path}': {e}")
        return

    for key, value in data.items():
        # Sanitize filename (replace spaces and remove invalid characters)
        safe_key = re.sub(r'[^a-zA-Z0-9_]', '_', key.lower())  # Keep alphanumeric + underscores
        filename = os.path.join(txt_folder, f"{safe_key}.txt")

        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(str(value))
            print(f"Saved '{key}' to '{filename}'")
        except Exception as e:
            print(f"Error: Failed to write to '{filename}': {e}")

if __name__ == "__main__":
    main()
