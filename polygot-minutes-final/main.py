from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import uvicorn
import tempfile
import whisper
import re
import string
import os
import logging
import torch
from typing import List, Dict


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("polyglot-minutes")


app = FastAPI(title="Polyglot Minutes API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


model_size =  "small"# options: "tiny", "base", "small", "medium", "large"
device = "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
try:
    logger.info(f"Loading Whisper model '{model_size}' on {device} ...")
    whisper_model = whisper.load_model(model_size, device=device)
    logger.info("✅ Whisper model loaded successfully.")
except Exception as e:
    if device != "cpu":
        logger.warning(f"MPS load failed ({e}). Falling back to CPU...")
        device = "cpu"
        whisper_model = whisper.load_model(model_size, device=device)
        logger.info("✅ Whisper model loaded on CPU.")
    else:
        logger.error(f"❌ Whisper model failed to load: {e}")
        raise RuntimeError("Failed to load Whisper model. Check installation.")

#
class SummarizeRequest(BaseModel):
    transcript: str
    target_lang: str = "en"

class ActionRequest(BaseModel):
    transcript: str

EN_STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can cannot could did do does doing down during each few for from further had
has have having he he'd he'll he's her here here's hers herself him himself his how how's i i'd
i'll i'm i've if in into is it it's its itself let's me more most mustn't my myself no nor not of
off on once only or other ought our ours ourselves out over own same shan't she she'd she'll she's
shouldn't so some such than that that's the their theirs them themselves then there there's
these they they'd they'll they're they've this those through to too under until up very was we
we'd we'll we're we've were what what's when when's where where's which while who who's whom why
why's with would you you'd you'll you're you've your yours yourself yourselves
""".split())

def sentence_split(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'[.!?]\s+', text) if s.strip()]

def word_tokenize(text: str) -> List[str]:
    words = text.lower().translate(str.maketrans('', '', string.punctuation)).split()
    return [w for w in words if w not in EN_STOPWORDS and len(w) > 2]

def summarize_text(transcript: str) -> Dict[str, str]:
    sents = sentence_split(transcript)
    if not sents:
        return {"summary_short": [], "summary_detailed": ""}
    words = word_tokenize(transcript)
    freq: Dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    scored = []
    for sent in sents:
        score = sum(freq.get(w, 0) for w in word_tokenize(sent))
        scored.append((score, sent))
    scored.sort(reverse=True)
    short = [s for _, s in scored[:4]]
    detailed = " ".join(s for _, s in scored[:8]) or transcript[:800]
    if not short and transcript:
        short = [transcript[:140] + ("..." if len(transcript) > 140 else "")]
    return {"summary_short": short, "summary_detailed": detailed}

def extract_actions(transcript: str) -> List[Dict]:
    actions: List[Dict] = []
    action_patterns = [
        r'need to (.*?)(?:\.|$)', r'will (.*?)(?:\.|$)', r'should (.*?)(?:\.|$)',
        r'must (.*?)(?:\.|$)', r"let's (.*?)(?:\.|$)", r'can you (.*?)(?:\.|$)',
        r'please (.*?)(?:\.|$)', r'action item[:\s]+(.*?)(?:\.|$)',
        r'follow up on (.*?)(?:\.|$)', r'prepare (.*?)(?:\.|$)', r'schedule (.*?)(?:\.|$)',
        r'review (.*?)(?:\.|$)', r'create (.*?)(?:\.|$)', r'send (.*?)(?:\.|$)',
        r'update (.*?)(?:\.|$)', r'complete (.*?)(?:\.|$)',
    ]
    hi = ['urgent', 'asap', 'immediately', 'critical', 'important', 'priority', 'today', 'tomorrow']
    mid = ['this week', 'soon', 'next week']
    low = ['when possible', 'eventually', 'nice to have']
    for sentence in re.split(r'[.!?]\s+', transcript):
        sentence = sentence.strip()
        if not sentence:
            continue
        for pattern in action_patterns:
            for match in re.finditer(pattern, sentence, re.IGNORECASE):
                action_text = match.group(1).strip()
                if len(action_text) < 10:
                    continue
                priority = "High" if any(k in sentence.lower() for k in hi) else \
                           "Medium" if any(k in sentence.lower() for k in mid) else \
                           "Low" if any(k in sentence.lower() for k in low) else "Medium"
                action_text = re.sub(r'^(the|a|an)\s+', '', action_text, flags=re.IGNORECASE)
                actions.append({"item": action_text, "priority": priority})
                break
    # dedupe
    seen, uniq = set(), []
    for a in actions:
        key = a["item"].lower()
        if key not in seen:
            seen.add(key); uniq.append(a)
    if not uniq:
        uniq.append({"item": "Review the meeting transcript for action items", "priority": "Medium"})
    return uniq[:5]

# ---------------------------------------------------
# Endpoints
# ---------------------------------------------------
@app.get("/", response_model=dict)
def health() -> dict:
    return {"status": "ok", "service": "polyglot-minutes"}

@app.post("/transcribe", response_model=dict)
async def transcribe(file: UploadFile = File(...)) -> dict:
    try:
        ext = (os.path.splitext(file.filename or "")[1]) or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        logger.info(f"Transcribing file: {file.filename}")
        result = whisper_model.transcribe(tmp_path)
        os.remove(tmp_path)
        return {
            "transcript": result.get("text", ""),
            "segments": [
                {"start": s.get("start"), "end": s.get("end"), "text": s.get("text")}
                for s in (result.get("segments") or [])
            ],
        }
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}")

@app.post("/summarize", response_model=dict)
async def summarize(request: SummarizeRequest) -> dict:
    logger.info("Generating summary...")
    return summarize_text(request.transcript)

@app.post("/actions", response_model=dict)
async def actions(request: ActionRequest) -> dict:
    logger.info("Extracting action items...")
    return {"actions": extract_actions(request.transcript)}

@app.post("/notes", response_model=dict)
async def notes(file: UploadFile = File(...)) -> dict:
    try:
        ext = (os.path.splitext(file.filename or "")[1]) or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        logger.info(f"Processing full pipeline for: {file.filename}")
        tr = whisper_model.transcribe(tmp_path)
        os.remove(tmp_path)
        transcript = tr.get("text", "")
        summaries = summarize_text(transcript)
        actions_list = extract_actions(transcript)
        return {
            "transcript": transcript,
            "summary_short": summaries["summary_short"],
            "summary_detailed": summaries["summary_detailed"],
            "actions": actions_list
        }
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing meeting: {e}")

@app.post("/download-notes")
async def download_notes(file: UploadFile = File(...)):
    ext = (os.path.splitext(file.filename or "")[1]) or ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    tr = whisper_model.transcribe(tmp_path)
    transcript = tr.get("text", "")
    summaries = summarize_text(transcript)
    actions_list = extract_actions(transcript)
    content = (
        "TRANSCRIPT:\n" + transcript + "\n\n"
        + "SUMMARY (bullets):\n" + '\n'.join(summaries["summary_short"]) + "\n\n"
        + "SUMMARY (detailed):\n" + summaries["summary_detailed"] + "\n\n"
        + "ACTION ITEMS:\n" + '\n'.join(f"- {a['item']} [{a['priority']}]" for a in actions_list)
    )
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": "attachment; filename=meeting-notes.txt"}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)