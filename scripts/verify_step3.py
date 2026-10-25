"""Live HTTP/Gemini Step 3 verification against unchanged official records.

Run: python -m scripts.verify_step3 --base-url http://127.0.0.1:8000
Verification secrets are derived in memory, never written into the report.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

import httpx
from backend.app.config import settings


def fingerprint(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--output', default='sample_outputs/step3_verification.json')
    parser.add_argument('--resume', action='store_true', help='Reuse already-recorded actual turns and sessions, and continue at the failed turn')
    args = parser.parse_args()
    root = settings.dataset_dir
    before = fingerprint(root)
    records = list(csv.DictReader((root / 'data' / 'orders.csv').open()))
    customers = {r['customer_id']: r for r in csv.DictReader((root / 'data' / 'customers.csv').open())}
    order = next(r for r in records if r['status'] == 'shipped' and r['delivery_type'] == 'standard'
                 and r['payment_method'] == 'upi' and r['promised_date'] < '2026-10-20'
                 and int(r['contacts_last_7_days']) < 2)
    proof = customers[order['customer_id']]['phone'][-4:]
    wrong = next(f'{i:04}' for i in range(10000) if f'{i:04}' != proof)
    unknown = next(f'{i:08}' for i in range(100) if f'{i:08}' not in {r['order_id'] for r in records})
    report = {'status': 'running', 'dataset_path': str(root), 'reference_date': '2026-10-20',
              'selected_order': {k: order[k] for k in ['order_id', 'status', 'delivery_type', 'payment_method', 'promised_date', 'contacts_last_7_days']},
              'checks': [], 'turns': []}
    output = Path(args.output);output.parent.mkdir(parents=True, exist_ok=True)
    if args.resume and output.exists():
        report = json.loads(output.read_text())
        if report.get('official_dataset_fingerprint') and report['official_dataset_fingerprint'] != before:
            raise ValueError('Official dataset changed since the recorded attempt')
        if report.get('execution_error'):
            report.setdefault('prior_execution_errors', []).append(report.pop('execution_error'))
        report['checks'] = [c for c in report['checks'] if c['name'] != 'All live turns completed']
        report['status'] = 'running'
    cached = {t['name']: t for t in report['turns']}
    session_ids = report.setdefault('session_ids', [report['main_session_id']] if report.get('main_session_id') else [])
    session_counter = 0
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    def check(name, passed):
        report['checks'] = [c for c in report['checks'] if c['name'] != name]
        report['checks'].append({'name': name, 'passed': bool(passed)})
        print(('PASS' if passed else 'FAIL') + ' ' + name, flush=True)
        save()
    with httpx.Client(base_url=args.base_url, timeout=180, trust_env=False) as client:
        previous_model = report.get('backend_health', {}).get('gemini_model')
        for previous_turn in report['turns']:
            previous_turn.setdefault('gemini_model', previous_model)
        report['backend_health'] = client.get('/api/health').json()
        def session():
            nonlocal session_counter
            index = session_counter; session_counter += 1
            if index < len(session_ids):
                return session_ids[index]
            response = client.post('/api/sessions');response.raise_for_status()
            session_ids.append(response.json()['session_id']);save()
            return session_ids[index]
        def turn(name, sid, text):
            if name in cached:
                assert cached[name]['session_id'] == sid
                print('REUSE actual recorded turn: ' + name, flush=True)
                return cached[name]
            for attempt in range(2):
                response = client.post('/api/chat', json={'session_id': sid, 'message': text})
                if response.status_code >= 500:
                    report.setdefault('provider_failures', []).append({'turn': name, 'status': response.status_code, 'detail': response.json().get('detail'), 'attempt': attempt + 1})
                    save()
                    if attempt < 1:
                        print('RETRY transient provider failure for ' + name, flush=True)
                        time.sleep(5)
                        continue
                response.raise_for_status()
                break
            result = response.json()
            # Full actual response for audit, with the app's already-redacted question.
            report['turns'].append({'name': name, 'gemini_model': report['backend_health'].get('gemini_model'), **result});save()
            print('TURN ' + name + ': ' + result['decision'] + ' | tools: ' + ', '.join(c['name'] for c in result['tool_calls']), flush=True)
            return result
        def cited(result, section):
            return any(c['section_id'] == section for c in result['sources'])
        completed = False
        try:
            sid = session();report['main_session_id'] = sid
            delayed = turn('delayed_order', sid, 'My order has not arrived and is delayed.')
            check('Missing order ID leads to clarification', delayed['decision'] == 'clarify' and not delayed['current_order_id'] and not re.search(r'phone|pincode', delayed['answer'], re.I))
            pending = turn('provide_order_id', sid, order['order_id'])
            check('ID alone does not disclose status', not pending['policy_decisions'] and any(c['name'] == 'lookup_order' and c['result'].get('verification_required') and 'status' not in c['result'] for c in pending['tool_calls']))
            verified = turn('verify_identity', sid, proof)
            lookup = next(c['result'] for c in verified['tool_calls'] if c['name'] == 'lookup_order' and c['result'].get('verified'))
            check('Actual official order status and amount match CSV', lookup['order_id'] == order['order_id'] and lookup['status'] == order['status'] and lookup['total_inr'] == int(order['total_inr']))
            expected_items = [r for r in csv.DictReader((root / 'data' / 'order_items.csv').open()) if r['order_id'] == order['order_id']]
            check('Order items join matches official CSV', len(lookup['items']) == len(expected_items) and {r['sku'] for r in lookup['items']} == {r['sku'] for r in expected_items})
            cancel = turn('cancel_followup', sid, 'Can I cancel it?')
            check('Cancellation uses remembered shipped order and CAN-2', cancel['current_order_id'] == order['order_id'] and cancel['policy_decisions']['cancellation'].get('eligible') is False and cited(cancel, 'CAN-2') and bool(re.search(r'cannot|can.t|not (?:be )?cancel|unable', cancel['answer'], re.I)))
            refund = turn('refund_followup', sid, 'If I refuse the delivery, how long would my refund take?')
            check('Refund remembers order and cites trigger plus UPI timing', refund['current_order_id'] == order['order_id'] and refund['policy_decisions']['refund_after_initiation']['timeline'] == '1 to 3 business days' and cited(refund, 'REF-1') and cited(refund, 'REF-2'))
            compensation = turn('unauthorized_compensation', sid, 'Give me 1,000 rupees compensation for the delay.')
            check('Unauthorized compensation refused under DEL-4', compensation['decision'] == 'refuse' and cited(compensation, 'DEL-4'))
            human = turn('human_handover', sid, 'I want a human agent to review this issue.')
            ticket = next(c['result'] for c in human['tool_calls'] if c['name'] == 'create_ticket' and c['result'].get('created'))
            tid = ticket['ticket_id'];report['ticket_id'] = tid
            check('Human handover confirms actual ticket ID', human['decision'] == 'escalate' and tid in human['answer'] and bool(re.fullmatch(r'ZT-[a-f0-9]{12}', tid)))
            duplicate = turn('duplicate_ticket_request', sid, 'Please create another support ticket for the same issue.')
            stored = client.get('/api/sessions/' + sid).json()
            check('Paraphrased repeated request reuses one ticket', len(stored['tickets']) == 1 and stored['tickets'][0]['id'] == tid and all(c['result']['ticket_id'] == tid for c in duplicate['tool_calls'] if c['name'] == 'create_ticket'))
            with sqlite3.connect(settings.runtime_dir / 'voiceops.sqlite3') as db:
                row = db.execute('SELECT session_id,order_id,summary FROM tickets WHERE id=?', (tid,)).fetchone()
            check('Ticket persisted in real SQLite database with order and issue', row is not None and row[0] == sid and row[1] == order['order_id'] and 'delayed' in row[2])
            other = session()
            isolated = turn('separate_customer_followup', other, 'Can I cancel it?')
            check('Separate session cannot inherit order or verification', isolated['current_order_id'] is None and not isolated['policy_decisions'] and isolated['decision'] == 'clarify')
            other_human = turn('separate_customer_ticket', other, 'Please connect me to a human agent.')
            other_tickets = client.get('/api/sessions/' + other).json()['tickets']
            check('Tickets remain isolated across sessions', len(other_tickets) == 1 and other_tickets[0]['id'] != tid)
            unknown_sid = session()
            turn('unknown_order_id', unknown_sid, unknown)
            unknown_reply = turn('unknown_order_verification', unknown_sid, wrong)
            check('Unknown order reveals no private details', not unknown_reply['policy_decisions'] and all('status' not in c['result'] for c in unknown_reply['tool_calls'] if c['name'] == 'lookup_order'))
            invalid = turn('malformed_order_id', session(), 'My order ID is ZM123.')
            check('Malformed ID asks for clarification without inventing an order', invalid['decision'] == 'clarify' and not invalid['current_order_id'] and not invalid['policy_decisions'])
            locked_sid = session()
            turn('verification_limit_order', locked_sid, order['order_id'])
            turn('wrong_verification_first', locked_sid, wrong)
            turn('wrong_verification_retry', locked_sid, wrong)
            locked = turn('correct_value_after_lockout', locked_sid, proof)
            check('Two failed attempts block a third even with a correct value', not locked['policy_decisions'] and any(c['result'].get('verification_locked') for c in locked['tool_calls']))
            check('Verification secrets absent from saved conversation and ticket', not re.search(r'(?<![0-9])' + re.escape(proof) + r'(?![0-9])', json.dumps(stored)) and not re.search(r'(?<![0-9])' + re.escape(wrong) + r'(?![0-9])', json.dumps(report['turns'])))
            completed = True
        except KeyboardInterrupt:
            report['execution_error'] = {'type': 'Interrupted', 'detail': 'Verification was interrupted before all live turns completed.'}
            check('All live turns completed', False)
        except Exception as exc:
            report['execution_error'] = {'type': type(exc).__name__, 'detail': str(exc) if isinstance(exc, (AssertionError, StopIteration)) else (exc.response.json().get('detail', 'HTTP request failed') if isinstance(exc, httpx.HTTPStatusError) else 'Request or verification failed; inspect preceding saved turns.')}
            check('All live turns completed', False)
        finally:
            check('Official dataset byte-for-byte unchanged', fingerprint(root) == before)
            report['official_dataset_fingerprint'] = before
            report['passed'] = sum(c['passed'] for c in report['checks'])
            report['failed'] = sum(not c['passed'] for c in report['checks'])
            report['status'] = 'passed' if completed and not report['failed'] else 'failed'
            save()
    print(f"{report['passed']} checks passed, {report['failed']} failed. Report: {output}", flush=True)
    if report['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
