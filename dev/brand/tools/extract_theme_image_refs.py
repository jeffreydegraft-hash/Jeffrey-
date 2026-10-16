"""List every shopify:// image/file reference in pulled theme JSON files.

Usage: python3 -I extract_theme_image_refs.py <file-or-dir> [...]
Accepts raw theme JSON (config/settings_data.json, templates/*.json, sections/*.json)
or the JSON result of the ThemeBrandFiles GraphQL query (body.content strings).
Theme JSON may start with a /* ... */ auto-generated comment, stripped first
(same approach as the Shopify toolkit importer's parseThemeJson).
"""
import json, os, re, sys

def parse_theme_json(text):
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = "\n".join("" if l.lstrip().startswith("//") else l for l in text.split("\n"))
    return json.loads(text)

def walk(node, path, out):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, path + [str(k)], out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + [str(i)], out)
    elif isinstance(node, str) and node.startswith("shopify://") and "/collections/" not in node and "/products/" not in node and "/pages/" not in node and "/blogs/" not in node:
        out.append((".".join(path), node))

def handle(label, text, out):
    try:
        data = parse_theme_json(text)
    except Exception as e:
        print(f"skip {label}: {e}", file=sys.stderr); return
    # GraphQL result shape: data.theme.files.nodes[].body.content
    nodes = (((data.get("data") or {}).get("theme") or {}).get("files") or {}).get("nodes") if isinstance(data, dict) else None
    if nodes:
        for n in nodes:
            body = n.get("body") or {}
            if "content" in body and n["filename"].endswith(".json"):
                handle(n["filename"], body["content"], out)
        return
    refs = []
    walk(data, [], refs)
    for p, v in refs:
        out.append((label, p, v))

out = []
for arg in sys.argv[1:]:
    paths = [arg]
    if os.path.isdir(arg):
        paths = [os.path.join(r, f) for r, _, fs in os.walk(arg) for f in fs if f.endswith(".json")]
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            handle(os.path.relpath(p, arg) if os.path.isdir(arg) else p, fh.read(), out)
for label, p, v in out:
    print(f"{label}\t{p}\t{v}")
names = sorted({v.split("/")[-1] for _, _, v in out if v.startswith("shopify://shop_images/")})
if names:
    print("\nFiles query filter for these images:\n  " + " OR ".join(f"filename:{n}" for n in names))
