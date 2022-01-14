from typing import List

import matplotlib.pyplot as plt
import pandas as pd

from config import PIE_NAME, PORT_PLOT_NAME, RRG_NAME
from helpers import RelativeRotation


def plotRRG(rr: List[RelativeRotation], period: int = 15, padding: int = 0.5) -> None:
    """Creates a relative rotation graph for all given assets

    Args:
        rr (List[RelativeRotation]): List of Relative Rotation objects
        period (int, optional): How many periods to plot. Defaults to 15.
        padding (int, optional): Area around curves on graph. Defaults to 0.5.
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    
    dist = -1
    for asset in rr:
        asset.relativeStrength.reset_index(inplace=True, drop=True)
        asset.momentum.reset_index(inplace=True, drop=True)
        x = asset.relativeStrength[-period:]
        y = asset.momentum[-period:]
        ax.plot(x, y, label = asset.ticker)
        ax.plot(x[x.index[-1]], y[y.index[-1]], 'o')
        data = x.append(y)
        low = min(data)
        high = max(data)
        dist = int(max(abs(low - 100), abs(high - 100)) + padding) + 1
    
    ax.axhline(100, color = 'k')
    ax.axvline(100, color = 'k')
    ax.legend()
    
    ax.fill_between([100, 100+dist], [100]*2, [100+dist]*2,
                    facecolor = 'green',
                    alpha = 0.2)
    ax.fill_between([100, 100+dist], [100]*2, [100-dist]*2,
                    facecolor = 'darkorange',
                    alpha = 0.2)
    ax.fill_between([100-dist, 100], [100-dist]*2, [100]*2,
                    facecolor = 'red',
                    alpha = 0.2)
    ax.fill_between([100-dist, 100], [100]*2, [100+dist]*2,
                    facecolor = 'cornflowerblue',
                    alpha = 0.2)
    
    plt.xlabel('JdK RS Ratio')
    plt.ylabel("JdK RS Momentum")
    plt.title('Sector Relative Rotation')
    plt.xlim(100 - dist, 100 + dist)
    plt.ylim(100 - dist, 100 + dist)
    plt.grid()
    plt.savefig(RRG_NAME)
    return

def plotPie(tracker: pd.DataFrame) -> None:
    """Creates a pie chart to show portfolio weights

    Args:
        tracker (pd.DataFrame): Current holdings values
    """
    labels = tracker.columns[1:-1]
    values = tracker.iloc[tracker.shape[0] - 1]
    sizes = []
    for i in values.index:
        if(i in ['Date', 'Value']): continue
        sizes.append(values[i] / values['Value'])
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.axis('equal')
    plt.savefig(PIE_NAME)
    return

def plotPortfolio(tracker: pd.DataFrame) -> None:
    """Plots portfolio holdings over time

    Args:
        tracker (pd.DataFrame): Portfolio holdings over time
    """
    plot = tracker.plot(x = 'Date', rot = 90)
    fig = plot.get_figure()
    fig.savefig(PORT_PLOT_NAME)
    return