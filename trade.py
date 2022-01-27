# Relative Rotation Swing Trading Algorithm
# Copyright (C) 2022  Shaurya Tathgir

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Owner can be contacted via email: Shaurya [at] Tathgir [dot] com

from datetime import datetime
from sys import exit
from time import sleep
from typing import List, Tuple
from warnings import filterwarnings

from td.client import TDClient

from communicate import marketClosed, publish
from config import *
from helpers import *
from Markowitz import EfficientFrontier

filterwarnings("ignore", category=RuntimeWarning)

def authenticateAPI() -> TDClient:
    """Creates an authenticated API connection object

    Returns:
        TDClient: API object
    """
    TDSession = TDClient(client_id = CONSUMER_KEY, redirect_uri = REDIRECT_URL,
                         credentials_path = CREDENTIALS_PATH)
    TDSession.login()
    return TDSession

def checkMarket(TDSession: TDClient) -> None:
    """Checks if market is open

    Args:
        TDSession (TDClient): API object
    """
    open = TDSession.get_market_hours(markets = ['EQUITY'],
                                      date = datetime.today().strftime('%Y-%m-%d'))['equity']['EQ']['isOpen']
    if(not open):
        marketClosed()
        exit()
    return

def getAssets(TDSession: TDClient) -> Tuple[List[RelativeRotation], List[Asset], List[Asset]]:
    """Gets asset objects with data loaded

    Args:
        TDSession (TDClient): API object

    Returns:
        List[RelativeRotation]: All RelativeRotations to be used for RRG plot
        List[Asset]: Portfolio assets with data
        List[Asset]: All assets with data
    """
    setup = SetupRR(TDSession)
    rr = setup.getRR()

    if(setup.getLastPrice(VOL_INDEX) < VOL_CUTOFF):
        quadrants = LV_QUADRANTS
    else:
        quadrants = HV_QUADRANTS
    
    portfolio = [x for x in assets if quadrants[x.quadrant - 1]]
    return rr, portfolio, assets

def optimizeWeights(portfolio: List[Asset], assets: List[Asset]) -> List[Asset]:
    """Optimizes the weightings for included assets

    Args:
        portfolio (List[Asset]): Assets to be included
        assets (List[Asset]): List of all assets

    Returns:
        List[Asset]: All assets with weights assigned in parameter
    """
    optimizer = EfficientFrontier(portfolio)
    match OPT_METHOD:
        case 'Sharpe': optimizer.optimizeSharpeRatio()
        case 'GlobalMinimumVariance': optimizer.globalMinimumVarianceWeights()
    #   case 'RiskTolerance': optimizer.optimalPortfolioWeights(gamma)
    portAssets = optimizer.assets

    excluded = [x for x in assets if x not in portfolio]
    for x in excluded:
        x.weight = 0

    return portAssets + excluded

def getCurrentPositions(TDSession: TDClient, book: PositionTracker) -> dict:
    """Gets current quantities for shares within the portfolio

    Args:
        TDSession (TDClient): API object
        book (PositionTracker): Tracking object

    Returns:
        dict: Symbol: quantity
    """
    grabber = Data(TDSession)
    tickers = grabber.getTickers()['tickers']
    positions = list(book.positions.columns)
    for i in tickers + ['Date', 'Cash', 'Value', 'Benchmark']:
        if(i in positions): positions.remove(i)
    tickers += positions
    
    holdings = TDSession.get_accounts(account = TD_ACCOUNT,
                                      fields=['positions'])['securitiesAccount']['positions']
    current = {}
    for position in holdings:
        if(position['instrument']['symbol'] in tickers):
            current[position['instrument']['symbol']] = position['longQuantity']
    
    notHeld = [x for x in tickers if x not in current.keys()]
    for position in notHeld:
        current[position] = 0
    
    return current

def calculatePositions(TDSession: TDClient, book: PositionTracker, assets: List[Asset]) -> dict:
    """Finds the number of shares that need to be bought/sold to reach new target allocation

    Args:
        TDSession (TDClient): API object
        book (PositionTracker): Position tracking object
        assets (List[Asset]): All assets in consideration

    Returns:
        dict: Symbol: trade quantity
    """
    current = getCurrentPositions(TDSession, book)
    
    targetPositions = {}
    deltaPositions = {}
    
    strategyValue = book.getStrategyValue()
    for position in assets:
        targetPositions[position.ticker] = int(strategyValue * position.weight / position.lastPrice)
        deltaPositions[position.ticker] = targetPositions[position.ticker] - current[position.ticker]
    
    for oldTicker, currentPos in current.items():
        if(oldTicker not in deltaPositions.keys()):
            deltaPositions[oldTicker] = -1 * currentPos

    return deltaPositions

def placeTrade(TDSession: TDClient, symbol: str, quantity: int) -> float:
    """Places a trade

    Args:
        TDSession (TDClient): API object
        symbol (str): Ticker for asset
        quantity (int): Number of shares. Negative if sale. Must be non-zero.

    Returns:
        float: Execution price
    """
    if(quantity < 0):
        instruction = "sell"
        quantity *= -1
    else:
        instruction = "buy"
    
    quantity = int(quantity)
    
    order = {
                "orderType": "MARKET",
                "session": "NORMAL",
                "duration": "DAY",
                "orderStrategyType": "SINGLE",
                "orderLegCollection": [
                    {
                        "instruction": instruction,
                        "quantity": quantity,
                        "instrument": {
                            "symbol": symbol,
                            "assetType": "EQUITY"
                        }
                    }
                ]
            }
    resp = TDSession.place_order(account = TD_ACCOUNT, order = order)
    
    while TDSession.get_orders(account=TD_ACCOUNT,
                               order_id = resp['order_id'])['remainingQuantity'] != 0:
        sleep(1)
    
    execPrice = TDSession.get_orders(account=TD_ACCOUNT,
                                     order_id = resp['order_id'])
    execPrice = execPrice["orderActivityCollection"][0]["executionLegs"][0]["price"]
    
    return execPrice

def rebalance(TDSession: TDClient, numShares: dict) -> dict:
    """Rebalances the portfolio

    Args:
        TDSession (TDClient): API object
        numShares (dict): Size of trades that need to be made

    Returns:
        dict: Symbol: execution price
    """
    execPrice = {}
    for symbol, quantity in numShares.items():
        if(int(quantity) == 0):
            continue
        price = placeTrade(TDSession, symbol, quantity)
        execPrice[symbol] = price
    
    return execPrice

def logTrades(TDSession: TDClient, book: PositionTracker, quantity: dict, price: dict) -> None:
    """Logs the trades in position tracker

    Args:
        TDSession (TDClient): API object
        book (PositionTracker): Position tracker
        quantity (dict): Size of trades
        price (dict): Execution price of trades
    """
    today = datetime.now().strftime("%Y/%m/%d")
    deltaCash = 0
    
    for symbol, shares in quantity.items():
        if(shares == 0):
            continue
        value = shares * price[symbol]
        deltaCash -= value
        data = {'Date': today, 'Symbol': symbol, 'Quantity': shares, "Value": value}
        book.logTrade(data)
    
    current = getCurrentPositions(TDSession, book)
    cash = book.getPreviousCashBalance() + deltaCash
    
    grabber = Data(TDSession)
    
    positionValues = {}
    for symbol, quantity in current.items():
        positionValues[symbol] = quantity * grabber.getLastPrice(symbol)
    
    strategyValue = cash + sum(positionValues.values())
    
    book.addColumns()
    
    mult = book.getMarketMultiplier()
    benchmarkValue = grabber.getLastPrice(MARKET_INDEX) * mult
    
    value = {'Date': today, 'Cash': cash, 'Value': strategyValue, 'Benchmark': benchmarkValue}
    positions = {'Date': today, 'Cash': cash, 'Value': strategyValue, 'Benchmark': mult}
    for column in book.tracker.columns:
        if(column not in list(positionValues.keys()) + ['Date', 'Cash', 'Value', 'Benchmark']):
            value[column] = 0
            positions[column] = 0
            continue
        
        if(column in ['Date', 'Cash', 'Value', 'Benchmark']):
            continue
        
        value[column] = positionValues[column]
        positions[column] = current[column]
    
    book.addDay(value, positions)
    return

if __name__ == "__main__":
    TDSession = authenticateAPI()
    checkMarket(TDSession)
    rr, portfolio, assets = getAssets(TDSession)
    assets = optimizeWeights(portfolio, assets)
    book = PositionTracker(TDSession)
    deltaPositions = calculatePositions(TDSession, book, assets)
    price = rebalance(TDSession, deltaPositions)
    logTrades(TDSession, book, deltaPositions, price)
    publish(book, rr)
    book.saveLogs()