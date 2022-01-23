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

from collections import Counter as check
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import quandl
from multipledispatch import dispatch
from numpy import mean, nan, std
from td.client import TDClient

from aws import s3Download, s3Upload
from config import *


@dataclass
class Asset:
    """Asset data store class
    """
    ticker: str
    relativeStrength: float
    momentum: float
    prices: pd.Series
    lastPrice: float
    avgRet: float = None
    quadrant: int = None
    weight: float = None
    
    def __post_init__(self) -> None:
        """Sets calculated values
        """
        self._setQuadrant()
        self._setRet()
        return
    
    def _setRet(self) -> None:
        """Calculates average annual return for the asset
        """
        self.avgRet = (self.prices[len(self.prices) - 1] / self.prices[1]) ** (365 / len(self.prices)) - 1
        return
    
    def _setQuadrant(self) -> None:
        """Determines the quadrant of the RRG the asset is currently in
        """
        if(self.relativeStrength >= 100):
            if(self.momentum >= 100):
                self.quadrant = 1
            else:
                self.quadrant = 2
        elif(self.momentum < 100):
            self.quadrant = 3
        else:
            self.quadrant = 4
        return

class RelativeRotation:
    """Relative rotation asset class
    """
    def __init__(self, ticker: str, sector: pd.Series, benchmark: pd.Series, period: int = 50, smoothing: int = 50, change: int = 10) -> None:
        """Stores relevant data in class

        Args:
            ticker (str): Symbol for sector
            sector (pd.Series): Sector price data
            benchmark (pd.Series): Market benchmark price data
            period (int, optional): normalization period. Defaults to 50.
            smoothing (int, optional): SMA period to apply to final values. Defaults to 50.
            change (int, optional): percent change days difference. Defaults to 10.
        """
        self.ticker = ticker
        self.prices = sector
        self.market = benchmark
        self.period = period
        self.smoothing = smoothing
        self.change = change
        self.relativeStrength = self.jdkRSRatio(self.prices, self.market)
        self.momentum = self.jdkRSMomentum(self.relativeStrength)

    def getAsset(self) -> Asset:
        """Creates an asset allocation object store today's data

        Returns:
            Asset: Dataclass object with relevant info
        """
        asset = Asset(ticker = self.ticker,
                      relativeStrength = self.relativeStrength[self.relativeStrength.index[-1]],
                      momentum = self.momentum[self.momentum.index[-1]],
                      prices = self.prices,
                      lastPrice = self.prices[self.prices.index[-1]])
        return asset

    def normalize(self, data: pd.Series) -> pd.Series:
        """Normalizes data using z-score method

        Args:
            data (pd.Series): Data to be normalized.

        Returns:
            pd.Series: Normalized data
        """
        normalized = [nan] * self.period
        for t in range(self.period, len(data)):
            lookBackPeriod = data[t-self.period:t]
            val = 100 + ((data[t] - mean(lookBackPeriod))/(std(lookBackPeriod)))
            normalized.append(val)
        
        return pd.Series(normalized).rolling(self.smoothing).mean()

    def jdkRSRatio(self, asset: pd.Series, market: pd.Series) -> pd.Series:
        """Calculates the normalized JdK RS-Ratio for an asset compared to given market

        Args:
            asset (pd.Series): Asset to find relative strength
            market (pd.Series): Broad market index to compare against

        Returns:
            pd.Series: Normalized JdK RS data
        """
        return self.normalize(100 * (asset / asset[1]) / (market / market[1]))

    @dispatch(pd.Series)
    def jdkRSMomentum(self, rsRatio: pd.Series) -> pd.Series:
        """Calculates normalized JdK RS Momentum for the given RS Ratio

        Args:
            rsRatio (int): Relative Strength data

        Returns:
            pd.Series: JdK Momentum
        """
        chg = rsRatio.pct_change(periods=self.change)
        chg = chg[self.period:]
        chg.reset_index(inplace=True, drop=True)
        momentum = self.normalize(chg)
        blanks = pd.Series([nan] * self.period)
        return blanks.append(momentum, ignore_index= True)

    @dispatch(pd.Series, pd.Series)
    def jdkRSMomentum(self, asset: pd.Series, market: pd.Series) -> pd.Series:
        """Calculates the normalized JdK RS Momentum for the given asset
                in comparison to a given market index

        Args:
            asset (pd.Series): Asset to compare to market
            market (pd.Series): Market index

        Returns:
            pd.Series: JdK RS Momentum
        """
        rs = self.jdkRSRatio(asset, market)
        return self.jdkRSMomentum(rs)

class Data:
    """Base class to grab data without requiring initialization
    """
    def __init__(self, TDSession: TDClient) -> None:
        """Allows ticker grab without building RelativeRotation.

        Args:
            TDSession (TDClient): Authenticated TD API object.
        """
        self.TDSession = TDSession
        return
    
    def getTickers(self) -> dict:
        """Pulls investable sectors from TD watchlist

        Returns:
            dict: Assets are under 'tickers' key
                    and market is under 'comp' key
        """
        watchlist = self.TDSession.get_watchlist(account=TD_ACCOUNT, watchlist_id=WATCHLIST_ID)['watchlistItems']
        tickers = []
        for sector in watchlist:
            tickers.append(sector['instrument']['symbol'])
        return {'tickers': tickers, 'comp': MARKET_INDEX}
    
    def getLastPrice(self, symbol: str) -> float:
        """Gets most recent traded price for asset

        Args:
            symbol (str): Ticker

        Returns:
            float: Price in dollars
        """
        return self.TDSession.get_quotes([symbol])[symbol]['lastPrice']
    
    def getPrices(self, symbol: str) -> pd.Series:
        """Gets daily price data for last 10 years

        Args:
            symbol (str): Symbol for asset

        Returns:
            pd.Series: Daily close price data
        """
        ohlc = self.TDSession.get_price_history(symbol = symbol, period_type='year', period=10, frequency_type='daily', frequency=1, extended_hours=False)
        close = []
        for day in ohlc['candles']:
            close.append(day['close'])
        
        close.append(self.getLastPrice(symbol))
        
        return pd.Series(close)

class SetupRR(Data):
    """Pulls market data and creates RelativeRotation objects
    """
    def __init__(self, TDSession: TDClient, **kwargs) -> None:
        """Sets up relative rotation objects. Limits price data to shortest history
                or 10 years, whichever is smaller.

        Args:
            TDSession (TDClient): Authenticated API connection object
            **kwargs: Args to be passed to relative rotation contructor
        """
        self.TDSession = TDSession
        tickers = self.getTickers()
        self.sectors = tickers['tickers']
        self.market = tickers['comp']
        self.rr = []
        
        prices = []
        for sector in self.sectors:
            prices.append(self.getPrices(sector))
        
        prices.append(self.getPrices(self.market))
        shortestPriceHistory = min(list(map(len, prices)))
        
        shortPrices = []
        for stock in prices:
            ind = len(stock) - shortestPriceHistory
            stock = stock[ind:]
            stock.reset_index(inplace=True, drop=True)
            shortPrices.append(stock)
        
        for i in range(len(self.sectors)):
            self.rr.append(RelativeRotation(self.sectors[i], shortPrices[i], shortPrices[-1], **kwargs))
        return
    
    def getRR(self) -> list:
        """Stores all RelativeRotation objects

        Returns:
            list: List of RelativeRotation objects
        """
        return self.rr

class PositionTracker:
    def __init__(self, TDSession: TDClient) -> None:
        """Tracks trades and allocations by asset

        Args:
            TDSession (TDClient): Authenticated API connection object
        """
        existing = self._getCSVs()
        
        if not existing: self._generateDataFrames()
        
        self.TDSession = TDSession
        self.grabber = Data(self.TDSession)
        return

    def _generateDataFrames(self) -> None:
        """Creates tracking dataframes if there have been no trades ever
        """
        mult = ACCOUNT_START / self.grabber.getLastPrice(MARKET_INDEX)
        
        self.tracker = pd.DataFrame(columns=['Date', 'Cash', 'Value', 'Benchmark'])
        self.positions = pd.DataFrame(columns=['Date', 'Cash', 'Value', 'Benchmark'])
        
        yesterday = datetime.now() - timedelta(days=1)
        valData = {'Date': yesterday.strftime("%Y/%m/%d"), 'Cash': ACCOUNT_START, 'Value': ACCOUNT_START, 'Benchmark': ACCOUNT_START}
        posData = {'Date': yesterday.strftime("%Y/%m/%d"), 'Cash': ACCOUNT_START, 'Value': ACCOUNT_START, 'Benchmark': mult}
        self.addDay(valData, posData)
        
        self.trades = pd.DataFrame(columns = ['Date', 'Symbol', 'Quantity', 'Value'])
        return
    
    def _getCSVs(self) -> bool:
        """Downloads tracker and trades csv from s3

        Returns:
            bool: If all files exist in s3
        """
        self.tracker = s3Download(TRACKER)
        self.trades = s3Download(TRADES)
        self.positions = s3Download(POSITIONS)
        
        return type(None) not in [type(self.tracker), type(self.trades), type(self.positions)]

    def getStrategyValue(self) -> float:
        """Gets current value of the portfolio

        Returns:
            float: Value in dollars
        """
        strategy = 0
        for index, value in self.positions.iloc[self.positions.shape[0]-1].iteritems():
            if(index in ['Date', 'Value', 'Benchmark']): continue
            if(index == 'Cash'):
                strategy += value
                continue
            strategy += value * self.grabber.getLastPrice(index)
            
        return strategy
    
    def getPreviousCashBalance(self) -> float:
        """Gets cash balance from last period

        Returns:
            float: Cash in dollars
        """
        return self.tracker.iloc[self.tracker.shape[0] - 1, 1]
    
    def getMarketMultiplier(self) -> float:
        """Gets the multiplier to convert market index into comparable
            comparison based on portfolio value

        Returns:
            float: Multiplier
        """
        return self.tracker.iloc[self.tracker.shape[0] - 1, self.tracker.shape[1] - 1]
    
    def addSymbol(self, symbol: str) -> None:
        """Adds an asset to the tracker. Assumed no allocation in past

        Args:
            symbol (str): Ticker for asset
        """
        self.tracker.insert(2, symbol, [0] * self.tracker.shape[0])
        self.positions.insert(2, symbol, [0] * self.positions.shape[0])
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
    
    def addDay(self, values: dict, positions: dict) -> None:
        """Adds new periods allocations to tracker

        Args:
            values (dict): Allocations in dollars
            positions (dict): Allocations in shares

        Raises:
            ValueError: If given incorrect keys in data dict
        """
        if(check(values.keys()) != check(self.tracker.columns)):
            removedAssets = [x for x in self.tracker.columns if x not in values.keys()]
            for asset in removedAssets:
                values[asset] = 0
                positions[asset] = 0
            if(check(values.keys()) != check(self.tracker.columns)):
                raise ValueError("Incorrect data keys")
        
        self.tracker = self.tracker.append(values, ignore_index=True)
        self.positions = self.positions.append(positions, ignore_index=True)
        return
    
    def changeAllocation(self, amount: float) -> None:
        """Changes the amount of money that the strategy can use. Note that if allocation is decreased
            the algorithm would have to rebalance to free up the cash.

        Args:
            amount (float): Dollar amount to change allocation by. Positive to add, negative to remove
        """
        cash = self.getPreviousCashBalance() + amount
        currentStratValue = self.getStrategyValue()
        value = currentStratValue + amount
        mult = self.getMarketMultiplier() * (value / currentStratValue)
        
        self.tracker.iloc[self.tracker.shape[0] - 1, 1] = cash
        self.positions.iloc[self.positions.shape[0] - 1, 1] = cash
        
        self.tracker.iloc[self.tracker.shape[0] - 1, self.tracker.shape[1] - 2] = value
        self.positions.iloc[self.positions.shape[0] - 1, self.positions.shape[1] - 2] = value
        
        self.positions.iloc[self.positions.shape[0] - 1, self.positions.shape[1] - 1] = mult
        return
    
    def logTrade(self, data: dict) -> None:
        """Logs a trade in trades

        Args:
            data (dict): Trade data

        Raises:
            ValueError: If given incorrect data keys
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
        self.positions.to_csv(location + POSITIONS, index=False)
        s3Upload(location + TRACKER)
        s3Upload(location + TRADES)
        s3Upload(location + POSITIONS)
        return

def getRiskFreeRate() -> float:
    """Gets risk free rate from zero coupon bond yield curve

    Returns:
        float: Risk free rate
    """
    rates = quandl.get("FED/SVENY", authtoken=NQ_API_KEY)
    return rates.iloc[rates.shape[0] - 1]["SVENY01"] / 100
