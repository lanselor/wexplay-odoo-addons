# Copyright 2016-2023 Tecnativa, Ignacio Ibeas, Planesnet (OCA reference)
# Copyright 2026 Wexplay
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import binascii
import hashlib
import hmac
import json
import re

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _decode_base64(value):
    if not isinstance(value, str) or not value or len(value) > 16384:
        raise ValueError("Invalid encoded value")
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("Invalid base64") from error


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate parameter")
        result[key] = value
    return result


def _decode_parameters(value):
    try:
        result = json.loads(_decode_base64(value), object_pairs_hook=_unique_json_object)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid merchant parameters") from error
    if not isinstance(result, dict) or any(not isinstance(v, str) for v in result.values()):
        raise ValueError("Invalid merchant parameters")
    return result


def _sign_parameters(secret, order, parameters):
    if not isinstance(order, str) or not re.fullmatch(r"[0-9]{12}", order):
        raise ValueError("Invalid order")
    key = _decode_base64(secret)
    if len(key) != 24:
        raise ValueError("Invalid signing key")
    padded_order = order.encode("ascii")
    padded_order += b"\0" * (-len(padded_order) % 8)
    encryptor = Cipher(algorithms.TripleDES(key), modes.CBC(b"\0" * 8)).encryptor()
    operation_key = encryptor.update(padded_order) + encryptor.finalize()
    digest = hmac.new(operation_key, parameters.encode("ascii"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _verify_signature(secret, order, parameters, signature):
    expected = _sign_parameters(secret, order, parameters)
    return hmac.compare_digest(_decode_base64(signature), _decode_base64(expected))
