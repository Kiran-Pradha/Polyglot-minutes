# 🎙️ Polyglot Minutes - Meeting Summarizer

An AI-powered meeting transcription and action extraction tool built with FastAPI and OpenAI Whisper.

## Features

- 🎤 **Multi-language Transcription**: Supports English, Hindi, and Hinglish using OpenAI Whisper
- ✅ **Action Item Extraction**: Automatically identifies actionable items from meeting transcripts
- 🎯 **Priority Detection**: Categorizes actions as High, Medium, or Low priority
- 🌐 **Modern Web UI**: Beautiful, responsive interface for easy file upload and results viewing
- 📊 **Real-time Processing**: Fast transcription and action extraction

## Technology Stack

- **Backend**: FastAPI (Python)
- **AI Model**: OpenAI Whisper (small model)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Server**: Uvicorn

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd polyglot-minutes
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Note: This will install PyTorch and Whisper, which may take a few minutes.

## Usage

### 1. Start the API Server

```bash
python main.py
```

The server will start at `http://localhost:8001`

### 2. Open the Web UI

Open the `index.html` file in your web browser, or run a simple HTTP server:

```bash
# Python 3
python -m http.server 8080

# Then open http://localhost:8080/index.html
```

### 3. Use the Application

1. **Upload Audio**: Drag and drop or click to select an audio file (WAV, MP3, M4A)
2. **Process**: Click "Process Meeting" to transcribe and extract actions
3. **View Results**: See the transcript, action items, and summary

## API Endpoints

### `POST /transcribe`
Transcribes an audio file using Whisper.

**Request**: Audio file upload
**Response**: 
```json
{
  "transcript": "Full transcript text",
  "segments": [{"start": 0, "end": 5, "text": "First segment"}]
}
```

### `POST /actions`
Extracts action items from a transcript.

**Request**:
```json
{
  "transcript": "Meeting transcript text"
}
```

**Response**:
```json
{
  "actions": [
    {"item": "Prepare budget report", "priority": "High"},
    {"item": "Schedule review meeting", "priority": "Medium"}
  ]
}
```

### `POST /notes`
Complete pipeline: transcribe audio and extract actions.

**Request**: Audio file upload
**Response**: 
```json
{
  "transcript": "Full transcript",
  "summary_short": ["Bullet point 1", "Bullet point 2"],
  "summary_detailed": "Detailed summary text",
  "actions": [
    {"item": "Action item 1", "priority": "High"}
  ]
}
```

### `GET /`
Health check endpoint.
## Action Extraction Logic

The action extraction algorithm identifies actionable items by:

1. **Pattern Matching**: Searches for common action phrases like:
   - "need to", "will", "should", "must"
   - "let's", "can you", "please"
   - "action item", "follow up on"
   - "prepare", "schedule", "create", etc.

2. **Priority Detection**: Analyzes keywords to assign priority:
   - **High**: urgent, asap, critical, important
   - **Medium**: this week, soon, next week
   - **Low**: when possible, eventually

3. **Deduplication**: Removes duplicate or very similar action items

## Project Structure

```
polyglot-minutes/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── index.html          # Web UI
└── README.md           # This file
```

## Development

### Testing the API

You can test the API using curl:

```bash
# Health check
curl http://localhost:8001/

# Transcribe
curl -X POST http://localhost:8001/transcribe \
  -F "file=@your-audio-file.wav"

# Extract actions
curl -X POST http://localhost:8001/actions \
  -H "Content-Type: application/json" \
  -d '{"transcript": "We need to prepare the budget report by Friday."}'
```

### Customization

- **Change Whisper Model**: Edit `main.py` line 20 to use "tiny", "base", "medium", or "large" models
- **Adjust Action Patterns**: Modify the `action_patterns` list in the `extract_actions()` function
- **Update Priority Logic**: Edit the priority keyword lists in `extract_actions()`

## Troubleshooting

### Port Already in Use
If port 8000 is already in use:
```python
# Edit main.py last line to use a different port
uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
```

### CORS Issues
If you're running the UI from a different origin, make sure CORS is enabled in `main.py` (already configured).

### Audio Format Issues
Whisper supports most audio formats. If you encounter issues, try converting to WAV:
```bash
# Using ffmpeg
ffmpeg -i input.mp3 output.wav
```

## Future Enhancements

- [ ] Add real summarization models (replace placeholder)
- [ ] Add speaker identification/diarization
- [ ] Export to PDF/Markdown
- [ ] Support video file uploads
- [ ] Add user authentication
- [ ] Store meeting history in database

## License

This project is open source and available for educational purposes.

## Contributors

- API Development & Action Extraction
- UI Design & Implementation
- Summarization (to be implemented by Kiran)
- Action extraction (implemented, ready for Akshaya's enhancement)

## Contact

For questions or suggestions, please open an issue or reach out to the team.