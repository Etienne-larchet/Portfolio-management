from dataclasses import dataclass, field
import pandas as pd


@dataclass(kw_only=True)
class Security:
    quantity: int
    risk: int | None = None
    variance: int | None = None
    sd: int | None = None
    history = pd.DataFrame({
         "date_str": [], 
         "date_ts": [],
         "open": [],
         "close": [],   
    })


class SecuritiesList:
     stats: dict = {}
     positions: dict= {}

@dataclass
class Stock(Security):
    ticker: str 
    sector: str | None = None
    country: str | None = None

    def __init__(self, ticker: str, quantity:int, sector: str | None = None, country: str | None = None):
        self.ticker = ticker
        self.quantity = quantity
        self.sector = sector
        self.country = country


@dataclass
class Bond(Security):
    # Work in progress
    pass


@dataclass
class Portfolio:
    stocks: SecuritiesList = field(default_factory=SecuritiesList)
    bonds: SecuritiesList = field(default_factory=SecuritiesList)
    stats: dict = field(default_factory=dict)
    
    def add_security(self, type: int, ticker: str, quantity: int):
        match type:
            case 0:
                    self.stocks.positions[ticker] = Stock(ticker, quantity = quantity)


def main():
    ptf = Portfolio()
    ptf.add_security(0, "msft", 1)
    print(ptf.stocks.positions)
     

if __name__ == "__main__":
    main()