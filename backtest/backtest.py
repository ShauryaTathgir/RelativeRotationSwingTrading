import os, psutil
from typing import List

from communicate import publish
from config import ACCOUNT_START
from helpers import *
from trade import *

class CurrentPositions:
    def __init__(self, book: PositionTracker) -> None:
        """Unnecessarily inefficient way to get backtest current share quantities

        Args:
            book (PositionTracker): Trades tested
        """
        self.current = {}
        for _, row in book.trades.iterrows():
            try:
                self.current[row['Symbol']] += row['Quantity']
            except KeyError:
                self.current[row['Symbol']] = row['Quantity']
        return
    
    def getCurrent(self) -> dict:
        """Get holdings

        Returns:
            dict: Holdings
        """
        return self.current
        

def intToBinary(i: int) -> List[int]:
    """I have no clue why I implemented this in this weird way.
    It works though. Recursive backtracking or list comprehension would've been
        more pythonic and faster, but this is more fun.
    
    Converts integer into a list of ints of the binary version of the integer.
    To be used to generate all possible quadrants to be included/excluded

    Args:
        i (int): number

    Returns:
        List[int]: quadrants value
    """
    b = list(map(int, list(format(i, "b"))))
    b = [0] * (4 - len(b)) + b
    return b

def createAssets(rr: List[RelativeRotation], day: int) -> List[Asset]:
    """Creates assets with data only up to the current day of the backtest

    Args:
        rr (List[RelativeRotation]): List of relative rotation objects per sector
        day (int): Current day of backtest

    Returns:
        List[Asset]: Assets as of backtest day
    """
    assets = []
    for sector in rr:
        prices = sector.prices[:day]
        prices.reset_index(inplace=True, drop=True)
        
        assets.append(Asset(
            ticker = sector.ticker,
            relativeStrength = sector.relativeStrength[day],
            momentum = sector.momentum[day],
            prices = prices,
            lastPrice = sector.prices[day],
            avgRet = None,
            quadrant = None,
            weight = None
        ))
    
    return assets

def mem():
    # memory = psutil.Process().memory_info().rss / 1024 ** 3
    # if(memory > (1/10)): print(memory)
    return

TDSession = authenticateAPI()
setup = SetupRR(TDSession)
rr = setup.getRR()
mem()
profit = {}
for i in range(1, 16):
    saveDir = 'C:/Users/shaur/algotrading/RRG/backtest/files/' + str(i) + '/'
    try:
        os.mkdir(saveDir[:-1])
    except FileExistsError:
        pass
    
    quadrants = intToBinary(i)
    for j in range(170, 2518): # 160 is the first non NaN value. (period * 2 + smoothing + change)
        assets = createAssets(rr, j)
        portfolio = [x for x in assets if quadrants[x.quadrant - 1]]
        assets = optimizeWeights(portfolio, assets)
        mem()
        book = PositionTracker(TDSession, j, saveDir)
        deltaPositions = calculatePositions(TDSession, book, assets)
        price = rebalance(TDSession, deltaPositions, assets)
        mem()
        logTrades(TDSession, book, deltaPositions, price, j, assets)
        book.saveLogs(saveDir)
    
    publish(book, saveDir)
    profit[i] = book.getStrategyValue() - ACCOUNT_START
    #print(book.getStrategyValue() - ACCOUNT_START)
    mem()

#print(profit)
print(intToBinary(max(profit, key = profit.get)))
mem()