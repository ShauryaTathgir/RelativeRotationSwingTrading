# build backtesting engine
# fix returns calculation to annualize and be faster

from dataclasses import dataclass

import pandas as pd
from multipledispatch import dispatch
from numpy import mean, nan, std
from td.client import TDClient

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
    avgRet: float
    quadrant: int
    weight: float
    
    def __post_init__(self) -> None:
        """Sets calculated values
        """
        self._setQuadrant()
        self._setRet()
        return
    
    def _setRet(self) -> None:
        """Calculates average annual return for the asset
        """
        years = []
        for i in range(0, len(self.prices), 252):
            try:
                years.append(self.prices[i:i+252].tolist()) # make this faster
            except KeyError:
                years.append(self.prices[i:len(self.prices)].tolist())
        
        rets = []
        for y in years:
            rets.append(y[-1]/y[0] - 1)

        self.avgRet = mean(rets)
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
                      lastPrice = self.prices[self.prices.index[-1]],
                      avgRet = None,
                      quadrant = None,
                      weight = None)
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