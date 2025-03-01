import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata
import json
import os
import concurrent.futures
import time
from data_collect_helper import *

# Set headers to mimic a browser request

with open('../letterboxd_proj_data/kaggle_data/usernames.json', 'r') as file:
    try:
        usernames_json = json.load(file)
    except json.JSONDecodeError:
                usernames_json = []
usernames_sample = usernames_json['usernames'][:100]

start = time.time()
get_reviews_multi(usernames_sample, "usernames_sample_100") # took 30s with multi
# 100 took 75 mins
end = time.time()
print(f"Execution time: {end-start} seconds")
