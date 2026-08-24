""" 
    the unguessable part of a per-student link.

    a student is given an address like /s/9f3c1a...  which shows their own row
    and nothing else. the token is worked out from a secret kept on disk rather
    than stored per student, so the links handed out today still work after the
    server has been restarted
"""
import hashlib
import hmac
import os
import secrets

SECRET_NAME = ".link-secret"
# hex characters kept from the digest; 80 bits is far past guessing
TOKEN_LENGTH = 20

"""
    the secret behind every link.

    it is made once and then reused. losing it does not lose the sheets, but it
    does change every link, so it is written before anything depends on it
"""
def read_secret(directory):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, SECRET_NAME)
    if not os.path.exists(path):
        try:
            # opened this way so it is never readable by anyone else, even briefly
            handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(handle, "wb") as secretFile:
                secretFile.write(secrets.token_bytes(32))
        except FileExistsError:
            pass                              # something else got there first
    with open(path, "rb") as secretFile:
        return secretFile.read()

# the id a whole sheet is reached under; the person who uploaded it keeps this
def new_sheet_id():
    return secrets.token_hex(8)

def is_sheet_id(text):
    return len(text) == 16 and all(character in "0123456789abcdef" for character in text)

"""
    one student's token, worked out from the sheet it belongs to and the row it
    sits on. nothing is written down, and the same row always gives the same link
"""
def student_token(secret, sheetId, position):
    message = f"{sheetId}:{position}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:TOKEN_LENGTH]
