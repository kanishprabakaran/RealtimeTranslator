import os
import uuid
import time
import json
import urllib.request
import logging
import wave
import pyaudio
import google.generativeai as genai
import requests
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multilingual_translator")

# AWS configuration
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")
bucket_name = os.getenv("S3_BUCKET_NAME")

# Azure Translator configuration
azure_api_key = os.getenv("AZURE_API_KEY")
azure_region = os.getenv("AZURE_REGION")
azure_endpoint = os.getenv("AZURE_ENDPOINT")

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize S3 and Transcribe clients
s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region,
)
transcribe_client = boto3.client(
    "transcribe",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region,
)

# Global variables to store state
current_session_id = None
current_english_text = None
is_recording = False
audio_frames = []

# List of supported languages for AWS Transcribe
SUPPORTED_INPUT_LANGUAGES = {
    "te-IN": "Telugu",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "en-US": "English",
    "ml-IN": "Malayalam",
    "kn-IN": "Kannada"
}

# List of supported output languages for Azure Translator
SUPPORTED_OUTPUT_LANGUAGES = {
    "ta": "Tamil",
    "te": "Telugu",
    "hi": "Hindi",
    "ml": "Malayalam",
    "kn": "Kannada",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "pa": "Punjabi",
    "en": "English"
}

def validate_wav_file(file_path):
    """Validates if the file is a valid WAV audio file."""
    try:
        with wave.open(file_path, "rb") as wav_file:
            logger.info(
                f"Valid WAV file - Channels: {wav_file.getnchannels()}, Sample Rate: {wav_file.getframerate()}, Frames: {wav_file.getnframes()}"
            )
        return True
    except wave.Error as e:
        logger.error(f"Invalid WAV file: {str(e)}")
        return False

def upload_to_s3(file_path, bucket, object_name):
    """Uploads a file to an S3 bucket."""
    try:
        logger.info(f"Uploading {file_path} to S3...")
        with open(file_path, "rb") as file_data:
            s3_client.upload_fileobj(file_data, bucket, object_name)
        logger.info("File uploaded to S3 successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to upload to S3: {str(e)}")
        return False

def transcribe_audio(job_name, file_uri, language_code="te-IN"):
    """Transcribes an audio file using Amazon Transcribe."""
    try:
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": file_uri},
            MediaFormat="wav",
            LanguageCode=language_code,
        )
        logger.info(f"Started transcription job: {job_name}")

        while True:
            job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            status = job["TranscriptionJob"]["TranscriptionJobStatus"]
            logger.info(f"Job status: {status}")

            if status == "COMPLETED":
                transcript_uri = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                response = urllib.request.urlopen(transcript_uri, timeout=30)
                data = json.loads(response.read())
                
                logger.info(f"Full transcript data: {json.dumps(data, indent=2)}")
                
                if "results" in data and "transcripts" in data["results"] and data["results"]["transcripts"]:
                    text = data["results"]["transcripts"][0]["transcript"]
                    if text:
                        logger.info(f"Transcription completed: {text}")
                        return text
                    else:
                        logger.error("Transcription returned empty text.")
                        return None
                else:
                    logger.error(f"Unexpected transcript format: {data}")
                    return None

            elif status == "FAILED":
                error_reason = job["TranscriptionJob"].get("FailureReason", "Unknown reason")
                logger.error(f"Transcription failed: {error_reason}")
                return None

            time.sleep(5)  # Wait 5 seconds before checking again

    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return None

def correct_and_translate(source_text, source_lang):
    """Translates source text to English using Gemini API with context awareness."""
    try:
        with open("./Polyhouse Ontology.ttl", "r") as f:
            onto = f.read()
        
        prompt = f"""
        I'll give you an ontology file and a {SUPPORTED_INPUT_LANGUAGES.get(source_lang, 'unknown language')} text. The {SUPPORTED_INPUT_LANGUAGES.get(source_lang, 'unknown language')} text might have errors related to specific terms in the ontology.

        First, analyze the ontology file to understand its domain and key terms.
        Then, examine the {SUPPORTED_INPUT_LANGUAGES.get(source_lang, 'unknown language')} text for words that might be misused or misspelled based on context.
        Finally, return ONLY the corrected English translation. Don't include any explanations or additional text.

        Ontology file:
        {onto}

        Tamil text: {source_text}
        """

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        if response and hasattr(response, 'text'):
            translated_text = response.text.strip()
            logging.info(f"Translated to English: {translated_text}")
            return translated_text
        else:
            logging.error("Error: No valid response from the model.")
            return "Error: No valid translation received."
    
    except Exception as e:
        logging.error(f"Translation error: {str(e)}")
        return f"Error: {str(e)}"

def translate_to_target_language(english_text, target_lang):
    """Translates English text to target language using Azure Translator."""
    try:
        endpoint = "https://api.cognitive.microsofttranslator.com"
        path = "/translate"
        constructed_url = endpoint + path
        
        params = {
            'api-version': '3.0',
            'from': 'en',
            'to': target_lang
        }
        
        headers = {
            'Ocp-Apim-Subscription-Key': azure_api_key,
            'Ocp-Apim-Subscription-Region': azure_region,
            'Content-type': 'application/json'
        }
        
        body = [{'text': english_text}]
        
        response = requests.post(constructed_url, params=params, headers=headers, json=body)
        
        if response.status_code == 200:
            translated_text = response.json()[0]["translations"][0]["text"]
            logging.info(f"Translated to {target_lang}: {translated_text}")
            return translated_text
        else:
            logging.error(f"Azure Translation failed: {response.text}")
            return "Error: Translation failed."
            
    except Exception as e:
        logging.error(f"Translation error: {str(e)}")
        return f"Error: {str(e)}"

def process_audio(audio_path, input_language):
    """Processes audio file: validates, uploads to S3, transcribes, and translates."""
    global current_session_id, current_english_text

    try:
        if not validate_wav_file(audio_path):
            logger.error("Invalid WAV file. Exiting.")
            return {"status": "error", "message": "Invalid WAV file"}

        session_id = str(uuid.uuid4())
        current_session_id = session_id
        s3_file_name = f"{session_id}.wav"
        s3_uri = f"s3://{bucket_name}/{s3_file_name}"

        if not upload_to_s3(audio_path, bucket_name, s3_file_name):
            logger.error("Failed to upload to S3. Exiting.")
            return {"status": "error", "message": "Failed to upload to S3"}

        source_text = transcribe_audio(session_id, s3_uri, input_language)
        if not source_text or not source_text.strip():
            logger.error("Transcription failed.")
            return {"status": "error", "message": "Transcription failed"}

        english_text = correct_and_translate(source_text, input_language)
        if not english_text:
            logger.error("Translation to English failed.")
            return {"status": "error", "message": "Translation to English failed"}

        current_english_text = english_text

        return {
            "status": "success",
            "source_text": source_text,
            "english_text": english_text
        }

    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return {"status": "error", "message": f"Error: {str(e)}"}

def record_audio():
    """Records audio from the microphone and saves to file."""
    global is_recording, audio_frames
    
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024
    WAVE_OUTPUT_FILENAME = "recorded_audio.wav"

    audio = pyaudio.PyAudio()

    print("\n" + "="*50)
    print("Starting recording... Press Enter to stop")
    print("="*50 + "\n")

    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    is_recording = True
    audio_frames = []

    # Recording in a separate thread so we can listen for Enter key
    def recording_thread():
        while is_recording:
            data = stream.read(CHUNK)
            audio_frames.append(data)

    import threading
    thread = threading.Thread(target=recording_thread)
    thread.start()

    # Wait for Enter key to stop recording
    input()
    is_recording = False
    thread.join()

    print("\nStopping recording...")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save the recorded data as a WAV file
    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(audio_frames))

    print(f"Audio saved to {WAVE_OUTPUT_FILENAME}")
    return WAVE_OUTPUT_FILENAME

def main():
    """Main terminal interface for the translation system."""
    print("="*50)
    print("Multilingual Translation System")
    print("="*50)
    print("\nSupported Input Languages:")
    for code, name in SUPPORTED_INPUT_LANGUAGES.items():
        print(f"{code}: {name}")
    
    print("\nSupported Output Languages:")
    for code, name in SUPPORTED_OUTPUT_LANGUAGES.items():
        print(f"{code}: {name}")
    
    while True:
        print("\nOptions:")
        print("1. Record and translate")
        print("2. Translate existing English text to another language")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            # Record and translate
            print("\nAvailable input languages:")
            for code, name in SUPPORTED_INPUT_LANGUAGES.items():
                print(f"{code}: {name}")
                
            input_lang = input("\nEnter input language code (e.g., 'te-IN'): ").strip()
            if input_lang not in SUPPORTED_INPUT_LANGUAGES:
                print("Invalid language code. Please try again.")
                continue
                
            audio_file = record_audio()
            result = process_audio(audio_file, input_lang)
            
            if result["status"] == "success":
                print("\n" + "="*50)
                print("Translation Results:")
                print("="*50)
                print(f"\nOriginal Text ({SUPPORTED_INPUT_LANGUAGES[input_lang]}):")
                print(result["source_text"])
                print("\nEnglish Translation:")
                print(result["english_text"])
            else:
                print("\nError occurred during processing:")
                print(result["message"])
                
        elif choice == "2":
            # Translate existing English text
            if not current_english_text:
                print("\nNo English text available. Please record and translate first.")
                continue
                
            print("\nAvailable output languages:")
            for code, name in SUPPORTED_OUTPUT_LANGUAGES.items():
                print(f"{code}: {name}")
                
            output_lang = input("\nEnter target language code (e.g., 'ta'): ").strip()
            if output_lang not in SUPPORTED_OUTPUT_LANGUAGES:
                print("Invalid language code. Please try again.")
                continue
                
            translated_text = translate_to_target_language(current_english_text, output_lang)
            
            print("\n" + "="*50)
            print("Translation Result:")
            print("="*50)
            print(f"\nEnglish Text:")
            print(current_english_text)
            print(f"\n{SUPPORTED_OUTPUT_LANGUAGES[output_lang]} Translation:")
            print(translated_text)
            
        elif choice == "3":
            print("\nExiting...")
            break
            
        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    main()
