from fastapi import FastAPI
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv 
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI(debug=True)

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


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def score_label(score):
    if score >= 80:
        return "très favorable"
    if score >= 65:
        return "favorable"
    if score >= 45:
        return "équilibré"
    if score >= 30:
        return "fragile"
    return "risqué"


def risk_label(score):
    if score >= 75:
        return "faible"
    if score >= 55:
        return "modéré"
    if score >= 35:
        return "élevé"
    return "très élevé"


def badge_level(value):
    if value >= 75:
        return "green"
    if value >= 55:
        return "yellow"
    if value >= 35:
        return "orange"
    return "red"


@app.get("/analyze")
def analyze(ticker: str):
    ticker = ticker.upper().strip()

    def fmp_get(endpoint: str, params: str = ""):
        separator = "&" if params else ""
        url = f"https://financialmodelingprep.com/stable/{endpoint}?{params}{separator}apikey={FMP_API_KEY}"
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

    today = datetime.utcnow().date()
    in_10_days = today + timedelta(days=10)

    earnings_calendar = fmp_get(
        "earnings-calendar",
        f"from={today}&to={in_10_days}"
    )

    economic_calendar = fmp_get(
        "economic-calendar",
        f"from={today}&to={in_10_days}"
    )

    stock_news = fmp_get(
        "stock-news",
        f"symbols={ticker}&limit=5"
    )

    profile = company_profile[0] if isinstance(company_profile, list) and len(company_profile) > 0 else {}
    quote = market_data[0] if isinstance(market_data, list) and len(market_data) > 0 else {}
    ratios = ratios_ttm[0] if isinstance(ratios_ttm, list) and len(ratios_ttm) > 0 else {}
    metrics = key_metrics_ttm[0] if isinstance(key_metrics_ttm, list) and len(key_metrics_ttm) > 0 else {}

    company_name = profile.get("companyName") or ticker
    sector = profile.get("sector") or ""
    industry = profile.get("industry") or ""
    country = profile.get("country") or ""
    currency = quote.get("currency") or profile.get("currency") or ""

    price = safe_float(quote.get("price"))
    change = safe_float(quote.get("changesPercentage"))
    beta = safe_float(profile.get("beta"), 1)

    pe_ratio = safe_float(ratios.get("priceEarningsRatioTTM"))
    net_margin = safe_float(ratios.get("netProfitMarginTTM"))
    roe = safe_float(ratios.get("returnOnEquityTTM"))
    debt_equity = safe_float(ratios.get("debtEquityRatioTTM"))
    current_ratio = safe_float(ratios.get("currentRatioTTM"))
    operating_margin = safe_float(ratios.get("operatingProfitMarginTTM"))
    free_cash_flow_yield = safe_float(metrics.get("freeCashFlowYieldTTM"))
    revenue_per_share = safe_float(metrics.get("revenuePerShareTTM"))

    quality_score = 50
    quality_score += 20 if roe > 0.20 else 10 if roe > 0.10 else -10
    quality_score += 20 if net_margin > 0.20 else 10 if net_margin > 0.10 else -10
    quality_score += 15 if operating_margin > 0.20 else 5 if operating_margin > 0.10 else -5
    quality_score += 10 if free_cash_flow_yield > 0.03 else -10 if free_cash_flow_yield < 0 else 0
    quality_score = clamp(quality_score)

    valuation_score = 70
    valuation_score -= 30 if pe_ratio > 45 else 20 if pe_ratio > 30 else 10 if pe_ratio > 20 else 0
    valuation_score += 10 if pe_ratio > 0 and pe_ratio < 18 else 0
    valuation_score = clamp(valuation_score)

    risk_score = 75
    risk_score -= 25 if beta > 1.7 else 15 if beta > 1.2 else 0
    risk_score -= 20 if abs(change) > 5 else 10 if abs(change) > 2 else 0
    risk_score -= 15 if debt_equity > 2 else 8 if debt_equity > 1 else 0
    risk_score += 10 if current_ratio > 1.5 else 0
    risk_score = clamp(risk_score)

    momentum_score = 50
    momentum_score += 20 if change > 3 else 10 if change > 0 else -15 if change < -3 else -5
    momentum_score = clamp(momentum_score)

    global_score = round(
        quality_score * 0.35 +
        valuation_score * 0.20 +
        risk_score * 0.30 +
        momentum_score * 0.15
    )

    signals = {
        "sector": sector,
        "industry": industry,
        "market_tension": "élevée" if abs(change) > 5 else "modérée" if abs(change) > 2 else "faible",
        "financial_strength": "très solide" if roe > 0.20 and net_margin > 0.20 else "correcte" if roe > 0.10 else "fragile ou cyclique",
        "valuation_pressure": "valorisation élevée" if pe_ratio > 40 else "valorisation modérée" if pe_ratio > 25 else "valorisation raisonnable",
        "growth_dependency": "forte dépendance à la croissance" if sector == "Technology" else "dépendance modérée à la croissance",
        "cashflow_quality": "génération de cash robuste" if free_cash_flow_yield > 0.05 else "cashflow correct" if free_cash_flow_yield > 0 else "cashflow sous pression",
        "interest_rate_sensitivity": "élevée" if sector in ["Technology", "Communication Services"] else "faible" if sector in ["Utilities", "Consumer Defensive"] else "modérée",
        "portfolio_role": "croissance" if sector == "Technology" else "cyclique" if sector == "Energy" else "exposition financière" if sector == "Financial Services" else "industrie / défense" if "Defense" in industry else "diversification",
        "risk_short_term": "élevé" if beta > 1.5 or abs(change) > 5 else "modéré" if beta > 1 else "faible",
        "risk_long_term": "modéré" if sector in ["Technology", "Communication Services"] else "faible",
        "market_profile": "croissance volatile" if beta > 1.5 else "cyclique / sensible au marché" if beta > 1 else "profil plus défensif ou stable"
    }

    scorecards = {
        "global_score": global_score,
        "global_label": score_label(global_score),
        "quality_score": round(quality_score),
        "quality_label": score_label(quality_score),
        "valuation_score": round(valuation_score),
        "valuation_label": score_label(valuation_score),
        "risk_score": round(risk_score),
        "risk_label": risk_label(risk_score),
        "momentum_score": round(momentum_score),
        "momentum_label": score_label(momentum_score)
    }

    badges = [
        {
            "label": "Qualité financière",
            "value": round(quality_score),
            "level": badge_level(quality_score),
            "text": score_label(quality_score)
        },
        {
            "label": "Valorisation",
            "value": round(valuation_score),
            "level": badge_level(valuation_score),
            "text": score_label(valuation_score)
        },
        {
            "label": "Risque",
            "value": round(risk_score),
            "level": badge_level(risk_score),
            "text": risk_label(risk_score)
        },
        {
            "label": "Momentum",
            "value": round(momentum_score),
            "level": badge_level(momentum_score),
            "text": score_label(momentum_score)
        }
    ]

    synthetic_cards = {
        "business_card": {
            "title": "Profil de l'entreprise",
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "country": country,
            "currency": currency
        },
        "market_card": {
            "title": "Dynamique de marché",
            "price": price,
            "change_percent": quote.get("changesPercentage"),
            "market_tension": signals["market_tension"],
            "beta": beta
        },
        "risk_card": {
            "title": "Lecture du risque",
            "short_term": signals["risk_short_term"],
            "long_term": signals["risk_long_term"],
            "risk_score": round(risk_score),
            "risk_label": risk_label(risk_score)
        },
        "valuation_card": {
            "title": "Valorisation",
            "pe_ratio": pe_ratio,
            "valuation_pressure": signals["valuation_pressure"],
            "valuation_score": round(valuation_score)
        }
    }

    scenarios = {
        "favorable": "Le scénario favorable suppose une croissance soutenue, des marges résistantes, une demande solide et un marché qui continue de valoriser les qualités de l'entreprise.",
        "central": "Le scénario central suppose une normalisation progressive : l'entreprise conserve ses forces, mais le marché reste attentif à la valorisation, aux résultats et au contexte macroéconomique.",
        "defavorable": "Le scénario défavorable suppose une déception sur les résultats, une pression sur les marges, une hausse du risque sectoriel ou une rotation de marché défavorable."
    }

    risk_items = [
        {
            "risk": "Volatilité du titre",
            "importance": "élevé" if beta > 1.5 or abs(change) > 5 else "modéré",
            "why": "Le titre peut réagir fortement aux résultats, aux taux ou au sentiment de marché.",
            "signal_to_watch": "Variation brutale du cours, baisse des volumes acheteurs ou réaction négative aux publications."
        },
        {
            "risk": "Valorisation",
            "importance": "élevé" if pe_ratio > 40 else "modéré" if pe_ratio > 25 else "faible",
            "why": "Une valorisation élevée rend l'action plus sensible aux déceptions de croissance ou de marge.",
            "signal_to_watch": "Révision en baisse des prévisions, compression des multiples ou ralentissement du chiffre d'affaires."
        },
        {
            "risk": "Rentabilité",
            "importance": "modéré" if net_margin > 0.10 else "élevé",
            "why": "Les marges influencent directement la perception de qualité financière de l'entreprise.",
            "signal_to_watch": "Baisse de marge brute, hausse des coûts ou pression concurrentielle."
        },
        {
            "risk": "Sensibilité macroéconomique",
            "importance": signals["interest_rate_sensitivity"],
            "why": "Les taux, l'inflation et le cycle économique peuvent modifier les attentes des investisseurs.",
            "signal_to_watch": "Hausse des taux, ralentissement de la demande ou discours restrictif des banques centrales."
        },
        {
            "risk": "Risque sectoriel",
            "importance": "modéré",
            "why": "Le secteur peut subir une rotation de marché, des changements réglementaires ou une pression concurrentielle.",
            "signal_to_watch": "Résultats des concurrents, annonces réglementaires ou baisse de la demande sectorielle."
        }
    ]

    events_10_days = []

    if isinstance(earnings_calendar, list):
        for event in earnings_calendar[:20]:
            if event.get("symbol") == ticker:
                events_10_days.append({
                    "date": event.get("date"),
                    "type": "résultats entreprise",
                    "importance": "élevée",
                    "possible_impact": "incertain",
                    "what_to_watch": "chiffre d'affaires, marges, bénéfice par action, prévisions et commentaires du management"
                })

    if isinstance(economic_calendar, list):
        for event in economic_calendar[:10]:
            events_10_days.append({
                "date": event.get("date"),
                "type": event.get("event") or "événement macroéconomique",
                "importance": "modérée à élevée",
                "possible_impact": "incertain",
                "what_to_watch": "inflation, taux, emploi, croissance économique ou réaction des banques centrales"
            })

    if not events_10_days:
        events_10_days.append({
            "date": f"{today} à {in_10_days}",
            "type": "veille de marché",
            "importance": "modérée",
            "possible_impact": "incertain",
            "what_to_watch": "résultats, annonces sectorielles, taux, inflation, évolution du marché et nouvelles propres à l'entreprise"
        })

    prompt = f"""
Tu es un analyste financier professionnel. Tu fournis une analyse digitale claire, vendable et utile pour un investisseur non professionnel.
Tu ne donnes jamais de conseil d'achat, de vente ou de conservation.
Tu expliques simplement les faits, les risques, les moteurs et les scénarios.

Action analysée : {ticker}
Entreprise : {company_name}
Secteur : {sector}
Industrie : {industry}

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

Actualités récentes :
{stock_news}

Signaux calculés :
{signals}

Scores calculés :
{scorecards}

Risques identifiés :
{risk_items}

Événements sur 10 jours :
{events_10_days}

Structure obligatoire :

A. Résumé exécutif — sans recommandation ni conseil
Présente une synthèse claire de l'action.
Explique ce que fait l'entreprise, son secteur, pourquoi elle mérite une analyse attentive actuellement.
Indique le niveau général de risque observé.
Résume les points forts visibles.
Résume les points de vigilance.
Explique ce qui peut soutenir le titre, ce qui peut le fragiliser, et ce que l'investisseur doit surveiller dans les prochains jours.
Langage simple, direct et compréhensible.

B. Potentiel
Analyse les éléments pouvant soutenir positivement l'action dans les prochains mois, sans conseil.
Mentionne croissance, marges, dette, innovation, contrats, expansion, tendance sectorielle.
Explique si le marché intègre déjà beaucoup d'attentes positives.
Présente trois scénarios : favorable, central, défavorable.
Explique les conditions nécessaires pour chaque scénario.

C. Risques
Identifie les cinq principaux risques.
Pour chaque risque, explique pourquoi il est important, comment il peut affecter le cours, son niveau d'importance et les signaux à surveiller.
Inclure risques entreprise, marché, macroéconomie, réglementation, géopolitique si pertinent.

D. Calendrier des événements importants — horizon 10 jours
Présente uniquement les événements attendus dans les dix prochains jours.
Inclure événements entreprise, macroéconomiques et sectoriels si disponibles.
Pour chaque événement : date, type, importance, impact possible, ce qu'il faut surveiller.

E. Analyse du portefeuille
Même si une seule action est analysée, explique son rôle possible dans un portefeuille.
Analyse l'exposition sectorielle, la volatilité, les corrélations probables, les risques cachés et ce que cette ligne peut apporter ou ajouter comme risque.
Explique avec des mots simples.

F. Conclusion analytique
Conclusion claire, équilibrée, sans conseil.
Résume les éléments positifs et les risques.
Indique si le profil semble défensif, équilibré, dynamique ou spéculatif.
Présente le rapport potentiel / risque : favorable, équilibré, fragile ou incertain.
Termine par une phrase utile pour un non-professionnel : ce qu'il doit comprendre et surveiller.

Contraintes :
- Français clair.
- Accessible aux non-professionnels.
- Pas de recommandation.
- Pas de promesse de performance.
- Pas de Markdown complexe.
- Pas de tableaux.
- Maximum 1300 mots.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Tu es un analyste financier professionnel. Tu réponds en français, sans recommandation d'investissement, avec une pédagogie claire pour non-professionnels."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=1600,
        temperature=0.25
    )

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "country": country,
        "currency": currency,

        "analysis": completion.choices[0].message.content,

        "price": quote.get("price"),
        "change_percent": quote.get("changesPercentage"),
        "beta": beta,

        "scores": scorecards,
        "badges": badges,
        "synthetic_cards": synthetic_cards,
        "scenarios": scenarios,
        "risks": risk_items,
        "events_10_days": events_10_days,

        "market_tension": signals.get("market_tension"),
        "portfolio_role": signals.get("portfolio_role"),
        "risk_short_term": signals.get("risk_short_term"),
        "risk_long_term": signals.get("risk_long_term"),
        "financial_strength": signals.get("financial_strength"),
        "valuation_pressure": signals.get("valuation_pressure"),
        "growth_dependency": signals.get("growth_dependency"),
        "cashflow_quality": signals.get("cashflow_quality"),
        "interest_rate_sensitivity": signals.get("interest_rate_sensitivity"),
        "market_profile": signals.get("market_profile"),

        "raw_data": {
            "market_data": market_data,
            "company_profile": company_profile,
            "ratios_ttm": ratios_ttm,
            "key_metrics_ttm": key_metrics_ttm,
            "analyst_estimates": analyst_estimates,
            "stock_news": stock_news
        }
    }
