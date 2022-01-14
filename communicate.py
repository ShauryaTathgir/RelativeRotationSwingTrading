from datetime import datetime
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
    sms('/'.join(S3_BUCKET, img))
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

def publish(book, rr: List[RelativeRotation]) -> None:
    """Sends all summary data for portfolio

    Args:
        book (PositionTracker): Position tracker
        rr (List[RelativeRotation]): List of all relative rotation objects for circular graph
    """
    todayTrades = book.trades.loc[book.trades['Date'] == datetime.now().strftime("%Y/%m/%d")]
    sendTrades(todayTrades)

    plotRRG(rr)
    sendChart(RRG_NAME)
    
    plotPie(book.tracker)
    sendChart(PIE_NAME)
    
    plotPortfolio(book.tracker)
    sendChart(PORT_PLOT_NAME)
    return
