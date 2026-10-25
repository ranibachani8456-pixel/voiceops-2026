from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.storage import Store
from backend.app.rag import load_chunks
from backend.app.orders import Orders

@pytest.fixture
def store(tmp_path):return Store(tmp_path/'test.sqlite3')
def test_session_isolation_and_reset(store):
    a,b=store.new_session(),store.new_session()
    store.save(a,[{'role':'user','content':'private'}]);assert store.history(b)==[]
    store.reset(a);assert store.history(a)==[]
def test_unknown_session_rejected(store):
    with pytest.raises(ValueError):store.history('missing')
def test_ticket_persists_and_deduplicates(store):
    sid=store.new_session();a=store.ticket(sid,'Please review my request');b=store.ticket(sid,'Please review my request')
    assert a['ticket_id']==b['ticket_id'];assert b['reused'];assert len(Store(store.path).tickets(sid))==1
    assert store.tickets(store.new_session())==[]
def test_ticket_argument_validation(store):
    with pytest.raises(ValueError):store.ticket(store.new_session(),'x')
def test_history_bounded(store):
    sid=store.new_session();store.save(sid,[{'role':'user','content':str(i)} for i in range(40)]);assert len(store.history(sid))==24
def test_current_policy_and_sources(tmp_path):
    (tmp_path/'pol_returns_v4.md').write_text('# Test policy\n\nFixture policy text.\n\n## Eligibility\n\n'+'Test rule. '*300)
    (tmp_path/'pol_returns_v3_superseded.md').write_text('# Excluded test policy')
    chunks=load_chunks(tmp_path)
    assert chunks;assert all(c['filename']=='pol_returns_v4.md' for c in chunks)
    assert all(c['chunk_id'] and c['heading'] and c['text'] for c in chunks)
    assert chunks==load_chunks(tmp_path)
def test_missing_dataset_no_invented_orders(tmp_path):
    with pytest.raises(ValueError,match='blocked'):Orders(tmp_path).lookup('00000000')
def test_api(monkeypatch,tmp_path):
    from backend.app import main
    monkeypatch.setattr(main,'store',Store(tmp_path/'api.db'))
    client=TestClient(main.app)
    assert client.get('/api/health').status_code==200
    sid=client.post('/api/sessions').json()['session_id']
    assert client.get('/api/sessions/'+sid).json()['history']==[]
    assert client.post('/api/chat',json={'session_id':sid,'message':''}).status_code==422
    assert client.get('/api/sessions/invalid').status_code==422
    assert client.delete('/api/sessions/'+sid).status_code==200
    assert client.get('/api/audio/not-a-real-file.wav').status_code==404
    assert client.get('/api/evaluations').json()['metrics'] is None
    assert client.post('/api/voice/turn',data={'session_id':sid},files={'audio':('bad.exe',b'bad')}).status_code==415

def test_voice_adapters(monkeypatch,tmp_path):
    from backend.app.config import Settings
    from backend.app.voice import Voice
    import gnani.stt,gnani.tts
    settings=Settings(gnani_api_key='test-only',runtime_dir=tmp_path)
    voice=Voice(settings);sample=tmp_path/'normalized.wav';sample.write_bytes(b'test')
    monkeypatch.setattr(voice,'normalize',lambda p:sample)
    stt=Mock();stt.transcribe.return_value={'transcript':'  Hello  '}
    monkeypatch.setattr(gnani.stt,'GnaniSTTClient',Mock(return_value=stt))
    assert voice.transcribe(tmp_path/'input.wav')=='Hello'
    tts=Mock();tts.synthesize.return_value=b'RIFF-test-fixture'
    monkeypatch.setattr(gnani.tts,'GnaniTTSClient',Mock(return_value=tts))
    assert voice.synthesize('Hello').read_bytes()==b'RIFF-test-fixture'
    assert tts.synthesize.call_args.kwargs['model']=='timbre-v2.5'

def test_batch_continues_and_groups(monkeypatch,tmp_path):
    import run
    source=tmp_path/'in';source.mkdir();[(source/n).write_bytes(b'fixture') for n in ['a.wav','b.wav','bad.wav']];output=tmp_path/'out';audio=tmp_path/'speech.wav';audio.write_bytes(b'fixture')
    metadata=tmp_path/'meta.json';metadata.write_text(json.dumps([{'file':'b.wav','conversation_id':'c','turn':2},{'file':'a.wav','conversation_id':'c','turn':1},{'file':'bad.wav','conversation_id':'d','turn':0}]))
    monkeypatch.setattr(run.voice,'transcribe',lambda p: (_ for _ in ()).throw(ValueError('Invalid test audio')) if p.name=='bad.wav' else p.name)
    monkeypatch.setattr(run.voice,'synthesize',lambda t:audio)
    calls=[]
    def turn(sid,text):calls.append((sid,text));return {'answer':'fixture answer','sources':[]}
    monkeypatch.setattr(run.agent,'turn',turn)
    manifest=run.run(source,output,metadata)
    assert manifest['total']==3 and manifest['complete']==2
    assert calls[0][0]==calls[1][0] and calls[0][1]=='a.wav'
    assert (output/'manifest.json').exists()

def test_tool_schema():
    from backend.app.agent import OrderArgs,TicketArgs
    with pytest.raises(ValueError):OrderArgs(order_id='../etc')
    with pytest.raises(ValueError):TicketArgs(summary='x')

def test_agent_grounding_memory_tools_and_baseline(monkeypatch,tmp_path):
    from google import genai
    from backend.app.agent import Agent
    from backend.app.config import Settings
    store=Store(tmp_path/'agent.db');sid=store.new_session()
    rag=Mock();rag.search.return_value=[{'chunk_id':'fixture-1','text':'Test fixture, not an official policy','filename':'test.md'}]
    orders=Mock();orders.lookup.return_value={'found':False}
    client=Mock()
    monkeypatch.setattr(genai,'Client',Mock(return_value=client))
    from google.genai import types
    responses=[SimpleNamespace(function_calls=[SimpleNamespace(name='create_ticket',args={'summary':'Please ask a human to review'})],candidates=[SimpleNamespace(content=types.Content(role='model',parts=[types.Part.from_text(text='tool')]))]),SimpleNamespace(function_calls=[],text=json.dumps({'answer':'A human will review your ticket.','used_chunk_ids':['fixture-1','invented'],'decision':'escalate'}))]
    client.models.generate_content.side_effect=responses
    agent=Agent(Settings(gemini_api_key='test-only'),store,rag,orders)
    result=agent.turn(sid,'Please contact a human')
    assert 'AI' in result['answer'];assert len(result['sources'])==1;assert len(store.tickets(sid))==1
    assert store.history(sid)[-1]['verified_tool_results'][0]['name']=='create_ticket'
    rag.reset_mock();client.models.generate_content.side_effect=None;client.models.generate_content.return_value=SimpleNamespace(function_calls=[],text=json.dumps({'answer':'I am an AI assistant','used_chunk_ids':[]}))
    agent.turn(store.new_session(),'hello',baseline=True)
    rag.search.assert_not_called();assert client.models.generate_content.call_args.kwargs['config'].tools is None

def test_empty_stt_and_duration_limits(monkeypatch,tmp_path):
    from backend.app.voice import Voice
    from backend.app.config import Settings
    import gnani.stt, soundfile as sf, numpy as np
    v=Voice(Settings(gnani_api_key='test',runtime_dir=tmp_path))
    wave=tmp_path/'long.wav';sf.write(wave,np.zeros(16000*61),16000)
    with pytest.raises(ValueError,match='60 seconds'):v.normalize(wave)
    wave=tmp_path/'short.wav';sf.write(wave,np.zeros(1600),16000)
    stt=Mock();stt.transcribe.return_value={'transcript':' '}
    monkeypatch.setattr(gnani.stt,'GnaniSTTClient',Mock(return_value=stt))
    with pytest.raises(ValueError,match='No speech'):v.transcribe(wave)

def test_real_faiss_with_mock_embeddings(monkeypatch,tmp_path):
    import numpy as np, sys
    from backend.app.rag import RAG
    from backend.app.config import Settings
    kb=tmp_path/'dataset'/'kb';kb.mkdir(parents=True);(kb/'fixture.md').write_text('# Test fixture\n\nBlue bicycles are mentioned in this technical test.')
    class Embedder:
        def __init__(self,*a,**kw):pass
        def encode(self,texts,**kw):return np.array([[1.,0.,0.] for _ in texts],dtype='float32')
    monkeypatch.setitem(sys.modules,'sentence_transformers',SimpleNamespace(SentenceTransformer=Embedder))
    settings=Settings(dataset_dir=kb.parent,runtime_dir=tmp_path/'runtime')
    rag=RAG(settings);found=rag.search('fixture');assert found[0]['score']==pytest.approx(1)
    assert (settings.runtime_dir/'index/vectors.faiss').exists()
    reloaded=RAG(settings);assert reloaded.search('fixture')==found
    old=rag.fingerprint;(kb/'fixture.md').write_text('# Test fixture\n\nChanged technical text.');rag.build();assert rag.fingerprint!=old
