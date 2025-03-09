import whisper
import cv2
import numpy as np
import os
import subprocess
from pydub import AudioSegment
import random
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
from functools import lru_cache
import ffmpeg  # for consistency

# ---------------- Global Settings and Caching ----------------
font_cache = {}
frame_cache = {}
cache_lock = threading.Lock()

# Text size configuration
TEXT_SCALE_FACTOR = 0.5  # Adjust to make text bigger or smaller
BASE_FONT_SIZE = 120 * TEXT_SCALE_FACTOR
MAX_FONT_SIZE = 130 * TEXT_SCALE_FACTOR
OUTLINE_RATIO = 15  # Outline thickness relative to font size

# Oversaturated highlight colors
HIGHLIGHT_COLORS = [
    (255, 0, 0),      # Bright Red
    (255, 255, 0),    # Bright Yellow
    (0, 191, 255)     # Bright Light Blue
]

@lru_cache(maxsize=1)
def load_custom_font(size):
    try:
        return ImageFont.truetype("content/font.ttf", int(size))
    except Exception:
        print("Warning: Custom font not found, using default font")
        return ImageFont.load_default()

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
    
    # Draw outline by drawing text offset in each direction
    outline_size = int(font_size // OUTLINE_RATIO)
    for dx in [-outline_size, outline_size]:
        for dy in [-outline_size, outline_size]:
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    # Draw main text
    draw.text((x, y), text, font=font, fill=text_color)
    
    return overlay

# ---------------- Subtitles Functions ----------------
def generate_word_level_subtitles(video_path):
    model = whisper.load_model("base")
    print("Transcribing video to generate subtitles...")
    result = model.transcribe(video_path, word_timestamps=True)

    word_durations = [
        {"word": word_info["word"].strip(), "start": word_info["start"], "end": word_info["end"]}
        for segment in result["segments"]
        for word_info in segment["words"]
        if word_info["word"].strip()
    ]
    # Skip initial words until a '?' is found (as per your original logic)
    for i, word_info in enumerate(word_durations):
        if "?" in word_info["word"]:
            word_durations = word_durations[i + 1:]
            break
    # Adjust end times based on the next word start
    for i in range(len(word_durations) - 1):
        word_durations[i]["end"] = word_durations[i + 1]["start"]
    if word_durations:
        word_durations[-1]["end"] += 1.0
    
    # Add duration and assign oversaturated color with 15% probability
    for word_info in word_durations:
        word_info["duration"] = word_info["end"] - word_info["start"]
        if random.random() < 0.15:
            word_info["color"] = random.choice(HIGHLIGHT_COLORS)
        else:
            word_info["color"] = (255, 255, 255)  # White for non-highlighted words

    return word_durations

def process_subtitle_frame(frame, word_info, current_time, frame_width, frame_height):
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

def process_audio(video_path, duration, bg_music_path):
    print("Processing audio with background music overlay...")
    input_audio = AudioSegment.from_file(video_path)
    
    # Process background music: lower its volume and loop it through the full duration
    bg_music = AudioSegment.from_file(bg_music_path)
    # Reduce volume by 12 dB (adjust as needed for the desired balance)
    bg_music = bg_music - 12
    # Loop background music to cover entire duration
    loops = int(duration / (len(bg_music) / 1000)) + 1
    bg_music_looped = bg_music * loops
    bg_music_looped = bg_music_looped[:int(duration * 1000)]
    
    # Overlay background music softly
    final_audio = input_audio.overlay(bg_music_looped)
    final_audio.export("temp_audio.mp3", format="mp3")

# ---------------- Title Overlay Functions ----------------
def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

def apply_title_overlay(frame, frame_count, fps, width, height, overlay, overlay_size, overlay_frames, zoom_in_frames, fall_out_frames):
    if frame_count < overlay_frames:
        scale = 1
        y_offset = 0
        if frame_count < zoom_in_frames:
            t = frame_count / zoom_in_frames
            scale = 0.5 + (0.5 * ease_in_out_quad(t))
        elif frame_count > overlay_frames - fall_out_frames:
            t = (frame_count - (overlay_frames - fall_out_frames)) / fall_out_frames
            y_offset = int(ease_in_out_quad(t) * (height * 0.5))
        new_size = int(overlay_size * scale)
        resized_overlay = cv2.resize(overlay, (new_size, new_size))
        y_start = max(0, (height - new_size) // 2 + y_offset)
        x_start = max(0, (width - new_size) // 2)
        overlay_resized = np.zeros((height, width, 4), dtype=np.uint8)
        h, w, _ = resized_overlay.shape
        overlay_resized[y_start:y_start+h, x_start:x_start+w] = resized_overlay[:min(h, height-y_start), :min(w, width-x_start)]
        # If overlay has an alpha channel, blend it onto the frame
        if overlay.shape[2] == 4:
            alpha_channel = overlay_resized[:, :, 3] / 255.0
            overlay_rgb = overlay_resized[:, :, :3]
            frame = (1.0 - alpha_channel[:, :, None]) * frame + alpha_channel[:, :, None] * overlay_rgb
            frame = frame.astype(np.uint8)
    return frame

def get_audio_duration(audio_path):
    """Returns duration (in seconds) of the audio file."""
    result = subprocess.run(
        ["ffprobe", "-i", audio_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

# Function to process a range of frames
def process_frame_range(video_path, start_frame, end_frame, fps, width, height, 
                        word_durations, overlay, overlay_size, overlay_frames, 
                        zoom_in_frames, fall_out_frames, output_path):
    video = cv2.VideoCapture(video_path)
    video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    current_frame = start_frame
    word_index = 0
    
    # Find the starting word index
    current_time = current_frame / fps
    for i, word in enumerate(word_durations):
        if current_time < word["end"]:
            word_index = i
            break
    
    while current_frame < end_frame and video.isOpened():
        ret, frame = video.read()
        if not ret:
            break
        
        current_time = current_frame / fps
        # Apply subtitle overlay if current word is active
        if word_index < len(word_durations):
            word_info = word_durations[word_index]
            if current_time >= word_info["end"]:
                word_index += 1
            else:
                frame = process_subtitle_frame(frame.copy(), word_info, current_time, width, height)
        
        # Apply title overlay animation if within the title duration
        frame = apply_title_overlay(frame, current_frame, fps, width, height,
                                    overlay, overlay_size, overlay_frames, zoom_in_frames, fall_out_frames)
        out.write(frame)
        current_frame += 1
    
    video.release()
    out.release()
    return output_path

# ---------------- Main Combined Processing ----------------
def main():
    # File paths (adjust as needed)
    input_video = "content/EDIT1.mp4"
    bg_music_path = "content/bg.mp3"         # Background music file
    title_image_path = "content/title.png"
    title_audio = "audio/title.mp3"
    output_video = "content/EDIT3.mp4"
    
    # Check files existence
    if not os.path.exists(input_video):
        print(f"Input video not found: {input_video}")
        return
    if not os.path.exists(title_image_path):
        print(f"Title image not found: {title_image_path}")
        return
    if not os.path.exists(bg_music_path):
        print(f"Background music not found: {bg_music_path}")
        return
    
    # Generate word-level timings from subtitles
    word_durations = generate_word_level_subtitles(input_video)
    
    # Open video and prepare for processing
    video = cv2.VideoCapture(input_video)
    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count_total = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count_total / fps
    video.release()
    
    # Prepare title overlay: load and resize the overlay image
    overlay = cv2.imread(title_image_path, cv2.IMREAD_UNCHANGED)
    if overlay is None:
        raise FileNotFoundError(f"Error: Could not load overlay image from {title_image_path}")
    overlay_size = int(min(width, height) / 1.2)
    overlay = cv2.resize(overlay, (overlay_size, overlay_size))
    
    # Title overlay timing parameters
    title_duration = get_audio_duration(title_audio)
    overlay_frames = int(title_duration * fps)
    zoom_in_frames = int(fps * 0.3)
    fall_out_frames = int(fps * 0.3)
    
    # Split processing into chunks for parallel processing
    num_cpus = min(os.cpu_count(), 4)  # Limit to 4 CPUs to avoid memory issues
    chunk_size = frame_count_total // num_cpus
    temp_files = []
    
    print(f"Processing video frames in {num_cpus} parallel chunks...")
    
    with ProcessPoolExecutor(max_workers=num_cpus) as executor:
        futures = []
        for i in range(num_cpus):
            start_frame = i * chunk_size
            end_frame = (i+1) * chunk_size if i < num_cpus-1 else frame_count_total
            temp_output = f"temp_chunk_{i}.mp4"
            temp_files.append(temp_output)
            
            futures.append(executor.submit(
                process_frame_range, 
                input_video, start_frame, end_frame, fps, width, height,
                word_durations, overlay, overlay_size, overlay_frames,
                zoom_in_frames, fall_out_frames, temp_output
            ))
        
        # Wait for all processing to complete
        for future in futures:
            future.result()
    
    # Process audio with background music (no SFX)
    process_audio(input_video, duration, bg_music_path)
    
    # Concatenate temp video chunks
    with open("temp_concat_list.txt", "w") as f:
        for temp_file in temp_files:
            f.write(f"file '{temp_file}'\n")
    
    # Use ffmpeg to concatenate the chunks
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "temp_concat_list.txt", "-c", "copy", "temp_video.mp4"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Merge the processed video with the new audio
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", "temp_video.mp4",
        "-i", "temp_audio.mp3",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-c:a", "aac",
        "-strict", "experimental",
        output_video
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup temporary files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    if os.path.exists("temp_video.mp4"):
        os.remove("temp_video.mp4")
    if os.path.exists("temp_audio.mp3"):
        os.remove("temp_audio.mp3")
    if os.path.exists("temp_concat_list.txt"):
        os.remove("temp_concat_list.txt")
    
    print(f"Output saved to {output_video}")

if __name__ == "__main__":
    main()