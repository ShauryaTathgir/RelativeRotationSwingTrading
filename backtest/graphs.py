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
    fig.patch.set_facecolor('white')
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

def plotPie(tracker: pd.DataFrame, location: str) -> None:
    """Creates a pie chart to show portfolio weights

    Args:
        tracker (pd.DataFrame): Current holdings values
    """
    labels = tracker.columns[1:-2]
    values = tracker.iloc[tracker.shape[0] - 1]
    sizes = []
    for i in values.index:
        if(i in ['Date', 'Value', 'Benchmark']): continue
        if(values[i] < 0):
            sizes.append(0)
            continue
        sizes.append(values[i] / values['Value'])
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.axis('equal')
    plt.savefig(location + PIE_NAME)
    return

def plotPortfolio(tracker: pd.DataFrame, location: str) -> None:
    """Plots portfolio holdings over time

    Args:
        tracker (pd.DataFrame): Portfolio holdings over time
    """
    fig = plt.figure(dpi = 600)
    fig.patch.set_facecolor('white')
    plot = tracker.plot(x = 'Date', rot = 90, ax=plt.gca())
    plt.legend(bbox_to_anchor=(1, 1))
    fig = plot.get_figure()
    fig.savefig(location + PORT_PLOT_NAME, bbox_inches='tight')
    return