# Chess PGN Insights

Dashboard Streamlit para partidas PGN locais, Chess.com e Lichess.

## Instalação

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura

```text
chess-pgn-insights/
├── app.py
├── pgn_reader.py
├── statistics.py
├── oppenings.py
├── requirements.txt
├── README.md
└── eco_data/
    ├── ecoA.json
    ├── ecoB.json
    ├── ecoC.json
    ├── ecoD.json
    └── ecoE.json
```

A pasta eco_data é opcional: quando presente, seus arquivos JSON são usados para nomear as aberturas ECO.
