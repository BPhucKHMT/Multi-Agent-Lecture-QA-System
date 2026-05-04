from src.api.services.chat_service import JsonStreamCleaner

cleaner = JsonStreamCleaner()
chunks = [
    '{\n',
    '  "text": "',
    'RNN',
    ' g\u1eb7p',
    ' ph\u1ea3i',
    ' v\u1ea5n',
    ' \u0111\u1ec1',
    ' vanishing gradient',
    ' v\u00e0',
    ' kh\u00f4ng',
    ' nh\u1edb',
    ' \u0111\u01b0\u1ee3c',
    ' th\u00f4ng tin',
    ' \u0111\u1ee7 d\u00e0i',
    ',',
    ' \u0111i\u1ec1u',
    ' n\u00e0y',
    ' d\u1eabn \u0111\u1ebfn',
    ' vi\u1ec7c',
    ' c\u1ea7n',
    ' c\u00f3',
    ' LSTM',
    ' "\n}'
]

out = ""
for chunk in chunks:
    res = cleaner.process_token(chunk)
    out += res
    print(f"Chunk: {chunk!r} -> Res: {res!r}")

print(f"\nFinal: {out!r}")
