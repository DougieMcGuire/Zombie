import cv2
import subprocess
import random
from pathlib import Path
import sys

def get_audio_duration(audio_path):
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        sys.exit(1)

def get_video_duration(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return frame_count / fps

try:
    # Get audio durations and calculate total
    print("Getting audio durations...")
    body_duration = get_audio_duration('audio/body.mp3')
    title_duration = get_audio_duration('audio/title.mp3')
    total_audio_duration = body_duration + title_duration
    print(f"Total audio duration: {total_audio_duration:.2f} seconds")

    # Get background video info
    print("Getting background video duration...")
    bg_path = 'content/bg.mp4'
    bg_duration = get_video_duration(bg_path)
    print(f"Background video duration: {bg_duration:.2f} seconds")

    # Calculate random start time for background clip
    max_start = bg_duration - total_audio_duration
    if max_start <= 0:
        print("Error: Background video is shorter than combined audio")
        sys.exit(1)
    start_time = random.uniform(0, max_start)
    print(f"Selected start time: {start_time:.2f} seconds")

    # First, combine the audio files
    print("Combining audio files...")
    temp_audio = 'temp_combined_audio.mp3'
    subprocess.run([
        'ffmpeg', '-y',
        '-i', 'audio/title.mp3',
        '-i', 'audio/body.mp3',
        '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[aout]',
        '-map', '[aout]',
        temp_audio
    ], check=True)

    # Extract background clip
    temp_bg = 'temp_bg.mp4'
    print("Extracting background clip...")
    subprocess.run([
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-t', str(total_audio_duration),
        '-i', bg_path,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-an',  # Remove any existing audio
        temp_bg
    ], check=True)

    # Combine video and combined audio
    print("Combining video and audio...")
    subprocess.run([
        'ffmpeg', '-y',
        '-i', temp_bg,
        '-i', temp_audio,
        '-c:v', 'copy',
        '-c:a', 'libmp3lame',
        '-map', '0:v:0',  # Map video from first input
        '-map', '1:a:0',  # Map audio from second input
        '-shortest',
        'content/edit1.mp4'
    ], check=True)

    # Clean up temporary files
    print("Cleaning up temporary files...")
    for temp_file in [temp_bg, temp_audio]:
        if Path(temp_file).exists():
            Path(temp_file).unlink()
    
    print("Processing complete! Output saved as content/edit1.mp4")

except subprocess.CalledProcessError as e:
    print(f"FFmpeg error: {e}")
    # Clean up temporary files in case of error
    for temp_file in [temp_bg, temp_audio]:
        if Path(temp_file).exists():
            Path(temp_file).unlink()
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    # Clean up temporary files in case of error
    for temp_file in [temp_bg, temp_audio]:
        if Path(temp_file).exists():
            Path(temp_file).unlink()
    sys.exit(1)