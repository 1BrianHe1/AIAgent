import re

def clean_word(word: str) -> str:

    match = re.search(r'（(.*?)）|\((.*?)\)', word)
    if match:
        return match.group(1) or match.group(2)
    return re.sub(r'（.*?）|\(.*?\)', '', word).strip()