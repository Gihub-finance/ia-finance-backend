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
Analyse l'actif {ticker} à partir des données marché suivantes :
{market_data}

Explique clairement les risques actuels, la variation récente, le volume, la capitalisation si disponible.
Réponse en français, maximum 150 mots.
Ne donne pas de conseil d'achat ou de vente.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un analyste financier. Tu expliques simplement les risques pour un investisseur non expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=220,
        temperature=0.4
    )

    return {
        "ticker": ticker,
        "market_data": market_data,
        "analysis": completion.choices[0].message.content
    }
