# Price Source Selection

Use this reference when choosing how to fetch commodity prices.

## Preferred Methods

| commodity type | default method | notes |
| --- | --- | --- |
| listed stocks, ETFs, broad public funds | `beanprice` Yahoo source | Use exact exchange/listing evidence when symbols are ambiguous. |
| fiat FX | `beanprice` ECB source when EUR-based rates fit; otherwise search for a supported beanprice FX source | Record base and quote currency explicitly. |
| crypto | `beanprice` Coinbase source when supported | Confirm quote currency and historical support before writing. |
| indices | `beanprice` Yahoo or Financial Times source when supported | Use only for valuation/reference commodities, not held units unless ledger semantics are clear. |
| local mutual funds, pension funds, metals, private assets, reward points | web search to discover an authoritative page, then prefer a matching beanprice source if available | Require explicit source attribution and review before reuse. |

Beanprice advertises sources for Alphavantage, Coinbase, Coincap, Coinmarketcap, European Central Bank rates, Financial Times, OANDA, Quandl/Nasdaq Data Link, Rates API, Thrift Savings Plan, Yahoo, and EastMoneyFund. Prefer these before falling back to a manual web-search price page.

## Beanprice Availability Search

1. Build candidate source strings from the commodity, quote currency, exchange, ISIN, fund provider, and asset class.
2. Probe candidates with `./.venv/bin/bean-price -e '<QUOTE>:<SOURCE>/<SYMBOL>'`, for example `./.venv/bin/bean-price -e 'USD:yahoo/AAPL'`.
3. Treat a successful Beancount `price` line as source evidence; record the exact source string in the price artifact and memory suggestion.
4. If candidates fail, web-search the commodity with terms such as `<name> <ticker> yahoo finance`, `<ISIN> Financial Times`, `<fund name> NAV`, or `<currency pair> ECB rate`.
5. Ask for review before persisting a new source mapping, especially for ticker collisions, local listings, share classes, accumulating/distributing funds, or non-public assets.

## Method Shapes

`beanprice` source memory:

```json
{
  "method_type": "beanprice",
  "commodity": "AAPL",
  "quote_currency": "USD",
  "source": "USD:yahoo/AAPL"
}
```

Web-search fallback memory:

```json
{
  "method_type": "web_search",
  "commodity": "EXAMPLE",
  "quote_currency": "EUR",
  "source_url": "https://www.example.com/markets/example",
  "query": "EXAMPLE fund NAV EUR official"
}
```

## Web Search Starting Points

- Yahoo Finance: `https://finance.yahoo.com/quote/<symbol>` for listed stocks, ETFs, funds, currencies, and some crypto pairs.
- Financial Times Markets: `https://markets.ft.com/data/` for listed instruments, funds, and ISIN-based lookups.
- European Central Bank: `https://www.ecb.europa.eu/stats/eurofxref/` for EUR reference FX rates.
- Coinbase: `https://www.coinbase.com/price/<asset>` for major crypto assets.
- CoinMarketCap: `https://coinmarketcap.com/currencies/<asset>/` for crypto cross-checks.
- CoinCap: `https://coincap.io/assets/<asset>` for crypto cross-checks.
- Nasdaq Data Link: `https://data.nasdaq.com/` for datasets formerly associated with Quandl.
- OANDA rates: `https://www.oanda.com/currency-converter/` for FX cross-checks.
- TSP fund performance: `https://www.tsp.gov/fund-performance/` for US Thrift Savings Plan funds.
- EastMoney Fund: `https://fund.eastmoney.com/` for Chinese fund lookups.

## Selection Rules

- Prefer explicit ledger commodity metadata over broad ticker inference.
- Require a quoted currency for every external price.
- For ticker collisions, require exchange, ISIN, CUSIP, fund provider, or official source evidence before reuse.
- For web search, prefer issuer, exchange, central bank, or fund-provider pages over aggregators.
- When beanprice and web-search evidence conflict, record the conflict in the price artifact and ask the import orchestrator or direct user to choose.
