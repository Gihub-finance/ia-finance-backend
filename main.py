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
Tu es un analyste financier professionnel. Tu fournis une lecture stratégique d'un actif, sans donner de conseil d'achat ou de vente.

Analyse l'actif {ticker} à partir des données de marché fournies.

Ta réponse DOIT respecter STRICTEMENT cette structure :

1. Situation actuelle
Explique brièvement le comportement récent de l'actif : prix, variation, tendance courte période, volume ou tension de marché si disponible.

2. Sensibilités clés
Explique à quoi l'actif est principalement sensible : résultats financiers, taux, secteur, cycle économique, réglementation, géopolitique, matières premières, technologie ou autres facteurs pertinents selon l'actif.

3. Niveau de risque et justification
Qualifie le risque de manière claire : faible, modéré, élevé ou très élevé. Justifie ce niveau avec les données disponibles : volatilité, valorisation, dépendance sectorielle, momentum, amplitude récente ou incertitude.

4. Rôle possible dans un portefeuille
Explique ce que cet actif apporte dans une logique de portefeuille : croissance, technologie, défense, énergie, rendement, diversification, exposition sectorielle, cyclicité ou protection. Indique aussi ce qu'il peut ajouter comme risque.

5. Horizon de lecture
Indique si l'actif semble plutôt à analyser sur un horizon court terme, moyen terme ou long terme. Donne des repères temporels : court terme = quelques semaines à 12 mois, moyen terme = 1 à 5 ans, long terme = 5 à 10 ans ou plus. Justifie sans recommander.

6. Points à surveiller
Liste les principaux éléments que l'investisseur devra suivre dans les prochains mois : résultats, marges, demande, taux, concurrence, contexte macro, réglementation, valorisation, sentiment marché.

Contraintes :
- Réponds en français.
- Ton professionnel, clair et pédagogique.
- Maximum 320 mots.
- Ne donne jamais de conseil d'achat ou de vente.
- Ne dis jamais "il faut acheter" ou "il faut vendre".
- Ne fais pas de promesse de performance.
- Sois concret, contextualisé, et évite les généralités.

Données marché :
{market_data}
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Tu es un analyste financier professionnel. Tu réponds en français, de manière structurée, claire et prudente."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=350,
        temperature=0.3
    )

    return {
        "ticker": ticker,
        "market_data": market_data,
        "analysis": completion.choices[0].message.content
    }
