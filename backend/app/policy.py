"""Constrained order decisions with evidence loaded from current official documents."""
import re
from .rag import load_chunks


class Policies:
    def __init__(self, dataset):
        self.dataset = dataset

    def sections(self, *ids):
        return [c for c in load_chunks(self.dataset / 'kb') if c['section_id'] in ids]

    def assess(self, order):
        if not order:
            return {}
        evidence = self.sections('CAN-1', 'CAN-2', 'CAN-3', 'REF-1', 'REF-2', 'DEL-4', 'ESC-1')
        by_id = {c['section_id']: c['text'] for c in evidence}
        result = {'order_id': order['order_id'], 'status': order['status'], 'payment_method': order['payment_method']}
        # Apply the inspected cancellation rule only when its authoritative section exists.
        if order.get('shipped_on') and 'CAN-2' in by_id:
            result['cancellation'] = {'eligible': False, 'reason': 'Order has shipped; cancellation is unavailable. Refusal or eligible return follows policy.', 'section_id': 'CAN-2'}
        elif order.get('delivery_type') == 'slot' and 'CAN-3' in by_id:
            result['cancellation'] = {'decision': 'clarify', 'reason': 'Grocery slot start time is not recorded; ask for the time shown in My Orders.', 'section_id': 'CAN-3'}
        elif order['status'] in {'placed', 'packed'} and 'CAN-1' in by_id:
            result['cancellation'] = {'eligible': True, 'reason': 'Customer can cancel from My Orders before shipping; assistant cannot execute cancellation.', 'section_id': 'CAN-1'}
        else:
            result['cancellation'] = {'decision': 'unknown', 'reason': 'Do not infer cancellation eligibility for this status.'}
        # Extract the current published payment-method timing verbatim from REF-2.
        labels = {'upi': 'UPI', 'card': 'Credit or debit card', 'netbanking': 'Net banking', 'wallet': 'ZentroMart Wallet'}
        label = labels.get(order['payment_method'])
        if label and 'REF-2' in by_id:
            for line in by_id['REF-2'].splitlines():
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                if len(cells) == 2 and cells[0] == label:
                    result['refund_after_initiation'] = {'timeline': cells[1], 'section_id': 'REF-2'}
        if order.get('shipped_on') and order['payment_method'] != 'cod' and 'REF-1' in by_id:
            result['refund_trigger'] = {'section_id': 'REF-1', 'context': 'If refused or returned to origin, refund starts on warehouse receipt, not now. Do not claim it is already initiated.'}
        if 'DEL-4' in by_id:
            result['discretionary_compensation'] = {'allowed': False, 'section_id': 'DEL-4', 'reason': 'No compensation beyond the documented policy entitlement can be awarded by this assistant.'}
        if 'ESC-1' in by_id and int(order.get('contacts_last_7_days') or 0) >= 2:
            result['required_escalation'] = 'repeat_contact'
        return result

    def escalation_reason(self, order, message):
        # Source-gated ESC-1 conditions. Unknown/hypothetical claims are never
        # treated as authority to disclose an unverified order.
        if not self.sections('ESC-1'):
            return None
        if order and int(order.get('contacts_last_7_days') or 0) >= 2:
            return 'repeat_contact'
        if re.search(r'legal action|consumer court|police complaint|file a lawsuit', message, re.I):
            return 'legal_complaint'
        if re.search(r'swelling battery|swollen battery|burning smell|sparks|injury', message, re.I):
            return 'product_safety'
        if re.search(r"did not (?:place|make|authorize)|didn't (?:place|make|authorize)|unauthorized (?:order|payment|account)", message, re.I):
            return 'unauthorized_activity'
        if order and order.get('damage_issue') and order.get('damage_sku'):
            affected = [i for i in order.get('items', []) if i['sku'] == order['damage_sku']]
            if any(int(i['unit_price_inr']) > 10000 for i in affected):
                return 'high_value_damage'
        return None
