import os
import requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrape_offers():
    print("Starting data extraction...")
    
    # 1. Target URL (Example e-commerce test site)
    url = "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return
        
    soup = BeautifulSoup(response.text, 'html.parser')
    offers = []

    # 2. Extract specific elements (adjust class names based on your target site)
    cards = soup.find_all('div', class_='product-wrapper')
    
    for card in cards:
        try:
            title = card.find('a', class_='title').text.strip()
            price = card.find('h4', class_='price').text.strip()
            description = card.find('p', class_='description').text.strip()
            
            offers.append({
                "Date Found": datetime.now().strftime("%Y-%m-%d"),
                "Product": title,
                "Price": price,
                "Description": description,
                "Source": "WebScraper Test Site"
            })
        except AttributeError:
            continue # Skip if any field is missing

    # 3. Save to Excel
    if offers:
        df = pd.DataFrame(offers)
        filename = "daily_offers.xlsx"
        
        # Save beautifully with Pandas
        df.to_excel(filename, index=False, sheet_name="Today's Offers")
        print(f"Successfully saved {len(offers)} offers to {filename}!")
    else:
        print("No offers extracted.")

if __name__ == "__main__":
    scrape_offers()