import subprocess
import os
import time
import random
import flask
from flask import Flask, request, jsonify, send_file
import threading

app = Flask(__name__)

# Number of scripts
total_scripts = 11

# The path to the topic file
topic_file = "txt/topic.txt"

def randomize_topic():
    try:
        with open(topic_file, "r", encoding='utf-8') as file:
            topics = file.readlines()
        if topics:
            return random.choice(topics).strip()
        else:
            return None
    except FileNotFoundError:
        raise FileNotFoundError("Topic file not found.")

def save_topic_to_file(topic):
    try:
        # Clear the contents of topic.txt before saving the new topic
        with open("txt/topic.txt", "w", encoding='utf-8') as file:
            file.write(f"{topic}\n")
    except Exception as e:
        print(f"Error saving topic to file: {e}")

def run_scripts(topic, completion_event):
    try:
        start_time = time.time()

        scripts = [
            "script/cleanup.py", "script/ai.py", "script/edit1.py",
            "script/audio.py", "script/video.py", "script/edit.py"
        ]

        for index, script in enumerate(scripts, 1):
            try:
                subprocess.run(["python", script], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error running script {script}: {e}")
            update_progress(index)

        elapsed_time = int(time.time() - start_time)
        show_results(topic, elapsed_time)

    finally:
        # Notify that the task is completed
        completion_event.set()

def update_progress(step):
    # Update progress in the log (optional)
    print(f"Progress: Step {step}/{total_scripts}")

def show_results(topic, elapsed_time):
    # Show final result in the log (optional)
    print(f"Video on '{topic}' generated in {elapsed_time}s!")

@app.route('/process_video', methods=['POST'])
def process_video():
    # Get the topic from the request
    topic = request.form.get('topic')

    if not topic:
        topic = randomize_topic()

    if not topic:
        return jsonify({"error": "No valid topic found!"}), 400

    # Save the topic to the topic file
    save_topic_to_file(topic)

    # Create an event to signal completion
    completion_event = threading.Event()

    # Run the scripts in a separate thread to avoid blocking the server
    processing_thread = threading.Thread(target=run_scripts, args=(topic, completion_event), daemon=True)
    processing_thread.start()

    # Wait for the processing to complete
    completion_event.wait()

    # After processing, check if the video exists
    video_path = "content/edit3.mp4"

    # Ensure the file exists before sending it
    if os.path.exists(video_path):
        return send_file(video_path, mimetype='video/mp4', as_attachment=True)
    else:
        return jsonify({"error": "Video file not found!"}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
