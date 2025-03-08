import asyncio
import os
import edge_tts

async def generate_audio(input_file, output_file, sex_file):
    """
    Generate audio from a text file using Edge TTS with voice selection and faster speech.
    
    :param input_file: Path to the input text file
    :param output_file: Path to save the output MP3 file
    :param sex_file: Path to the file containing gender ('m' or 'f')
    """
    # Ensure the audio directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Read the text content
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    
    # Read the sex file to determine voice
    with open(sex_file, 'r', encoding='utf-8') as f:
        sex = f.read().strip().lower()
    
    # Select voice based on sex
    if sex == 'm':
        # Male voice
        voice = "en-US-SteffanNeural"
    elif sex == 'f':
        # Female voice
        voice = "en-US-JennyNeural"
    else:
        raise ValueError(f"Invalid sex setting in {sex_file}. Must be 'm' or 'f'.")
    
    # Create the communication with fine-tuned speech rate and pitch for a natural sound
    communicate = edge_tts.Communicate(
        text, 
        voice, 
        rate="+0%",  # Neutral rate, no speed up (adjust this if needed)
        pitch="+5Hz"  # Slightly increased pitch to sound natural (adjust if needed)
    )
    
    # Generate the audio file
    await communicate.save(output_file)
    print(f"Audio generated: {output_file}")

async def main():
    try:
        # Generate title audio
        await generate_audio(
            input_file='txt/story_title.txt', 
            output_file='audio/title.mp3', 
            sex_file='txt/sex2.txt'
        )
        
        # Generate body audio
        await generate_audio(
            input_file='txt/story_body.txt', 
            output_file='audio/body.mp3', 
            sex_file='txt/sex.txt'
        )
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    asyncio.run(main())
