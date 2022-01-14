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

# from datetime import datetime
from typing import List

import pandas as pd

from aws import *
from graphs import *
from helpers import *

def marketClosed() -> None:
    """Indicates market closure
    """
    sms('Market closed; no orders executed.')
    return

def sendTrades(trades: pd.DataFrame) -> None:
    """Send trade execution info

    Args:
        trades (pd.DataFrame): Trades executed with symbol, quantity, and value
    """
    for _, row in trades.iterrows():
        if(row['Quantity'] > 0):
            action = 'Bought'
        else:
            action = 'Sold'
        
        quantity = abs(row['Quantity'])
        price = row['Value'] / quantity
        message = [str(action), str(quantity), 'shares of', row['Symbol'], 'at $']
        message = ' '.join(message) + str(round(price, 2))
        sms(message)

def sendChart(img: str) -> None:
    """Sends image link to object uploaded to s3

    Args:
        img (str): File name
    """
    s3Upload(img)
    return

def summary(alpha: float, beta: float, sharpe: float, plTD: float, percentReturn: float) -> None:
    """Sends key statistics

    Args:
        alpha (float): Annualized alpha to benchmark
        beta (float): Covariance with benchmark
        sharpe (float): Sharpe ratio
        plTD (float): Total profit loss
        percentReturn (float): Percent return to date
    """
    message = '''Daily update:
    P/L of $%s
    %s%% Return
    \u03B1 = %s
    \u03B2 = %s
    Sharpe Ratio of %s''' % (str(plTD), str(percentReturn), str(alpha), str(beta), str(sharpe))
    sms(message)
    return

def publish(book, location: str = '') -> None:
    """Sends all summary data for portfolio

    Args:
        book (PositionTracker): Position tracker
    """
    # todayTrades = book.trades.loc[book.trades['Date'] == datetime.now().strftime("%Y/%m/%d")]
    # sendTrades(todayTrades)
    
    plotPie(book.tracker, location)
    sendChart(location + PIE_NAME)
    
    plotPortfolio(book.tracker, location)
    sendChart(location + PORT_PLOT_NAME)
    return
