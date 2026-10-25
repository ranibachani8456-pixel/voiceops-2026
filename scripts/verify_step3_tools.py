"""Real order/policy/ticket verification independent of provider availability.
No model replies are generated or substituted. Uses the actual application DB.
"""
import csv
import json
import re
import uuid
from pathlib import Path

from backend.app.agent import Agent, TicketArgs
from backend.app.config import settings
from backend.app.orders import Orders
from backend.app.rag import RAG
from backend.app.storage import Store
from .verify_step3 import fingerprint


def main():
    root = settings.dataset_dir
    before = fingerprint(root)
    records = list(csv.DictReader((root / 'data/orders.csv').open()))
    order = next(r for r in records if r['status'] == 'shipped' and r['delivery_type'] == 'standard'
                 and r['payment_method'] == 'upi' and r['promised_date'] < '2026-10-20'
                 and int(r['contacts_last_7_days']) < 2)
    customer = next(r for r in csv.DictReader((root / 'data/customers.csv').open()) if r['customer_id'] == order['customer_id'])
    store = Store(settings.runtime_dir / 'voiceops.sqlite3')
    agent = Agent(settings, store, RAG(settings), Orders(root))
    sid = store.new_session()
    state = {'issue_key': uuid.uuid4().hex, 'current_issue': 'Customer reports a delayed order.', 'current_order_id': order['order_id']}
    pending = agent._lookup(sid, state, order['order_id'], None, None)
    assert pending['verification_required'] and 'status' not in pending
    proof = customer['phone'][-4:]
    verified = agent._lookup(sid, state, order['order_id'], proof, proof)
    assert verified['verified'] and verified['status'] == order['status']
    decisions = agent.policies.assess(verified)
    assert decisions['cancellation']['eligible'] is False
    assert decisions['refund_after_initiation']['timeline'] == '1 to 3 business days'
    assert decisions['discretionary_compensation']['allowed'] is False
    # Simulate process restart: durable verified state is sufficient for a follow-up.
    restored = Store(store.path).state(sid)
    assert restored['verified_order']['order_id'] == order['order_id']
    summary = f"Customer reports delayed order {order['order_id']}, shipped and promised for {order['promised_date']}. Identity checked; current cancellation and refund policies checked. Customer requests human review after unsupported compensation request."
    ticket = agent._ticket(sid, restored, TicketArgs(summary=summary, reason='customer_request', intent='delayed_order'), None, True)
    duplicate = agent._ticket(sid, restored, TicketArgs(summary='Please ask a representative to review the same delayed order again.', reason='customer_request', intent='delayed_order'), None, True)
    assert ticket['created'] and ticket['ticket_id'] == duplicate['ticket_id'] and duplicate['reused']
    persisted = Store(store.path).tickets(sid)
    assert len(persisted) == 1 and persisted[0]['id'] == ticket['ticket_id']
    assert re.fullmatch(r'ZT-[a-f0-9]{12}', ticket['ticket_id'])
    assert fingerprint(root) == before
    report = {'status': 'passed', 'scope': 'Actual read-only official helper, policy decisions, durable session state and SQLite tickets; no model responses generated or substituted.',
              'session_id': sid, 'order_id': order['order_id'], 'checks_passed': ['identity_gate', 'actual_order_status', 'cancellation_CAN-2', 'refund_REF-1_REF-2', 'unauthorized_compensation_DEL-4', 'durable_state_reload', 'persisted_ticket_ID', 'paraphrase_deduplication', 'official_dataset_unchanged'],
              'policy_decisions': decisions, 'ticket': ticket, 'duplicate_ticket': duplicate,
              'tool_calls': ['lookup_order', 'lookup_order', 'assess_order_policy', 'create_ticket', 'create_ticket'],
              'database': str(store.path), 'official_dataset_fingerprint': before}
    Path('sample_outputs/step3_tools_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
