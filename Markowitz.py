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

from typing import List, Tuple

import numpy as np
import pandas as pd

from config import NUM_PORTFOLIOS
from helpers import Asset, getRiskFreeRate


class EfficientFrontier:
    def __init__(self, assets: List[Asset]) -> None:
        """Determines efficient portfolio weights

        Args:
            assets (List[Asset]): list of assets with data
        """
        self.assets = assets
        self.n = len(self.assets)
        
        if(self.n > 1):
            data = []
            for asset in self.assets:
                prices = asset.prices.pct_change()[1:].to_list()
                data.append(prices)
            
            data = np.array(data)
            self.covMat = np.cov(data)
            self.covMat = self.covMat * 252
            self.invSigma = np.linalg.inv(self.covMat)
            self.one = np.ones(len(self.assets))
        return
    
    def portfolioMean(self, weights: np.ndarray = None) -> float:
        """Mean of portfolio given weights
        
        Args:
            weights (np.ndarray): Weights of porfolio.
                                    defaults to current weights

        Returns:
            float: Portfolio mean
        """
        mu_p = 0
        
        if(weights is None):
            for asset in self.assets:
                mu_p += asset.weight * asset.avgRet
        else:
            for i in range(len(self.assets)):
                mu_p += self.assets[i].avgRet * weights[i]
        
        return mu_p
    
    def portfolioVariance(self, weights: np.ndarray = None) -> np.ndarray:
        """Variance of portfolio
        
        Args:
            weights (np.ndarray, Optional): Asset weights. Defaults to assigned values

        Returns:
            np.ndarray: Portfolio variance
        """
        if(weights is None):
            omega = []
            for asset in self.assets:
                omega.append(asset.weight)
            omega = np.array(omega)
        else:
            omega = weights
        
        return np.matmul(np.matmul(omega.T, self.covMat), omega)
    
    def _optimizedDenominator(self) -> np.ndarray:
        """Value of $1^T \\Sigma^{-1} 1

        Returns:
            np.ndarray: Value
        """
        return (np.matmul(np.matmul(self.one.T, self.invSigma), self.one))
    
    def _assignWeights(self, omega: np.ndarray) -> None:
        """Stores weights in asset object

        Args:
            omega (np.ndarray): Weights
        """
        for i in range(len(omega)):
            self.assets[i].weight = omega[i]
        return
    
    def _checkInsuffAssets(self) -> Tuple[bool, np.ndarray]:
        """Deals with edge cases where 0 or 1 asset were selected for portfolio

        Returns:
            bool: If already optimized here
            np.ndarray: Asset weights, none if self.n > 1
        """
        if(self.n == 0): return True, np.array([])
        if(self.n == 1):
            self.assets[0].weight = 1
            return True, np.array([1])
        return False, None
            
    def getSharpeRatio(self, weights: np.ndarray = None) -> float:
        """Calculates the Sharpe ratio

        Args:
            weights (np.ndarray, optional): Asset weights. Defaults to current assigned values.

        Returns:
            float: Sharpe ratio
        """
        return (self.portfolioMean(weights) - getRiskFreeRate()) / self.portfolioVariance(weights)
    
    def globalMinimumVarianceWeights(self) -> np.ndarray:
        """Finds the long short global minimum variance portfolio using Markowitz portfolio theory

        Returns:
            np.ndarray: Weights
        """
        insuff, weights = self._checkInsuffAssets()
        if(insuff): return weights
        
        omega = np.matmul(self.invSigma, self.one)
        omega = omega / self._optimizedDenominator()
        
        self._assignWeights(omega)
        
        return omega
    
    def optimizeSharpeRatio(self) -> np.ndarray:
        """Finds the long only portfolio allocation with the highest Sharpe ratio

        Returns:
            np.ndarray: Asset weights
        """
        insuff, weights = self._checkInsuffAssets()
        if(insuff): return weights
        
        rfr = getRiskFreeRate()
        
        results = pd.DataFrame(columns=['Allocation', 'Variance', 'Return', 'Sharpe'])

        for _ in range(NUM_PORTFOLIOS):
            weights = np.random.random(self.n)
            weights /= np.sum(weights)
            ret = self.portfolioMean(weights)
            var = self.portfolioVariance(weights)
            shrp = (ret - rfr) / var
            results = results.append({'Allocation': str(weights), 'Variance': var, 'Return': ret, 'Sharpe': shrp}, ignore_index=True)
        
        i = results['Sharpe'].idxmax()
        weights = results.iloc[i]['Allocation'].strip('[]').split()
        weights = [float(i) for i in weights]
        
        self._assignWeights(weights)
        return weights
    
    def _getMu(self) -> np.ndarray:
        """Gets average returns of assets

        Returns:
            np.ndarray: Vector of returns
        """
        mu = []
        for asset in self.assets:
            mu.append(asset.avgRet)
        return np.array(mu)
    
    def optimalPortfolioWeights(self, gamma: float) -> np.ndarray: # this does not produce logical results as gamma changes
        """Finds long short optimal portfolio weight given non-risk averse investor

        Args:
            gamma (float): Inverse risk punishment. Small value is risk on, while large value penalizes volatility

        Returns:
            np.ndarray: Weights
        """
        gm = self.globalMinimumVarianceWeights()
        mu = self._getMu()
        denom = self._optimizedDenominator()
        omega = (1/gamma) * ((denom * np.matmul(self.invSigma, mu)
                             - np.matmul(np.matmul(mu.T, self.invSigma), self.one)
                             * np.matmul(self.invSigma, self.one))
                             / denom)
        
        omega += gm
        
        self._assignWeights(omega)
        
        return omega
