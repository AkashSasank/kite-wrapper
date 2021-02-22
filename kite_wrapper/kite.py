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
        user_data = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "redirect_url": self.redirect_url,
            "access_token": self.access_token
        }

        with open('secret.json', 'w') as fp:
            json.dump(user_data, fp)

    def validate_token(self):
        try:
            self.session.profile()
            return True
        except Exception as e:
            return False

    def __set_secrets(self):
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
        secrets = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "redirect_url": self.redirect_url,
            "access_token": self.access_token
        }
        return secrets

    def get_historic_data(self, instrument_token, interval='day'):
        """
        Gets historic data till today
        :param instrument_token: instrument identifier (retrieved from the instruments()) call.
        :param interval: candle interval (hour, minute, day, 5 minute etc.).
        :return:
        """
        try:
            assert interval in self.valid_intervals
        except AssertionError as e:
            print('Enter a valid interval.')
            print(self.valid_intervals)
            return
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
        to_date = datetime.datetime.now()
        from_date = to_date - delta
        data = self.session.historical_data(instrument_token, interval=interval, from_date=from_date,
                                            to_date=to_date)
        return data

    def get_latest_technical_indicators(self, *args, instrument_token, interval='minute', normalize=True,
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
        indicators = analysis.get_indicators(*args, data=data, normalize=False)
        indicator_values = {}
        for indicator, value in indicators.items():

            v = value[-1]
            if normalize:
                v = 1 / (1 + np.exp(-coeff * v))
            indicator_values[indicator] = v
        return indicator_values

    def get_trading_symbol(self, instrument_token):
        return [i['tradingsymbol'] for i in self.instruments if i['instrument_token'] == instrument_token][0]

    def get_trend(self, instrument_token, interval='minute'):
        """
        Find market trend of an instrument in a given time frame
        :param instrument_token:
        :param interval:
        :return: trend
        """
        indicators = self.get_latest_technical_indicators('close_60_sma', 'close_30_sma', 'pdi', 'mdi',
                                                          instrument_token=instrument_token, interval=interval,
                                                          normalize=False)
        sma30 = indicators['close_30_sma']
        sma60 = indicators['close_60_sma']
        pdi = indicators['pdi']
        mdi = indicators['mdi']
        trend = 'None'
        try:
            ltp = self.session.ltp([instrument_token]).get(str(instrument_token))['last_price']
            if ltp > sma30 > sma60:
                trend = 'Long'
            elif ltp < sma30 < sma60:
                trend = 'Short'
            elif sma30 <= ltp <= sma60 or sma30 >= ltp >= sma60:
                if pdi > mdi:
                    trend = 'Long'
                if pdi <= mdi:
                    trend = 'Short'
            else:
                trend = 'None'
        except Exception as e:
            pass
        return trend

    @property
    def valid_intervals(self):
        return ['minute', '2minute', '3minute', '4minute', '5minute', '10minute', '15minute', '30minute',
                'hour', '2hour', '3hour', 'day', 'week']

    @property
    def instruments(self):
        return self.session.instruments()
