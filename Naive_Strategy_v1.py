def Alpha_1(quotes, trades, book, volume = 0.01):

  '''
  Inputs:
  quotes: a dataframe of quotes data
  trades: a dataframe of trades data
  book: a dataframe of limit order book
  volume: volume per trade, default = 0.01 unit
  
  Output:
  a dictionary containing the price&volume of buy&sell orders.
  maybe a dictionary of list
  '''
  
  buy_price = [book['bid'][0], book['bid'][1]]
  sell_price = [book['ask'][0], book['ask'][1]]
  buy_volume = [volume/4, volume/4]
  sell_volume = [volume/4, volume/4]
  
  return {'buy_price': buy_price,
          'buy_volume': buy_volume,
          'sell_price': sell_price,
          'sell_volume': sell_volume
          }
