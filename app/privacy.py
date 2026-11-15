import re


def redact(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", text)
    return re.sub(r"(?<!\d)\d{10,}(?!\d)", "[identifier removed]", text)
