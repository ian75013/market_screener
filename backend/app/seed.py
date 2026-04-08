"""
Market Screener — Seed Data
Generates ~100 realistic stocks across multiple markets.
"""
import math
import logging
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Stock
from app.yahoo_finance import fetch_all_stocks


logger = logging.getLogger(__name__)


def _sr(seed: int) -> float:
    """Seeded pseudo-random [0,1)."""
    x = math.sin(seed) * 10000
    return x - math.floor(x)


# ── Stock Universe ───────────────────────────────────────────────────────────

RAW_STOCKS = [
    # France — CAC 40
    ("TotalEnergies", "TTE.PA", "France", "Énergie", "CAC 40", "EUR", "FR0000120271"),
    ("LVMH", "MC.PA", "France", "Consommation", "CAC 40", "EUR", "FR0000121014"),
    ("Sanofi", "SAN.PA", "France", "Santé", "CAC 40", "EUR", "FR0000120578"),
    ("Schneider Electric", "SU.PA", "France", "Industrie", "CAC 40", "EUR", "FR0000121972"),
    ("Air Liquide", "AI.PA", "France", "Matériaux", "CAC 40", "EUR", "FR0000120073"),
    ("BNP Paribas", "BNP.PA", "France", "Finance", "CAC 40", "EUR", "FR0000131104"),
    ("Hermès", "RMS.PA", "France", "Consommation", "CAC 40", "EUR", "FR0000052292"),
    ("Dassault Systèmes", "DSY.PA", "France", "Technologie", "CAC 40", "EUR", "FR0014003TT8"),
    ("Capgemini", "CAP.PA", "France", "Technologie", "CAC 40", "EUR", "FR0000125338"),
    ("Orange", "ORA.PA", "France", "Télécoms", "CAC 40", "EUR", "FR0000133308"),
    ("Stellantis", "STLAP.PA", "France", "Industrie", "CAC 40", "EUR", "NL00150001Q9"),
    ("Vinci", "DG.PA", "France", "Industrie", "CAC 40", "EUR", "FR0000125486"),
    ("Safran", "SAF.PA", "France", "Industrie", "CAC 40", "EUR", "FR0000073272"),
    ("L'Oréal", "OR.PA", "France", "Consommation", "CAC 40", "EUR", "FR0000120321"),
    ("Saint-Gobain", "SGO.PA", "France", "Matériaux", "CAC 40", "EUR", "FR0000125007"),
    # USA — S&P 500
    ("Apple", "AAPL", "USA", "Technologie", "S&P 500", "USD", "US0378331005"),
    ("Microsoft", "MSFT", "USA", "Technologie", "S&P 500", "USD", "US5949181045"),
    ("NVIDIA", "NVDA", "USA", "Technologie", "S&P 500", "USD", "US67066G1040"),
    ("Amazon", "AMZN", "USA", "Consommation", "S&P 500", "USD", "US0231351067"),
    ("Alphabet", "GOOGL", "USA", "Technologie", "S&P 500", "USD", "US02079K3059"),
    ("Meta", "META", "USA", "Technologie", "S&P 500", "USD", "US30303M1027"),
    ("JPMorgan Chase", "JPM", "USA", "Finance", "S&P 500", "USD", "US46625H1005"),
    ("Johnson & Johnson", "JNJ", "USA", "Santé", "S&P 500", "USD", "US4781601046"),
    ("Exxon Mobil", "XOM", "USA", "Énergie", "S&P 500", "USD", "US30231G1022"),
    ("Procter & Gamble", "PG", "USA", "Consommation", "S&P 500", "USD", "US7427181091"),
    ("Tesla", "TSLA", "USA", "Industrie", "S&P 500", "USD", "US88160R1014"),
    ("Berkshire Hathaway", "BRK.B", "USA", "Finance", "S&P 500", "USD", "US0846707026"),
    ("Visa", "V", "USA", "Finance", "S&P 500", "USD", "US92826C8394"),
    ("UnitedHealth", "UNH", "USA", "Santé", "S&P 500", "USD", "US91324P1021"),
    ("Walmart", "WMT", "USA", "Consommation", "S&P 500", "USD", "US9311421039"),
    ("Mastercard", "MA", "USA", "Finance", "S&P 500", "USD", "US57636Q1040"),
    ("Pfizer", "PFE", "USA", "Santé", "S&P 500", "USD", "US7170811035"),
    ("Broadcom", "AVGO", "USA", "Technologie", "S&P 500", "USD", "US11135F1012"),
    ("Costco", "COST", "USA", "Consommation", "S&P 500", "USD", "US22160K1051"),
    ("AMD", "AMD", "USA", "Technologie", "S&P 500", "USD", "US0079031078"),
    # Allemagne — DAX
    ("SAP", "SAP.DE", "Allemagne", "Technologie", "DAX", "EUR", "DE0007164600"),
    ("Siemens", "SIE.DE", "Allemagne", "Industrie", "DAX", "EUR", "DE0007236101"),
    ("Allianz", "ALV.DE", "Allemagne", "Finance", "DAX", "EUR", "DE0008404005"),
    ("BASF", "BAS.DE", "Allemagne", "Matériaux", "DAX", "EUR", "DE000BASF111"),
    ("Deutsche Telekom", "DTE.DE", "Allemagne", "Télécoms", "DAX", "EUR", "DE0005557508"),
    ("Rheinmetall", "RHM.DE", "Allemagne", "Industrie", "DAX", "EUR", "DE0007030009"),
    ("Infineon", "IFX.DE", "Allemagne", "Technologie", "DAX", "EUR", "DE0006231004"),
    ("BMW", "BMW.DE", "Allemagne", "Industrie", "DAX", "EUR", "DE0005190003"),
    ("Deutsche Bank", "DBK.DE", "Allemagne", "Finance", "DAX", "EUR", "DE0005140008"),
    ("Adidas", "ADS.DE", "Allemagne", "Consommation", "DAX", "EUR", "DE000A1EWWW0"),
    # UK — FTSE 100
    ("AstraZeneca", "AZN.L", "UK", "Santé", "FTSE 100", "GBP", "GB0009895292"),
    ("Shell", "SHEL.L", "UK", "Énergie", "FTSE 100", "GBP", "GB00BP6MXD84"),
    ("HSBC", "HSBA.L", "UK", "Finance", "FTSE 100", "GBP", "GB0005405286"),
    ("Unilever", "ULVR.L", "UK", "Consommation", "FTSE 100", "GBP", "GB00B10RZP78"),
    ("BP", "BP.L", "UK", "Énergie", "FTSE 100", "GBP", "GB0007980591"),
    ("GSK", "GSK.L", "UK", "Santé", "FTSE 100", "GBP", "GB00BN7SWP63"),
    ("Rio Tinto", "RIO.L", "UK", "Matériaux", "FTSE 100", "GBP", "GB0007188757"),
    ("Diageo", "DGE.L", "UK", "Consommation", "FTSE 100", "GBP", "GB0002374006"),
    # Suisse — SMI
    ("Nestlé", "NESN.SW", "Suisse", "Consommation", "SMI", "CHF", "CH0038863350"),
    ("Novartis", "NOVN.SW", "Suisse", "Santé", "SMI", "CHF", "CH0012005267"),
    ("Roche", "ROG.SW", "Suisse", "Santé", "SMI", "CHF", "CH0012032048"),
    ("Zurich Insurance", "ZURN.SW", "Suisse", "Finance", "SMI", "CHF", "CH0011075394"),
    ("ABB", "ABBN.SW", "Suisse", "Industrie", "SMI", "CHF", "CH0012221716"),
    # Japon — NIKKEI 225
    ("Toyota", "7203.T", "Japon", "Industrie", "NIKKEI 225", "JPY", "JP3633400001"),
    ("Sony", "6758.T", "Japon", "Technologie", "NIKKEI 225", "JPY", "JP3435000009"),
    ("SoftBank", "9984.T", "Japon", "Technologie", "NIKKEI 225", "JPY", "JP3436100006"),
    ("Keyence", "6861.T", "Japon", "Technologie", "NIKKEI 225", "JPY", "JP3236200006"),
    ("Nintendo", "7974.T", "Japon", "Technologie", "NIKKEI 225", "JPY", "JP3756600007"),
    ("Mitsubishi UFJ", "8306.T", "Japon", "Finance", "NIKKEI 225", "JPY", "JP3902900004"),
    # Canada — TSX
    ("Shopify", "SHOP.TO", "Canada", "Technologie", "TSX", "CAD", "CA82509L1076"),
    ("Royal Bank", "RY.TO", "Canada", "Finance", "TSX", "CAD", "CA7800871021"),
    ("Enbridge", "ENB.TO", "Canada", "Énergie", "TSX", "CAD", "CA29250N1050"),
    ("Barrick Gold", "ABX.TO", "Canada", "Matériaux", "TSX", "CAD", "CA0679011084"),
    # Pays-Bas — AEX
    ("ASML", "ASML.AS", "Pays-Bas", "Technologie", "AEX", "EUR", "NL0010273215"),
    ("Philips", "PHIA.AS", "Pays-Bas", "Santé", "AEX", "EUR", "NL0000009538"),
    ("ING Group", "INGA.AS", "Pays-Bas", "Finance", "AEX", "EUR", "NL0011821202"),
    ("Prosus", "PRX.AS", "Pays-Bas", "Technologie", "AEX", "EUR", "NL0013654783"),
    # Italie
    ("Ferrari", "RACE.MI", "Italie", "Industrie", "FTSE MIB", "EUR", "NL0011585146"),
    ("Enel", "ENEL.MI", "Italie", "Énergie", "FTSE MIB", "EUR", "IT0003128367"),
    ("Intesa Sanpaolo", "ISP.MI", "Italie", "Finance", "FTSE MIB", "EUR", "IT0000072618"),
    # Espagne
    ("Inditex", "ITX.MC", "Espagne", "Consommation", "IBEX 35", "EUR", "ES0148396007"),
    ("Iberdrola", "IBE.MC", "Espagne", "Énergie", "IBEX 35", "EUR", "ES0144580Y14"),
    ("Banco Santander", "SAN.MC", "Espagne", "Finance", "IBEX 35", "EUR", "ES0113900J37"),
    # Corée du Sud
    ("Samsung Electronics", "005930.KS", "Corée du Sud", "Technologie", "KOSPI", "KRW", "KR7005930003"),
    # Inde
    ("Reliance Industries", "RELIANCE.NS", "Inde", "Énergie", "NIFTY 50", "INR", "INE002A01018"),
    ("Infosys", "INFY.NS", "Inde", "Technologie", "NIFTY 50", "INR", "INE009A01021"),
    # Australie
    ("BHP Group", "BHP.AX", "Australie", "Matériaux", "ASX 200", "AUD", "AU000000BHP4"),
    ("Commonwealth Bank", "CBA.AX", "Australie", "Finance", "ASX 200", "AUD", "AU000000CBA7"),
    # Danemark
    ("Novo Nordisk", "NOVO-B.CO", "Danemark", "Santé", "C25", "DKK", "DK0060534915"),
    # Taïwan
    ("TSMC", "2330.TW", "Taïwan", "Technologie", "TAIEX", "TWD", "TW0002330008"),
]


def generate_stocks() -> list[Stock]:
    """Generate Stock ORM instances with realistic simulated data."""
    stocks = []
    for i, (name, ticker, country, sector, idx, currency, isin) in enumerate(RAW_STOCKS):
        r = lambda n: _sr(i * 137 + n)

        price = round(5 + r(1) * 995, 2)
        market_cap = round(r(6) * 2800 + 2, 1)

        # Performance
        c1d = round((r(2) - 0.48) * 8, 2)
        c1w = round((r(3) - 0.45) * 15, 2)
        c1m = round((r(4) - 0.42) * 25, 2)
        c3m = round((r(40) - 0.40) * 35, 2)
        c6m = round((r(41) - 0.38) * 50, 2)
        cytd = round((r(5) - 0.4) * 60, 2)
        c1y = round((r(42) - 0.35) * 80, 2)
        h52 = round(price * (1 + r(43) * 0.4), 2)
        l52 = round(price * (1 - r(44) * 0.35), 2)

        # Valuation
        per = round(r(7) * 60 + 3, 1)
        peg = round(r(71) * 3 + 0.2, 2)
        pbr = round(r(72) * 12 + 0.3, 2)
        ps = round(r(74) * 15 + 0.5, 2)
        ev_ebitda = round(r(73) * 25 + 2, 1)
        ev_sales = round(r(75) * 10 + 0.3, 2)
        ev = round(market_cap * (0.9 + r(76) * 0.4), 1)

        # Dividends
        div_yield = round(r(8) * 7, 2)
        payout = round(r(80) * 80 + 5, 1)

        # Profitability
        roe = round(r(9) * 40 - 5, 1)
        roa = round(r(90) * 20 - 2, 1)
        roic = round(r(91) * 30 - 3, 1)
        m_ebit = round(r(10) * 35 - 2, 1)
        m_net = round(r(92) * 25 - 3, 1)
        m_gross = round(r(93) * 50 + 15, 1)

        # Growth
        rev_g = round((r(11) - 0.3) * 50, 1)
        eps_g = round((r(23) - 0.3) * 60, 1)
        ebitda_g = round((r(94) - 0.3) * 45, 1)

        # Financial health
        nd_ebitda = round(r(12) * 5 - 0.5, 1)
        curr_r = round(r(24) * 3 + 0.3, 2)
        quick_r = round(curr_r * (0.5 + r(95) * 0.4), 2)
        d_eq = round(r(96) * 2.5, 2)
        fcf_y = round(r(13) * 12 - 1, 1)
        int_cov = round(r(97) * 20 + 1, 1)

        # Technical
        rsi = round(r(14) * 100)
        dmm50 = round((r(18) - 0.5) * 20, 1)
        dmm200 = round((r(19) - 0.45) * 30, 1)
        beta = round(r(16) * 1.8 + 0.2, 2)
        vol = round(r(17) * 50 + 5, 1)
        vol_avg = round(r(15) * 50 + 0.1, 1)

        # Analysts
        an_rating = round(1 + r(21) * 4, 1)
        an_count = int(5 + r(98) * 35)
        target = round(price * (0.8 + r(22) * 0.5), 2)
        ups = round(((target - price) / price) * 100, 1)

        # ESG
        esg = round(r(20) * 60 + 30)
        esg_e = round(r(100) * 60 + 30)
        esg_s = round(r(101) * 60 + 30)
        esg_g = round(r(102) * 60 + 30)

        # AI Scores
        ai_fund = round(30 + r(30) * 70)
        ai_tech = round(20 + r(31) * 80)
        ai_mom = round(15 + r(32) * 85)
        ai_risk = round(10 + r(33) * 90)
        ai_overall = round(ai_fund * 0.35 + ai_tech * 0.25 + ai_mom * 0.25 + ai_risk * 0.15)

        ai_signal = (
            "ACHAT FORT" if ai_overall >= 70 else
            "ACHAT" if ai_overall >= 55 else
            "NEUTRE" if ai_overall >= 45 else
            "VENTE" if ai_overall >= 30 else
            "VENTE FORTE"
        )

        stocks.append(Stock(
            name=name, ticker=ticker, country=country, sector=sector,
            market_index=idx, currency=currency, isin=isin,
            price=price,
            change_1d=c1d, change_1w=c1w, change_1m=c1m, change_3m=c3m,
            change_6m=c6m, change_ytd=cytd, change_1y=c1y,
            high_52w=h52, low_52w=l52,
            market_cap=market_cap, enterprise_value=ev,
            per=per, peg=peg, pbr=pbr, ps_ratio=ps,
            ev_ebitda=ev_ebitda, ev_sales=ev_sales,
            dividend_yield=div_yield, payout_ratio=payout,
            roe=roe, roa=roa, roic=roic,
            margin_ebit=m_ebit, margin_net=m_net, margin_gross=m_gross,
            revenue_growth=rev_g, eps_growth=eps_g, ebitda_growth=ebitda_g,
            net_debt_ebitda=nd_ebitda, current_ratio=curr_r,
            quick_ratio=quick_r, debt_equity=d_eq,
            fcf_yield=fcf_y, interest_coverage=int_cov,
            rsi=rsi, dist_mm50=dmm50, dist_mm200=dmm200,
            beta=beta, volatility=vol, volume_avg=vol_avg,
            analyst_rating=an_rating, analyst_count=an_count,
            target_price=target, upside=ups,
            esg_score=esg, esg_env=esg_e, esg_social=esg_s, esg_gov=esg_g,
            ai_score_overall=ai_overall, ai_score_fundamental=ai_fund,
            ai_score_technical=ai_tech, ai_score_momentum=ai_mom,
            ai_score_risk=ai_risk, ai_signal=ai_signal,
        ))

    return stocks


def _is_false_stat_payload(payload: dict) -> bool:
    """Detect clearly invalid market stats coming from an upstream source."""
    price = payload.get("price")
    return price is None or price <= 0


def _stock_from_payload(payload: dict) -> Stock:
    """Map a Yahoo Finance payload to the Stock ORM model."""
    return Stock(**payload)


async def refresh_stocks_from_yahoo(
    db: AsyncSession,
    min_required: int = 20,
    wipe_if_false_stats: bool = True,
) -> dict:
    """
    Refresh database from Yahoo Finance.

    Behavior:
    - Wipes the whole table if existing rows look invalid (false stats).
    - Replaces the table with fresh Yahoo data when enough valid rows are fetched.
    """
    total_before = (await db.execute(select(func.count(Stock.id)))).scalar() or 0
    false_before = (
        await db.execute(
            select(func.count(Stock.id)).where(
                or_(
                    Stock.price <= 0,
                    Stock.market_cap <= 0,
                    Stock.price.is_(None),
                    Stock.market_cap.is_(None),
                )
            )
        )
    ).scalar() or 0

    wiped_for_false_stats = False
    if wipe_if_false_stats and false_before > 0:
        await db.execute(delete(Stock))
        await db.commit()
        wiped_for_false_stats = True
        logger.warning(
            "🧹 Wiped stocks table because %s rows had false stats",
            false_before,
        )

    yahoo_payloads = await fetch_all_stocks(min_valid=min_required)
    valid_payloads = [p for p in yahoo_payloads if not _is_false_stat_payload(p)]

    if len(valid_payloads) < min_required:
        logger.warning(
            "⚠️ Yahoo refresh skipped: only %s valid rows fetched (min=%s)",
            len(valid_payloads),
            min_required,
        )
        total_after = (await db.execute(select(func.count(Stock.id)))).scalar() or 0
        return {
            "updated": False,
            "wiped_for_false_stats": wiped_for_false_stats,
            "reason": "not_enough_valid_yahoo_rows",
            "min_required": min_required,
            "fetched": len(yahoo_payloads),
            "valid": len(valid_payloads),
            "total_before": total_before,
            "total_after": total_after,
            "false_before": false_before,
        }

    await db.execute(delete(Stock))
    db.add_all([_stock_from_payload(payload) for payload in valid_payloads])
    await db.commit()

    total_after = (await db.execute(select(func.count(Stock.id)))).scalar() or 0
    logger.info("✅ Yahoo refresh completed with %s stocks", total_after)

    return {
        "updated": True,
        "wiped_for_false_stats": wiped_for_false_stats,
        "fetched": len(yahoo_payloads),
        "valid": len(valid_payloads),
        "total_before": total_before,
        "total_after": total_after,
        "false_before": false_before,
    }
