MAIN = main
LATEX = pdflatex
BIBTEX = bibtex

.PHONY: all clean

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
	TEXINPUTS=./styles//:$$TEXINPUTS $(LATEX) $(MAIN)
	BIBINPUTS=./styles/bibtex//:$$BIBINPUTS $(BIBTEX) $(MAIN)
	TEXINPUTS=./styles//:$$TEXINPUTS $(LATEX) $(MAIN)
	TEXINPUTS=./styles//:$$TEXINPUTS $(LATEX) $(MAIN)

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out \
	      $(MAIN).toc $(MAIN).fdb_latexmk $(MAIN).fls $(MAIN).synctex.gz \
	      $(MAIN).pdf
