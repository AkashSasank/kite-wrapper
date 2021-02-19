import logging
from kiteconnect import KiteConnect
import kiteconnect.exceptions as exceptions
import requests
from selenium import webdriver
import json
import datetime
import numpy as np

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

    def connect(self):
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
        url = driver.current_url
        while self.redirect_url not in url:
            url = driver.current_url
        request_token = url.split('request_token=')[1].split('&')[0]
        driver.close()
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
        except exceptions.TokenException as e:
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

    @property
    def valid_intervals(self):
        return ['minute', '2minute', '3minute', '4minute', '5minute', '10minute', '15minute', '30minute',
                'hour', '2hour', '3hour', 'day', 'week']

    @property
    def instruments(self):
        return self.session.instruments()
