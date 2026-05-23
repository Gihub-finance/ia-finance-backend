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
    def fmp_get(endpoint: str, params: str = ""):
        url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
        response = requests.get(url, timeout=20)
        try:
            return response.json()
        except Exception:
            return {"error": "Invalid FMP response", "raw": response.text}

    market_data = fmp_get("quote", f"symbol={ticker}")
    company_profile = fmp_get("profile", f"symbol={ticker}")
    ratios_ttm = fmp_get("ratios-ttm", f"symbol={ticker}")
    key_metrics_ttm = fmp_get("key-metrics-ttm", f"symbol={ticker}")
    analyst_estimates = fmp_get("analyst-estimates", f"symbol={ticker}&period=annual&page=0&limit=3")

    prompt = f"""
    Tu es un analyste financier professionnel. Tu fournis une lecture stratégique, contextualisée et pédagogique d'un actif coté, sans jamais donner de conseil d'achat ou de vente.

    Analyse l'actif {ticker} à partir des données de marché fournies.

    Objectif : produire une analyse utile à un investisseur qui veut comprendre :
    - ce qui influence réellement l'action,
    - son niveau de risque,
    - son rôle possible dans un portefeuille,
    - les horizons de lecture pertinents,
    - les points à surveiller.

    Ta réponse DOIT respecter STRICTEMENT cette structure :

    1. Situation actuelle de l'action
    Explique la dynamique récente du titre : prix, variation, tendance, niveau de tension, comportement du marché. Ne te limite pas aux chiffres : interprète ce que le marché semble intégrer.

    2. Sensibilités clés
    Explique à quoi l'action est principalement sensible : résultats financiers, taux d'intérêt, cycle économique, secteur, réglementation, innovation, géopolitique, devise, matières premières ou dépendance à un narratif de marché.

    3. Niveau de risque court / moyen / long terme
    Décompose le risque :
    - court terme : quelques semaines à 6 mois,
    - moyen terme : 6 à 24 mois,
    - long terme : 2 à 10 ans.
    Explique pourquoi le risque peut être différent selon l'horizon.

    4. Rôle possible dans un portefeuille
    Explique ce que l'action peut représenter dans une allocation : croissance, technologie, valeur cyclique, défensive, rendement, spéculative, exposition sectorielle ou diversification. Mentionne aussi le risque ajouté au portefeuille.

    5. Horizon de lecture
    Indique si l'actif se comprend plutôt à court terme, moyen terme ou long terme. Donne une justification claire sans recommander d'acheter ou de vendre.

    6. Points de vigilance
    Liste les éléments que l'investisseur devra surveiller : résultats, marges, dette, cash-flow, concurrence, valorisation, volatilité, taux, réglementation, sentiment marché ou événements sectoriels.

    Contraintes :
    - Réponds en français.
    - Ton professionnel, clair, pédagogique.
    - Maximum 450 mots.
    - Ne donne jamais de conseil d'achat ou de vente.
    - Ne dis jamais "il faut acheter" ou "il faut vendre".
    - Ne fais aucune promesse de performance.
    - Sois concret, contextualisé et utile.
    - Évite les généralités.
    - Explique les mécanismes derrière les chiffres.

    Données disponibles :

    Données marché temps réel :
    {market_data}

    Profil société :
    {company_profile}

    Ratios financiers TTM :
    {ratios_ttm}

    Indicateurs fondamentaux TTM :
    {key_metrics_ttm}

    Estimations analystes :
    {analyst_estimates}
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
                "content": "Analyse l'action <ticker> à partir des données suivantes : <marketData>.\n\nStructure la réponse ainsi :\n\n1. Situation actuelle\n- prix actuel\n- dynamique récente\n- volatilité\n\n2. Sensibilités clés\n- résultats financiers\n- IA / semi-conducteurs\n- macro / taux\n- géopolitique si pertinent\n\n3. Positionnement portefeuille\n- croissance\n- volatilité\n- diversification\n- exposition sectorielle\n\n4. Horizon de lecture\n- court terme\n- moyen terme\n- long terme\n\n5. Points de vigilance\n\nContraintes :\n- ton professionnel\n- synthétique\n- utile\n- sans conseil d'achat ou vente\n- exploite explicitement les données fournies\n- ne jamais dire que les données sont indisponibles"
            }
        ],
        max_tokens=350,
        temperature=0.3
    )

    return {
        "ticker": ticker,
        "market_data": market_data,
        "company_profile": company_profile,
        "ratios_ttm": ratios_ttm,
        "key_metrics_ttm": key_metrics_ttm,
        "analyst_estimates": analyst_estimates,
        "analysis": completion.choices[0].message.content
    }
