from typing import List, Tuple

import numpy as np

from helpers import Asset


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
                data.append(asset.prices.tolist())
            
            data = np.array(data)
            self.covMat = np.cov(data)
            self.invSigma = np.linalg.inv(self.covMat)
            self.one = np.ones(len(self.assets))
        return
    
    def portfolioMean(self) -> float:
        """Mean of portfolio given weights

        Returns:
            float: Portfolio mean
        """
        mu_p = 0
        for asset in self.assets:
            mu_p += asset.weight * asset.avgRet
        
        return mu_p
    
    def portfolioVariance(self) -> np.ndarray:
        """Variance of portfolio

        Returns:
            np.ndarray: Portfolio variance
        """
        omega = []
        for asset in self.assets:
            omega.append(asset.weight)
        omega = np.array(omega)
        
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
            
    
    def globalMinimumVarianceWeights(self) -> np.ndarray:
        """Finds the long short global minimum variance portfolio using Markowitz portfolio theory

        Returns:
            np.ndarray: Weights
        """
        insuff, weights = self._checkInsuffAssets()
        if(insuff): return weights
        
        omega = np.matmul(self.invSigma, self.one)
        omega = omega / self._optimizedDenominator()
        
        ############################################
        #                                          #
        # Temporary workaround to make long only   #
        # not to be actually used                  #
        # it wouldn't actually make any sense      #
        #                                          #
        ############################################
        
        for i in range(len(omega)):
            if(omega[i]) < 0: omega[i] = 0
        
        omega /= sum(omega)
        
        self._assignWeights(omega)
        
        return omega
    
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