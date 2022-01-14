# Relative Rotation Swing Trading Algorithm
## Theory
Relative Rotation Graphs, or RRGs, are a concept initially developed by Julius de Kempenaer that plots a sector's relative momentum against its relative strength. Relative strength is fundamentally how well a sector is performing compared to the market, and the relative momentum is based on the percent change of the relative strength. Once these values are calculated they can be plotted on a relative rotation graph as so:
![Example Relative Rotation Graph](http://rrg.tathgir.com/example-rrg.png) <br>

<span style="font-size:.9em;">*Note*: This graph looks different and has different values compared to relative rotation graphs that can be found on the Bloomberg terminal or [JdK's website stockcharts](stockcharts.com). This is due to proprietary normalization algorithms and different parameters used in smoothing, look back periods, and percent change. This graph noticeably has very straight lines and values that do not range far from 100; however, the quadrant the assets are located in and the general direction that they move do match Bloomberg's calculated values.</span><br><br>

In theory, sectors will follow a clockwise rotational move through the quadrants. Here <span style="color:green">quadrant 1</span> refers to leading sectors, <span style="color:yellow">quadrant 2</span> refers to weakening sectors, <span style="color:red">quadrant 3</span> refers to lagging sectors, and <span style="color:blue">quadrant 4</span> refers to improving sectors. <br><br>

## Algorithm
This algorithm is based on JdK's sector rotation strategy, but was created to be applied broadly to swing trade regular equity positions based on its relative performance to the S&P 500 index. Backtesting results indicated that the most profitable strategy (when limited to long only positions) was to only invest in assets that were in quadrant 4 indicating that they are improving relative to the market. Markowitz Portfolio Theory is then applied to create weight the selected assets on the theoretical efficient frontier. To allow for easy changes to the assets in consideration, the list of potential investments and sectors are stored in a watchlist within my brokerage account and accessed prior to rebalancing. The algorithm then rebalances the portfolio on a daily basis after updating all values in consideration.<br><br>

## Theoretical Pros and Cons
### Pros:
* **Increased Upside & Limited Drawdown**: The goal of this strategy is to invest in the portions of the market that are pulling it upwards while ignoring the portions that are dragging it down. In theory, the covariance (beta) of the portfolio should be high (greater than 1) when the market is up, and low (between 0 and 1) when the market is down.
* **Automated Swing Trading**: The algorithm should be able to invest in assets as they begin an uptrend and close the position as the asset begins trending in the wrong direction. This can allow for swing trading without having to actively manage the position when busy.<br>
### Cons:
* **Market Risk**: While one of the goals of this strategy is to limit drawdowns, it is currently implemented with assets and optimizations to almost always have a positive beta. Therefore, in the event of a market correction, this strategy will still suffer losses and will not adjust to a bear market.
* **Tax Inefficiency**: Due to the daily rebalancing, it is very likely that assets will not be held for over a year to be considered long term capital gains to be taxed at a lower rate.
* **Operational Risk**: I am not a software developer. As a result, there may be errors in the code or edge cases I failed to consider that result in trades that do not follow the strategy and expose me to risks that I am not aware of.
* **Running Costs**: Running costs for this algorithm in AWS on a t4g.micro after enrollment in a Compute Saving Plan are around $5/month. This does not include the costs of utilizing Amazon SNS for notifications and S3 storage for image distribution. Assuming a strategy allocation of $5,000 annual costs would be 1.2%. This also does not include the management fees for ETFs that may be held in the portfolio.<br><br>

## Backtesting

**Backtesting performance is not indicative of future results.**

<br><br>
## Tips
Want to say thanks? You can send me a tip here:<br>
[<img src="https://cdn1.venmo.com/marketing/images/branding/venmo-icon.svg" width="95" height="95" />](https://venmo.com/code?user_id=2901264383868928600&created=1642144602.2140841&printed=1)&nbsp;&nbsp;&nbsp;&nbsp;[![PayPal Logo](https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_74x46.jpg)](https://paypal.me/ShauryaTathgir)<br><br>


## Disclaimer
This code is provided with no warranty and has no guarantee to work. All information, documentation, and code provided are for educational purposes only and should not be misconceived as finanical advice. Investing involves risks, including (but not limited to) the loss of principle invested.