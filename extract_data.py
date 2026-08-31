import re, json, os

with open('idiomas.html', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'const CATS = \[(.*?)\n\];', html, re.S)
body = m.group(1) + '\n'

cat_pattern = re.compile(r"\['([^']*)','([^']*)','([^']*)',\[(.*?)\]\],?\n", re.S)
word_pattern = re.compile(r"\['((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)'\]")

topics = []
for cm in cat_pattern.finditer(body):
    cid, name, emoji, wordsblock = cm.groups()
    words = []
    for wm in word_pattern.finditer(wordsblock):
        pt, en, wemoji = wm.groups()
        pt = pt.replace("\\'", "'")
        en = en.replace("\\'", "'")
        words.append({"pt": pt, "en": en, "emoji": wemoji})
    topics.append({"id": cid, "name": name, "emoji": emoji, "words": words})

print(len(topics), "topics")
total = sum(len(t['words']) for t in topics)
print(total, "words")

os.makedirs('app/data', exist_ok=True)
with open('app/data/words.json', 'w', encoding='utf-8') as f:
    json.dump({"topics": topics}, f, ensure_ascii=False, indent=2)

print("OK")
