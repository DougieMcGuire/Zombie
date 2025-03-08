import whisper
import cv2
import numpy as np
import os
import subprocess
from pydub import AudioSegment
import re
import random
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
from functools import lru_cache

# Global variables for caching and text sizing
font_cache = {}
frame_cache = {}
cache_lock = threading.Lock()

# Text size configuration
TEXT_SCALE_FACTOR = 1.5  # Adjust this to make all text bigger or smaller
BASE_FONT_SIZE = 120 * TEXT_SCALE_FACTOR  # Base font size
MAX_FONT_SIZE = 130 * TEXT_SCALE_FACTOR   # Maximum font size for animation
OUTLINE_RATIO = 15  # Outline thickness relative to font size

@lru_cache(maxsize=1)
def load_custom_font(size):
    try:
        return ImageFont.truetype("content/font.ttf", int(size))
    except:
        print("Warning: Custom font not found, using default font")
        return ImageFont.load_default()

def generate_word_level_ass_with_sfx(video_path, sfx_times_path):
    model = whisper.load_model("base")
    print("Transcribing video to generate subtitles...")
    result = model.transcribe(video_path, word_timestamps=True)

    word_durations = [
        {"word": word_info["word"].strip(), "start": word_info["start"], "end": word_info["end"]}
        for segment in result["segments"]
        for word_info in segment["words"]
        if word_info["word"].strip()
    ]

    for i, word_info in enumerate(word_durations):
        if "?" in word_info["word"]:
            word_durations = word_durations[i + 1:]
            break

    for i in range(len(word_durations) - 1):
        word_durations[i]["end"] = word_durations[i + 1]["start"]

    if word_durations:
        word_durations[-1]["end"] += 1.0

    for word_info in word_durations:
        word_info["duration"] = word_info["end"] - word_info["start"]
        if random.random() < 0.15:
            colors = [
                (255, 0, 0),     # Super saturated red
                (0, 255, 255),   # Super saturated cyan
                (255, 255, 0),   # Super saturated yellow
                (255, 0, 255),   # Super saturated magenta
                (0, 255, 0)      # Super saturated green
            ]
            word_info["color"] = random.choice(colors)
        else:
            word_info["color"] = (255, 255, 255)  # Pure white

    longest_words = sorted(word_durations, key=lambda w: w["duration"], reverse=True)[:3]
    longest_words_set = {word_info["word"] for word_info in longest_words}

    with open(sfx_times_path, "w", encoding="utf-8") as sfx_file:
        for word_info in word_durations:
            if word_info["word"] in longest_words_set:
                sfx_file.write(f"{word_info['start']}\n")

    return word_durations, longest_words_set

@lru_cache(maxsize=150)
def get_text_size(text, font_size):
    font = load_custom_font(font_size)
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def create_text_overlay(text, font_size, text_color, outline_color, width, height):
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    font = load_custom_font(font_size)
    text_width, text_height = get_text_size(text, font_size)
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Optimized outline drawing with scaled outline size
    outline_size = int(font_size // OUTLINE_RATIO)
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    
    # Main text
    draw.text((x, y), text, font=font, fill=text_color)
    
    return overlay

def process_frame(args):
    frame, word_info, current_time, frame_width, frame_height = args
    
    if word_info["start"] <= current_time <= word_info["end"] + 0.15:
        base_scale = int(BASE_FONT_SIZE)
        max_scale = int(MAX_FONT_SIZE)
        scale_duration = 0.3
        fade_duration = 0.15

        time_elapsed = current_time - word_info["start"]
        t = min(1, time_elapsed / scale_duration)
        scale = int(base_scale + (max_scale - base_scale) * (1 - (1 - t) ** 2))

        if current_time > word_info["end"]:
            fade_t = min(1, (current_time - word_info["end"]) / fade_duration)
            alpha = max(0, 1 - fade_t)
        else:
            alpha = 1

        overlay = create_text_overlay(
            word_info["word"],
            scale,
            word_info["color"],
            (0, 0, 0),
            frame_width,
            frame_height
        )
        
        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
        frame_pil = Image.alpha_composite(frame_pil, overlay)
        frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGBA2BGR)

    return frame

def add_subtitles_and_sfx_with_cv2(video_path, word_durations, longest_words_set, sfx_path, output_path):
    print("Adding subtitles and rendering video with OpenCV...")

    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter("temp_video.mp4", fourcc, fps, (width, height))

    current_frame = 0
    word_index = 0

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        while video.isOpened():
            ret, frame = video.read()
            if not ret:
                break

            current_time = current_frame / fps

            if word_index < len(word_durations):
                word_info = word_durations[word_index]
                if current_time >= word_info["end"]:
                    word_index += 1
                else:
                    frame = process_frame((frame.copy(), word_info, current_time, width, height))

            out.write(frame)
            current_frame += 1

    video.release()
    out.release()

    print("Processing audio...")
    sfx_times = [float(line.strip()) for line in open(sfx_times_path).readlines()]
    sfx_audio = AudioSegment.from_file(sfx_path)
    input_audio = AudioSegment.from_file(video_path)
    final_audio = AudioSegment.silent(duration=duration * 1000)

    def add_sfx(start_time):
        return sfx_audio, start_time * 1000

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        sfx_positions = list(executor.map(add_sfx, sfx_times))
        for sfx, position in sfx_positions:
            final_audio = final_audio.overlay(sfx, position=position)

    final_audio = final_audio.overlay(input_audio)
    final_audio.export("temp_audio.mp3", format="mp3")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", "temp_video.mp4",
        "-i", "temp_audio.mp3",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-c:a", "aac",
        "-strict", "experimental",
        output_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.remove("temp_video.mp4")
    os.remove("temp_audio.mp3")
    print(f"Output saved to {output_path}")

input_video = "content/EDIT1.mp4"
sfx_times_path = "txt/sfx_times.txt"
ding_sound = "content/ding.mp3"
output_video = "content/EDIT2.mp4"

if not os.path.exists(input_video):
    print(f"Input video not found: {input_video}")
elif not os.path.exists(ding_sound):
    print(f"Sound effect not found: {ding_sound}")
else:
    word_durations, longest_words_set = generate_word_level_ass_with_sfx(input_video, sfx_times_path)
    add_subtitles_and_sfx_with_cv2(input_video, word_durations, longest_words_set, ding_sound, output_video)