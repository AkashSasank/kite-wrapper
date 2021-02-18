import json
import csv
import numpy as np
from stockstats import StockDataFrame
import pandas as pd


def load_secrets():
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
    def __init__(self, data, name: str):
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

            if prev_value < value < next_value:
                trend.append('A')
            elif prev_value > value > next_value:
                trend.append('D')
            elif prev_value < value > next_value:
                trend.append('SH')
            elif prev_value > value < next_value:
                trend.append('SL')
            else:
                trend.append('-')
        return trend

    def get_swing_data(self, stride, type='close', data=None):
        """
        Get actions and swing data for given data
        :param data: Price data
        :param stride: Neighbour distance to consider for determining trend
        :param type: Open, high, low or close.
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

        """
        Assign actions corresponding to price.
        """
        actions = []
        for value in strong_values:
            if value == 'SH':
                actions.append('Sell')
            elif value == 'SL':
                actions.append('Buy')
            else:
                actions.append('Hold')

        return {
            'actions': actions,
            'swing_high_indices': swing_high_indices,
            'swing_low_indices': swing_low_indices
        }

    def get_indicators(self, *args, data=None, normalize=True, coeff=0.001415926535):
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

    def generate_data_set(self):
        swing = self.get_swing_data(stride=1)

        indicators = self.get_indicators('close_10_sma', 'close_20_sma',
                                         'close_50_sma',
                                         'close_100_sma', 'close_200_sma', 'volume_delta',
                                         'boll_ub', 'boll_lb', 'rsi_6', 'rsi_12', 'rsi_20', 'rsi_50', 'pdi', 'mdi',
                                         'adx')
        indicators['actions'] = swing['actions']
        data_set = pd.DataFrame(data=indicators)
        data_set.to_csv(self.name + '.csv', index=False)
