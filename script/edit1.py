import cv2
import numpy as np

# Paths
input_image_path = "content/post.png"
output_image_path = "content/title.png"
text_file_path = "txt/story_title.txt"

# Load the text from the file
with open(text_file_path, "r") as file:
    text = file.read().strip()

# Word wrap function
def wrap_text(text, max_length):
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        # Check if adding the word exceeds the max length
        if len(" ".join(current_line + [word])) <= max_length:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]

    # Append the last line if any words remain
    if current_line:
        lines.append(" ".join(current_line))

    return lines

# Wrap the text to fit within 50 characters per line
max_characters_per_line = 50
text_lines = wrap_text(text, max_characters_per_line)

# Read the image with transparency preserved
image = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)

# Define font properties
font = cv2.FONT_HERSHEY_DUPLEX
font_scale = 3
font_color = (255,255,255,255)  # Black with full alpha

# Get image dimensions
height, width = image.shape[:2]

# Adjust starting offsets for text positioning
x_offset = -30  # Horizontal adjustment
y_offset = 220  # Vertical adjustment

# Calculate total text block height and maximum line width
line_heights = [cv2.getTextSize(line, font, font_scale, 2)[0][1] for line in text_lines]
line_widths = [cv2.getTextSize(line, font, font_scale, 2)[0][0] for line in text_lines]
text_height = sum(line_heights) + (len(text_lines) - 1) * 24  # Add padding between lines
max_line_width = max(line_widths)

# Calculate starting position to center the text with offsets
x = (width - max_line_width) // 2 + x_offset
y = (height - text_height) // 2 + line_heights[0] + y_offset

# Ensure image has an alpha channel
if len(image.shape) < 3 or image.shape[2] < 4:
    image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)

 # Function to draw even bolder text
def draw_bold_text(image, text, position, font, scale, color, thickness):
    x, y = position
    offsets = [
        (-2, -2), (-2, 0), (-2, 2), 
        (0, -2), (0, 2), 
        (2, -2), (2, 0), (2, 2), 
        (-1, -1), (-1, 1), (1, -1), (1, 1), 
        (0, 0)  # Center
    ]  # Added more offsets for increased bold effect
    for dx, dy in offsets:
        cv2.putText(image, text, (x + dx, y + dy), font, scale, color, thickness, cv2.LINE_AA)

# Put wrapped text on the image
for i, line in enumerate(text_lines):
    line_height = line_heights[i]
    draw_bold_text(image, line, (x, y + i * (line_height + 24)), 
                   font, font_scale, font_color, 2)

# Save the image with transparency
cv2.imwrite(output_image_path, image)
print(f"Saved the updated image to {output_image_path}")
