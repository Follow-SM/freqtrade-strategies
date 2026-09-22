from freqtrade.strategy import IStrategy
from pandas import DataFrame
from followsm import FollowSMClient

class ToxicityProtectedStrategy(IStrategy):
    """
    Freqtrade Strategy augmented with followsm-sdk telemetry.
    Automatically halts trade entries when VPIN > 0.70 or Depth Imbalance > 2.0.
    """
    INTERFACE_VERSION = 3
    timeframe = '5m'
    minimal_roi = {"0": 0.02}
    stoploss = -0.05

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Unauthenticated client (30 req/min free tier rate limit)
        self.followsm_client = FollowSMClient()

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            symbol = metadata['pair'].replace('/', '')
            snapshot = self.followsm_client.get_toxicity_snapshot(symbol)
            
            vpin = getattr(snapshot, 'vpin', 0.0)
            ob_toxicity = getattr(snapshot, 'ob_toxicity_1pct', 1.0)
            
            dataframe['vpin'] = vpin
            dataframe['ob_toxicity'] = ob_toxicity
            dataframe['is_toxic'] = (vpin > 0.70) | (ob_toxicity > 2.0)
        except Exception:
            dataframe['vpin'] = 0.0
            dataframe['ob_toxicity'] = 1.0
            dataframe['is_toxic'] = False

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['is_toxic'] == False)  # Gate entry on toxic flow check
            ),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['is_toxic'] == True),  # Exit on toxic liquidity spike
            'exit_long'] = 1
        return dataframe