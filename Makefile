.PHONY: serve smoke

serve:
	python3 -m http.server 8080

smoke:
	@python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('index.html').read())" && echo "smoke: html parse ok" || (echo "smoke: html parse fail" && exit 1)
