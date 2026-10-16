import json, sys, os, base64, hashlib
out = sys.argv[1]
for src in sys.argv[2:]:
    d = json.load(open(src))
    nodes = d['data']['theme']['files']['nodes']
    for n in nodes:
        fn = n['filename']; b = n['body']; t = b['__typename']
        p = os.path.join(out, fn); os.makedirs(os.path.dirname(p), exist_ok=True)
        if t == 'OnlineStoreThemeFileBodyText':
            data = b['content'].encode('utf-8')
        elif t == 'OnlineStoreThemeFileBodyBase64':
            data = base64.b64decode(b['contentBase64'])
        else:
            print('URL-ONLY', fn, b.get('url','')[:80]); continue
        open(p, 'wb').write(data)
        ok = hashlib.md5(data).hexdigest() == n['checksumMd5']
        print(('OK ' if ok else 'MD5-MISMATCH ') + fn, len(data))
    pi = d['data']['theme']['files'].get('pageInfo', {})
    if pi.get('hasNextPage'): print('HAS NEXT PAGE', src, pi.get('endCursor'))
