from wxpy import *

import matplotlib

matplotlib.rcParams['backend'] = 'TkAgg'

    
import re
import random
import string

from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config

from IPython.display import display
from iexfinance.stocks import Stock
from datetime import datetime, timedelta
import numpy as np
from iexfinance.stocks import get_historical_data
import pandas as pd



import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# set parameters so all plots are consistent
plt.rcParams['figure.figsize'] = (20, 8)

# prettier plotting with seaborn
import seaborn as sns; 
sns.set(font_scale=1.5)
sns.set_style("whitegrid")



# Create a trainer that uses this config
trainer = Trainer(config.load("config_spacy.yml"))

# Load the training data
training_data = load_data('demo-rasa-stock.json')

# Create an interpreter by training the model
interpreter = trainer.train(training_data)


responses = ['What kind of stock information for {0} would you like to see?', 
             "Current Stock Price: {0}",
             "Today's Volume: {0}\nAnything else?",
             "Market cap: {0}",
             "Yes, of course. But you have to tell me dates at first.",
             "I can offer you a plot like this",
             "haha, thank you!",
             "piece of cake~",
             "it's my pleasure",
             "Peers of {0}: {1}"
            ]

ticker_symbol = ''
ent_vals_all = ''


def extract_ticker_symbol(message):
    entities = interpreter.parse(message)["entities"]
    ent_vals = [e["value"] for e in entities]
    global ticker_symbol
    if len(ent_vals) == 1:
        ticker_symbol = ent_vals
        return ticker_symbol
    return 'none'

def extract_dates(message):
    entities = interpreter.parse(message)["entities"]
    ent_vals = [e["value"] for e in entities]
    global ent_vals_all
    if len(ent_vals) >1:
        ent_vals_all = ','.join(ent_vals)
        return ent_vals_all
    return 'none'

def show_data(ent_vals_all):
    sy, sm, sd, ey, em, ed = eval(ent_vals_all)
    start = datetime(sy,sm,sd)
    end = datetime(ey,em,ed)
    historical_prices = get_historical_data(ticker_symbol, start, end,token="pk_7cf36b882a64479f888346329fda2dbb")
    stock_historicals = pd.DataFrame(historical_prices).T
    return stock_historicals

def show_plot(ent_vals_all):
    # plot
    sy, sm, sd, ey, em, ed = eval(ent_vals_all)
    start = datetime(sy,sm,sd)
    end = datetime(ey,em,ed)
    historical_prices = get_historical_data(ticker_symbol, start, end,token="pk_7cf36b882a64479f888346329fda2dbb")
    stock_historicals = pd.DataFrame(historical_prices).T
    dformat = "%m/%d/%Y"
    fig, ax = plt.subplots()
    ax.xaxis_date()
    ax.plot_date(stock_historicals.index.values,stock_historicals.close,'p-')
    ax.set(xlabel="Date", ylabel="Closing Price",)
    ax.set_title("Historical Stock Prices For: " + ticker_symbol +
                 "\n " + start.strftime(dformat) + " to " + end.strftime(dformat))
    plt.xticks(rotation=45)
    plt.savefig('plot.png', dpi=200, bbox_inches='tight')
    plt.show()
    return plt

def intent_respond(message):
    data = interpreter.parse(message)
    global stock_historicals, ticker_symbol, company_info, sy, sm, sd, ey, em, ed, ent_vals_all 
    if data["intent"]["name"] == "stock_company":
        ticker_symbol = ''.join(extract_ticker_symbol(message))
        return responses[0].format(ticker_symbol)
    if data["intent"]["name"] == "stock_current_price":
        company_info = Stock(ticker_symbol, token="pk_7cf36b882a64479f888346329fda2dbb")
        return responses[1].format(company_info.get_price())
    if data["intent"]["name"] == "stock_today_volume":
        return responses[2].format(company_info.get_volume())
    if data["intent"]["name"] == "stock_market_cap":
        return responses[3].format(company_info.get_market_cap())
    if data["intent"]["name"] == "stock_historical_information":
        return responses[4]
    if data["intent"]["name"] == "stock_date":
        ent_vals_all = extract_dates(message)
#        print(ent_vals_all)
        display(show_data(ent_vals_all))
        show_plot(ent_vals_all)
        my_friend.send_image('plot.png')
        return responses[5]
    if data["intent"]["name"] == "praise":
        return responses[6]
    if data["intent"]["name"] == "data_excel":
        #Save Historical Stock Prices to Excel File:
        stock_historicals=show_data(ent_vals_all)
        file_name = "HistoricalStockPrices.xlsx"
        excel_sheet = stock_historicals.to_excel(file_name)
        my_friend.send_file("HistoricalStockPrices.xlsx")
        return responses[7]
    if data["intent"]["name"] == "thanks":
        return responses[8]
    if data["intent"]["name"] == "peers":
        return responses[9].format(ticker_symbol, ', '.join(company_info.get_peers()))
    return None


# Define the states
INIT=0
AUTHED=1

# Define the policy rules
policy_rules = {
    (INIT, "ask_explanation"): (INIT, "I'm a robot to help you search for stock information", None),
    (INIT, "search"): (INIT, "you'll have to log in first, what's your phone number?", AUTHED),
    (INIT, "number"): (AUTHED, "perfect, welcome back!\nwhich company would you like to know about?", None),
}

def interpret(message):
    msg = message.lower()
    if 'do' in msg:
        return 'ask_explanation'
    if 'search' in msg:
        return 'search'
    if '-' in msg:
        return 'number'    
    return 'none'

# Define send_message()
def send_message(state, pending, message):
    print("USER : {}".format(message))
   
    if interpret(message) != 'none':
        new_state, response, pending_state = policy_rules[(state, interpret(message))]
        print("BOT : {}".format(response))
        if pending is not None:
            new_state, response, pending_state = policy_rules[pending]
            print("BOT : {}".format(response))        
        if pending_state is not None:
            pending = (pending_state, interpret(message))
        return new_state, pending, response
    if interpret(message) == 'none':
        response = intent_respond(message)
        print("BOT : {}".format(response))
        return state, pending, response

def send_messages(messages):
    state = INIT
    pending = None
    for msg in messages:
        state, pending, response = send_message(state, pending, msg)
    return response


bot = Bot()

my_friend = bot.friends().search('WWW')[0]
my_friend.send("Hello, I'm Robot!")



@bot.register(my_friend)
def reply_my_friend(msg):
    messages = [msg.text]
#    messages = [msg]
    response = send_messages(messages)
    my_friend.send(response)
#reply_my_friend("And could you please provide me with the historical information for the stock")
