""" 
    passwords, sessions and join codes.

    nothing here knows about marks. it answers three questions: is this the
    password that was set, who is holding this cookie, and what code do students
    type to find their organisation
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

# how long a signed-in browser stays signed in
SESSION_SECONDS = 14 * 24 * 60 * 60

"""
    join codes are read off a board and typed in by hand, so the alphabet
    leaves out the characters people confuse: O and 0, I and 1, S and 5
"""
CODE_ALPHABET = "ABCDEFGHJKLMNPQRTUVWXY2346789"
CODE_LENGTH = 8

def new_join_code():
    letters = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    return f"{letters[:4]}-{letters[4:]}"

# what a person typed, compared without caring about case or the dash
def tidy_join_code(text):
    kept = "".join(character for character in str(text).upper() if character.isalnum())
    return f"{kept[:4]}-{kept[4:]}" if len(kept) == CODE_LENGTH else ""

def new_id():
    return secrets.token_hex(8)

# ---------- passwords ----------

MIN_PASSWORD = 8

"""
    hashing a password so the stored form is useless on its own.

    scrypt is deliberately slow and memory hungry, which is what makes a stolen
    table expensive to attack. it needs a modern OpenSSL, so a build without it
    falls back to many rounds of pbkdf2
"""
def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    raw = password.encode("utf-8")
    try:
        digest = hashlib.scrypt(raw, salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
        return f"scrypt${salt.hex()}${digest.hex()}"
    except (ValueError, AttributeError):
        digest = hashlib.pbkdf2_hmac("sha256", raw, salt, 240000, dklen=32)
        return f"pbkdf2${salt.hex()}${digest.hex()}"

def check_password(password, stored):
    try:
        scheme, saltHex, digestHex = str(stored).split("$")
        salt = bytes.fromhex(saltHex)
    except ValueError:
        return False

    raw = password.encode("utf-8")
    if scheme == "scrypt":
        try:
            made = hashlib.scrypt(raw, salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
        except (ValueError, AttributeError):
            return False
    elif scheme == "pbkdf2":
        made = hashlib.pbkdf2_hmac("sha256", raw, salt, 240000, dklen=32)
    else:
        return False
    # compared this way so the time taken says nothing about how close it was
    return hmac.compare_digest(made.hex(), digestHex)

# the one rule, kept as a sentence so the page and the check cannot disagree
PASSWORD_RULE = f"at least {MIN_PASSWORD} characters"

def password_problem(password, again=None):
    if len(password or "") < MIN_PASSWORD:
        return f"Please choose a password of {PASSWORD_RULE}."
    if again is not None and password != again:
        return "Those two passwords are not the same."
    return ""

# ---------- sessions ----------

def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _unb64(text):
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))

"""
    a session is the whole answer, signed, rather than a key into a table.

    the browser carries who it is and when that stops being true; the signature
    is what stops it editing either
"""
def make_session(secret, kind, personId, orgId, now=None):
    body = {"kind": kind, "id": personId, "org": orgId,
            "exp": int(now or time.time()) + SESSION_SECONDS}
    payload = _b64(json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64(hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"

def read_session(secret, cookie, now=None):
    if not cookie or "." not in cookie:
        return None
    payload, _, signature = cookie.rpartition(".")
    expected = _b64(hmac.new(secret, payload.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        body = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if body.get("exp", 0) < (now or time.time()):
        return None
    return body
