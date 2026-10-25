import json, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .config import settings
from .storage import Store
from .rag import RAG, load_chunks
from .orders import Orders
from .agent import Agent
from .voice import Voice
store=Store(settings.runtime_dir/'voiceops.sqlite3');rag=RAG(settings)
agent=Agent(settings,store,rag,Orders(settings.dataset_dir));voice=Voice(settings)
app=FastAPI(title='VoiceOps 2026')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type'])
class Turn(BaseModel):
    session_id: str
    message: str=Field(min_length=1,max_length=6000)
    baseline: bool=False
@app.exception_handler(ValueError)
async def value_error(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422,content={'detail':str(exc)})
@app.get('/api/health')
def health():
    chunks = load_chunks(settings.dataset_dir / 'kb')
    return dict(status='ok', dataset_present=bool(chunks), dataset_path=str(settings.dataset_dir),
                knowledge_documents=len({c['filename'] for c in chunks}),
                indexed_documents=len({c['filename'] for c in rag.chunks}),
                indexed_chunks=len(rag.chunks), gemini_model=settings.gemini_model, gemini_thinking_level=settings.gemini_thinking_level, gemini_configured=bool(settings.gemini_api_key),
                gnani_configured=bool(settings.gnani_api_key), reference_date='2026-10-20')
@app.post('/api/sessions')
def new_session(): return {'session_id':store.new_session()}
@app.get('/api/sessions/{sid}')
def session(sid:str): return dict(history=store.history(sid),tickets=store.tickets(sid))
@app.delete('/api/sessions/{sid}')
def reset(sid:str): store.reset(sid);return {'status':'reset'}
@app.post('/api/chat')
def chat(turn:Turn):
    try: return agent.turn(turn.session_id,turn.message,turn.baseline)
    except ValueError: raise
    except Exception as exc:
        if getattr(exc, 'code', None) == 429:
            raise HTTPException(429, 'Gemini quota exhausted or rate limited; retry after the provider reset or configure another supported GEMINI_MODEL')
        if getattr(exc, 'code', None) in {503, 504}:
            raise HTTPException(getattr(exc, 'code'), 'Gemini temporarily unavailable or generation deadline exceeded; verified state and any created ticket are preserved')
        raise HTTPException(502, 'Provider request failed; check credentials, quota, model and network')
@app.post('/api/voice/turn')
def voice_turn(audio:UploadFile=File(...),session_id:str=Form(...)):
    store.history(session_id)
    folder=settings.runtime_dir/'uploads';folder.mkdir(parents=True,exist_ok=True)
    suffix=Path(audio.filename or '').suffix.lower()
    if suffix not in {'.wav','.mp3','.webm','.ogg','.m4a','.flac'}: raise HTTPException(415,'Unsupported audio format')
    path=folder/(uuid.uuid4().hex+suffix)
    try:
        with path.open('wb') as output:
            size=0
            while chunk:=audio.file.read(65536):
                size+=len(chunk)
                if size>settings.max_audio_bytes: raise HTTPException(413,'Audio upload too large')
                output.write(chunk)
        transcript=voice.transcribe(path);result=agent.turn(session_id,transcript)
        try:
            generated=voice.synthesize(result['answer']);result['audio_url']='/api/audio/'+generated.name
        except Exception: result['audio_error']='Reply generated, but speech synthesis failed. Text is preserved.'
        return dict(result,transcript=transcript)
    except (ValueError,HTTPException): raise
    except Exception: raise HTTPException(502,'Voice provider request failed')
    finally: path.unlink(missing_ok=True)
@app.get('/api/audio/{name}')
def audio_file(name:str):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}\.wav',name): raise HTTPException(404)
    path=settings.runtime_dir/'audio'/name
    if not path.exists(): raise HTTPException(404)
    return FileResponse(path,media_type='audio/wav')
@app.get('/api/evaluations')
def evaluations():
    path=settings.runtime_dir/'evaluation.json'
    return json.loads(path.read_text()) if path.exists() else {'status':'not_run','reason':'Official practice dataset required','metrics':None,'results':[]}
