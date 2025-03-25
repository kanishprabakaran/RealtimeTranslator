# Multilingual Speech-to-Text Translator

## Overview

This application is a Flask-based web service that records speech, transcribes it into text using AWS Transcribe, translates it to English using Google's Gemini AI with ontology-based corrections, and finally translates the English text into multiple target languages using Azure Translator.

## Features

- Record audio directly in the browser.
- Upload and validate WAV audio files.
- Transcribe speech to text using AWS Transcribe.
- Correct transcription errors and translate text to English using Gemini AI.
- Translate English text into multiple languages using Azure Translator.
- Store audio files securely in AWS S3.
- Supports multiple Indian languages including Tamil, Telugu, Hindi, Malayalam, Kannada, etc.

## Technologies Used

- **Backend:** Python, Flask
- **Cloud Services:**
  - **AWS** (S3 for storage, Transcribe for speech-to-text)
  - **Google Gemini AI** (for ontology-based translation and correction)
  - **Azure Translator** (for language translation)
- **Audio Processing:** PyAudio, Wave
- **Environment Management:** dotenv
- **Logging:** Python logging module

## Prerequisites

### Install Dependencies

Ensure you have Python 3 installed. Install the required dependencies using:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root and add the following variables:

```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=your_aws_region
S3_BUCKET_NAME=your_s3_bucket_name
AZURE_API_KEY=your_azure_api_key
AZURE_REGION=your_azure_region
AZURE_ENDPOINT=https://api.cognitive.microsofttranslator.com
GEMINI_API_KEY=your_gemini_api_key
```

## Running the Application

Start the Flask application using:

```bash
python app.py
```

The application will run on `http://127.0.0.1:5000/` by default.

## API Endpoints

### 1. Home Page

- **Route:** `/`
- **Method:** GET
- **Description:** Renders the main page with language selection options.

### 2. Start Recording

- **Route:** `/start-recording`
- **Method:** POST
- **Description:** Starts audio recording.

### 3. Stop Recording

- **Route:** `/stop-recording`
- **Method:** POST
- **Description:** Stops recording, saves the audio file, and processes it (uploads to S3, transcribes, translates).
- **Request Data:**
  ```json
  {
    "input_language": "te-IN"
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "source_text": "Original text",
    "english_text": "Translated text"
  }
  ```

### 4. Translate to Target Language

- **Route:** `/translate-to-language`
- **Method:** POST
- **Description:** Translates the processed English text into the selected target language.
- **Request Data:**
  ```json
  {
    "target_language": "ta"
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "translated_text": "மொழிபெயர்ப்பு செய்யப்பட்டது",
    "target_language": "Tamil"
  }
  ```

## File Structure

```
├── app.py                   # Main Flask application
├── requirements.txt          # Python dependencies
├── templates/
│   ├── index.html           # HTML file for UI
├── static/
│   ├── styles.css           # CSS file
├── uploads/                 # Directory to store audio files
├── .env                     # Environment variables
├── README.md                # Project documentation
```

## Notes

- The ontology file `Polyhouse Ontology.ttl` is used for context-aware corrections in translation.
- Ensure AWS, Azure, and Google API credentials are correctly configured before running the application.

## Future Enhancements

- Improve UI with real-time visualization of audio processing.
- Add support for more languages.
- Deploy the application to cloud platforms (AWS, GCP, Azure).

