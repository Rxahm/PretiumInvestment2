#Importing libraries

import simfin as sf
import pandas as pd

#Set API key and local directory

sf.set_api_key('db09ea19-dd4e-4afa-9f93-81dc1c19b416')
sf.set_data_dir('~simfin_data/')

income_df = sf.load_income(variant = 'quarterly', market = 'us").reset_index()
income_df

Print income_df