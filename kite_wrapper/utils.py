import json
import csv
import numpy as np
from stockstats import StockDataFrame
import pandas as pd
import mplfinance as mpf


def load_secrets():
    """
    Load data from secret.json as JSON
    :return: Dict.
    """
    try:
        with open('secret.json', 'r') as fp:
            data = json.load(fp)
        return data
    except Exception as e:
        raise e


def to_csv(filename, input_list: list):
    """
    :param input_list: List of dict
    :param filename: filename.csv
    :return:
    """
    rows = []
    keys, values = [], []

    for data in input_list:
        keys, values = [], []
        for key, value in data.items():
            keys.append(key)
            values.append(value)
        rows.append(values)
    with open(filename, "w") as outfile:
        csvwriter = csv.writer(outfile)
        csvwriter.writerow(keys)
        for row in rows:
            csvwriter.writerow(row)


class TechnicalAnalysis:
    """
    Class to perform technical analysis on input stock data.
    The input data should have columns date, open, high, low, close, volume etc.
    """

    def __init__(self, data=None, name: str = None):
        self.data = pd.DataFrame(data)
        self.name = name

    @staticmethod
    def __get_trend(data, stride=1):
        """
        Get trend from a given data.
        :param data: Price data
        :param stride: Neighbour distance to consider for determining trend
        :return: Trend list
        """
        if stride < 1:
            stride = 1
        trend = []
        stride_list = [i for i in range(stride)]
        stride_list.extend([(i - (len(data) - 1)) * -1 for i in range(stride)])
        for index, value in enumerate(data):
            if index in stride_list:
                trend.append('-')
                continue
            prev_value = data[index - stride]
            next_value = data[index + stride]

            if prev_value <= value < next_value or prev_value < value <= next_value:
                trend.append('A')
            elif prev_value >= value > next_value or prev_value > value >= next_value:
                trend.append('D')
            elif prev_value < value > next_value:
                trend.append('SH')
            elif prev_value > value < next_value:
                trend.append('SL')
            else:
                trend.append('-')
        return trend

    def get_swing_data(self, stride, type='close', data=None, ramp=False, swing=True):
        """
        Get actions and swing data for given data
        :param data: Price data
        :param stride: Neighbour distance to consider for determining trend
        :param type: Open, high, low or close.
        :param ramp: Consider ascend and descend separately
        :param swing: If True, considers swing high and low and movement as separate, else Swing low and ascending in
        one and swing high and descending in another
        :return: Dict {actions, swing high, swing low}
        """
        if data:
            data = pd.DataFrame(data)[type]
        else:
            data = self.data[type]
        trends = []
        for s in range(0, stride, 1):
            trend = self.__get_trend(data=data, stride=s)
            trends.append(trend)

        length = len(trends[0])
        strong_values = []
        for index in range(length):
            value = [t[index] for t in trends]
            equal = all(ele == value[0] for ele in value)
            if equal:
                strong_values.append(value[0])
            else:
                strong_values.append('.')

        """
        Indices for Swing high and Swing low values.
        """
        swing_high_indices = [hi for hi, value in enumerate(strong_values) if value == 'SH']
        swing_low_indices = [li for li, value in enumerate(strong_values) if value == 'SL']
        ascend_indices = [li for li, value in enumerate(strong_values) if value == 'A']
        descend_indices = [li for li, value in enumerate(strong_values) if value == 'D']
        """
        Assign actions corresponding to price.
        """
        actions = []
        if swing:
            for value in strong_values:
                if value == 'SH':
                    actions.append('Sell')
                elif value == 'SL':
                    actions.append('Buy')
                else:
                    if ramp:
                        if value == 'A':
                            actions.append('Hold-Up')
                        else:
                            actions.append('Hold-Down')

                    else:
                        actions.append('Hold')
        if not swing:
            for value in strong_values:
                if value == 'SH' or value == 'D':
                    actions.append('Sell')
                elif value == 'SL' or value == 'A':
                    actions.append('Buy')
                else:
                    actions.append('Buy')

        return {
            'actions': actions,
            'swing_high_indices': swing_high_indices,
            'swing_low_indices': swing_low_indices,
            'ascend_indices': ascend_indices,
            'descend_indices': descend_indices
        }

    def get_indicators(self, *args, data=None, normalize=False, coeff=0.001415926535):
        """
        Get set of indicators on input data
        :param data: Input data (any of open, high, low, close)
        :param args: indicator strings ==> https://pypi.org/project/stockstats/
        :param normalize: Boolean - data should be normalised or not
        :param coeff :Normalisation coefficient for sigmoid.
        :return: Dictionary of technical indicators on input file.
        """
        if data:
            data = pd.DataFrame(data)
        else:
            data = self.data
        stock = StockDataFrame.retype(data)
        indicators = {}
        for arg in args:
            try:
                values = stock[arg]
                if normalize:
                    values = [1 / (1 + np.exp(-coeff * i)) for i in values]
                indicators[arg] = values
            except Exception as e:
                pass
        return indicators

    def generate_data_set(self, type='close', ramp=False, swing=True, normalize=False, coeff=0.001415926535):
        """
        Generate dataset from given data and save as csv file.
        :param type: Column to consider. open, high, low or close.
        :param ramp:Boolean. Consider ascend and descend separately
        :param swing:Boolean. If True, considers swing high and low and movement as separate, else Swing low and ascending in
        one and swing high and descending in another
        :param normalize: Boolean. Normalize data or not.
        :param coeff: Coefficient for normalization.
        :return:
        """
        swing = self.get_swing_data(stride=1, type=type, ramp=ramp, swing=swing)

        # indicators = self.get_indicators('close_10_sma', 'close_20_sma',
        #                                  'close_50_sma',
        #                                  'close_100_sma', 'close_200_sma', 'volume_delta',
        #                                  'boll_ub', 'boll_lb', 'rsi_6', 'rsi_12', 'rsi_20', 'rsi_50', 'pdi', 'mdi',
        #                                  'adx', normalize=normalize, coeff=coeff)
        # indicators = self.get_indicators('rsi_6', 'rsi_10', 'pdi', 'mdi', 'adx', 'kdjk', 'kdjd',
        #                                  'kdjj', 'wr_6', 'wr_10', 'dma', 'vr', normalize=normalize, coeff=coeff)
        indicators = self.get_indicators('rsi_6', 'rsi_10', 'pdi', 'mdi', 'adx', 'kdjk', 'kdjd',
                                         'kdjj', 'wr_6', 'wr_10', normalize=normalize, coeff=coeff)

        indicators['actions'] = swing['actions']
        data_set = pd.DataFrame(data=indicators).iloc[5:]
        data_set.to_csv(self.name + '.csv', index=False)

    @staticmethod
    def __rotate(input_list, n):
        return input_list[n:] + input_list[:n]

    def get_best_moving_average(self, max_length=200, min_length=10):
        """
        Get the best moving average that act as support/resistance.
        :param max_length:
        :param min_length:
        :return: best moving average
        """
        data = self.data
        data_open = data.get('open')
        data_close = data.get('close')
        data_high = data.get('high')
        data_low = data.get('low')
        assert len(data_close) > max_length

        errors = []
        # True: Green, False:Red
        # Looking for consecutive red or green candles to confirm trend
        candle_type = [data_close[i] >= data_open[i] for i in range(len(data_close))]
        next_candle_1 = self.__rotate(candle_type, -1)
        next_candle_2 = self.__rotate(candle_type, 1)
        trend = np.logical_and(np.logical_and(candle_type, next_candle_1), next_candle_2)

        for length in range(min_length, max_length + 1, 1):
            sma = 'close_' + str(length) + '_sma'

            average_close = list(self.get_indicators(sma)[sma])[length - 1:]
            high = list(data_high)[length - 1:]
            low = list(data_low)[length - 1:]
            direction = trend[length - 1:]
            anchor = [low[index] if value else high[index] for index, value in enumerate(direction)]

            error = [abs(anchor[index] - value) for index, value
                     in enumerate(average_close)]
            errors.append(np.median(error))
        return int(errors.index(max(errors)) + 1)

    def plot_chart(self, type='candle', moving_averages=(100, 30), show_volume=True):
        """
        Plot candlestick
        :param show_volume: plot volume or not
        :param type: candle, line, renko, ohlc, bars
        :param moving_averages: tuple. Moving averages tobe plotted
        :return:
        """
        mpf.plot(self.data, type=type, mav=moving_averages, volume=show_volume)
