import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt

from classes.Portfolio import Portfolio
from mylibs.t212 import Trading212
from mylibs.Oath import ApiKeys


def get_ticker(stocks_list: dict) -> dict:
    data = {
        't212_id': [],
        'ticker': [],
        'quantity': []
    }
    df = pd.DataFrame(data)
    for index, stock in enumerate(stocks_list):
        ticker = input(f'{index+1}/{len(stocks_list)} - Yfinance ticker for {stock['ticker']} : ')
        new_row = {'t212_id': stock['ticker'], 'ticker': ticker, 'quantity': stock['quantity']}
        df.loc[len(df)] = new_row
        df = df.reset_index(drop=True)
    data = df.to_dict(orient="records")
    return data

def define_new_tickers(ptf: Portfolio, broker_data: dict) -> list:
    ptf_tickers = [(i['t212_id'], i['ticker']) for i in ptf.stocks.positions]
    new_stocks = [i for i in broker_data if i['ticker'] not in [t212_id for (t212_id, _) in ptf_tickers]]
    old_stocks = [i for i in broker_data if i not in new_stocks]

    update = []

    # New Stocks
    for index, stock in enumerate(new_stocks):
        ticker = input(f'{index+1}/{len(new_stocks)} - Yfinance ticker for {stock['ticker']} : ')
        if ticker != "":
            update.append([ticker, {'t212_id': stock['ticker'], 'quantity': stock['quantity']}])

    # Old Stocks 
    for stock in old_stocks:
        ticker = ""
        for i in ptf_tickers:
            if stock['ticker'] == i[0]:
                ticker = i[1]
        update.append([ticker, {'quantity': stock['quantity']}])

    return update

def generate_randoms_proba(probas_req: dict, arraysize=1, seed: int | None = None) -> pd.DataFrame:
    """
    Generate random probability distributions given specified minimum and maximum bounds for each ticker.

    **Example usage:**
    >>> probas_req = {
    >>> 'tickers': ['AAPL', 'AMZN', 'MSFT'],
    >>> 'min': [0.05, 0.1, 0.1],
    >>> 'max': [0.5, 0.6, 0.3]
    >>> }
    >>> result = generate_randoms_proba(probas_req, 300)
    >>> print(result)
    """
    def _weights_calc(min_probs, max_probs, n, seed: int | None = None):
        random_values = np.random.default_rng(seed).random(size=(arraysize, n), dtype=np.float32)
        weights = min_probs + max_probs * random_values
        weights /= weights.sum(axis=1, keepdims=True)
        return weights
    
    n = len(probas_req['tickers'])
    min_probs = probas_req.get('min', None)
    max_probs = probas_req.get('max', None)
    if not min_probs:
        min_probs = np.zeros(n)
    if not max_probs:
        max_probs = np.ones(n)
    if sum(min_probs) > 1:
        raise ValueError("Sum of min probabilities must be inferior to 1")
    elif sum(max_probs) < 1:
        raise ValueError("Sum of max probabilities must be superior to 1")  
    weights = _weights_calc(min_probs=min_probs, max_probs=max_probs, n=n, seed=seed)
    return pd.DataFrame(weights, columns=probas_req['tickers'])

    
def main() -> None:
    # Create Portfolio instance
    ptf = Portfolio()
    ptf.load("Portfolio.json")

    t212 = Trading212(ApiKeys.t212)
    positions = t212.get_positions()
    instruments = t212.get_instruments()

    for pos in positions:
        for instrument in instruments:
            t212_ticker = pos['ticker']
            record_ticker = instrument['ticker']
            if t212_ticker == record_ticker:
                update = {'t212_id': t212_ticker, 'quantity': pos['quantity']}
                ptf.stocks.update(instrument['shortName'], update, upsert=True)
                break
            else:
                print('Ticker id not found in local instruments list, update in progress')
                t212.update_instruments()



    # Select new tickers and create / update stock instances within the portfolio
    update = define_new_tickers(ptf, instruments)
    for el in update:
        ptf.stocks.update(el[0], el[1], upsert=True)

    # Fetch prices history for each stock of the portfolio
    ptf.stocks.fetch_history_many("2019-01-01", "2023-12-31")

    # Load portfolio data in a datafame
    stocks = ptf.stocks.positions
    ptf_data = {}
    for stock in stocks:
        df = pd.DataFrame(stock.history).transpose()
        log_return = np.log(df['Adj Close'] / df['Adj Close'].shift(1))
        ptf_data[stock.ticker] = log_return
    
    tickers = ptf_data.keys()

    stocks_log_return = pd.concat(ptf_data.values(), keys=tickers, axis=1).dropna(axis='index')

    # Determine the X number of randoms weights
    weights = generate_randoms_proba(probas_req={'tickers':tickers}, arraysize=1000000)

    # Calculation of standard deviation
    ptf_variances = np.sum(np.dot(weights, stocks_log_return.cov()) * weights, axis=1)
    ptf_sd = np.sqrt(ptf_variances) * np.sqrt(252)

    # Calculate portfolio returns
    stocks_annualized_returns = ((1+stocks_log_return.mean()) ** 252 ) -1
    ptf_returns = np.dot(weights, stocks_annualized_returns)

    # Calculate the sharpe ratio
    sharpe_ratios = ptf_returns / ptf_sd

    # Concatenate all data
    ratios = {
        'sharpe ratio': sharpe_ratios, 
        'Expected return': ptf_returns, 
        'standart Deviation': ptf_sd
    }
    ratios = pd.DataFrame(ratios)
    globaltbl = pd.merge(ratios, weights, right_index=True, left_index=True, how='left')


    # Display result
    print("\nMax sharpe ratio")
    max_sharpe_idx = globaltbl['sharpe ratio'].idxmax()
    print(globaltbl.iloc[max_sharpe_idx])
    plt.figure(figsize=(8, 6))
    plt.pie(weights.iloc[max_sharpe_idx], labels=tickers, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Max sharpe ratio')
    plt.show()

    print("\nMax return")
    max_return_idx = globaltbl['Expected return'].idxmax()
    print(globaltbl.iloc[max_return_idx])
    plt.figure(figsize=(8, 6))
    plt.pie(weights.iloc[max_return_idx], labels=tickers, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Max return')
    plt.show()

    print('\nMin volatility')
    min_stdev_idx = globaltbl['standart Deviation'].idxmin()
    print(globaltbl.iloc[min_stdev_idx])
    plt.figure(figsize=(8, 6))
    plt.pie(weights.iloc[min_stdev_idx], labels =tickers, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Min volatility')
    plt.show()

    # # Save the Portfolio
    # ptf.export("Portfolio.json")


if __name__ == "__main__":
    main()