"""
Market Screener — Yahoo Finance Data Fetcher
Fetches real market data from Yahoo Finance using yfinance.
"""
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

YAHOO_CHUNK_SIZE = 8
YAHOO_MAX_RETRIES = 2
YAHOO_BACKOFF_SECONDS = 2
YAHOO_MAX_EMPTY_CHUNKS_AT_START = 3

# Thread pool for blocking yfinance calls
_executor = ThreadPoolExecutor(max_workers=4)

# Stock universe with known Yahoo Finance tickers
STOCK_UNIVERSE = [
    # France — CAC 40
    ("TotalEnergies",       "TTE.PA",    "France",        "Énergie",      "CAC 40",      "EUR", "FR0000120271"),
    ("LVMH",                "MC.PA",     "France",        "Consommation", "CAC 40",      "EUR", "FR0000121014"),
    ("Sanofi",              "SAN.PA",    "France",        "Santé",        "CAC 40",      "EUR", "FR0000120578"),
    ("Schneider Electric",  "SU.PA",     "France",        "Industrie",    "CAC 40",      "EUR", "FR0000121972"),
    ("Air Liquide",         "AI.PA",     "France",        "Matériaux",    "CAC 40",      "EUR", "FR0000120073"),
    ("BNP Paribas",         "BNP.PA",    "France",        "Finance",      "CAC 40",      "EUR", "FR0000131104"),
    ("Hermès",              "RMS.PA",    "France",        "Consommation", "CAC 40",      "EUR", "FR0000052292"),
    ("Dassault Systèmes",   "DSY.PA",    "France",        "Technologie",  "CAC 40",      "EUR", "FR0014003TT8"),
    ("Capgemini",           "CAP.PA",    "France",        "Technologie",  "CAC 40",      "EUR", "FR0000125338"),
    ("Orange",              "ORA.PA",    "France",        "Télécoms",     "CAC 40",      "EUR", "FR0000133308"),
    ("Vinci",               "DG.PA",     "France",        "Industrie",    "CAC 40",      "EUR", "FR0000125486"),
    ("Safran",              "SAF.PA",    "France",        "Industrie",    "CAC 40",      "EUR", "FR0000073272"),
    ("L'Oréal",             "OR.PA",     "France",        "Consommation", "CAC 40",      "EUR", "FR0000120321"),
    ("Saint-Gobain",        "SGO.PA",    "France",        "Matériaux",    "CAC 40",      "EUR", "FR0000125007"),
    ("Stellantis",          "STLAP.PA",  "France",        "Industrie",    "CAC 40",      "EUR", "NL00150001Q9"),
    # USA — S&P 500
    ("Apple",               "AAPL",      "USA",           "Technologie",  "S&P 500",     "USD", "US0378331005"),
    ("Microsoft",           "MSFT",      "USA",           "Technologie",  "S&P 500",     "USD", "US5949181045"),
    ("NVIDIA",              "NVDA",      "USA",           "Technologie",  "S&P 500",     "USD", "US67066G1040"),
    ("Amazon",              "AMZN",      "USA",           "Consommation", "S&P 500",     "USD", "US0231351067"),
    ("Alphabet",            "GOOGL",     "USA",           "Technologie",  "S&P 500",     "USD", "US02079K3059"),
    ("Meta",                "META",      "USA",           "Technologie",  "S&P 500",     "USD", "US30303M1027"),
    ("JPMorgan Chase",      "JPM",       "USA",           "Finance",      "S&P 500",     "USD", "US46625H1005"),
    ("Johnson & Johnson",   "JNJ",       "USA",           "Santé",        "S&P 500",     "USD", "US4781601046"),
    ("Exxon Mobil",         "XOM",       "USA",           "Énergie",      "S&P 500",     "USD", "US30231G1022"),
    ("Procter & Gamble",    "PG",        "USA",           "Consommation", "S&P 500",     "USD", "US7427181091"),
    ("Tesla",               "TSLA",      "USA",           "Industrie",    "S&P 500",     "USD", "US88160R1014"),
    ("Berkshire Hathaway",  "BRK-B",     "USA",           "Finance",      "S&P 500",     "USD", "US0846707026"),
    ("Visa",                "V",         "USA",           "Finance",      "S&P 500",     "USD", "US92826C8394"),
    ("UnitedHealth",        "UNH",       "USA",           "Santé",        "S&P 500",     "USD", "US91324P1021"),
    ("Walmart",             "WMT",       "USA",           "Consommation", "S&P 500",     "USD", "US9311421039"),
    ("Mastercard",          "MA",        "USA",           "Finance",      "S&P 500",     "USD", "US57636Q1040"),
    ("Pfizer",              "PFE",       "USA",           "Santé",        "S&P 500",     "USD", "US7170811035"),
    ("Broadcom",            "AVGO",      "USA",           "Technologie",  "S&P 500",     "USD", "US11135F1012"),
    ("Costco",              "COST",      "USA",           "Consommation", "S&P 500",     "USD", "US22160K1051"),
    ("AMD",                 "AMD",       "USA",           "Technologie",  "S&P 500",     "USD", "US0079031078"),
    # Allemagne — DAX
    ("SAP",                 "SAP.DE",    "Allemagne",     "Technologie",  "DAX",         "EUR", "DE0007164600"),
    ("Siemens",             "SIE.DE",    "Allemagne",     "Industrie",    "DAX",         "EUR", "DE0007236101"),
    ("Allianz",             "ALV.DE",    "Allemagne",     "Finance",      "DAX",         "EUR", "DE0008404005"),
    ("BASF",                "BAS.DE",    "Allemagne",     "Matériaux",    "DAX",         "EUR", "DE000BASF111"),
    ("Deutsche Telekom",    "DTE.DE",    "Allemagne",     "Télécoms",     "DAX",         "EUR", "DE0005557508"),
    ("Rheinmetall",         "RHM.DE",    "Allemagne",     "Industrie",    "DAX",         "EUR", "DE0007030009"),
    ("Infineon",            "IFX.DE",    "Allemagne",     "Technologie",  "DAX",         "EUR", "DE0006231004"),
    ("BMW",                 "BMW.DE",    "Allemagne",     "Industrie",    "DAX",         "EUR", "DE0005190003"),
    ("Deutsche Bank",       "DBK.DE",    "Allemagne",     "Finance",      "DAX",         "EUR", "DE0005140008"),
    ("Adidas",              "ADS.DE",    "Allemagne",     "Consommation", "DAX",         "EUR", "DE000A1EWWW0"),
    # UK — FTSE 100
    ("AstraZeneca",         "AZN.L",     "UK",            "Santé",        "FTSE 100",    "GBP", "GB0009895292"),
    ("Shell",               "SHEL.L",    "UK",            "Énergie",      "FTSE 100",    "GBP", "GB00BP6MXD84"),
    ("HSBC",                "HSBA.L",    "UK",            "Finance",      "FTSE 100",    "GBP", "GB0005405286"),
    ("Unilever",            "ULVR.L",    "UK",            "Consommation", "FTSE 100",    "GBP", "GB00B10RZP78"),
    ("BP",                  "BP.L",      "UK",            "Énergie",      "FTSE 100",    "GBP", "GB0007980591"),
    ("GSK",                 "GSK.L",     "UK",            "Santé",        "FTSE 100",    "GBP", "GB00BN7SWP63"),
    ("Rio Tinto",           "RIO.L",     "UK",            "Matériaux",    "FTSE 100",    "GBP", "GB0007188757"),
    ("Diageo",              "DGE.L",     "UK",            "Consommation", "FTSE 100",    "GBP", "GB0002374006"),
    # Suisse — SMI
    ("Nestlé",              "NESN.SW",   "Suisse",        "Consommation", "SMI",         "CHF", "CH0038863350"),
    ("Novartis",            "NOVN.SW",   "Suisse",        "Santé",        "SMI",         "CHF", "CH0012005267"),
    ("Roche",               "ROG.SW",    "Suisse",        "Santé",        "SMI",         "CHF", "CH0012032048"),
    ("Zurich Insurance",    "ZURN.SW",   "Suisse",        "Finance",      "SMI",         "CHF", "CH0011075394"),
    ("ABB",                 "ABBN.SW",   "Suisse",        "Industrie",    "SMI",         "CHF", "CH0012221716"),
    # Japon — NIKKEI 225
    ("Toyota",              "7203.T",    "Japon",         "Industrie",    "NIKKEI 225",  "JPY", "JP3633400001"),
    ("Sony",                "6758.T",    "Japon",         "Technologie",  "NIKKEI 225",  "JPY", "JP3435000009"),
    ("SoftBank",            "9984.T",    "Japon",         "Technologie",  "NIKKEI 225",  "JPY", "JP3436100006"),
    ("Keyence",             "6861.T",    "Japon",         "Technologie",  "NIKKEI 225",  "JPY", "JP3236200006"),
    ("Nintendo",            "7974.T",    "Japon",         "Technologie",  "NIKKEI 225",  "JPY", "JP3756600007"),
    ("Mitsubishi UFJ",      "8306.T",    "Japon",         "Finance",      "NIKKEI 225",  "JPY", "JP3902900004"),
    # Canada — TSX
    ("Shopify",             "SHOP.TO",   "Canada",        "Technologie",  "TSX",         "CAD", "CA82509L1076"),
    ("Royal Bank",          "RY.TO",     "Canada",        "Finance",      "TSX",         "CAD", "CA7800871021"),
    ("Enbridge",            "ENB.TO",    "Canada",        "Énergie",      "TSX",         "CAD", "CA29250N1050"),
    ("Barrick Gold",        "ABX.TO",    "Canada",        "Matériaux",    "TSX",         "CAD", "CA0679011084"),
    # Pays-Bas — AEX
    ("ASML",                "ASML.AS",   "Pays-Bas",      "Technologie",  "AEX",         "EUR", "NL0010273215"),
    ("Philips",             "PHIA.AS",   "Pays-Bas",      "Santé",        "AEX",         "EUR", "NL0000009538"),
    ("ING Group",           "INGA.AS",   "Pays-Bas",      "Finance",      "AEX",         "EUR", "NL0011821202"),
    ("Prosus",              "PRX.AS",    "Pays-Bas",      "Technologie",  "AEX",         "EUR", "NL0013654783"),
    # Italie — FTSE MIB
    ("Ferrari",             "RACE.MI",   "Italie",        "Industrie",    "FTSE MIB",    "EUR", "NL0011585146"),
    ("Enel",                "ENEL.MI",   "Italie",        "Énergie",      "FTSE MIB",    "EUR", "IT0003128367"),
    ("Intesa Sanpaolo",     "ISP.MI",    "Italie",        "Finance",      "FTSE MIB",    "EUR", "IT0000072618"),
    # Espagne — IBEX 35
    ("Inditex",             "ITX.MC",    "Espagne",       "Consommation", "IBEX 35",     "EUR", "ES0148396007"),
    ("Iberdrola",           "IBE.MC",    "Espagne",       "Énergie",      "IBEX 35",     "EUR", "ES0144580Y14"),
    ("Banco Santander",     "SAN.MC",    "Espagne",       "Finance",      "IBEX 35",     "EUR", "ES0113900J37"),
    # Corée du Sud — KOSPI
    ("Samsung Electronics", "005930.KS", "Corée du Sud",  "Technologie",  "KOSPI",       "KRW", "KR7005930003"),
    # Inde — NIFTY 50
    ("Reliance Industries", "RELIANCE.NS","Inde",         "Énergie",      "NIFTY 50",    "INR", "INE002A01018"),
    ("Infosys",             "INFY.NS",   "Inde",          "Technologie",  "NIFTY 50",    "INR", "INE009A01021"),
    # Australie — ASX 200
    ("BHP Group",           "BHP.AX",    "Australie",     "Matériaux",    "ASX 200",     "AUD", "AU000000BHP4"),
    ("Commonwealth Bank",   "CBA.AX",    "Australie",     "Finance",      "ASX 200",     "AUD", "AU000000CBA7"),
    # Danemark — C25
    ("Novo Nordisk",        "NOVO-B.CO", "Danemark",      "Santé",        "C25",         "DKK", "DK0060534915"),
    # Taïwan — TAIEX
    ("TSMC",                "2330.TW",   "Taïwan",        "Technologie",  "TAIEX",       "TWD", "TW0002330008"),
]


def _safe_float(value, default: Optional[float] = None) -> Optional[float]:
    """Convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        f = float(value)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return default


def _fetch_ticker_data(ticker: str, meta: tuple) -> Optional[dict]:
    """
    Fetch real market data from Yahoo Finance for a single ticker.
    Returns a dict of stock fields or None on failure.
    """
    name, ticker_sym, country, sector, index, currency, isin = meta
    try:
        yf_ticker = yf.Ticker(ticker_sym)
        info = yf_ticker.info

        # Basic check - if no price data, ticker likely failed
        price = _safe_float(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"))
        if price is None or price <= 0:
            logger.warning(f"⚠️  No price data for {ticker_sym}, skipping")
            return None

        # Historical data for performance metrics
        hist = yf_ticker.history(period="1y")
        hist_1d = yf_ticker.history(period="2d")

        change_1d = 0.0
        if len(hist_1d) >= 2:
            p0, p1 = hist_1d["Close"].iloc[-2], hist_1d["Close"].iloc[-1]
            if p0 > 0:
                change_1d = round((p1 - p0) / p0 * 100, 2)

        change_1w = 0.0
        if len(hist) >= 5:
            p0 = hist["Close"].iloc[-6] if len(hist) >= 6 else hist["Close"].iloc[0]
            if p0 > 0:
                change_1w = round((price - float(p0)) / float(p0) * 100, 2)

        change_1m = 0.0
        if len(hist) >= 22:
            p0 = hist["Close"].iloc[-23]
            if p0 > 0:
                change_1m = round((price - float(p0)) / float(p0) * 100, 2)

        change_3m = 0.0
        if len(hist) >= 63:
            p0 = hist["Close"].iloc[-64]
            if p0 > 0:
                change_3m = round((price - float(p0)) / float(p0) * 100, 2)

        change_6m = 0.0
        if len(hist) >= 126:
            p0 = hist["Close"].iloc[-127]
            if p0 > 0:
                change_6m = round((price - float(p0)) / float(p0) * 100, 2)

        # YTD: from Jan 1 of current year
        change_ytd = 0.0
        if len(hist) > 0:
            import datetime
            ytd_hist = yf_ticker.history(
                start=datetime.date(datetime.date.today().year, 1, 2),
                end=datetime.date.today(),
            )
            if len(ytd_hist) >= 1:
                p0 = ytd_hist["Close"].iloc[0]
                if p0 > 0:
                    change_ytd = round((price - float(p0)) / float(p0) * 100, 2)

        change_1y = 0.0
        if len(hist) >= 2:
            p0 = hist["Close"].iloc[0]
            if p0 > 0:
                change_1y = round((price - float(p0)) / float(p0) * 100, 2)

        # 52-week high/low
        high_52w = _safe_float(info.get("fiftyTwoWeekHigh"))
        low_52w = _safe_float(info.get("fiftyTwoWeekLow"))
        if high_52w is None and len(hist) > 0:
            high_52w = round(float(hist["High"].max()), 2)
        if low_52w is None and len(hist) > 0:
            low_52w = round(float(hist["Low"].min()), 2)

        # Valuation
        market_cap_raw = _safe_float(info.get("marketCap"), 0.0)
        market_cap = round(market_cap_raw / 1e9, 2) if market_cap_raw else 0.0

        ev_raw = _safe_float(info.get("enterpriseValue"))
        enterprise_value = round(ev_raw / 1e9, 2) if ev_raw else None

        per           = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
        peg           = _safe_float(info.get("pegRatio"))
        pbr           = _safe_float(info.get("priceToBook"))
        ps_ratio      = _safe_float(info.get("priceToSalesTrailing12Months"))
        ev_ebitda     = _safe_float(info.get("enterpriseToEbitda"))
        ev_sales      = _safe_float(info.get("enterpriseToRevenue"))

        # Dividends
        dividend_yield = _safe_float(info.get("dividendYield"), 0.0)
        if dividend_yield:
            dividend_yield = round(dividend_yield * 100, 2)  # convert to %
        payout_ratio = _safe_float(info.get("payoutRatio"))
        if payout_ratio:
            payout_ratio = round(payout_ratio * 100, 2)

        # Profitability
        roe         = _safe_float(info.get("returnOnEquity"))
        if roe: roe = round(roe * 100, 2)
        roa         = _safe_float(info.get("returnOnAssets"))
        if roa: roa = round(roa * 100, 2)
        margin_gross = _safe_float(info.get("grossMargins"))
        if margin_gross: margin_gross = round(margin_gross * 100, 2)
        margin_ebit  = _safe_float(info.get("operatingMargins"))
        if margin_ebit: margin_ebit = round(margin_ebit * 100, 2)
        margin_net   = _safe_float(info.get("profitMargins"))
        if margin_net: margin_net = round(margin_net * 100, 2)

        # Growth
        revenue_growth = _safe_float(info.get("revenueGrowth"))
        if revenue_growth: revenue_growth = round(revenue_growth * 100, 2)
        eps_growth = _safe_float(info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth"))
        if eps_growth: eps_growth = round(eps_growth * 100, 2)

        # Financial health
        current_ratio    = _safe_float(info.get("currentRatio"))
        quick_ratio      = _safe_float(info.get("quickRatio"))
        debt_equity      = _safe_float(info.get("debtToEquity"))
        if debt_equity: debt_equity = round(debt_equity / 100, 4)  # yfinance gives % form

        total_debt = _safe_float(info.get("totalDebt"), 0.0)
        ebitda     = _safe_float(info.get("ebitda"))
        net_debt_ebitda = None
        if ebitda and ebitda != 0 and total_debt:
            cash = _safe_float(info.get("totalCash"), 0.0) or 0.0
            net_debt = total_debt - cash
            net_debt_ebitda = round(net_debt / ebitda, 2)

        fcf = _safe_float(info.get("freeCashflow"))
        fcf_yield = None
        if fcf and market_cap_raw and market_cap_raw > 0:
            fcf_yield = round(fcf / market_cap_raw * 100, 2)

        interest_coverage = _safe_float(info.get("ebitdaMargins"))  # proxy

        # --- Technical ---
        beta    = _safe_float(info.get("beta"))
        vol_avg = _safe_float(info.get("averageVolume"))
        if vol_avg:
            vol_avg = round(vol_avg / 1e6, 2)  # convert to millions

        # RSI (14-period) from 1-year history
        rsi = None
        dist_mm50 = None
        dist_mm200 = None
        if len(hist) >= 14:
            closes = hist["Close"].values.astype(float)
            deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
            gains = [max(d, 0) for d in deltas[-14:]]
            losses = [abs(min(d, 0)) for d in deltas[-14:]]
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = round(100 - (100 / (1 + rs)), 1)
            else:
                rsi = 100.0

        if len(hist) >= 50:
            mm50 = float(hist["Close"].iloc[-50:].mean())
            if mm50 > 0:
                dist_mm50 = round((price - mm50) / mm50 * 100, 2)

        if len(hist) >= 200:
            mm200 = float(hist["Close"].iloc[-200:].mean())
            if mm200 > 0:
                dist_mm200 = round((price - mm200) / mm200 * 100, 2)

        # --- Analysts ---
        analyst_rating = _safe_float(info.get("recommendationMean"))
        analyst_count = info.get("numberOfAnalystOpinions")
        if analyst_count is not None:
            try:
                analyst_count = int(analyst_count)
            except (TypeError, ValueError):
                analyst_count = None
        target_price = _safe_float(info.get("targetMeanPrice"))
        upside = None
        if target_price and price > 0:
            upside = round((target_price - price) / price * 100, 1)

        # Override currency from yfinance if available
        yf_currency = info.get("currency", currency)

        return {
            "name":             name,
            "ticker":           ticker_sym,
            "country":          country,
            "sector":           sector,
            "market_index":     index,
            "currency":         yf_currency or currency,
            "isin":             isin,
            "price":            round(price, 4),
            "change_1d":        change_1d,
            "change_1w":        change_1w,
            "change_1m":        change_1m,
            "change_3m":        change_3m,
            "change_6m":        change_6m,
            "change_ytd":       change_ytd,
            "change_1y":        change_1y,
            "high_52w":         high_52w,
            "low_52w":          low_52w,
            "market_cap":       market_cap,
            "enterprise_value": enterprise_value,
            "per":              per,
            "peg":              peg,
            "pbr":              pbr,
            "ps_ratio":         ps_ratio,
            "ev_ebitda":        ev_ebitda,
            "ev_sales":         ev_sales,
            "dividend_yield":   dividend_yield or 0.0,
            "payout_ratio":     payout_ratio,
            "roe":              roe,
            "roa":              roa,
            "roic":             None,      # not available in yfinance
            "margin_ebit":      margin_ebit,
            "margin_net":       margin_net,
            "margin_gross":     margin_gross,
            "revenue_growth":   revenue_growth,
            "eps_growth":       eps_growth,
            "ebitda_growth":    None,      # not available in yfinance
            "net_debt_ebitda":  net_debt_ebitda,
            "current_ratio":    current_ratio,
            "quick_ratio":      quick_ratio,
            "debt_equity":      debt_equity,
            "fcf_yield":        fcf_yield,
            "interest_coverage": interest_coverage,
            # technical
            "beta":             beta,
            "volume_avg":       vol_avg,
            "rsi":              rsi,
            "dist_mm50":        dist_mm50,
            "dist_mm200":       dist_mm200,
            "volatility":       None,      # would need returns std dev
            # analysts
            "analyst_rating":   analyst_rating,
            "analyst_count":    analyst_count,
            "target_price":     target_price,
            "upside":           upside,
        }

    except Exception as exc:
        logger.warning(f"⚠️  Failed to fetch {ticker_sym}: {exc}")
        return None


async def fetch_stock_data(ticker_sym: str, meta: tuple) -> Optional[dict]:
    """Async wrapper around the blocking yfinance call."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _fetch_ticker_data, ticker_sym, meta)


async def fetch_all_stocks(min_valid: int | None = None, ticker_offset: int = 0) -> list[dict]:
    """
    Fetch real market data from Yahoo Finance using chunked batch requests.
    Chunking + retries improves resilience against Yahoo rate limiting.
    """
    universe = list(STOCK_UNIVERSE)
    if universe and ticker_offset:
        shift = ticker_offset % len(universe)
        universe = universe[shift:] + universe[:shift]

    logger.info(
        "📡 Fetching data from Yahoo Finance for %s tickers (chunk=%s, retries=%s)",
        len(universe),
        YAHOO_CHUNK_SIZE,
        YAHOO_MAX_RETRIES,
    )

    tickers = [meta[1] for meta in universe]
    loop = asyncio.get_event_loop()

    history_by_ticker: dict[str, pd.DataFrame] = {}
    empty_chunks_while_empty = 0

    for start in range(0, len(tickers), YAHOO_CHUNK_SIZE):
        chunk = tickers[start:start + YAHOO_CHUNK_SIZE]
        unresolved = list(chunk)

        for attempt in range(1, YAHOO_MAX_RETRIES + 1):
            if not unresolved:
                break

            pending = list(unresolved)

            def _download_chunk() -> pd.DataFrame:
                return yf.download(
                    tickers=" ".join(pending),
                    period="1y",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )

            try:
                history = await loop.run_in_executor(_executor, _download_chunk)
            except Exception as exc:
                logger.warning(
                    "⚠️ Yahoo chunk download failed (attempt %s/%s, size=%s): %s",
                    attempt,
                    YAHOO_MAX_RETRIES,
                    len(pending),
                    exc,
                )
                history = None

            if history is None or history.empty:
                if attempt < YAHOO_MAX_RETRIES:
                    await asyncio.sleep(YAHOO_BACKOFF_SECONDS * (2 ** (attempt - 1)))
                continue

            received: list[str] = []
            if isinstance(history.columns, pd.MultiIndex):
                available = set(history.columns.get_level_values(0))
                for ticker in pending:
                    if ticker in available:
                        ticker_data = history[ticker]
                        if isinstance(ticker_data, pd.Series):
                            ticker_data = ticker_data.to_frame(name="Close")
                        df = ticker_data.dropna(how="all")
                        if not df.empty:
                            history_by_ticker[ticker] = df
                            received.append(ticker)
            else:
                # Single-ticker fallback shape.
                if len(pending) == 1:
                    df = history.dropna(how="all")
                    if not df.empty:
                        history_by_ticker[pending[0]] = df
                        received.append(pending[0])

            unresolved = [ticker for ticker in unresolved if ticker not in received]

            if unresolved and attempt < YAHOO_MAX_RETRIES:
                await asyncio.sleep(YAHOO_BACKOFF_SECONDS * (2 ** (attempt - 1)))

        if unresolved:
            logger.warning("⚠️ Yahoo unresolved tickers after retries: %s", len(unresolved))
        else:
            empty_chunks_while_empty = 0

        # If Yahoo is globally rate-limiting this host, avoid blocking startup too long.
        if unresolved and not history_by_ticker:
            empty_chunks_while_empty += 1
            if empty_chunks_while_empty >= YAHOO_MAX_EMPTY_CHUNKS_AT_START:
                logger.warning(
                    "⚠️ Aborting Yahoo fetch early after %s empty chunks (rate limited)",
                    empty_chunks_while_empty,
                )
                break

        if min_valid is not None and len(history_by_ticker) >= min_valid:
            logger.info("✅ Early stop: collected %s tickers (target=%s)", len(history_by_ticker), min_valid)
            break

    stocks: list[dict] = []
    failed = 0

    for name, ticker_sym, country, sector, index, currency, isin in universe:
        try:
            df = history_by_ticker.get(ticker_sym)
            if df is None:
                failed += 1
                continue

            if df.empty or "Close" not in df.columns:
                failed += 1
                continue

            close = df["Close"].dropna()
            high = df["High"].dropna() if "High" in df.columns else pd.Series(dtype=float)
            low = df["Low"].dropna() if "Low" in df.columns else pd.Series(dtype=float)
            volume = df["Volume"].dropna() if "Volume" in df.columns else pd.Series(dtype=float)

            if close.empty:
                failed += 1
                continue

            price = float(close.iloc[-1])
            if price <= 0:
                failed += 1
                continue

            def pct_change(days: int) -> float:
                if len(close) <= days:
                    return 0.0
                start = float(close.iloc[-days - 1])
                if start <= 0:
                    return 0.0
                return round((price - start) / start * 100, 2)

            # Approximate YTD using first trading day of current year in available history.
            ytd_change = 0.0
            try:
                year = pd.Timestamp.utcnow().year
                ytd_series = close[close.index >= f"{year}-01-01"]
                if not ytd_series.empty and float(ytd_series.iloc[0]) > 0:
                    ytd_change = round((price - float(ytd_series.iloc[0])) / float(ytd_series.iloc[0]) * 100, 2)
            except Exception:
                ytd_change = 0.0

            high_52w = round(float(high.max()), 2) if not high.empty else None
            low_52w = round(float(low.min()), 2) if not low.empty else None
            volume_avg = round(float(volume.tail(20).mean()) / 1e6, 2) if not volume.empty else None

            # Simple technical signals from market data only.
            dist_mm50 = None
            dist_mm200 = None
            if len(close) >= 50:
                mm50 = float(close.tail(50).mean())
                if mm50 > 0:
                    dist_mm50 = round((price - mm50) / mm50 * 100, 2)
            if len(close) >= 200:
                mm200 = float(close.tail(200).mean())
                if mm200 > 0:
                    dist_mm200 = round((price - mm200) / mm200 * 100, 2)

            daily_returns = close.pct_change().dropna()
            volatility = None
            if not daily_returns.empty:
                volatility = round(float(daily_returns.std()) * (252 ** 0.5) * 100, 2)

            # Lightweight AI-style scoring from real price behavior.
            momentum_score = max(0.0, min(100.0, 50 + pct_change(252) * 1.2))
            technical_score = max(0.0, min(100.0, 50 + (dist_mm50 or 0) * 1.0))
            risk_score = max(0.0, min(100.0, 70 - (volatility or 25) * 0.8))
            fundamental_score = 50.0
            ai_overall = round(
                0.35 * fundamental_score
                + 0.25 * technical_score
                + 0.25 * momentum_score
                + 0.15 * risk_score,
                1,
            )
            ai_signal = (
                "ACHAT FORT" if ai_overall >= 70 else
                "ACHAT" if ai_overall >= 55 else
                "NEUTRE" if ai_overall >= 45 else
                "VENTE" if ai_overall >= 30 else
                "VENTE FORTE"
            )

            stocks.append(
                {
                    "name": name,
                    "ticker": ticker_sym,
                    "country": country,
                    "sector": sector,
                    "market_index": index,
                    "currency": currency,
                    "isin": isin,
                    "price": round(price, 4),
                    "change_1d": pct_change(1),
                    "change_1w": pct_change(5),
                    "change_1m": pct_change(21),
                    "change_3m": pct_change(63),
                    "change_6m": pct_change(126),
                    "change_ytd": ytd_change,
                    "change_1y": pct_change(252),
                    "high_52w": high_52w,
                    "low_52w": low_52w,
                    # No reliable market cap in batch mode without extra rate-limited calls.
                    "market_cap": 0.0,
                    "enterprise_value": None,
                    "per": None,
                    "peg": None,
                    "pbr": None,
                    "ps_ratio": None,
                    "ev_ebitda": None,
                    "ev_sales": None,
                    "dividend_yield": 0.0,
                    "payout_ratio": None,
                    "roe": None,
                    "roa": None,
                    "roic": None,
                    "margin_ebit": None,
                    "margin_net": None,
                    "margin_gross": None,
                    "revenue_growth": None,
                    "eps_growth": None,
                    "ebitda_growth": None,
                    "net_debt_ebitda": None,
                    "current_ratio": None,
                    "quick_ratio": None,
                    "debt_equity": None,
                    "fcf_yield": None,
                    "interest_coverage": None,
                    "rsi": None,
                    "dist_mm50": dist_mm50,
                    "dist_mm200": dist_mm200,
                    "beta": None,
                    "volatility": volatility,
                    "volume_avg": volume_avg,
                    "analyst_rating": None,
                    "analyst_count": None,
                    "target_price": None,
                    "upside": None,
                    "esg_score": None,
                    "esg_env": None,
                    "esg_social": None,
                    "esg_gov": None,
                    "ai_score_overall": ai_overall,
                    "ai_score_fundamental": fundamental_score,
                    "ai_score_technical": round(technical_score, 1),
                    "ai_score_momentum": round(momentum_score, 1),
                    "ai_score_risk": round(risk_score, 1),
                    "ai_signal": ai_signal,
                }
            )

        except Exception as exc:
            logger.warning("⚠️ Failed to parse %s from batch data: %s", ticker_sym, exc)
            failed += 1

    logger.info(
        "✅ Fetched %s stocks from Yahoo (%s failed, %s chunked requests)",
        len(stocks),
        failed,
        (len(tickers) + YAHOO_CHUNK_SIZE - 1) // YAHOO_CHUNK_SIZE,
    )
    return stocks
