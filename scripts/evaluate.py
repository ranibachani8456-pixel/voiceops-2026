"""Preserve real responses. Decision labels require an explicit schema mapping, not guessed columns."""
import argparse,csv,json
from pathlib import Path
from backend.app.main import agent,store,settings

def main():
    p=argparse.ArgumentParser();p.add_argument('--questions',required=True);p.add_argument('--id-column',required=True);p.add_argument('--question-column',required=True);p.add_argument('--decision-column');p.add_argument('--decision-map',help='JSON mapping official labels to answer/clarify/refuse/escalate/unknown');a=p.parse_args()
    mapping=json.loads(a.decision_map) if a.decision_map else {};results=[]
    for row in csv.DictReader(open(a.questions)):
        for mode in ['baseline','rag']:
            result={'id':row[a.id_column],'question':row[a.question_column],'mode':mode,'expected_decision':row.get(a.decision_column) if a.decision_column else None}
            try:
                result.update(agent.turn(store.new_session(),result['question'],baseline=mode=='baseline'))
                expected=mapping.get(result['expected_decision']);result['decision_correct']=result['decision']==expected if expected else None
                result['status']='complete'
            except Exception as e: result.update(status='error',error_type=type(e).__name__)
            results.append(result)
    metrics={}
    for mode in ['baseline','rag']:
        scored=[r for r in results if r['mode']==mode and r.get('decision_correct') is not None]
        metrics[mode]={'scored':len(scored),'correct':sum(r['decision_correct'] for r in scored),'decision_accuracy':100*sum(r['decision_correct'] for r in scored)/len(scored) if scored else None}
    report={'status':'complete','metrics':metrics,'results':results,'limitations':'Decision agreement is not full answer correctness. Retrieval and conversation metrics need inspected official reference schemas.'}
    settings.runtime_dir.mkdir(exist_ok=True);(settings.runtime_dir/'evaluation.json').write_text(json.dumps(report,indent=2))
    with (settings.runtime_dir/'evaluation.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=['id','mode','question','answer','expected_decision','decision','decision_correct','status'],extrasaction='ignore');writer.writeheader();writer.writerows(results)
if __name__=='__main__':main()
