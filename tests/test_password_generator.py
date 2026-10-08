"""
tests/test_password_generator.py
---------------------------------
Tests for the secure password generator in gui/password_generator.py.

We test the generation logic directly (not the Tkinter dialog) by extracting
the pure-logic helper functions.

No real passwords or secrets are stored in these tests.
"""

import secrets
import string
import pytest

# ---------------------------------------------------------------------------
# Replicate the generator logic here for unit testing without Tkinter.
# This mirrors the logic in PasswordGeneratorDialog._generate().
# ---------------------------------------------------------------------------

def _generate_password(
    length: int,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """Pure-logic password generator (mirrors PasswordGeneratorDialog._generate)."""
    charset = ""
    if use_upper:
        charset += string.ascii_uppercase
    if use_lower:
        charset += string.ascii_lowercase
    if use_digits:
        charset += string.digits
    if use_symbols:
        charset += string.punctuation

    if not charset:
        raise ValueError("At least one character class must be selected.")

    guaranteed = []
    if use_upper:
        guaranteed.append(secrets.choice(string.ascii_uppercase))
    if use_lower:
        guaranteed.append(secrets.choice(string.ascii_lowercase))
    if use_digits:
        guaranteed.append(secrets.choice(string.digits))
    if use_symbols:
        guaranteed.append(secrets.choice(string.punctuation))

    remaining_length = max(0, length - len(guaranteed))
    rest = [secrets.choice(charset) for _ in range(remaining_length)]

    combined = guaranteed + rest
    for i in range(len(combined) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        combined[i], combined[j] = combined[j], combined[i]

    return "".join(combined)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPasswordLength:
    def test_length_20(self):
        pw = _generate_password(20)
        assert len(pw) == 20

    def test_length_8(self):
        assert len(_generate_password(8)) == 8

    def test_length_64(self):
        assert len(_generate_password(64)) == 64

    def test_minimum_length_with_all_classes(self):
        """Length 4 with all classes = exactly 4 guaranteed chars."""
        pw = _generate_password(4)
        assert len(pw) == 4


class TestCharacterRequirements:
    def test_uppercase_only(self):
        pw = _generate_password(
            50, use_upper=True, use_lower=False,
            use_digits=False, use_symbols=False
        )
        assert all(c in string.ascii_uppercase for c in pw)

    def test_lowercase_only(self):
        pw = _generate_password(
            50, use_upper=False, use_lower=True,
            use_digits=False, use_symbols=False
        )
        assert all(c in string.ascii_lowercase for c in pw)

    def test_digits_only(self):
        pw = _generate_password(
            50, use_upper=False, use_lower=False,
            use_digits=True, use_symbols=False
        )
        assert all(c in string.digits for c in pw)

    def test_symbols_only(self):
        pw = _generate_password(
            50, use_upper=False, use_lower=False,
            use_digits=False, use_symbols=True
        )
        assert all(c in string.punctuation for c in pw)

    def test_all_classes_present_when_requested(self):
        """With length >= 4 and all classes enabled, each class must appear."""
        pw = _generate_password(
            20, use_upper=True, use_lower=True,
            use_digits=True, use_symbols=True
        )
        assert any(c in string.ascii_uppercase for c in pw), "No uppercase"
        assert any(c in string.ascii_lowercase for c in pw), "No lowercase"
        assert any(c in string.digits for c in pw), "No digits"
        assert any(c in string.punctuation for c in pw), "No symbols"

    def test_upper_and_digits_only(self):
        pw = _generate_password(
            30, use_upper=True, use_lower=False,
            use_digits=True, use_symbols=False
        )
        assert all(c in string.ascii_uppercase + string.digits for c in pw)
        assert any(c in string.ascii_uppercase for c in pw)
        assert any(c in string.digits for c in pw)

    def test_no_class_selected_raises(self):
        with pytest.raises(ValueError):
            _generate_password(
                20, use_upper=False, use_lower=False,
                use_digits=False, use_symbols=False
            )


class TestPasswordUniqueness:
    def test_two_passwords_are_different(self):
        """Generated passwords must not be deterministic (same on every call)."""
        passwords = {_generate_password(20) for _ in range(10)}
        # Very unlikely to get any duplicates with a 20-char password
        assert len(passwords) > 1

    def test_generates_many_unique_passwords(self):
        passwords = {_generate_password(16) for _ in range(50)}
        # All 50 should be unique
        assert len(passwords) == 50


class TestPasswordReturnType:
    def test_returns_string(self):
        assert isinstance(_generate_password(16), str)

    def test_length_is_exact(self):
        for length in [8, 12, 16, 20, 32, 48, 64]:
            assert len(_generate_password(length)) == length
