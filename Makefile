MAIN = main
LATEX = pdflatex
BIBTEX = bibtex

.PHONY: all clean pdf

all: pdf

pdf:
	TEXINPUTS=./styles//:$$TEXINPUTS $(LATEX) $(MAIN)
	BSTINPUTS=./styles/bibtex//:$$BSTINPUTS BIBINPUTS=./styles/bibtex//:$$BIBINPUTS $(BIBTEX) $(MAIN)
	TEXINPUTS=./styles//:$$TEXINPUTS $(LATEX) $(MAIN)
	TEXINPUTS=./styles//:$$TEXINPUTS $(LATEX) $(MAIN)

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out \
	      $(MAIN).toc $(MAIN).fdb_latexmk $(MAIN).fls $(MAIN).synctex.gz \
	      $(MAIN).pdf
