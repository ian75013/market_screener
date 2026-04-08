"""
Market Screener — AI Analysis Service
Generates detailed AI-powered stock analysis.
In production, this would call an LLM (Ollama / Claude API).
"""
from app.models import Stock
from app.schemas import AIAnalysisResponse, AIScores


def generate_ai_analysis(stock: Stock) -> AIAnalysisResponse:
    """
    Generate a comprehensive AI analysis for a stock.
    Uses rule-based heuristics here — in production, replace with
    Ollama / Claude API call for natural language generation.
    """
    scores = AIScores(
        overall=stock.ai_score_overall,
        fundamental=stock.ai_score_fundamental,
        technical=stock.ai_score_technical,
        momentum=stock.ai_score_momentum,
        risk=stock.ai_score_risk,
    )

    # ── Strengths / Weaknesses ───────────────────────────────────────
    strengths = []
    weaknesses = []

    # Fundamental
    if stock.ai_score_fundamental and stock.ai_score_fundamental >= 65:
        strengths.append("Fondamentaux solides avec des métriques financières robustes")
    elif stock.ai_score_fundamental and stock.ai_score_fundamental < 40:
        weaknesses.append("Fondamentaux fragiles nécessitant une surveillance accrue")

    # Technical
    if stock.ai_score_technical and stock.ai_score_technical >= 65:
        strengths.append("Momentum technique favorable — tendance haussière confirmée")
    elif stock.ai_score_technical and stock.ai_score_technical < 40:
        weaknesses.append("Signaux techniques négatifs — pression baissière détectée")

    # Valuation
    if stock.per and 0 < stock.per < 15:
        strengths.append(f"Valorisation attractive (PER {stock.per}x) — potentiel de rerating")
    elif stock.per and stock.per > 40:
        weaknesses.append(f"Valorisation tendue (PER {stock.per}x) — sensible aux déceptions")

    # Dividends
    if stock.dividend_yield >= 3:
        strengths.append(f"Rendement attractif ({stock.dividend_yield}%) soutenant le cours")
    if stock.payout_ratio and stock.payout_ratio > 80:
        weaknesses.append(f"Taux de distribution élevé ({stock.payout_ratio}%) — soutenabilité à vérifier")

    # Profitability
    if stock.roe and stock.roe > 20:
        strengths.append(f"Rentabilité élevée (ROE {stock.roe}%) — création de valeur forte")
    if stock.margin_ebit and stock.margin_ebit > 20:
        strengths.append(f"Marge opérationnelle confortable ({stock.margin_ebit}%)")
    elif stock.margin_ebit and stock.margin_ebit < 5:
        weaknesses.append(f"Marge opérationnelle faible ({stock.margin_ebit}%) — peu de marge de manoeuvre")

    # Growth
    if stock.revenue_growth and stock.revenue_growth > 15:
        strengths.append(f"Croissance soutenue du chiffre d'affaires (+{stock.revenue_growth}%)")
    elif stock.revenue_growth and stock.revenue_growth < -5:
        weaknesses.append(f"Recul du chiffre d'affaires ({stock.revenue_growth}%)")

    # Financial health
    if stock.net_debt_ebitda and stock.net_debt_ebitda > 3:
        weaknesses.append(f"Endettement significatif (DN/EBITDA {stock.net_debt_ebitda}x)")
    if stock.current_ratio and stock.current_ratio < 1:
        weaknesses.append("Ratio de liquidité inférieur à 1 — risque de trésorerie")

    # Technical
    if stock.rsi and stock.rsi > 70:
        weaknesses.append(f"RSI en zone de surachat ({stock.rsi}) — risque de correction")
    elif stock.rsi and stock.rsi < 30:
        strengths.append(f"RSI en zone de survente ({stock.rsi}) — opportunité d'achat technique")

    if stock.dist_mm200 and stock.dist_mm200 > 10:
        strengths.append("Cours bien au-dessus de la MM200 — tendance de fond haussière")
    elif stock.dist_mm200 and stock.dist_mm200 < -10:
        weaknesses.append("Cours nettement sous la MM200 — tendance baissière")

    # ── Catalysts ────────────────────────────────────────────────────
    catalysts = []
    if stock.upside and stock.upside > 10:
        catalysts.append(f"Potentiel de hausse de {stock.upside}% selon le consensus analystes")
    if stock.revenue_growth and stock.revenue_growth > 10:
        catalysts.append("Dynamique de croissance positive pouvant soutenir une revalorisation")
    if stock.esg_score and stock.esg_score > 70:
        catalysts.append(f"Profil ESG attractif ({stock.esg_score}/100) — éligible aux fonds responsables")
    if stock.analyst_rating and stock.analyst_rating > 3.5:
        catalysts.append(f"Consensus analystes favorable ({stock.analyst_rating}/5 sur {stock.analyst_count or '?'} analystes)")
    if stock.eps_growth and stock.eps_growth > 20:
        catalysts.append(f"Forte croissance des bénéfices attendue (+{stock.eps_growth}%)")
    if stock.fcf_yield and stock.fcf_yield > 6:
        catalysts.append(f"Rendement de free cash-flow élevé ({stock.fcf_yield}%) — capacité de distribution")

    # ── Risks ────────────────────────────────────────────────────────
    risks = []
    if stock.beta and stock.beta > 1.3:
        risks.append(f"Beta élevé ({stock.beta}) — sensibilité accrue aux mouvements de marché")
    if stock.volatility and stock.volatility > 35:
        risks.append(f"Forte volatilité historique ({stock.volatility}%) — fluctuations importantes")
    if stock.net_debt_ebitda and stock.net_debt_ebitda > 2.5:
        risks.append("Levier financier à surveiller dans un contexte de taux élevés")
    if stock.per and stock.per > 35:
        risks.append("Multiple de valorisation tendu — vulnérable aux révisions de résultats")
    if stock.upside and stock.upside < -10:
        risks.append(f"Cours au-dessus de l'objectif consensus ({stock.upside}%) — risque de correction")
    if stock.change_ytd and stock.change_ytd > 40:
        risks.append(f"Forte hausse depuis le début d'année (+{stock.change_ytd}%) — prise de bénéfices possible")
    if stock.debt_equity and stock.debt_equity > 2:
        risks.append(f"Ratio d'endettement élevé (D/E {stock.debt_equity}x)")

    # ── Summary ──────────────────────────────────────────────────────
    signal_desc = {
        "ACHAT FORT": "un signal d'achat fort",
        "ACHAT": "un signal d'achat",
        "NEUTRE": "un signal neutre",
        "VENTE": "un signal de vente",
        "VENTE FORTE": "un signal de vente forte",
    }
    sig = signal_desc.get(stock.ai_signal, "un signal indéterminé")

    summary_parts = [
        f"{stock.name} ({stock.ticker}) affiche un score IA global de "
        f"{stock.ai_score_overall}/100 avec {sig}.",
    ]
    if strengths:
        summary_parts.append(
            f"Points forts identifiés : {'; '.join(strengths[:3])}."
        )
    if weaknesses:
        summary_parts.append(
            f"Points de vigilance : {'; '.join(weaknesses[:3])}."
        )
    if catalysts:
        summary_parts.append(
            f"Le titre bénéficie de {len(catalysts)} catalyseur(s) potentiel(s)."
        )
    if risks:
        summary_parts.append(
            f"Attention à {len(risks)} facteur(s) de risque identifié(s)."
        )

    summary = " ".join(summary_parts)

    # ── Key Metrics ──────────────────────────────────────────────────
    key_metrics = {
        "PER": f"{stock.per}x" if stock.per else "N/A",
        "PEG": f"{stock.peg}" if stock.peg else "N/A",
        "P/B": f"{stock.pbr}x" if stock.pbr else "N/A",
        "EV/EBITDA": f"{stock.ev_ebitda}x" if stock.ev_ebitda else "N/A",
        "ROE": f"{stock.roe}%" if stock.roe else "N/A",
        "ROA": f"{stock.roa}%" if stock.roa else "N/A",
        "Marge EBIT": f"{stock.margin_ebit}%" if stock.margin_ebit else "N/A",
        "Marge brute": f"{stock.margin_gross}%" if stock.margin_gross else "N/A",
        "Div. Yield": f"{stock.dividend_yield}%" if stock.dividend_yield else "N/A",
        "Crois. CA": f"{stock.revenue_growth}%" if stock.revenue_growth else "N/A",
        "Crois. BPA": f"{stock.eps_growth}%" if stock.eps_growth else "N/A",
        "FCF Yield": f"{stock.fcf_yield}%" if stock.fcf_yield else "N/A",
        "DN/EBITDA": f"{stock.net_debt_ebitda}x" if stock.net_debt_ebitda else "N/A",
        "D/E": f"{stock.debt_equity}x" if stock.debt_equity else "N/A",
        "RSI": f"{stock.rsi}" if stock.rsi else "N/A",
        "Beta": f"{stock.beta}" if stock.beta else "N/A",
        "Objectif": f"{stock.target_price} {stock.currency}",
        "Potentiel": f"{stock.upside}%",
        "ESG": f"{stock.esg_score}/100" if stock.esg_score else "N/A",
    }

    return AIAnalysisResponse(
        ticker=stock.ticker,
        name=stock.name,
        signal=stock.ai_signal or "N/A",
        scores=scores,
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        catalysts=catalysts,
        risks=risks,
        key_metrics=key_metrics,
    )
