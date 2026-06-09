import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI

load_dotenv()

app = FastAPI(debug=True)

FMP_API_KEY = os.getenv("FMP_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


@app.get("/")
def home():
    return {"status": "IA Finance backend running"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_pct(value: Any) -> str:
    number = safe_float(value)
    return f"{number:.1f}%"


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def badge_level(value: float) -> str:
    if value >= 75:
        return "green"
    if value >= 55:
        return "yellow"
    if value >= 35:
        return "orange"
    return "red"


def quality_label(score: float) -> str:
    if score >= 80:
        return "très solide"
    if score >= 65:
        return "solide"
    if score >= 45:
        return "correcte"
    if score >= 30:
        return "fragile"
    return "très fragile"


def risk_label(score: float) -> str:
    if score >= 75:
        return "faible"
    if score >= 55:
        return "modéré"
    if score >= 35:
        return "élevé"
    return "très élevé"


def valuation_label(pe_ratio: float) -> str:
    if pe_ratio <= 0:
        return "difficile à lire"
    if pe_ratio < 18:
        return "peu exigeante"
    if pe_ratio < 30:
        return "raisonnable à modérée"
    if pe_ratio < 45:
        return "exigeante"
    return "très exigeante"


def importance_from_percent(percent: float) -> str:
    if percent >= 40:
        return "Très élevée"
    if percent >= 20:
        return "Élevée"
    if percent >= 10:
        return "Moyenne"
    return "Faible"


def list_first(data: Any) -> Dict[str, Any]:
    if isinstance(data, list) and data:
        return data[0] if isinstance(data[0], dict) else {}
    return {}


def fmp_get(endpoint: str, params: str = "") -> Any:
    separator = "&" if params else ""
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}{separator}apikey={FMP_API_KEY}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc), "endpoint": endpoint}


def build_financial_scores(profile: Dict[str, Any], quote: Dict[str, Any], ratios: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:

    print("RATIOS =", ratios)
    
    beta = safe_float(profile.get("beta"), 1)
    change = safe_float(quote.get("changesPercentage"))
    pe_ratio = safe_float(ratios.get("priceEarningsRatioTTM"))
    net_margin = safe_float(ratios.get("netProfitMarginTTM"))
    roe = safe_float(ratios.get("returnOnEquityTTM"))
    debt_equity = safe_float(ratios.get("debtEquityRatioTTM"))
    current_ratio = safe_float(ratios.get("currentRatioTTM"))
    operating_margin = safe_float(ratios.get("operatingProfitMarginTTM"))
    free_cash_flow_yield = safe_float(metrics.get("freeCashFlowYieldTTM"))

    financial_quality = 50
    financial_quality += 20 if roe > 0.20 else 10 if roe > 0.10 else -10
    financial_quality += 20 if net_margin > 0.20 else 10 if net_margin > 0.10 else -10
    financial_quality += 15 if operating_margin > 0.20 else 5 if operating_margin > 0.10 else -5
    financial_quality += 10 if free_cash_flow_yield > 0.03 else -10 if free_cash_flow_yield < 0 else 0
    financial_quality += 10 if current_ratio > 1.5 else -5 if current_ratio < 1 else 0
    financial_quality = clamp(financial_quality)

    risk_score = 75
    risk_score -= 25 if beta > 1.7 else 15 if beta > 1.2 else 0
    risk_score -= 20 if abs(change) > 5 else 10 if abs(change) > 2 else 0
    risk_score -= 15 if debt_equity > 2 else 8 if debt_equity > 1 else 0
    risk_score += 10 if current_ratio > 1.5 else 0
    risk_score = clamp(risk_score)

    market_expectation_score = 50
    market_expectation_score += 25 if pe_ratio > 45 else 15 if pe_ratio > 30 else 5 if pe_ratio > 20 else -5
    market_expectation_score += 10 if beta > 1.3 else 0
    market_expectation_score = clamp(market_expectation_score)

    return {
        "financial_quality_score": round(financial_quality),
        "financial_quality_label": quality_label(financial_quality),
        "risk_score": round(risk_score),
        "risk_label": risk_label(risk_score),
        "market_expectation_score": round(market_expectation_score),
        "market_expectation_label": "élevée" if market_expectation_score >= 65 else "modérée" if market_expectation_score >= 45 else "faible",
        "valuation_label": valuation_label(pe_ratio),
        "beta": beta,
        "pe_ratio": pe_ratio,
        "net_margin": net_margin,
        "operating_margin": operating_margin,
        "roe": roe,
        "debt_equity": debt_equity,
        "current_ratio": current_ratio,
        "free_cash_flow_yield": free_cash_flow_yield,
    }


def build_events_30_days(ticker: str, today: datetime.date, earnings_calendar: Any, economic_calendar: Any) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []

    if isinstance(earnings_calendar, list):
        for event in earnings_calendar:
            if str(event.get("symbol", "")).upper() == ticker:
                events.append({
                    "date": event.get("date"),
                    "event": "Résultats de la société",
                    "importance": "🔴 Élevée",
                    "why": "Les résultats peuvent modifier rapidement la perception du marché sur la croissance, les marges et les prévisions.",
                    "watch": "Chiffre d'affaires, marges, bénéfice par action, guidance et commentaires du management."
                })

    macro_keywords_high = ["CPI", "Inflation", "Interest Rate", "Fed", "FOMC", "ECB", "GDP", "Nonfarm", "Unemployment"]
    if isinstance(economic_calendar, list):
        for event in economic_calendar[:30]:
            name = event.get("event") or event.get("name") or "Événement macroéconomique"
            is_high = any(keyword.lower() in str(name).lower() for keyword in macro_keywords_high)
            if is_high:
                events.append({
                    "date": event.get("date"),
                    "event": name,
                    "importance": "🔴 Élevée" if any(k.lower() in str(name).lower() for k in ["cpi", "inflation", "interest", "fed", "fomc", "ecb"]) else "🟠 Moyenne",
                    "why": "Cet événement peut influencer les taux, la valorisation des actions et l'appétit pour le risque.",
                    "watch": "Écart avec les attentes du marché, réaction des taux et réaction des indices."
                })

    if not events:
        events.append({
            "date": f"{today} à {today + timedelta(days=30)}",
            "event": "Veille société et marché",
            "importance": "🟠 Moyenne",
            "why": "Aucun événement majeur détecté dans les données disponibles, mais le titre peut rester sensible aux actualités de l'entreprise et du secteur.",
            "watch": "Communiqués officiels, résultats des concurrents, nouvelles sectorielles et mouvements de marché."
        })

    return events[:5]


@app.get("/analyze")
def analyze(ticker: str):
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker manquant")

    market_data = fmp_get("quote", f"symbol={ticker}")
    company_profile = fmp_get("profile", f"symbol={ticker}")
    ratios_ttm = fmp_get("ratios-ttm", f"symbol={ticker}")
    key_metrics_ttm = fmp_get("key-metrics-ttm", f"symbol={ticker}")
    analyst_estimates = fmp_get("analyst-estimates", f"symbol={ticker}&period=annual&page=0&limit=3")
    stock_news = fmp_get("stock-news", f"symbols={ticker}&limit=8")

    today = datetime.utcnow().date()
    in_30_days = today + timedelta(days=30)
    earnings_calendar = fmp_get("earnings-calendar", f"from={today}&to={in_30_days}")
    economic_calendar = fmp_get("economic-calendar", f"from={today}&to={in_30_days}")

    profile = list_first(company_profile)
    quote = list_first(market_data)
    ratios = list_first(ratios_ttm)
    metrics = list_first(key_metrics_ttm)

    company_name = profile.get("companyName") or ticker
    sector = profile.get("sector") or "Non renseigné"
    industry = profile.get("industry") or "Non renseigné"
    country = profile.get("country") or "Non renseigné"
    currency = quote.get("currency") or profile.get("currency") or ""
    price = safe_float(quote.get("price"))
    market_cap = safe_float(profile.get("mktCap") or quote.get("marketCap"))

    scores = build_financial_scores(profile, quote, ratios, metrics)
    events_30_days = build_events_30_days(ticker, today, earnings_calendar, economic_calendar)

    business_context = {
        "company_name": company_name,
        "ticker": ticker,
        "sector": sector,
        "industry": industry,
        "country": country,
        "currency": currency,
        "price": price,
        "market_cap": market_cap,
        "description": profile.get("description", ""),
        "website": profile.get("website", ""),
        "exchange": profile.get("exchangeShortName") or quote.get("exchange"),
    }

    watch_sources = [
        "Résultats trimestriels et rapport annuel de la société",
        "Communiqués officiels et présentations investisseurs",
        "Transcripts des conférences de résultats",
        "Résultats et commentaires des concurrents directs",
        "Calendrier macroéconomique : inflation, taux, emploi, banques centrales",
        "Actualités sectorielles récentes"
    ]

    prompt = f"""
Tu rédiges l'analyse payante d'une seule action pour un investisseur particulier intermédiaire.
Objectif produit : lecture en moins de 2 minutes, forte valeur utile, pas de remplissage, pas de conseil d'investissement.
Tu dois vulgariser sans appauvrir l'analyse.
Tu dois être concret : chaque affirmation importante doit indiquer quoi surveiller et où le surveiller.
Tu ne dois jamais écrire acheter, vendre, conserver, recommandation, objectif de cours, promesse de performance.
Tu dois éviter les phrases creuses du type "si ça monte vous gagnez, si ça baisse vous perdez".

ACTION ANALYSÉE
{business_context}

DONNÉES MARCHÉ
{market_data}

PROFIL SOCIÉTÉ
{company_profile}

RATIOS TTM
{ratios_ttm}

MÉTRIQUES TTM
{key_metrics_ttm}

ESTIMATIONS ANALYSTES
{analyst_estimates}

ACTUALITÉS RÉCENTES
{stock_news}

SCORES INTERNES
{scores}

ÉVÉNEMENTS 30 JOURS
{events_30_days}

SOURCES DE VEILLE À UTILISER DANS L'ANALYSE
{watch_sources}

FORMAT OBLIGATOIRE EXACT

# {company_name} ({ticker})

## A. La société en 30 secondes
- Qui est l'entreprise ? 1 à 2 phrases maximum.
- Position dans son secteur : leader mondial, leader régional, challenger, acteur de niche ou position difficile à déterminer.
- Taille : capitalisation boursière approximative si disponible.
- Présence géographique : uniquement si les données sont disponibles ; sinon indiquer que la répartition n'est pas suffisamment détaillée dans les données disponibles.
- D'où vient l'argent ? Donner 3 à 5 activités ou segments probables, avec importance : Très élevée, Élevée, Moyenne, Faible. Ne pas inventer de pourcentages si les données ne les fournissent pas.
- Pourquoi c'est important ? 2 phrases maximum sur diversification, dépendance et qualité économique.

## B. Ce qui fait vraiment bouger le cours
Donner maximum 3 moteurs réels du cours.
Pour chaque moteur :
- Nom du moteur.
- Pourquoi cela compte ? 1 phrase.
- Comment le suivre concrètement ? 2 à 3 éléments de veille maximum avec sources claires.

## C. Ce qui pourrait poser problème
Donner maximum 3 risques principaux.
Pour chaque risque :
- Risque clairement nommé.
- Pourquoi ? 1 phrase.
- Signal d'alerte : indicateur concret + source où le vérifier.

## D. Ce que le marché surveille actuellement
Donner maximum 3 priorités de surveillance.
Pour chaque priorité :
- Indicateur surveillé.
- Ce qu'une bonne lecture signifierait.
- Ce qu'une mauvaise lecture signalerait.
Phrase courte, opérationnelle, sans jargon excessif.

## E. Événements des 30 prochains jours
Faire un tableau court avec maximum 5 événements.
Colonnes : Date | Événement | Importance | Pourquoi cela compte.
Après le tableau, ajouter 2 à 4 points que le marché vérifiera lors de l'événement principal.

## F. Synthèse opérationnelle
- Ce qui soutient actuellement l'entreprise : 4 à 5 points courts.
- Ce qui mérite une attention particulière : 3 à 4 points courts.
- Les 3 éléments à surveiller en priorité : liste numérotée.
- En une phrase : 3 à 4 lignes maximum qui résument le profil de l'entreprise, sa solidité, ses dépendances et ce qui peut modifier la perception du marché.

## Information importante
Cette analyse constitue une aide à la compréhension de l'entreprise et de son environnement. Elle ne constitue pas un conseil en investissement. Tout investissement en bourse comporte un risque de perte partielle ou totale du capital.

CONTRAINTES STRICTES
- Français simple, clair, premium.
- Maximum 900 mots.
- Phrases courtes.
- Pas de longue introduction.
- Pas de tableau sauf dans la section E.
- Si une donnée manque, le dire proprement au lieu de l'inventer.
- Ne pas parler d'analyse de portefeuille.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un analyste financier spécialisé dans les analyses courtes, utiles et compréhensibles "
                    "pour investisseurs particuliers intermédiaires. Tu ne fournis jamais de conseil d'investissement."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1400,
        temperature=0.2,
    )

    analysis_text = completion.choices[0].message.content

    badges = [
        {
            "label": "Qualité financière",
            "value": scores["financial_quality_score"],
            "level": badge_level(scores["financial_quality_score"]),
            "text": scores["financial_quality_label"],
        },
        {
            "label": "Risque observé",
            "value": scores["risk_score"],
            "level": badge_level(scores["risk_score"]),
            "text": scores["risk_label"],
        },
        {
            "label": "Exigence du marché",
            "value": scores["market_expectation_score"],
            "level": badge_level(100 - scores["market_expectation_score"]),
            "text": scores["market_expectation_label"],
        },
    ]

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "country": country,
        "currency": currency,
        "price": quote.get("price"),
        "change_percent": quote.get("changesPercentage"),
        "market_cap": market_cap,
        "analysis": analysis_text,
        "scores": scores,
        "badges": badges,
        "events_30_days": events_10_days,
        "watch_sources": watch_sources,
    }
