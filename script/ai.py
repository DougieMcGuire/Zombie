import requests
import os
import json
import re

def get_story_from_groq(groq_api_key):
    """
    Reads a topic from txt/topic.txt and sends a prompt to the Groq AI API 
    to generate a horror-themed, 15-second first-person story for a YouTube Shorts video.

    **Title:** A hook-style question asked by someone else to engage viewers.  
    **Story Body:** The main character recounting a terrifying event in first-person POV.  
    - The story should feel **real and relatable** with a **chilling narrative** that leaves hints of more to come.  
    - Start with **"One time..."**, **"So basically I encountered..."**, or something similar.
    - The story should be **15 seconds** long, ideal for YouTube Shorts.
    """
    topic_file = "txt/topic.txt"
    if not os.path.exists(topic_file):
        print(f"Error: {topic_file} does not exist.")
        return None

    try:
        with open(topic_file, "r", encoding="utf-8") as file:
            topic = file.read().strip()
    except Exception as e:
        print(f"Error reading the topic file: {e}")
        return None

    groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""Generate a video of a horror story based on the topic '{topic}'.

A great TikTok/YouTube Shorts horror story has these key elements:

1. **Strong emotional hook** - Start with a scenario viewers can instantly relate to (being home alone, walking at night, strange sounds)
2. **Clear stakes** - Establish what the narrator risks losing (safety, sanity, loved ones)
3. **Escalating tension** - Start with small, odd details that grow increasingly threatening
4. **Sensory details** - Include specific sounds, visuals, or physical sensations that make fear tangible
5. **Limited scope** - Focus on one frightening element rather than many
6. **Authentic voice** - Use casual, conversational language like actual TikTok storytellers

**Follow these exact rules:**  
- The **title** should be phrased as a question that teases the content without revealing the twist.
- The **story body** must be in **first-person POV**, starting casually like a friend sharing a story. Example: "So last week I was home alone when..." or "I still get chills thinking about what happened when..."
- Include specific, realistic details that ground the story (exact times, weather conditions, specific locations in a house)
- Build tension through progression: normal situation → something slightly off → increasingly wrong → terrifying revelation
- **The story must be under 1 min** when read aloud, with natural pacing
- Make thes perfect for keepping the viewerr watching and made for people with a low attention span and make it for everyone a nd scary 
**IMPORTANT RULES FOR OUTPUT FORMAT:**  
- **No weird symbols, backslashes, or non-UTF-8 characters.**  
- Ensure the response is VALID JSON format with properly quoted keys and values.
- The response must contain ONLY the JSON object, with no markdown formatting or backticks.
- Use natural pauses and commas to ensure the best sounding TTS outcome  

I WANT A FULLLLLLLL STORY. 
dont reference out previous chats if you have access to those.

- Use this exact JSON structure:  
{{
    "Story Title": "Generated hook-style question",
    "Story Body": "Generated first-person story",
    "SEX": "m",  
    "Video Caption": "caption of the video",  
    "SEX2": "f"  
}}
- The **"SEX" field must always be 'm'** and **"SEX2" must always be 'f'** (this is required).  
- **Do NOT include dialogue or quotation marks.** The entire story should feel like the narrator's unfiltered inner monologue.  

For the "Video Caption" field, create a short, intriguing phrase that complements the story and enhances engagement."""
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are an AI that generates horror stories in valid JSON format without any formatting or explanation. Include ONLY the JSON object in your response."},
            {"role": "user", "content": prompt}
        ],
        "model": "llama3-70b-8192",
        "temperature": 2,
        "max_completion_tokens": 1024,
        "top_p": 1,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(groq_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        # Strip any markdown code block formatting if present
        content = re.sub(r'```json\s*|\s*```', '', content)
        content = content.strip()
        
        return content
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except KeyError as e:
        print(f"Failed to parse 'content': {e}")
        if 'response' in locals():
            print(f"Raw response: {response.text}")
        return None

def clean_json(json_text):
    """
    Fixes common JSON issues like missing commas and unescaped characters.
    Ensures that the output is properly formatted and error-free.
    """
    try:
        # First try to parse it directly - might already be valid
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass  # Continue with cleaning
        
        # Remove any non-json text before or after the json object
        match = re.search(r'(\{.*\})', json_text, re.DOTALL)
        if match:
            json_text = match.group(1)
        
        # Fix unquoted keys
        json_text = re.sub(r'([{,])\s*([A-Za-z0-9_]+)\s*:', r'\1"\2":', json_text)
        
        # Fix missing quotes around string values
        json_text = re.sub(r':\s*([A-Za-z0-9_]+)([,}])', r':"\1"\2', json_text)
        
        # Handle escaping of quotes within values
        json_text = re.sub(r'([^\\])"([^"]*)([^\\])"', r'\1"\2\3\"', json_text)
        
        # Fix missing commas
        json_text = re.sub(r'(["}])\s*"', r'\1,"', json_text)
        
        # Replace double quotes within already quoted strings
        # This is complex and might require multiple approaches
        
        # Sometimes backslashes need to be doubled
        json_text = json_text.replace("\\", "\\\\")
        
        # But avoid doubling already doubled backslashes
        json_text = json_text.replace("\\\\\\\\", "\\\\")
        
        # Try to load the cleaned JSON
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            # Last resort: construct a basic valid JSON if cleaning failed
            print(f"Advanced cleaning failed: {e}")
            print(f"Attempting to extract individual fields...")
            
            # Try to extract fields using regex
            story_title = re.search(r'"Story Title"\s*:\s*"([^"]*)"', json_text)
            story_body = re.search(r'"Story Body"\s*:\s*"([^"]*)"', json_text)
            video_caption = re.search(r'"Video Caption"\s*:\s*"([^"]*)"', json_text)
            
            if story_title and story_body:
                return {
                    "Story Title": story_title.group(1),
                    "Story Body": story_body.group(1),
                    "SEX": "m",
                    "Video Caption": video_caption.group(1) if video_caption else "Horror Story",
                    "SEX2": "f"
                }
            else:
                print("Could not extract required fields from JSON.")
                return None
            
    except Exception as e:
        print(f"Error during JSON cleaning: {e}")
        print(f"Problematic JSON: {json_text}")
        return None

def save_response_to_file(response_data, file_path):
    """
    Saves the raw response data to a single text file.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(response_data)
        return True
    except Exception as e:
        print(f"Error while saving the file: {e}")
        return False

def sort_and_save_parsed_data(index_file_path, txt_folder):
    """
    Reads the cleaned JSON file, sorts the data, and saves it into separate text files.
    """
    if not os.path.exists(txt_folder):
        print(f"Error: The folder '{txt_folder}' does not exist.")
        return False

    if not os.path.isfile(index_file_path):
        print(f"Error: The file '{index_file_path}' does not exist.")
        return False

    try:
        with open(index_file_path, "r", encoding="utf-8") as file:
            json_text = file.read().strip()

        # Clean and parse JSON
        data = clean_json(json_text)
        if data is None:
            print("Failed to parse JSON data from index file.")
            # Create a backup of the problematic file for debugging
            backup_path = index_file_path + ".bak"
            with open(backup_path, "w", encoding="utf-8") as backup_file:
                backup_file.write(json_text)
            print(f"Created backup of problematic JSON at {backup_path}")
            return False

    except Exception as e:
        print(f"Error: Failed to read '{index_file_path}': {e}")
        return False

    success = True
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
            success = False
            
    return success

def main():
    groq_api_key = "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"  # Replace with your actual Groq API key
    index_file_path = "txt/index.txt"
    txt_folder = "txt"
    
    # Ensure txt directory exists
    os.makedirs(txt_folder, exist_ok=True)

    try:
        # Make sure the topic file exists and create it with a default topic if it doesn't
        if not os.path.exists(os.path.join(txt_folder, "topic.txt")):
            with open(os.path.join(txt_folder, "topic.txt"), "w", encoding="utf-8") as f:
                f.write("haunted house")
            print("Created default topic.txt file with 'haunted house' topic")
            
        story_content = get_story_from_groq(groq_api_key)
        if story_content:
            if save_response_to_file(story_content, index_file_path):
                print("Story saved to 'txt/index.txt'.")
                if sort_and_save_parsed_data(index_file_path, txt_folder):
                    print("Successfully parsed and saved all story components.")
                else:
                    print("Warning: There were issues parsing the story components.")
            else:
                print("Failed to save the story response.")
        else:
            print("Failed to generate a story.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()