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

    Ta réponse DOIT respecter STRICTEMENT ce format :

    1. Situation actuelle
    - résumé de la situation du titre
    - tendance récente
    - éléments importants du marché

    2. Risques et vigilance
    - principaux risques
    - volatilité
    - éléments à surveiller

    3. Facteurs favorables
    - éléments pouvant soutenir une hausse
    - tendances positives
    - facteurs de croissance

    4. Facteurs défavorables
    - éléments pouvant peser sur le cours
    - risques de baisse
    - contexte négatif possible

    Contraintes :
    - maximum 220 mots
    - ton professionnel et pédagogique
    - aucune recommandation d'achat ou de vente
    - ne jamais dire "il faut acheter"
    - ne jamais dire "il faut vendre"

    Données marché :
    {market_data}
    """
