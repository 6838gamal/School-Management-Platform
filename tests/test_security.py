"""Unit tests for password hashing and session tokens (no DB required)."""

from app.core.security import (
    decode_session,
    encode_session,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("StrongPass!2026")
        assert hashed != "StrongPass!2026"
        assert verify_password("StrongPass!2026", hashed)

    def test_wrong_password_rejected(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_multibyte_password_beyond_72_bytes(self):
        # كلمة مرور عربية تتجاوز حد bcrypt (72 بايت) — يجب ألا ترفع خطأً
        long_arabic = "كلمة_مرور_سرية_طويلة_جداً_" * 20
        hashed = hash_password(long_arabic)
        assert verify_password(long_arabic, hashed)

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed)

    def test_hashes_are_salted(self):
        assert hash_password("same-pass") != hash_password("same-pass")


class TestSessionTokens:
    def test_encode_decode_roundtrip(self):
        token = encode_session({"user_id": "123", "permissions": ["a", "b"]})
        payload = decode_session(token)
        assert payload is not None
        assert payload["user_id"] == "123"

    def test_tampered_token_rejected(self):
        token = encode_session({"user_id": "1"})
        forged = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
        assert decode_session(forged) is None

    def test_decode_respects_max_age(self):
        token = encode_session({"user_id": "1"})
        # أقصى عمر سالب لا يمكن تحقيقه أبدًا → يجب رفض التوكن
        assert decode_session(token, max_age=-1) is None
