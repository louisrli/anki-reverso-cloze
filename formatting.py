import string

INVALID_PUNCTUATION = ''.join([c for c in string.punctuation if c != "'"])

def strip_punctuation(s: str) -> str:
    """
    Strips punctuation since Reverso matches punctuation exactly.
    Does NOT remove apostrophes.
    """
    return s.translate(str.maketrans('', '', INVALID_PUNCTUATION))
