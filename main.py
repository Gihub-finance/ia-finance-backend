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


def safe_float(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


@app.get("/analyze")
def analyze(ticker: str):
    def fmp_get(endpoint: str, params: str = ""):
        url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}&apikey={FMP_API_KEY}"
        try:
            response = requests.get(url, timeout=20)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    market_data = fmp_get("quote", f"symbol={ticker}")
    company_profile = fmp_get("profile", f"symbol={ticker}")
    ratios_ttm = fmp_get("ratios-ttm", f"symbol={ticker}")
    key_metrics_ttm = fmp_get("key-metrics-ttm", f"symbol={ticker}")
    analyst_estimates = fmp_get("analyst-estimates", f"symbol={ticker}&period=annual&page=0&limit=3")

    profile = company_profile[0] if isinstance(company_profile, list) and len(company_profile) > 0 else {}
    quote = market_data[0] if isinstance(market_data, list) and len(market_data) > 0 else {}

    beta = safe_float(profile.get("beta"), 1)
    sector = profile.get("sector") or ""
    industry = profile.get("industry") or ""
    change = safe_float(quote.get("changesPercentage"), 0)

    signals = {
        "sector": sector,
        "industry": industry,
        "market_tension": "élevée" if abs(change) > 5 else "modérée" if abs(change) > 2 else "faible",
        "interest_rate_sensitivity": "élevée" if sector in ["Technology", "Communication Services"] else "faible" if sector in ["Utilities", "Consumer Defensive"] else "modérée",
        "portfolio_role": "croissance" if sector == "Technology" else "cyclique" if sector == "Energy" else "exposition financière" if sector == "Financial Services" else "industrie / défense" if "Defense" in industry else "diversification",
        "risk_short_term": "élevé" if beta > 1.5 else "modéré" if beta > 1 else "faible",
        "risk_long_term": "modéré" if sector in ["Technology", "Communication Services"] else "faible",
        "market_profile": "croissance volatile" if beta > 1.5 else "cyclique / sensible au marché" if beta > 1 else "profil plus défensif ou stable"
    }

    prompt = f"""
Tu es un analyste financier professionnel. Tu fournis une lecture stratégique, contextualisée et pédagogique d'un actif coté, sans jamais donner de conseil d'achat ou de vente.

Analyse l'actif {ticker} à partir des données disponibles.

Signaux IA calculés :
{signals}

Données marché :
{market_data}

Profil société :
{company_profile}

Ratios financiers TTM :
{ratios_ttm}

Indicateurs fondamentaux TTM :
{key_metrics_ttm}

Estimations analystes :
{analyst_estimates}

Ta réponse DOIT respecter STRICTEMENT cette structure :

1. Situation actuelle de l'action
Explique la dynamique récente du titre et ce que le marché semble intégrer.

2. Sensibilités clés
Explique à quoi l'action est principalement sensible.

3. Niveau de risque court / moyen / long terme
Décompose le risque : court terme, moyen terme, long terme.

4. Rôle possible dans un portefeuille
Explique ce que l'action peut représenter dans une allocation et quel risque elle ajoute.

5. Horizon de lecture
Indique si l'actif se comprend plutôt à court terme, moyen terme ou long terme, sans recommander.

6. Points de vigilance
Liste les éléments à surveiller dans les prochains mois.

Contraintes :
- Réponds en français.
- Maximum 450 mots.
- Ton professionnel, clair et pédagogique.
- Ne donne jamais de conseil d'achat ou de vente.
- Ne fais aucune promesse de performance.
- Sois concret et évite les généralités.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Tu es un analyste financier professionnel. Tu réponds en français, de façon structurée, prudente et pédagogique."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=600,
        temperature=0.3
    )

    return {
        "ticker": ticker,
        "market_data": market_data,
        "company_profile": company_profile,
        "signals": signals,
        "analysis": completion.choices[0].message.content
    }
