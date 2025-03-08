import os

def delete_file():
    files_to_delete = [
        # Initial list of files
        "content/subtitle.mp4",
        "content/edit1.mp4",
        "production/video.mp4",
        "audio/title.mp3",
        "audio/body.mp3",
        "video/body.mp4",
        "video/title.mp4",
        "content/title.mp4",
        "output/title_standardized.mp4",
        "output/subtitle_standardized.mp4",
        "output/title_with_woosh.mp4",
        "output/combined_video.mp4",
        "content/final_video.mp4",
        "production/video.mp4"
    ]

    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            else:
                print(f"File not found: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

if __name__ == "__main__":
    delete_file()
