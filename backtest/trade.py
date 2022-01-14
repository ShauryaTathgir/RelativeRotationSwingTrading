from collections import Counter as check
from sys import exit
from time import sleep
from types import NoneType
from typing import List, Tuple
from warnings import filterwarnings

import pandas as pd
from td.client import TDClient

from aws import s3Download, s3Upload
from communicate import marketClosed
from config import *
from Markowitz import EfficientFrontier
from helpers import *

filterwarnings("ignore", category=RuntimeWarning)


class PositionTracker:
    def __init__(self, TDSession: TDClient, day: int, location: str = '') -> None:
        """Tracks trades and allocations by asset

        Args:
            TDSession (TDClient): Authenticated API connection object
            location (str): Directory to save files
        """
        existing = self._getCSVs(location)
        
        if not existing: self._generateDataFrames(day)
        
        self.TDSession = TDSession
        return

    def _generateDataFrames(self, day: int) -> None:
        """Creates tracking dataframes if there have been no trades ever
        """
        self.tracker = pd.DataFrame(columns=['Date', 'Cash', 'Value'])
        yesterday = day - 1
        self.addDay({'Date': yesterday, 'Cash': ACCOUNT_START, 'Value': ACCOUNT_START})
        self.trades = pd.DataFrame(columns = ['Date', 'Symbol', 'Quantity', 'Value'])
        return
    
    def _getCSVs(self, location: str) -> bool:
        """Downloads tracker and trades csv from s3

        Args:
            location(str): folder to locate files
        
        Returns:
            bool: If files exist in s3
        """
        self.tracker = s3Download(location + TRACKER)
        self.trades = s3Download(location + TRADES)
        
        return type(None) not in [type(self.tracker), type(self.trades)]

    def getStrategyValue(self) -> float:
        """Gets current value of the portfolio

        Returns:
            float: Value in dollars
        """
        return self.tracker.iloc[self.tracker.shape[0] - 1, self.tracker.shape[1] - 1]
    
    def getPreviousCashBalance(self) -> float:
        """Gets cash balance from last period

        Returns:
            float: Cash in dollars
        """
        return self.tracker.iloc[self.tracker.shape[0] - 1, 1]
    
    def addSymbol(self, symbol: str) -> None:
        """Adds an asset to the tracker;. Assumed no allocation in past

        Args:
            symbol (str): Ticker for asset
        """
        self.tracker.insert(2, symbol, [0] * self.tracker.shape[0])
        return
    
    def addColumns(self) -> None:
        """Adds assets in already in storage to allocation tracker
        """
        grabber = Data(self.TDSession)
        symbols = grabber.getTickers()['tickers']
        
        newSymbols = [x for x in symbols if x not in self.tracker.columns]
        
        for sym in newSymbols:
            self.addSymbol(sym)
        
        return
    
    def addDay(self, data: dict) -> None:
        """Adds new periods allocations to tracker

        Args:
            data (dict): Allocations

        Raises:
            ValueError: If given incorrect keys in data dict
        """
        if(check(data.keys()) != check(self.tracker.columns)):
            raise ValueError("Incorrect data keys")
        
        self.tracker = self.tracker.append(data, ignore_index=True)
        return
    
    def logTrade(self, data: dict) -> None:
        """Logs a trade in trades

        Args:
            data (dict): Trade data

        Raises:
            ValueError: If given incorrect data
        """
        if(check(data.keys()) != check(self.trades.columns)):
            raise ValueError("Incorrect data keys")
        
        self.trades = self.trades.append(data, ignore_index=True)
        return
    
    def saveLogs(self, location: str = '') -> None:
        """Uploads final files to s3 for storage
        
        Args:
            location (str): Pre-path to file
        """
        self.tracker.to_csv(location + TRACKER, index=False)
        self.trades.to_csv(location + TRADES, index=False)
        s3Upload(location + TRACKER)
        s3Upload(location + TRADES)
        return


def authenticateAPI() -> TDClient:
    """Creates an authenticated API connection object

    Returns:
        TDClient: API object
    """
    TDSession = TDClient(client_id = CONSUMER_KEY, redirect_uri = REDIRECT_URL, credentials_path = CREDENTIALS_PATH)
    TDSession.login()
    return TDSession

def checkMarket(TDSession: TDClient) -> None:
    """Checks if market is open

    Args:
        TDSession (TDClient): API object
    """
    # if(not TDSession.get_market_hours(markets = ['EQUITY'], date = datetime.today().strftime('%Y-%m-%d'))['equity']['EQ']['isOpen']):
    #     marketClosed()
    #     exit()
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

    assets = [relRot.getAsset() for relRot in rr]
    portfolio = [x for x in assets if QUADRANTS[x.quadrant - 1]]
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
    optimizer.globalMinimumVarianceWeights()
    portAssets = optimizer.assets

    excluded = [x for x in assets if x not in portfolio]
    for x in excluded:
        x.weight = 0

    return portAssets + excluded

def getCurrentPositions(TDSession: TDClient, book: PositionTracker) -> dict:
    """Gets current quantities for shares within the portfolio

    Args:
        TDSession (TDClient): API object

    Returns:
        dict: Symbol: quantity
    """
    grabber = Data(TDSession)
    tickers = grabber.getTickers()['tickers']
    
    current = {}
    for _, row in book.trades.iterrows():
        try:
            current[row['Symbol']] += row['Quantity']
        except KeyError:
            current[row['Symbol']] = row['Quantity']
    
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

    return deltaPositions

def placeTrade(TDSession: TDClient, symbol: str, quantity: int, assets: List[Asset]) -> float:
    """Places a trade

    Args:
        TDSession (TDClient): API object
        symbol (str): Ticker for asset
        quantity (int): Number of shares. Negative if sale

    Returns:
        float: Execution price
    """
    # if(quantity < 0):
    #     instruction = "sell"
    #     quantity *= -1
    # else:
    #     instruction = "buy"
    
    # order = {
    #             "orderType": "MARKET",
    #             "session": "NORMAL",
    #             "duration": "DAY",
    #             "orderStrategyType": "SINGLE",
    #             "orderLegCollection": [
    #                 {
    #                     "instruction": instruction,
    #                     "quantity": quantity,
    #                     "instrument": {
    #                         "symbol": symbol,
    #                         "assetType": "EQUITY"
    #                     }
    #                 }
    #             ]
    #         }
    # resp = TDSession.place_order(account = TD_ACCOUNT, order = order)
    
    # while TDSession.get_orders(account=TD_ACCOUNT, order_id = resp['order_id'])['remainingQuantity'] != 0:
    #     sleep(1)
    
    # execPrice = TDSession.get_orders(account=TD_ACCOUNT, order_id = resp['order_id'])["orderActivityCollection"][0]["executionLegs"][0]["price"]
    
    for asset in assets:
        if(asset.ticker == symbol):
            return asset.lastPrice
    
    raise ValueError('asset price not found, trade.placeTrade')

def rebalance(TDSession: TDClient, numShares: dict, assets: List[Asset]) -> dict:
    """Rebalances the portfolio

    Args:
        TDSession (TDClient): API object
        numShares (dict): Size of trades that need to be made

    Returns:
        dict: Symbol: execution price
    """
    execPrice = {}
    for symbol, quantity in numShares.items():
        if(quantity == 0):
            continue
        price = placeTrade(TDSession, symbol, quantity, assets)
        execPrice[symbol] = price
    
    return execPrice

def logTrades(TDSession: TDClient, book: PositionTracker, quantity: dict, price: dict, day: int, assets: List[Asset]) -> None:
    """Logs the trades in position tracker

    Args:
        TDSession (TDClient): API object
        book (PositionTracker): Position tracker
        quantity (dict): Size of trades
        price (dict): Execution price of trades
    """
    today = day
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
    
    positionValues = {}
    for symbol, quantity in current.items():
        for i in assets:
            if(i.ticker == symbol):
                p = i.lastPrice
                continue
        positionValues[symbol] = quantity * p
    
    strategyValue = cash + sum(positionValues.values())
    
    book.addColumns()
    
    data = {'Date': today, 'Cash': cash, 'Value': strategyValue}
    for column in book.tracker.columns:
        if(column not in list(positionValues.keys()) + ['Date', 'Cash', 'Value']):
            data[column] = 0
            continue
        
        if(column in ['Date', 'Cash', 'Value']):
            continue
        
        data[column] = positionValues[column]
    
    book.addDay(data)
    return
