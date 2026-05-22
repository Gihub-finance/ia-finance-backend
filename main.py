from fastapi import FastAPI
import os
import requests
from openai import OpenAI

app = FastAPI()

FMP_API_KEY = os.getenv("FMP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

@app.get("/")
def home():
    return {"status": "IA Finance backend running"}

@app.get("/analyze")
def analyze(ticker: str):
    fmp_url = f"https://financialmodelingprep.com/stable/quote?symbol={ticker}&apikey={FMP_API_KEY}"
    fmp_response = requests.get(fmp_url)
    market_data = fmp_response.json()

   prompt = f"""
Tu es un analyste financier professionnel.

Analyse l'actif {ticker} à partir des données de marché fournies.

Structure la réponse en 4 parties :

1. Situation actuelle de l'actif
2. Principaux risques et points de vigilance
3. Facteurs pouvant soutenir une hausse
4. Facteurs pouvant peser sur le cours

Reste factuel, clair et pédagogique pour un investisseur non expert.

Ne donne jamais de conseil d'achat ou de vente.
Ne recommande jamais d'investir.

Les investisseurs devront surveiller :
- les risques de volatilité,
- les résultats financiers,
- les tendances sectorielles,
- le contexte macroéconomique,
- les mouvements du marché.

Données marché :
{market_data}
"""
