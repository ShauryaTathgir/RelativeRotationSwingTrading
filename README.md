# Relative Rotation Swing Trading Algorithm
## Theory
Relative Rotation Graphs, or RRGs, are a concept initially developed by Julius de Kempenaer that plots a sector's relative momentum against its relative strength. Relative strength is fundamentally how well a sector is performing compared to the market, and the relative momentum is based on the percent change of the relative strength. Once these values are calculated they can be plotted on a relative rotation graph as so:<br>
![Example Relative Rotation Graph](http://rrg.tathgir.com/example-rrg-new.png) <br>

<span style="font-size:10pt;">*Note*: This graph looks different and has different values compared to relative rotation graphs that can be found on the Bloomberg terminal or [JdK's website stockcharts](stockcharts.com). This is due to proprietary normalization algorithms and different parameters used in smoothing, look back periods, and percent change. This graph noticeably has very straight lines and values that do not range far from 100; however, the quadrant the assets are located in and the general direction that they move do somewhat match Bloomberg's calculated values.</span><br>

In theory, sectors will follow a clockwise rotational move through the quadrants. Here <span style="color:green">quadrant 1</span> refers to leading sectors, <span style="color:yellow">quadrant 2</span> refers to weakening sectors, <span style="color:red">quadrant 3</span> refers to lagging sectors, and <span style="color:blue">quadrant 4</span> refers to improving sectors. <br><br>

## Algorithm
This algorithm is based on JdK's sector rotation strategy, but was created to be applied broadly to swing trade regular equity positions based on its relative performance to the S&P 500 index. Backtesting results indicated that the most profitable strategy (when limited to long only positions) was to only invest in assets that were in quadrant 4 indicating that they are improving relative to the market. Markowitz Portfolio Theory is then applied to create weight the selected assets on the theoretical efficient frontier. To allow for easy changes to the assets in consideration, the list of potential investments and sectors are stored in a watchlist within my brokerage account and accessed prior to rebalancing. The algorithm then rebalances the portfolio on a daily basis after updating all values in consideration.<br><br>

## Theoretical Pros and Cons
### Pros:
* **Increased Upside & Limited Drawdown**: The goal of this strategy is to invest in the portions of the market that are pulling it upwards while ignoring the portions that are dragging it down. In theory, the covariance with the market (beta) of the portfolio should be high (greater than 1) when the market is up, and low (between 0 and 1) when the market is down.
* **Automated Swing Trading**: The algorithm should be able to invest in assets as they begin an uptrend and close the position as the asset begins trending in the wrong direction. This can allow for swing trading without having to actively manage the position when busy.<br>
### Cons:
* **Market Risk**: While one of the goals of this strategy is to limit drawdowns, it is currently implemented with assets and optimizations to almost always have a positive beta. Therefore, in the event of a market correction, this strategy will still suffer losses and will not adjust to a bear market.
* **Tax Inefficiency**: Due to the daily rebalancing, it is very likely that assets will not be held for over a year to be considered long term capital gains to be taxed at a lower rate.
* **Operational Risk**: I am not a software developer. As a result, there may be errors in the code or edge cases I failed to consider that result in trades that do not follow the strategy and expose me to risks that I am not aware of.
* **Running Costs**: Running costs for this algorithm in AWS on a t3a.micro after enrollment in a Compute Saving Plan are around $5/month. This does not include the costs of utilizing Amazon SNS for notifications and S3 storage for image distribution. Assuming a strategy allocation of $10,000 annual costs would be 60 bps. This also does not include the management fees for ETFs that may be held in the portfolio.
* **Lack of awareness**: The only input that this strategy uses are the daily closing prices for the relevant assets. The strategy does not take any broader set of information into account when making trades.<br><br>

## Backtesting
Detailed backtesting data can be found in the backtesting file. The folder number corresponds to the quadrants included if that number was in binary. So, 1 is [0, 0, 0, 1] and 5 is [0, 1, 0, 1], etc.<br>
This is a plot over the last ~9 years with the following SPDR Sector ETFs in consideration: 'XLY', 'XLP', 'XLE', 'XLF', 'XLV', 'XLI', 'XLB', 'XLK', and 'XLU'. These were selected because they had a long price history and for no other reason. The benchmark is the S&P 500 index and the included assets are only in quadrant 4 when the VIX is above 18, and both quadrants 3 and 4 were included when the VIX was below 18.<br>
![BacktestResult](http://rrg.tathgir.com/githubbacktest.png) <br>
This backtest assumed a starting allocation of $1,000 with an additional annual investment of $100. We can see that the alogrithm strongly outperformed the market post COVID while also generating some alpha in prior years. Some lack of performance is due to not including all sectors in the algorithm, so when sectors outside of the 9 included sectors were pulling up the market, the algorithm was instead sitting on cash. The strong performance post COVID is due to the algorithm's preference for higher volatility markets. When sector prices diverge by a larger margin and in a short time frame, the algorithm can capitalize on this by only weighting the leading sectors to generate alpha since the market was being weighed down by other sectors. If all sectors are performing relatively the same (which they typically do due to their very high correlation), the algorithm fails to generate a distictive advantage.<br>
However, it is clear that changing the quadrants included based on market volatility is extremely effective at improving the performance of the overall algorithm. Including lagging and improving sectors performs better than only improving sectors in a stable bull market, but the opposite is true in unstable bull markets.<br>
Learning from this backtest, we can see that the choice of chosen assets are extremely important for strategy performance. An ideal possible asset list would include assets from all sectors with minimal correlations and relatively high variances.<br>

**Backtesting performance is not indicative of future results.**<br><br>

## Future Improvements
* **Allow for short sales**: To increase leverage the placeTrade function needs to be allowed to use the sell short command and if the current position is long, it would need to be closed prior to opening a short position. This would also allow for a negative beta strategy in certain market conditions.
* **Improve Relative Rotation Calculations**: Reduce smoothing and apply different normalization methods to have the graph match Bloomberg's to allow for more advanced strategies.
* **Hedge the portfolio**: Automate hedging positions to reduce drawdowns.
* **Deal with orders not filling or being rejected**: Program will currently be stuck in endless loop or raise an error in these cases, respectively.
* **Take dividends into account**: Since TD does not allow fractional share trading, dividends on assets with DRIP have been ignored. Relative rotation calculations would also be thrown off as raw price data is used instead of adjusted price.
* **Handle previous positions**: When an asset is removed from the watchlist, the algorithm will close any open position that it had in that asset. However, it will continue to close any position in that asset even if it did not initiate it. For example, if the original watchlist was ABC and XYZ, and XYZ was removed from the list, all shares of XYZ will be sold. The problem is if I ever try to open a position in XYZ in the same account moving forward, the algorithm would close that position at rebalance as it does not distinguish between specific positions on an asset.
* **Clean up code**:
    1. Have PositionTracker class handle all benchmark multiplier as a private attribute, so trade script does not need to do any calculations. Would require some way to store multiplier when garbage collector deletes the instance.
    2. Take into account whole share sizes in optimization. Optimal weights assume fractional shares can be purchased, TD does not allow for fractional share trading so actual allocation will differ from optimal weights.<br><br>

## Implementation
1. Conduct a proper code review and recognize that none of this code should be used.
2. Add values to config file.
3. Follow initialization steps for the [unofficial TD Python API](https://github.com/areed1192/td-ameritrade-python-api).
4. Create an EC2 instance and create an SNS notification.
5. Connect EC2 instance to an IAM role with full S3 access and SNS publishing access.
6. Ensure account is margin or has at least triple additional cash balance not allocated to the strategy to reduce risk of good faith violations.
7. Close any positions in assets included in the strategy or the algorithm may automatically do so and add its cash value to its allocation.<br><br>


## Tips
Want to say thanks? You can send me a tip here:<br>
[<img src="https://cdn1.venmo.com/marketing/images/branding/venmo-icon.svg" width="95" height="95" />](https://venmo.com/code?user_id=2901264383868928600&created=1642144602.2140841&printed=1)&nbsp;&nbsp;&nbsp;&nbsp;[![PayPal Logo](https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_74x46.jpg)](https://paypal.me/ShauryaTathgir)<br><br>


## Disclaimer
This code is provided with no warranty and has no guarantee to work. All information, documentation, and code provided are for educational purposes only and should not be misconceived as finanical advice. Investing involves risks, including (but not limited to) the loss of principle invested. Please review the license for more information.
