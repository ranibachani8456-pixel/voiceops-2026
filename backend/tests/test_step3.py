"""Actual official records, real lookup/SQLite/policies; only external generation mocked."""
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.agent import Agent, OrderArgs
from backend.app.config import Settings
from backend.app.orders import Orders
from backend.app.policy import Policies
from backend.app.storage import Store


@pytest.fixture
def official():
    root = Settings().dataset_dir
    if not (root / 'data' / 'orders.csv').exists():
        pytest.skip('Official dataset is not configured')
    orders = list(csv.DictReader((root / 'data' / 'orders.csv').open()))
    customers = {r['customer_id']: r for r in csv.DictReader((root / 'data' / 'customers.csv').open())}
    selected = next(r for r in orders if r['status'] == 'shipped' and r['delivery_type'] == 'standard'
                    and r['payment_method'] == 'upi' and r['promised_date'] < '2026-10-20'
                    and int(r['contacts_last_7_days']) < 2)
    return root, selected, customers[selected['customer_id']]['phone'][-4:], orders


@pytest.fixture
def harness(monkeypatch, tmp_path, official):
    from google import genai
    root, record, proof, records = official
    settings = Settings(dataset_dir=root, runtime_dir=tmp_path, gemini_api_key='unit-test-only')
    store = Store(tmp_path / 'test.db')
    rag = Mock(); rag.search.return_value = []
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(function_calls=[], text=json.dumps(
        {'answer': 'AI test response from mocked external model.', 'used_chunk_ids': [], 'decision': 'answer'}))
    monkeypatch.setattr(genai, 'Client', Mock(return_value=client))
    agent = Agent(settings, store, rag, Orders(root))
    return agent, store, client, record, proof, records


def test_real_order_helper_gates_and_joins(official):
    root, record, proof, _ = official
    orders = Orders(root)
    pending = orders.lookup(record['order_id'])
    assert pending['verification_required'] and 'status' not in pending and 'items' not in pending
    result = orders.lookup(record['order_id'], proof)
    assert result['verified'] and result['status'] == record['status']
    assert result['order_id'] == record['order_id'] and result['total_inr'] == int(record['total_inr'])
    expected_items = [r for r in csv.DictReader((root / 'data' / 'order_items.csv').open()) if r['order_id'] == record['order_id']]
    assert len(result['items']) == len(expected_items)
    assert {r['sku'] for r in result['items']} == {r['sku'] for r in expected_items}
    assert all(key not in result for key in ['delivery_pincode', 'phone_last4', 'phone', 'email'])


def test_unknown_and_malformed_ids_do_not_disclose(official):
    root, _, _, records = official
    unknown = next(f'{i:08}' for i in range(100) if f'{i:08}' not in {r['order_id'] for r in records})
    orders = Orders(root)
    assert orders.lookup(unknown)['verification_required']
    result = orders.lookup(unknown, '0000')
    assert result['verified'] is False and 'status' not in result and 'items' not in result
    with pytest.raises(ValueError): orders.lookup('../etc')
    with pytest.raises(ValueError): OrderArgs(order_id='ZM123')


def test_verified_state_survives_followups_history_trimming_and_reload(harness):
    agent, store, client, record, proof, _ = harness
    sid = store.new_session()
    agent.turn(sid, 'My order is delayed.')
    assert not store.state(sid).get('current_order_id')
    agent.turn(sid, record['order_id'])
    assert not store.state(sid).get('verified_order')
    agent.turn(sid, proof)
    result = agent.turn(sid, 'Can I cancel it?')
    assert result['current_order_id'] == record['order_id']
    assert result['policy_decisions']['cancellation']['eligible'] is False
    assert result['policy_decisions']['cancellation']['section_id'] == 'CAN-2'
    assert result['policy_decisions']['discretionary_compensation']['allowed'] is False
    store.save(sid, [])  # verified state is independent of a bounded model history
    agent2 = Agent(agent.s, Store(store.path), agent.rag, Orders(agent.s.dataset_dir))
    refund = agent2.turn(sid, 'How long would the refund take?')
    assert refund['current_order_id'] == record['order_id']
    assert refund['policy_decisions']['refund_after_initiation']['timeline'] == '1 to 3 business days'
    assert any(c['section_id'] == 'REF-2' for c in refund['retrieved_sources'])
    assert proof not in json.dumps(store.history(sid))
    assert proof not in json.dumps(store.state(sid))


def test_verification_limit_persists_and_cannot_be_guessed_by_model(harness):
    agent, store, _, record, proof, _ = harness
    sid = store.new_session();agent.turn(sid, record['order_id'])
    wrong = '0000' if proof != '0000' else '1111'
    with pytest.raises(ValueError, match='supplied'):
        agent._lookup(sid, store.state(sid), record['order_id'], proof, wrong)
    agent.turn(sid, wrong);agent.turn(sid, wrong)
    result = agent.turn(sid, proof)
    assert not store.state(sid).get('verified_order')
    assert any(c['result'].get('verification_locked') for c in result['tool_calls'])
    assert store.state(sid)['verification'][record['order_id']]['attempts'] == 2
    assert not store.tickets(sid)


def test_separate_sessions_and_reset_clear_verification(harness):
    agent, store, client, record, proof, _ = harness
    a, b = store.new_session(), store.new_session()
    agent.turn(a, record['order_id']);agent.turn(a, proof)
    result = agent.turn(b, 'Can I cancel it?')
    prompt = json.loads(client.models.generate_content.call_args.kwargs['contents'][0].parts[0].text)
    assert result['current_order_id'] is None and prompt['verified_order'] is None
    assert record['order_id'] not in json.dumps(prompt)
    store.reset(a)
    assert not store.state(a) and not store.history(a)


def test_paraphrased_ticket_requests_reuse_real_ticket(harness):
    agent, store, _, record, proof, _ = harness
    sid = store.new_session();agent.turn(sid, 'My order is delayed');agent.turn(sid, record['order_id']);agent.turn(sid, proof)
    first = agent.turn(sid, 'Please connect me to a human agent.')
    second = agent.turn(sid, 'I still want a support representative to review this.')
    tickets = store.tickets(sid)
    assert len(tickets) == 1 and re.fullmatch(r'ZT-[a-f0-9]{12}', tickets[0]['id'])
    assert tickets[0]['order_id'] == record['order_id']
    assert 'delayed' in tickets[0]['summary'] and 'Escalation reason' in tickets[0]['summary']
    assert proof not in tickets[0]['summary']
    ids = [c['result']['ticket_id'] for r in [first, second] for c in r['tool_calls'] if c['name'] == 'create_ticket']
    assert set(ids) == {tickets[0]['id']}
    assert Store(store.path).tickets(sid) == tickets


def test_concurrent_ticket_idempotency(tmp_path):
    store = Store(tmp_path / 'tickets.db');sid = store.new_session()
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(lambda n: store.ticket(sid, f'Please review this customer issue, attempt {n}', issue_key='same-issue'), range(12)))
    assert len({r['ticket_id'] for r in results}) == 1 and len(store.tickets(sid)) == 1
    other = store.ticket(sid, 'A separate support issue needs review', issue_key='another-issue')
    assert other['ticket_id'] != results[0]['ticket_id']


def test_repeat_contact_requires_real_escalation(harness):
    agent, store, _, _, _, records = harness
    repeated = next(r for r in records if int(r['contacts_last_7_days']) >= 2)
    customers = {r['customer_id']: r for r in csv.DictReader((agent.s.dataset_dir / 'data' / 'customers.csv').open())}
    proof = customers[repeated['customer_id']]['phone'][-4:]
    sid = store.new_session();agent.turn(sid, repeated['order_id']);result = agent.turn(sid, proof)
    assert result['policy_decisions']['required_escalation'] == 'repeat_contact'
    assert len(store.tickets(sid)) == 1


def test_ticket_survives_model_failure_and_retry(harness):
    agent, store, client, _, _, _ = harness
    sid = store.new_session();client.models.generate_content.side_effect = RuntimeError('Simulated external failure')
    with pytest.raises(RuntimeError):agent.turn(sid, 'I need a human agent')
    first = store.tickets(sid)[0]['id']
    client.models.generate_content.side_effect = None
    agent.turn(sid, 'I need a representative')
    assert len(store.tickets(sid)) == 1 and store.tickets(sid)[0]['id'] == first


def test_missing_policy_evidence_does_not_invent_timing(official, tmp_path):
    root, record, proof, _ = official
    verified = Orders(root).lookup(record['order_id'], proof)
    result = Policies(tmp_path).assess(verified)
    assert result['cancellation']['decision'] == 'unknown'
    assert 'refund_after_initiation' not in result


def test_repeated_tool_call_does_not_consume_two_verification_attempts(harness):
    from google.genai import types
    agent, store, client, record, proof, _ = harness
    sid = store.new_session();agent.turn(sid, record['order_id'])
    wrong = '0000' if proof != '0000' else '1111'
    client.models.generate_content.side_effect = [
        SimpleNamespace(function_calls=[SimpleNamespace(name='lookup_order', args={'order_id': record['order_id'], 'verification_value': wrong})], candidates=[SimpleNamespace(content=types.Content(role='model', parts=[types.Part.from_text(text='tool')]))]),
        SimpleNamespace(function_calls=[], text=json.dumps({'answer': 'Please try verification once more.', 'used_chunk_ids': [], 'decision': 'clarify'}))]
    agent.turn(sid, wrong)
    assert store.state(sid)['verification'][record['order_id']]['attempts'] == 1


def test_unjustified_ticket_tool_call_is_rejected(harness):
    from backend.app.agent import TicketArgs
    agent, store, _, _, _, _ = harness
    sid = store.new_session()
    with pytest.raises(ValueError, match='customer-requested'):
        agent._ticket(sid, {'issue_key': 'test'}, TicketArgs(summary='Unjustified model attempt to create a ticket'), None, False)
    assert store.tickets(sid) == []


def test_separate_issues_can_have_identical_ticket_summaries(tmp_path):
    store = Store(tmp_path / 'issues.db');sid = store.new_session()
    first = store.ticket(sid, 'Customer asks for review', issue_key='first')
    second = store.ticket(sid, 'Customer asks for review', issue_key='second')
    assert first['ticket_id'] != second['ticket_id']


def test_quota_failure_returns_actionable_http_status(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import main
    class QuotaError(Exception):
        code = 429
    monkeypatch.setattr(main.agent, 'turn', Mock(side_effect=QuotaError()))
    response = TestClient(main.app).post('/api/chat', json={'session_id': 'unit-test', 'message': 'Hello'})
    assert response.status_code == 429 and 'quota' in response.json()['detail'].lower()


def test_switching_orders_never_reuses_wrong_order_details(harness):
    agent, store, _, record, proof, records = harness
    other = next(r for r in records if r['order_id'] != record['order_id'])
    sid = store.new_session();agent.turn(sid, record['order_id']);agent.turn(sid, proof)
    pending = agent.turn(sid, other['order_id'])
    assert not pending['policy_decisions'] and not store.state(sid).get('verified_order')
    restored = agent.turn(sid, record['order_id'])
    assert restored['policy_decisions']['order_id'] == record['order_id']
    assert store.state(sid)['verified_order']['order_id'] == record['order_id']


def test_legal_and_safety_handover_are_source_supported(harness):
    agent, store, _, _, _, _ = harness
    for message in ['I will take legal action about this issue.', 'My device has a swelling battery.']:
        sid = store.new_session();result = agent.turn(sid, message)
        assert any(c['name'] == 'create_ticket' and c['result']['created'] for c in result['tool_calls'])
        assert len(store.tickets(sid)) == 1
