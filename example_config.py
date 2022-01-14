CONSUMER_KEY = None # TD Consumer key
REDIRECT_URL = None # Local uri to redirect eg: 'http://localhost/test'
CREDENTIALS_PATH = None # Path to td_state.json
TD_ACCOUNT = None # TD account number
WATCHLIST_ID = None # Watchlist ID (not the name) can be found from get watchlists endpoint
MARKET_INDEX = None # Market benchmark eg: '$SPX.X'

PHONE_NUMBER = None # Your phone number for SNS, requires SNS to SMS to be set up
S3_BUCKET = None # Name of s3 bucket to store data
RRG_NAME = None # Name of rrg plot file eg: 'rrg.png'
PIE_NAME = None # Name of pie plot file eg: 'pie.png'
PORT_PLOT_NAME = None # Name of portfolio plot file eg: 'portfolio.png'
TRACKER = None # Name of value tracker csv file eg: 'tracker.csv'
TRADES = None # Name of trade tracker csv file eg: 'trades.csv'
ACCOUNT_START = None # Cash available to the strategy

QUADRANTS = None # Which quadrants to include. list where index + 1 corresponds to the quadrant.
                 #     1 or 0 value for True and False repectively. eg: [0, 0, 0, 1]
TARGET_RETURN = None # Target return of portfolio used in Markowitz optimization