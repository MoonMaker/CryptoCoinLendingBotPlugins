# coding=utf-8
import os
import io
from plugins.Plugin import Plugin
import time
import numpy
import datetime
import json
import pandas as pd
import sqlite3 as sqlite

import matplotlib

class MarketDataException(Exception):
    pass

class AnalysisCharts(Plugin):
    report_interval = 300 # Minimal report interval

    def on_bot_init(self):
        super(AnalysisCharts, self).on_bot_init()
        
        # Parameters
        self.report_interval = int(self.config.get("ANALYSISCHARTS", "ReportInterval", 10, 300, 84600))
        self.report_json = self.config.get("ANALYSISCHARTS", "ReportJson", "www/analysischarts/fundingbook.json")
        self.currencies_to_analyse = self.config.get_currencies_list('analyseCurrencies', 'MarketAnalysis')
        self.update_interval = int(self.config.get('MarketAnalysis', 'analyseUpdateInterval', 10, 1, 3600))
        self.lending_style = int(self.config.get('MarketAnalysis', 'lendingStyle', 75, 1, 99))
        self.data_tolerance = float(self.config.get('MarketAnalysis', 'data_tolerance', 15, 10, 90))
        self.analysis_method = self.config.get('Daily_min', 'method', 'percentile')
        self.boxplot_intval = 15; # In Minutes


        # Needed for calculation
        self.MACD_long_win_seconds = int(self.config.get('MarketAnalysis', 'MACD_long_win_seconds',
                                                    60 * 30 * 1 * 1,
                                                    60 * 1 * 1 * 1,
                                                    60 * 60 * 24 * 7))
        self.MACD_short_win_seconds = int(self.config.get('MarketAnalysis', 'MACD_short_win_seconds', int(self.MACD_long_win_seconds / 12),  1, self.MACD_long_win_seconds / 2))        
        self.percentile_seconds = int(self.config.get('MarketAnalysis', 'percentile_seconds',
                                                 60 * 60 * 24 * 1,
                                                 60 * 60 * 1 * 1,
                                                 60 * 60 * 24 * 14))
        self.daily_min_multiplier = float(self.config.get('Daily_min', 'multiplier', 1.05, 1))

        # Folders
        self.modules_dir = os.path.dirname(os.path.realpath(__file__))
        self.top_dir = os.path.dirname(self.modules_dir)
        self.db_dir = os.path.join(self.top_dir, 'market_data')

        self.run();
 
    # Event before lending
    def before_lending(self):
        self.run();
 
    # Event after lending is successfully
    def after_lending(self):
        self.run();

    def run(self):
        """
        Main entry point to start recording data. This starts all the other threads.
        """
        
        # Write JSON file
        df = pd.DataFrame();
        rates = pd.DataFrame();
        data = {};
        tjson= "";

        with io.open(self.report_json, 'w', encoding='utf8') as outfile:

            data['id'] = 'Bitfinex';
            data['time'] = datetime.datetime.utcnow().isoformat()[:-3] + 'Z'
            data['conditions'] = self.currencies_to_analyse;

            for cur in self.currencies_to_analyse:
                self.db_con = self.create_connection(cur)
                df = self.get_rate_suggestion(self.db_con, None);
                
                try:
                    rates = df.rate0*100;
                    
                    # Quantile for box plot: http://www.ritchieng.com/pandas-variability/
                    iqr = (rates.quantile(0.75) - rates.quantile(0.25)) * 1.5;
    
                    data[cur]= {'q1'    : self.truncate( rates.quantile(q=0.25), 6 ),
                                'q2'    : self.truncate( rates.quantile(q=0.5), 6 ),
                                'q3'    : self.truncate( rates.quantile(q=0.75), 6 ),
                                'iqr'   : self.truncate( iqr, 6 ),              # Interquartile (IQR) range
                                'lower' : self.truncate( rates.quantile(0.25) - (iqr*1.5), 6 ), # Statistically outlier min
                                'upper' : self.truncate( rates.quantile(0.75) + (iqr*1.5), 6 ), # Statistically outlier max
                                'std'   : self.truncate( rates.std(), 6 ),   # Standard Deviation
                                'mean'  : self.truncate( rates.mean(), 6 ),  # Mean
                                'var'   : self.truncate( rates.var(), 6 ),   # Variance sum((x_i - x_mean)^2) / n
                                'mad'   : self.truncate( rates.mad(), 6 ),   # Mean (average) absolute deviation
                                'percentile' : numpy.percentile(rates, int(self.lending_style)), # Used Percentile function
                                'mac'   : self.get_MACD_rate( cur, df )*100,
                                'x'     : rates.index.tolist(),
                                'y'     : rates.values, # pd.to_datetime([1490195805.433, 1490195805.433502912], unit='s')
                                'z'     : rates.values
                                #'box'   : rates[(rates.index > '2017-10-17')].values
                               }
                    #print rates[(rates.index > (datetime.datetime.now()-datetime.timedelta(minutes=self.boxplot_intval)))].values

                except AttributeError:
                    print( "Waiting for more data from %s", data['id'] );

                self.db_con.close()

            
            tjson= pd.Series(data).to_json(date_format='iso');
        
            #print data
            outfile.write(unicode(tjson, errors='replace'))
            outfile.close()


    @staticmethod
    def get_day_difference(date_time):  # Will be a number of seconds since epoch
        """
        Get the difference in days between the supplied date_time and now.

        :param date_time: A python date time object
        :return: The number of days that have elapsed since date_time
        """
        date1 = datetime.datetime.fromtimestamp(float(date_time))
        now = datetime.datetime.now()
        diff_days = (now - date1).days
        return diff_days


    def get_analysis_seconds(self):
        """
        Gets the correct number of seconds to use for anylsing data depeding on the method being used.
        """
        if self.analysis_method == 'percentile':
            return self.percentile_seconds
        elif self.analysis_method == 'MACD':
            return self.MACD_long_win_seconds


    def get_rate_list(self, db_con, seconds):
        """
        Query the database (db_con) for rates that are within the supplied number of seconds and now.

        :param db_con: The currency (database) to remove data from
        :param seconds: The number of seconds between the oldest order returned and now.

        :return: A pandas DataFrame object with named columns ('time', 'rate0', 'rate1',...)
        """
        # Request more data from the DB than we need to allow for skipped seconds
        request_seconds = int(seconds * 1.1)
        if isinstance(db_con, sqlite.Connection):
            price_levels = ['rate0']
            rates = self.get_rates_from_db(db_con, from_date=time.time() - request_seconds, price_levels=price_levels)
            if len(rates) == 0:
                return []
    
            df = pd.DataFrame(rates)
    
            columns = ['time']
            columns.extend(price_levels)
            try:
                df.columns = columns
            finally:
                # convert unixtimes to datetimes so we can resample
                df.time = pd.to_datetime(df.time, unit='s')
    
            # Resample into 1 second intervals, average if we get two in the same second and fill any empty spaces with the
            # previous value
            df = df.resample('1s', on='time').mean().ffill()
            return df
        
        else:
            return None;


    def get_rates_from_db(self, db_con, from_date=None, price_levels=['rate0']):
        """
        Query the DB for all rates for a particular currency

        :param db_con: Connection to the database
        :param cur: The currency you want to get the rates for
        :param from_date: The earliest data you want, specified in unix time (seconds since epoch)
        :price_level: We record multiple price levels in the DB, the best offer being rate0
        """
        with db_con:
            cursor = db_con.cursor()
            query = "SELECT unixtime, {0} FROM loans ".format(",".join(price_levels))
            if from_date is not None:
                query += "WHERE unixtime > {0}".format(from_date)
            query += ";"
            cursor.execute(query)
            return cursor.fetchall()


    def get_rate_suggestion(self, cur, rates=None):
        """
        Return the suggested rate from analysed data. This is the main method for retrieving data from this module.
        Currently this only supports returning of a single value, the suggested rate. However this will be expanded to
        suggest a lower and higher rate for spreads.

        :param cur: The currency (database) to remove data from
        :param rates: This is used for unit testing only. It allows you to populate the data used for the suggestion.

        :return: A float with the suggested rate for the currency.
        """

        try:
            rates = self.get_rate_list(cur, self.get_analysis_seconds()) if rates is None else rates
            if not isinstance(rates, pd.DataFrame):
                raise ValueError("Rates must be a Pandas DataFrame")

            if len(rates) == 0:
                print("Rate list not populated")
            #else:
                #print(rates);
        finally:
            return rates


    def create_connection(self, cur, db_path=None, db_type='sqlite3'):
        """
        Create a connection to the sqlite DB. This will create a new file if one doesn't exist.  We can use :memory:
        here for db_path if we don't want to store the data on disk

        :param cur: The currency (database) in the DB
        :param db_path: DB directory
        :return: Connection object or None
        """
        if db_path is None:
            prefix = self.config.get_exchange()
            db_path = os.path.join(self.db_dir, '{0}-{1}.db'.format(prefix, cur))
            
        if os.path.isfile(db_path):
            con = sqlite.connect(db_path)
            return con
        else:
            print "error message: DB not found"

    def truncate(self, f, n):
        """Truncates/pads a float f to n decimal places without rounding"""
        # From https://stackoverflow.com/questions/783897/truncating-floats-in-python
        s = '{}'.format(f)
        if 'e' in s or 'E' in s:
            return float('{0:.{1}f}'.format(f, n))
        i, p, d = s.partition('.')
        return float('.'.join([i, (d + '0' * n)[:n]]))

    def get_MACD_rate(self, cur, rates_df):
        """
        Golden cross is a bit of a misnomer. But we're trying to look at the short term moving average and the long
        term moving average. If the short term is above the long term then the market is moving in a bullish manner and
        it's a good time to lend. So return the short term moving average (scaled with the multiplier).
 
        :param cur: The currency (database) to remove data from
        :param rates_df: A pandas DataFrame with times and rates
        :param short_period: Length in seconds of the short window for MACD calculations
        :param long_period: Length in seconds of the long window for MACD calculations
        :param multiplier: The multiplier to apply to the rate before returning.
 
        :retrun: A float of the suggested, calculated rate
        """
        if len(rates_df) < self.get_analysis_seconds() * (self.data_tolerance / 100):
            print("{0} : Need more data for analysis, still collecting. I have {1}/{2} records"
                  .format(cur, len(rates_df), int(self.get_analysis_seconds() * (self.data_tolerance / 100))))
            raise MarketDataException
 
        short_rate = rates_df.rate0.tail(self.MACD_short_win_seconds).mean()
        long_rate = rates_df.rate0.tail(self.MACD_long_win_seconds).mean()
 
        if short_rate > long_rate:
            if rates_df.rate0.iloc[-1] < short_rate:
                return short_rate * self.daily_min_multiplier
            else:
                return rates_df.rate0.iloc[-1] * self.daily_min_multiplier
        else:
            return long_rate * self.daily_min_multiplier
