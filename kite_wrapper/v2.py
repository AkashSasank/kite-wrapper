import json
import csv
import numpy as np
from stockstats import StockDataFrame
import pandas as pd
import mplfinance as mpf
import seaborn as sn
import matplotlib.pyplot as plt


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


class TechnicalAnalysisV2:
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

    def get_indicators(self, *args, data=None, to_percentage=True):
        """
        Get set of indicators on input data
        :param data: Input data (any of open, high, low, close)
        :param args: indicator strings ==> https://pypi.org/project/stockstats/
        :param to_percentage: divide by 100
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
                if 'vwap' == arg:
                    vwap = self.get_vwap(data)
                    indicators['vwap'] = vwap
                    continue
                if to_percentage:
                    indicators[arg] = stock[arg] / 100
                    continue
                indicators[arg] = stock[arg]

            except Exception as e:
                pass

        return indicators

    def get_vwap(self, data=None, autoscale=True):
        """
        Find VWAP for given data
        :param data:
        :param autoscale: scale vwap with price to get a smaller value
        :return:
        """
        close = data['close']
        volume = data['volume']
        vwap = (np.cumsum(volume * close) / np.cumsum(volume))
        if autoscale:
            vwap = vwap / max(vwap)
        return vwap

    def get_vwap_gradient(self, data=None, delta=100):
        """
        Get slope of vwap
        :param data:
        :param delta:
        :return:
        """
        if data:
            data = pd.DataFrame(data)
        else:
            data = self.data

        vwap = list(self.get_vwap(data, autoscale=True))
        r = []
        for i in range(1, delta):
            rotated = self.__rotate(vwap, -i)
            v = [(i - j) for (i, j) in zip(vwap, rotated)]
            r.append(v)
        mean = np.mean(r, 0)
        return mean

    def get_candle_ratios(self, data=None, to_percentage=True):
        """
        Get ratios of candle and wicks
        :param data:
        :param to_percentage: divide by 100
        :return:
        """
        if data:
            data = pd.DataFrame(data)
        else:
            data = self.data
        high = data['high']
        low = data['low']
        open_ = data['open']
        close = data['close']

        candle = abs(open_ - close)
        candle_type = close > open_

        total_candle = high - low
        upper_wick = [abs(high[index] - close[index]) if i else abs(high[index] - open_[index]) for
                      index, i in enumerate(candle_type)]

        lower_wick = [abs(low[index] - open_[index]) if i else abs(low[index] - close[index]) for
                      index, i in enumerate(candle_type)]
        type_ = [1 if i else 0 for i in list(close > open_)]
        #     ratios
        if to_percentage:
            r1 = [(i / (j + 0.1)) / 100 for i, j in zip(candle, total_candle)]
            r2 = [(i / (j + 0.1)) / 100 for i, j in zip(upper_wick, total_candle)]
            r3 = [(i / (j + 0.1)) / 100 for i, j in zip(lower_wick, total_candle)]
            r4 = [(i / (j + 0.1)) / 100 for i, j in zip(upper_wick, lower_wick)]
            r5 = [(i / (j + 0.1)) / 100 for i, j in zip(upper_wick, candle)]
            r6 = [(i / (j + 0.1)) / 100 for i, j in zip(lower_wick, candle)]
        else:
            r1 = [(i / (j + 0.1)) for i, j in zip(candle, total_candle)]
            r2 = [(i / (j + 0.1)) for i, j in zip(upper_wick, total_candle)]
            r3 = [(i / (j + 0.1)) for i, j in zip(lower_wick, total_candle)]
            r4 = [(i / (j + 0.1)) for i, j in zip(upper_wick, lower_wick)]
            r5 = [(i / (j + 0.1)) for i, j in zip(upper_wick, candle)]
            r6 = [(i / (j + 0.1)) for i, j in zip(lower_wick, candle)]

        return {
            'r1': r1,
            'r2': r2,
            'r3': r3,
            'r4': r4,
            'r5': r5,
            'r6': r6,
            't': type_
        }

    def generate_data_set(self, type='close', ramp=False, swing=True,
                          include_candle_ratios=True):
        """
        Generate dataset from given data and save as csv file.
        :param type: Column to consider. open, high, low or close.
        :param ramp:Boolean. Consider ascend and descend separately
        :param swing:Boolean. If True, considers swing high and low and movement as separate, else Swing low and ascending in
        one and swing high and descending in another
        :param normalize: Boolean. Normalize data or not.
        :param coeff: Coefficient for normalization.
        :param include_candle_ratios: Boolean. Include the different ratios of a candle wicks and body.
        :return:
        """
        swing = self.get_swing_data(stride=1, type=type, ramp=ramp, swing=swing)

        indicators = self.get_indicators('rsi_6', 'rsi_10', 'pdi', 'mdi', 'adx', 'kdjk', 'kdjd',
                                         'kdjj', 'wr_6', 'wr_10', 'vwap')

        if include_candle_ratios:
            ratios = self.get_candle_ratios()
            indicators.update(ratios)

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
        assert min_length <= max_length

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
            errors.append(int(np.median(error) * 10000))
        return errors.index(np.median(errors)) + 1

    def plot_chart(self, type='candle', moving_averages: tuple = None, show_volume=True, length=100):
        """
        Plot candlestick
        :param show_volume: plot volume or not
        :param type: candle, line, renko, ohlc, bars
        :param moving_averages: tuple. Moving averages tobe plotted
        :param length: length of data tobe displayed
        :return:
        """
        max_length = len(self.data)
        assert max_length > length
        data = self.data[max_length - length:]
        if moving_averages:
            mpf.plot(data, type=type, mav=moving_averages, volume=show_volume)
        else:
            mpf.plot(data, type=type, volume=show_volume)

    def analyse_dataset(self):
        """
        Plot correlation matrix from dataset
        :return:
        """
        filename = self.name + '.csv'
        try:
            dataset = pd.read_csv(filename)
            correlation = dataset.corr()
            sn.heatmap(correlation, annot=True)
            plt.show()
            dataset.plot(kind='hist')
            plt.show()
            dataset.plot(kind='density')
            plt.show()
            print('Max value: ', dataset.max(), ' Min value: ', dataset.min())

        except Exception as e:

            print(e)
