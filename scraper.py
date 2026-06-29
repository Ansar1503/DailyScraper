import os
import requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

def scrape_offers():
    print("Starting cross-site data extraction...")
    
    # 1. Define your list of target URLs
    urls = [
        "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops",
        "https://webscraper.io/test-sites/e-commerce/allinone/computers/tablets"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_offers = []

    # 2. Loop through each URL
    for url in urls:
        print(f"Scraping: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Skipping {url} - Status code: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            cards = soup.find_all('div', class_='product-wrapper')
            
            for card in cards:
                try:
                    title = card.find('a', class_='title').text.strip()
                    price = card.find('h4', class_='price').text.strip()
                    description = card.find('p', class_='description').text.strip()
                    
                    all_offers.append({
                        "Date Found": datetime.now().strftime("%Y-%m-%d"),
                        "Product": title,
                        "Price": price,
                        "Description": description,
                        "Source URL": url  # Helps you track which site it came from
                    })
                except AttributeError:
                    continue # Skip if any field is missing
                    
            # Polite scraping practice: wait 1 second between requests so you don't overwhelm servers
            time.sleep(1)
            
        except Exception as e:
            print(f"An error occurred while scraping {url}: {e}")
            continue

    # 3. Save everything to a single Excel file
    if all_offers:
        df = pd.DataFrame(all_offers)
        filename = "daily_offers.xlsx"
        
        df.to_excel(filename, index=False, sheet_name="All Daily Offers")
        print(f"Successfully saved {len(all_offers)} total offers to {filename}!")
    else:
        print("No offers extracted from any of the URLs.")

if __name__ == "__main__":
    scrape_offers()