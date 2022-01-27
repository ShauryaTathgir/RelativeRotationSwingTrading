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

CONSUMER_KEY = None     # TD Consumer key
REDIRECT_URL = None     # Local uri to redirect eg: 'http://localhost/test'
CREDENTIALS_PATH = None # Path to td_state.json
TD_ACCOUNT = None       # TD account number, string format
WATCHLIST_ID = None     # Watchlist ID (not the name) can be found from get watchlists endpoint
MARKET_INDEX = None     # Market benchmark eg: '$SPX.X'
NQ_API_KEY = None       # Nasdaq data API key

PHONE_NUMBER = None     # Your phone number for SNS, requires SNS to SMS to be set up
S3_BUCKET = None        # Name of s3 bucket to store data
RRG_NAME = None         # Name of rrg plot file eg: 'rrg.png'
PIE_NAME = None         # Name of pie plot file eg: 'pie.png'
PORT_PLOT_NAME = None   # Name of portfolio plot file eg: 'portfolio.png'
TRACKER = None          # Name of value tracker csv file eg: 'tracker.csv'
TRADES = None           # Name of trade tracker csv file eg: 'trades.csv'
POSITIONS = None        # Name of positions tracker csv file eg: 'positions.csv'
BNCHMRK_MULT = None     # Place to save multiplier value

ACCOUNT_START = None    # Cash available to the strategy
LV_QUADRANTS = None     # Which quadrants to use when volatility is low
HV_QUADRANTS = None     # Which quadrants to use when volatility is high
VOL_INDEX = None        # What index to use to determine market volatility
VOL_CUTOFF = None       # Cutoff to determine high or low vol
OPT_METHOD = None       # Optimization method, check trade.optimizeWeights for options and Markowitz for documentation.
NUM_PORTFOLIOS = None   # Number of random portfolios to generate when maximizing Sharpe ratio