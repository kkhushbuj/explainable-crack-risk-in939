# Paper

`IN939_LPBF_paper.pdf` is the compiled paper (29 pages). `main.tex` is its LaTeX source.

Build with XeLaTeX, twice:

    xelatex main.tex

The default body size is 11 pt (29 pages). For 10 pt (25 pages):

    xelatex "\def\bodysize{10}\def\bodyskip{15.1}\input{main}"

Fonts are in `fonts/` (Gelasio and Liberation, both SIL Open Font License). `make_fig.py` redraws the crack-rate chart from the per-paper counts in Table 2.1.
