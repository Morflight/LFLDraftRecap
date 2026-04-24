.PHONY: sync serve smoke

sync:
	python3 scripts/sync.py

serve:
	python3 -m http.server 8080

smoke:
	@python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('index.html').read())" && echo "smoke: html parse ok" || (echo "smoke: html parse fail" && exit 1)
	@python3 -c "import py_compile; py_compile.compile('scripts/sync.py', doraise=True)" && echo "smoke: sync.py compiles" || (echo "smoke: sync.py compile fail" && exit 1)
