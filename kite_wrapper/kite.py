import logging
from kiteconnect import KiteConnect
import requests
import json
import datetime
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .utils import TechnicalAnalysis

logging.basicConfig(level=logging.DEBUG)

analysis = TechnicalAnalysis()


class Kite:
    """
    A wrapper class for kiteconnect API.
    """

    def __init__(self, api_key, api_secret, redirect_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_url = redirect_url
        self.access_token = None
        self.request_token = None
        self.session = KiteConnect(api_key=self.api_key)
        self.__set_secrets()
        if self.access_token:
            self.session.set_access_token(self.access_token)

    def connect(self, auto=False, user_id=None, password=None, pin=None):
        """
        Authentication. Get request token.
        :param auto: Boolean. Automate authentication.
        :param user_id: Kite User ID.
        :param password: Kite password.
        :param pin: Kite pin.
        :return:
        """
        kite = self.session
        url = kite.login_url()
        r = requests.get(url)
        try:
            driver = webdriver.Chrome('./chromedriver')
        except Exception as e:
            print("""
            Download appropriate version of chrome driver
            """)
            raise e
        driver.get(r.url)
        if auto:
            WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "userid"))
            )
            uid = driver.find_element_by_id('userid')
            uid.send_keys(user_id)
            pwd = driver.find_element_by_id('password')
            pwd.send_keys(password)
            pwd.send_keys(Keys.RETURN)
            WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "pin"))
            )
            code = driver.find_element_by_id('pin')
            code.send_keys(pin)
            code.send_keys(Keys.RETURN)
        url = driver.current_url
        while self.redirect_url not in url:
            url = driver.current_url
        request_token = url.split('request_token=')[1].split('&')[0]
        driver.quit()
        data = kite.generate_session(request_token, api_secret=self.api_secret)
        access_token = data["access_token"]
        self.access_token = access_token
        self.request_token = request_token

        self.save_secrets()
        self.session.set_access_token(access_token)

    def save_secrets(self):
        """
        Save credentials in secret.json file.
        :return:
        """
        user_data = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "redirect_url": self.redirect_url,
            "access_token": self.access_token
        }

        with open('secret.json', 'w') as fp:
            json.dump(user_data, fp)

    def validate_token(self):
        """
        Validate request token.
        :return: Boolean.
        """
        try:
            self.session.profile()
            return True
        except Exception as e:
            return False

    def __set_secrets(self):
        """
        Initialise secret credentials from secret.json file.
        :return:
        """
        try:
            with open('secret.json', 'r') as fp:
                data = json.load(fp)
            self.api_key = data['api_key']
            self.api_secret = data['api_secret']
            self.redirect_url = data['redirect_url']
            self.access_token = data['access_token']
            self.request_token = data['request_token']
        except Exception as e:
            pass

    def get_secrets(self):
        """
        Get the secrete credentials initialised in class.
        :return: Dict.
        """
        secrets = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "redirect_url": self.redirect_url,
            "access_token": self.access_token
        }
        return secrets

    def get_historic_data(self, instrument_token, interval='day', sets=1, delta=None):
        """
        Gets historic data till today
        :param instrument_token: instrument identifier (retrieved from the instruments()) call.
        :param interval: candle interval (hour, minute, day, 5 minute etc.).
        :param sets: Number of sets of historic data to fetch. Default 1. Used as multiplier for the total time span
        of data.
        :param delta: Number of days for which data need to be fetched.
        :return: List of historic data
        """
        try:
            assert interval in self.valid_intervals
        except AssertionError as e:
            print('Enter a valid interval.')
            print(self.valid_intervals)
            return
        if delta:
            assert delta > 0
            assert delta < 60
            delta = datetime.timedelta(days=delta)
        else:
            if interval in ['minute', '2minute']:
                delta = datetime.timedelta(days=60)
            elif interval in ['3minute', '4minute', '5minute', '10minute']:
                delta = datetime.timedelta(days=100)
            elif interval in ['15minute', '30minute']:
                delta = datetime.timedelta(days=200)
            elif interval in ['hour', '2hour', '3hour']:
                delta = datetime.timedelta(days=400)
            elif interval in ['day', 'week']:
                delta = datetime.timedelta(days=2000)
            else:
                delta = datetime.timedelta(days=1)
        now = datetime.datetime.now()
        data = []
        for s in range(sets):
            to_date = now - s * delta
            from_date = to_date - delta
            historical_data = self.session.historical_data(instrument_token, interval=interval, from_date=from_date,
                                                           to_date=to_date)
            data.extend(historical_data)
        return data

    def get_latest_technical_indicators(self, *args, instrument_token, interval='minute', normalize=False,
                                        coeff=0.001415926535):
        """
        Fetch latest indicator values
        :param args: indicator strings ==> https://pypi.org/project/stockstats/
        :param instrument_token: instrument identifier (retrieved from the instruments()) call.
        :param interval: candle interval (hour, minute, day, 5 minute etc.).
        :param normalize: Boolean - data should be normalised or not
        :param coeff :Normalisation coefficient for sigmoid.
        :return: Dict of latest indicator values.
        """
        data = self.get_historic_data(instrument_token, interval)
        indicators = analysis.get_indicators(*args, data=data, normalize=normalize)
        indicator_values = {}
        for indicator, value in indicators.items():

            v = value[-1]
            # Mapping using sigmoid
            if normalize:
                v = 1 / (1 + np.exp(-coeff * v))
            indicator_values[indicator] = v
        return indicator_values

    def get_latest_candle_ratios(self, instrument_token, interval='minute'):
        """
        Get latest candle ratios.
        :param instrument_token:
        :param interval:
        :return:
        """
        data = self.get_historic_data(instrument_token, interval)
        ratios = analysis.get_candle_ratios(data=data)
        indicator_values = {}
        for ratio, value in ratios.items():
            v = value[-1]
            indicator_values[ratio] = v
        return indicator_values

    def get_input_features(self, *args, instrument_token, interval='minute'):
        """
        Get input features to feed ML model
        :param args: indicator strings ==> https://pypi.org/project/stockstats/
        :param instrument_token: instrument identifier (retrieved from the instruments()) call.
        :param interval: candle interval (hour, minute, day, 5 minute etc.).
        :return: Dict of latest indicator values.
        """
        data = self.get_historic_data(instrument_token, interval)
        indicators = analysis.get_indicators(*args, data=data)
        ratios = analysis.get_candle_ratios(data=data)
        indicators.update(ratios)
        indicator_values = {}
        for indicator, value in indicators.items():
            v = value[-1]
            indicator_values[indicator] = v

        return indicator_values

    def get_trading_symbol(self, instrument_token):
        """
        Get trading symbol for a given instrument token.
        :param instrument_token:
        :return: trading_symbol
        """
        return [i['tradingsymbol'] for i in self.instruments if i['instrument_token'] == instrument_token][0]

    def get_trend(self, instrument_token, interval='minute', smal=30, smah=60):
        """
        Find market trend of an instrument in a given time frame
        :param instrument_token:
        :param interval:
        :param smal: Lower simple moving average
        :param smah:Higher simple moving average
        :return: trend
        """
        # TODO: Improve trend prediction
        assert smah > smal
        sma_low = 'close_' + str(smal) + '_sma'
        sma_high = 'close_' + str(smah) + '_sma'
        indicators = self.get_latest_technical_indicators(sma_high, sma_low, 'pdi', 'mdi',
                                                          instrument_token=instrument_token, interval=interval,
                                                          normalize=False)
        smal = indicators[sma_low]
        smah = indicators[sma_high]
        pdi = indicators['pdi']
        mdi = indicators['mdi']
        trend = 'None'
        try:
            ltp = self.session.ltp([instrument_token]).get(str(instrument_token))['last_price']
            if ltp > smal and ltp > smah:
                trend = 'Long'
            elif ltp < smal and ltp < smah:
                trend = 'Short'
            elif smal <= ltp <= smah or smal >= ltp >= smah:
                if pdi > mdi:
                    trend = 'Long'
                if pdi <= mdi:
                    trend = 'Short'
            else:
                trend = 'None'
        except Exception as e:
            pass
        return trend

    def get_trend_and_input_features(self, *args, instrument_token, interval='minute', smal=30, smah=60):
        """
        Find market trend of an instrument in a given time frame
        :param instrument_token:
        :param interval:
        :param smal: Lower simple moving average
        :param smah:Higher simple moving average
        :return: trend
        """
        # TODO: Improve trend prediction
        assert smah > smal
        # calculate delta for historic data
        delta = self.__get_delta(smah, interval=interval)
        # Get historic data
        data = self.get_historic_data(instrument_token, interval, delta=delta)
        #     Trend Calculation
        sma_low = 'close_' + str(smal) + '_sma'
        sma_high = 'close_' + str(smah) + '_sma'
        # get indicators
        indicators = analysis.get_indicators(*args, sma_high, sma_low, 'pdi', 'mdi', data=data)
        indicator_values = {}
        # Get the latest values
        for indicator, value in indicators.items():
            indicator_values[indicator] = value[-1]

        smal = indicator_values.pop(sma_low)
        smah = indicator_values.pop(sma_high)
        pdi = indicator_values['pdi']
        mdi = indicator_values['mdi']
        trend = 'None'
        # Find trend
        try:
            ltp = self.session.ltp([instrument_token]).get(str(instrument_token))['last_price']
            if ltp > smal and ltp > smah:
                trend = 'Long'
            elif ltp < smal and ltp < smah:
                trend = 'Short'
            elif smal <= ltp <= smah or smal >= ltp >= smah:
                if pdi > mdi:
                    trend = 'Long'
                if pdi <= mdi:
                    trend = 'Short'
            else:
                trend = 'None'
        except Exception as e:
            trend = 'None'
            return
        #   Input feature calculation
        # Get candle ratios
        ratios = analysis.get_candle_ratios(data=data)
        for r, value in ratios.items():
            indicator_values[r] = value[-1]

        return trend, indicator_values, ltp

    @staticmethod
    def __get_delta(min_length, interval, trading_hours=5):
        num_min_candles_per_day = trading_hours * 60
        if interval == 'minute':
            num_candles = num_min_candles_per_day
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 1
        if interval == '2minute':
            num_candles = num_min_candles_per_day // 2
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 1
        if interval == '3minute':
            num_candles = num_min_candles_per_day // 3
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 1
        if interval == '4minute':
            num_candles = num_min_candles_per_day // 4
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 1
        if interval == '5minute':
            num_candles = num_min_candles_per_day // 5
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 2
        if interval == '10minute':
            num_candles = num_min_candles_per_day // 10
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 2
        if interval == '15minute':
            num_candles = num_min_candles_per_day // 15
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 2
        if interval == '30minute':
            num_candles = num_min_candles_per_day // 30
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 3
        if interval == 'hour':
            num_candles = num_min_candles_per_day // 60
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 5
        if interval == '2hour':
            num_candles = num_min_candles_per_day // 120
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 8
        if interval == '3hour':
            num_candles = num_min_candles_per_day // 180
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 10
        if interval == 'day':
            num_candles = 1
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 25
        if interval == 'week':
            num_candles = 0.2
            if min_length > num_candles:
                return np.ceil(min_length / num_candles)
            else:
                return 50

    def get_combined_historic_data_for_multiple_instruments(self, *args, interval='day', sets=1):
        """
        Get historic data for multiple instruments
        :param args: Instrument tokens
        :param interval: Data interval
        :param sets: Number of sets of historic data to fetch. Default 1. Used as multiplier for the total time span
        of data.
        :return: List of data
        """
        historic_data = []
        for instrument_token in args:
            try:
                data = self.get_historic_data(instrument_token, interval=interval, sets=sets)
                historic_data.extend(data)
            except Exception as e:
                continue
        return historic_data

    @property
    def valid_intervals(self):
        return ['minute', '2minute', '3minute', '4minute', '5minute', '10minute', '15minute', '30minute',
                'hour', '2hour', '3hour', 'day', 'week']

    @property
    def instruments(self):
        return self.session.instruments()
