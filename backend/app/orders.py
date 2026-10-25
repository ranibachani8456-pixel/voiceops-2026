"""Read-only adapter around the official identity-gated dataset helper."""
import re
import types
from pathlib import Path


class Orders:
    def __init__(self, dataset):
        self.dataset = Path(dataset)
        self._helper = None

    def _load(self):
        path = self.dataset / 'tools' / 'tools.py'
        if not path.is_file():
            raise ValueError('Order tools blocked: official dataset helper is missing')
        if self._helper is None:
            # Execute the inspected local helper without creating __pycache__ or
            # runtime ticket files in the official dataset directory.
            module = types.ModuleType('voiceops_official_order_tools')
            module.__file__ = str(path)
            exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
            self._helper = module
        return self._helper

    def lookup(self, order_id, verification_value=None):
        if not re.fullmatch(r'[0-9]{4}[ -]?[0-9]{4}', order_id):
            raise ValueError('Order ID must contain eight digits')
        if verification_value is not None and not re.fullmatch(r'(?:[0-9]{4}|[0-9]{6})', verification_value):
            raise ValueError('Supply one phone suffix (4 digits) or delivery pincode (6 digits)')
        result = self._load().lookup_order(order_id, verification_value=verification_value)
        # The pincode is a verification secret, not response or history content.
        return {key: value for key, value in result.items()
                if key not in {'delivery_pincode', 'phone_last4', 'phone', 'email'}}
