import cv2
import numpy as np
import subprocess
import ffmpeg

def get_audio_duration(audio_path):
    """Returns the duration of the audio file in seconds."""
    result = subprocess.run(
        ["ffprobe", "-i", audio_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def ease_in_out_quad(t):
    """Smooth easing function for animations."""
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

def overlay_image_on_video(input_video, overlay_image, audio_file, output_video):
    """Overlays an image with smooth zoom-in and fall-out animation for the duration of an audio file on a video while keeping the audio intact."""
    
    # Get overlay duration
    overlay_duration = get_audio_duration(audio_file)
    
    # Open video
    cap = cv2.VideoCapture(input_video)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_video = "temp_video.mp4"
    out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
    
    # Load overlay image and ensure it's a larger square
    overlay = cv2.imread(overlay_image, cv2.IMREAD_UNCHANGED)
    if overlay is None:
        raise FileNotFoundError(f"Error: Could not load overlay image from {overlay_image}")
    
    overlay_size = int(min(width, height) / 1.2)  # Ensure integer division
    overlay = cv2.resize(overlay, (overlay_size, overlay_size))
    
    frame_count = 0
    overlay_frames = int(overlay_duration * fps)
    zoom_in_frames = int(fps * 0.3)  # Faster zoom-in
    fall_out_frames = int(fps * 0.3)  # Faster fall-out
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count < overlay_frames:
            scale = 1.0
            y_offset = 0
            
            if frame_count < zoom_in_frames:
                t = frame_count / zoom_in_frames
                scale = 0.5 + (0.5 * ease_in_out_quad(t))  # Smooth zoom-in effect
            elif frame_count > overlay_frames - fall_out_frames:
                t = (frame_count - (overlay_frames - fall_out_frames)) / fall_out_frames
                y_offset = int(ease_in_out_quad(t) * (height * 0.5))  # Smooth fall-out effect
            
            new_size = int(overlay_size * scale)
            resized_overlay = cv2.resize(overlay, (new_size, new_size))
            
            y_start = max(0, (height - new_size) // 2 + y_offset)
            x_start = max(0, (width - new_size) // 2)
            
            overlay_resized = np.zeros((height, width, 4), dtype=np.uint8)
            h, w, _ = resized_overlay.shape
            overlay_resized[y_start:y_start+h, x_start:x_start+w] = resized_overlay[:min(h, height-y_start), :min(w, width-x_start)]
            
            if overlay.shape[2] == 4:
                alpha_channel = overlay_resized[:, :, 3] / 255.0
                overlay_rgb = overlay_resized[:, :, :3]
                frame = (1.0 - alpha_channel[:, :, None]) * frame + alpha_channel[:, :, None] * overlay_rgb
                frame = frame.astype(np.uint8)
        
        out.write(frame)
        frame_count += 1
    
    cap.release()
    out.release()
    
    # Merge with original audio
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_video, "-i", input_video, "-c:v", "copy", "-c:a", "aac", "-strict", "-2", "-map", "0:v:0", "-map", "1:a:0", output_video
    ])
    
    print(f"Output saved to {output_video}")

# Run the function
overlay_image_on_video("content/edit2.mp4", "content/title.png", "audio/title.mp3", "content/edit3.mp4")
