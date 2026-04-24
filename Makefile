.PHONY: sync serve smoke build

sync:
	python3 scripts/sync.py

serve:
	python3 -m http.server 8080

smoke:
	@python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('index.html').read())" && echo "smoke: html parse ok" || (echo "smoke: html parse fail" && exit 1)
	@python3 -c "import py_compile; py_compile.compile('scripts/sync.py', doraise=True)" && echo "smoke: sync.py compiles" || (echo "smoke: sync.py compile fail" && exit 1)

# Package a deploy artifact for the coach: index.html + data/.
# Produces dist/LFLDraftRecap-YYYY-MM-DD.zip. Unzip → open index.html →
# 💾 Base locale → Remplacer par un fichier → pick data/lfl-2026-nav.json.
build:
	@python3 -c "\
import zipfile, datetime, pathlib;\
out = pathlib.Path('dist') / f'LFLDraftRecap-{datetime.date.today().isoformat()}.zip';\
out.parent.mkdir(exist_ok=True);\
out.unlink(missing_ok=True);\
z = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED);\
paths = [pathlib.Path('index.html')] + sorted(pathlib.Path('data').rglob('*'));\
[z.write(p) for p in paths if p.is_file()];\
z.close();\
print(f'✓ {out} ({out.stat().st_size / 1024:.0f} KB, {len(z.namelist())} files)')"
