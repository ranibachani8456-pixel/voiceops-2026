"""Explicit live provider test. Saves sanitized statuses and real successful responses only."""
import json
from pathlib import Path
from backend.app.main import agent,voice,store
results={}
try:
    r=agent.turn(store.new_session(),'Please introduce yourself in one sentence.',baseline=True)
    results['gemini']={'status':'passed','response':r['answer']}
except Exception as e:results['gemini']={'status':'failed','error_type':type(e).__name__,'status_code':getattr(e,'code',None)}
try:
    path=voice.synthesize('Hello. I am the ZentroMart AI support assistant.')
    results['gnani_tts']={'status':'passed','audio_filename':path.name,'bytes':path.stat().st_size}
    transcript=voice.transcribe(path)
    results['gnani_stt']={'status':'passed','transcript':transcript}
except Exception as e:
    results['gnani_tts' if 'gnani_tts' not in results else 'gnani_stt']={'status':'failed','error_type':type(e).__name__,'status_code':getattr(e,'status_code',None)}
Path('sample_outputs/integration_smoke.json').write_text(json.dumps(results,indent=2,default=str));print(json.dumps(results,indent=2,default=str))
