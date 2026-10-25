import subprocess, uuid
from pathlib import Path
class Voice:
    def __init__(self,settings): self.s=settings
    def normalize(self,path):
        target=self.s.runtime_dir/'audio'/(uuid.uuid4().hex+'.wav');target.parent.mkdir(parents=True,exist_ok=True)
        try:
            import soundfile as sf
            info=sf.info(str(path))
            if not 0<info.duration<=self.s.max_audio_seconds: raise ValueError('Audio must be between 0 and 60 seconds')
            samples, rate=sf.read(str(path),always_2d=True)
            if rate==16000:
                sf.write(str(target),samples.mean(axis=1),16000,subtype='PCM_16');return target
        except (RuntimeError, sf.LibsndfileError):
            pass
        try:
            probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True,timeout=15,check=True)
            duration=float(probe.stdout)
            if not 0<duration<=self.s.max_audio_seconds: raise ValueError('Audio must be between 0 and 60 seconds')
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-ac','1','-ar','16000',str(target)],capture_output=True,timeout=30,check=True)
        except (subprocess.SubprocessError,FileNotFoundError) as e: raise ValueError('Invalid audio, or ffmpeg/ffprobe unavailable') from e
        return target
    def transcribe(self,path):
        if not self.s.gnani_api_key: raise ValueError('GNANI_API_KEY is not configured')
        from gnani.stt import GnaniSTTClient
        normalized=self.normalize(path)
        try:
            result=GnaniSTTClient(api_key=self.s.gnani_api_key,timeout=45).transcribe(str(normalized),language_code=self.s.language)
            text=result.get('transcript','').strip()
            if not text: raise ValueError('No speech was recognized')
            return text
        finally: normalized.unlink(missing_ok=True)
    def synthesize(self,text):
        if not self.s.gnani_api_key: raise ValueError('GNANI_API_KEY is not configured')
        from gnani.tts import GnaniTTSClient, AudioConfig
        audio=GnaniTTSClient(api_key=self.s.gnani_api_key,timeout=45).synthesize(text,voice=self.s.tts_voice,model=self.s.tts_model,language=self.s.language,audio_config=AudioConfig(container='wav',sample_rate=16000))
        path=self.s.runtime_dir/'audio'/(uuid.uuid4().hex+'.wav');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(audio)
        return path
