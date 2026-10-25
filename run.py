"""Batch audio runner. Metadata JSON: [{file, conversation_id, turn}]."""
import argparse,json,shutil
from pathlib import Path
from backend.app.main import agent,voice,store

def run(input_dir,output_dir,metadata=None):
    source=Path(input_dir).resolve();output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    rows=json.loads(Path(metadata).read_text()) if metadata else [{'file':p.name,'conversation_id':p.name,'turn':0} for p in sorted(source.iterdir()) if p.suffix.lower() in {'.wav','.mp3','.webm','.ogg','.m4a','.flac'}]
    sessions={};results=[]
    for i,row in enumerate(sorted(rows,key=lambda r:(str(r['conversation_id']),int(r['turn'])))):
        result={'input_filename':row['file'],'conversation_id':row['conversation_id'],'turn':row['turn'],'status':'error'}
        try:
            path=(source/row['file']).resolve()
            if not path.is_relative_to(source): raise ValueError('Input path escapes input directory')
            if path.stat().st_size>voice.s.max_audio_bytes: raise ValueError('Audio file too large')
            sid=sessions.setdefault(row['conversation_id'],None)
            if sid is None: sid=store.new_session();sessions[row['conversation_id']]=sid
            transcript=voice.transcribe(path);result.update(transcript=transcript)
            result.update(agent.turn(sid,transcript));audio=voice.synthesize(result['answer'])
            target=output/f'{i:04d}.wav';shutil.copyfile(audio,target)
            result.update(status='complete',output_audio=target.name)
        except Exception as e: result.update(error_type=type(e).__name__,error='Processing failed; verify provider configuration and input. '+str(e) if isinstance(e,ValueError) else 'External provider or runtime failure')
        (output/f'{i:04d}.json').write_text(json.dumps(result,indent=2));(output/f'{i:04d}.txt').write_text(result.get('transcript','')+'\n'+result.get('answer',result.get('error','')))
        results.append(result)
    manifest={'total':len(results),'complete':sum(r['status']=='complete' for r in results),'results':results}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input_dir',required=True);p.add_argument('--output_dir',required=True);p.add_argument('--metadata');a=p.parse_args();run(a.input_dir,a.output_dir,a.metadata)
