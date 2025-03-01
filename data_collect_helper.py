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
import threading



MAX_THREADS = 30
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

json_lock = threading.Lock()
def save_review_to_json(file_path, user, film_title, unix_timestamp, rating, liked, review_text):
    # Create a dictionary with the extracted details
    review_data = {
        "user": user,
        "title": film_title,
        "review_date": unix_timestamp,
        "rating": rating,
        "liked": liked,
        "review_text": review_text
    }
    
    with json_lock:
        with open(file_path, 'a') as file:
            file.write(json.dumps(review_data) + '\n')



def log_failed_fetch(i, user):
    # print('fail L nerd moment')
    # Load existing data if the file exists, else start with an empty list
    file_path = "../letterboxd_proj_data/failed_fetches.jsonl"
    fail = {"user": user, "i": i}
    with json_lock:
        with open(file_path, 'a') as file:
            file.write(json.dumps(fail) + '\n')
    

def scrape_single_review_page(user, i, session, output_file_name):
    url = "https://letterboxd.com/{}/films/reviews/page/{}".format(user, i)
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all film detail blocks
        film_blocks = soup.find_all("div", class_="film-detail-content")
        # print(user, url)
        # Iterate over each block and extract the required information
        for film in film_blocks:
            # Extract film title
            try:
                film_title_tag = film.find("h2", class_="headline-2 prettify").find("a")
                film_title = film_title_tag.text.strip() if film_title_tag else "Unknown Title"
            except:
                film_title = None
                log_failed_fetch(i, user)





            # Extract star rating
            try:
                rating_tag = film.find("span", class_="rating")
                rating_text = rating_tag.text.strip() if rating_tag else None
                if rating_text:
                    rating = rating_text.count('\u00BD')*0.5 + rating_text.count('\u2605')
                else:
                    rating = None
            except:
                rating = None
                log_failed_fetch(i, user)


            # Extract date
            try:
                date_tag = film.find("span", class_="_nobr")
                date_string = date_tag.text.strip() if date_tag else None
                
                if date_string:
                    date_object = datetime.strptime(date_string, "%d %b %Y")
                    unix_timestamp = int(date_object.timestamp())
                elif date_tag.find("time", class_="localtime-d-mmm-yyyy"):
                    time_tag = span_tag.find("time", class_="localtime-d-mmm-yyyy")
                    
                    datetime_str = time_tag["datetime"]
                    if datetime_str:
                        # Convert to a Unix timestamp
                        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                        unix_timestamp = int(time.mktime(dt.timetuple()))
                else:    
                    print("no date ", user, film_title, date_tag, date_string)
            except:
                log_failed_fetch(i, user)

            # Check if "icon-liked" exists in the attribution block
            try:
                liked_icon = film.find("span", class_="has-icon icon-16 icon-liked")
                liked = 1 if liked_icon else 0
            except:
                log_failed_fetch(i, user)

            # Extract review text
            try:
                review_body_tag = film.find("div", class_="body-text -prose js-review-body js-collapsible-text")
                review_text = review_body_tag.get_text(" ", strip=True) if review_body_tag else None
            except:
                log_failed_fetch(i, user)


            # save review to json
            try:
                reviews_file_name = "../letterboxd_proj_data/{}.jsonl".format(output_file_name)
                save_review_to_json(reviews_file_name, user, film_title, unix_timestamp, rating, liked, review_text)
            except:
                log_failed_fetch(i, user)
    else:
        log_failed_fetch(i, user)
    time.sleep(np.random.uniform(0.5, 1.5))

def get_reviews(usernames, output_file_name):
    print("STARTING get_reviews")
    # Create a session
    session = requests.Session()
    for user in usernames:
        url = "https://letterboxd.com/{}/films/reviews/".format(user)
        
        # Fetch the webpage
        response = session.get(url, headers=headers)
        # Check if request was successful
        if response.status_code == 200:
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            last_page = max(int(a.get_text()) for a in soup.select(".paginate-page a") if a.get_text().isdigit())

            for i in range(1, last_page + 1):
                scrape_single_review_page(user, i, session, output_file_name)
        else:
            log_failed_fetch(-1, user)
    session.close()


def get_reviews_multi(usernames, output_file_name):
    print("STARTING get_reviews_multi")
    # Create a session
    session = requests.Session()
    for user in usernames:
        url = "https://letterboxd.com/{}/films/reviews/".format(user)
        
        # Fetch the webpage
        response = session.get(url, headers=headers)
        # Check if request was successful
        if response.status_code == 200:
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            try:
                last_page = max(int(a.get_text()) for a in soup.select(".paginate-page a") if a.get_text().isdigit())
            except:
                log_failed_fetch(-2, user)
                continue
            threads = min(MAX_THREADS, last_page)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [
                    executor.submit(scrape_single_review_page, user, i, session, output_file_name)
                    for i in range(1, last_page + 1)
                ]
                # Wait for all tasks to complete
                concurrent.futures.wait(futures)

        else:
            log_failed_fetch(-1, user)
    session.close()
