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

import os, psutil
from typing import List

from communicate import publish
from config import ACCOUNT_START, DIRECTORY
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
        market = sector.market[:day]
        prices.reset_index(inplace=True, drop=True)
        market.reset_index(inplace=True, drop=True)
        
        assets.append(Asset(
            ticker = sector.ticker,
            relativeStrength = sector.relativeStrength[day],
            momentum = sector.momentum[day],
            prices = prices,
            lastPrice = sector.prices[day],
            market = market
        ))
    
    return assets

def mem():
    """Checker to ensure program won't exceed EC2 memory limits
    """
    memory = psutil.Process().memory_info().rss / 1024 ** 3
    if(memory > (1/3)): print('RAM use exceeded value, currently at ' + str(memory) + ' GB.')
    return

"""
This should be implemented so daily assets are only created once and the quadrants loop
    is run within that. Basically, the nested loops should be inverted. Inside loop should be outside
    and outside loop should be inside.
    
This should cut down backtesting run time significantly.

Additionally, the days of the backtest should be automatically generated so that the asset list
    in consideration can be easily changed without having to worry about the length of price history data.

I'll implement these at some point, currently not worth the effort as running this backtest "only" takes 4 to 5 days
    and there are other things I should be doing instead.
"""
if __name__ == "__main__":
    TDSession = authenticateAPI()
    setup = SetupRR(TDSession)
    rr = setup.getRR()
    mem()
    profit = {}
    for i in range(1, 16):
        saveDir = DIRECTORY + str(i) + '/'
        try:
            os.mkdir(saveDir[:-1])
        except FileExistsError:
            pass
        
        quadrants = intToBinary(i)
        for j in range(170, 2517): # 160 is the first non NaN value. (period * 2 + smoothing + change)
            assets = createAssets(rr, j)
            portfolio = [x for x in assets if quadrants[x.quadrant - 1]]
            assets = optimizeWeights(portfolio, assets)
            mem()
            book = PositionTracker(TDSession, j, assets, saveDir)
            if(j != 170 and ((j - 170) % 252) == 0): book.changeAllocation(1000)
            deltaPositions = calculatePositions(TDSession, book, assets)
            price = rebalance(TDSession, deltaPositions, assets)
            mem()
            logTrades(TDSession, book, deltaPositions, price, j, assets)
            book.saveLogs(saveDir)
        
        publish(book, saveDir)
        profit[str(quadrants)] = book.getStrategyValue() - ACCOUNT_START
        #print(book.getStrategyValue() - ACCOUNT_START)
        mem()

    print(profit)
    print(max(profit, key = profit.get))
    mem()