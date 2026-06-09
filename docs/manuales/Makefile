# Compila los manuales LaTeX del proyecto K-QGMIP (Fase 8).
# Uso:  make            -> genera ambos PDFs en build/ y los copia a esta carpeta
#       make tecnico    -> solo el Manual Técnico
#       make usuario    -> solo el Manual de Usuario
#       make clean      -> borra artefactos intermedios

LATEX = pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build
BUILD = build

.PHONY: all tecnico usuario clean

all: tecnico usuario

$(BUILD):
	mkdir -p $(BUILD)

tecnico: | $(BUILD)
	$(LATEX) Manual_Tecnico.tex
	$(LATEX) Manual_Tecnico.tex
	cp $(BUILD)/Manual_Tecnico.pdf .

usuario: | $(BUILD)
	$(LATEX) Manual_Usuario.tex
	$(LATEX) Manual_Usuario.tex
	cp $(BUILD)/Manual_Usuario.pdf .

clean:
	rm -rf $(BUILD)
