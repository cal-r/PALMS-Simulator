.PHONY: all clean

FORMULAS = $(wildcard *.tex)
PNGS = $(FORMULAS:%.tex=%.png)

all: $(PNGS) clean_pdf

tex/%.pdf: %.tex | tex
	latexmk -pdf -outdir=tex $<

%.png: tex/%.pdf
	magick convert -density 300 -background white -alpha remove -alpha off $< -quality 90 $@

tex:
	mkdir -p tex

clean_pdf:
	rm -rf tex

clean: clean_pdf
	rm -rf $(PNGS)
