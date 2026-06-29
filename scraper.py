import os
import re
import requests
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

# --- TASK CONFIGURATIONS ---
CONFIG = {
    "TIMEOUT": 10,
    "DELAY_BETWEEN_SITES": 1
}

# Define different scraping rules for different sets of URLs
TASKS = [
    {
        "name": "Enigma & Taif Targets",
        "type": "keyword",
        "keywords": ["enigma", "taif"],
        "urls": [
            "https://www.naazperfumes.com/category/swiss-arabain",
            "https://www.perfumenetwork.in/collections/swiss-arabian",
            "https://scentira.in/collections/swiss-arabian",
            "https://www.fridaycharm.com/collections/swiss-arabian-perfumes",
            "https://www.fragranceheaven.in/collections/swiss-arabian",
            "https://vanellaindia.com/collections/swiss-arabian",
            "https://perfumepalace.in/collections/swiss-arabian",
            "https://halalsauda.com/collections/swiss-arabian-attar",
            "https://belvish.com/collections/swiss-arabian",
            "https://perfumex.in/collections/swiss-arabian-perfumes",
            "https://perfumeaddiction.com/collections/swiss-arabian"
        ],
        "currency": "₹"
    },
    {
        "name": "Intertec Under 100 QAR",
        "type": "budget",
        "max_price": 100.0,
        "urls": [
            # Added pages 1, 2, and 3 to capture more of their catalog
            "https://shopintertec.com/collections/all",
            "https://shopintertec.com/collections/all?page=2",
            "https://shopintertec.com/collections/all?page=3"
        ],
        "currency": "QAR "
    }
]

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def clean_title(title_clean):
    # Added QAR to the stripping regex
    title_clean = re.sub(r'(?:Rs\.?|₹|INR|QAR)\s*[\d,]+(?:\.\d{2})?', '', title_clean, flags=re.I)
    title_clean = re.sub(r'\b(?:from|sale|sold\s*out|in\s*stock|regular\s*price|sale\s*price|unit\s*price\s*/\s*per)\b', '', title_clean, flags=re.I)
    title_clean = title_clean.replace("Swiss ArabianSwiss Arabian", "Swiss Arabian")
    title_clean = re.sub(r'^[-\s/|]+|[-\s/|]+$', '', title_clean)
    return clean_text(title_clean)

def extract_best_title(candidate_titles, handle):
    handle_words = set(re.findall(r'[a-z]+', handle.lower()))
    best_title = ""
    best_score = -1
    
    for title in candidate_titles:
        title_clean = clean_title(title)
        if not title_clean: continue
        title_lower = title_clean.lower()
        if any(x in title_lower for x in ["quick buy", "quick view", "add to cart", "read more", "buy now"]): continue
        if len(title_clean) > 100: continue
            
        title_words = set(re.findall(r'[a-z]+', title_lower))
        score = len(handle_words.intersection(title_words))
        
        if "online in india" in title_lower or "scentira" in title_lower or "perfume network" in title_lower:
            score -= 2
            
        if score > best_score:
            best_score = score
            best_title = title_clean
        elif score == best_score and len(title_clean) > len(best_title):
            best_title = title_clean
            
    if not best_title:
        best_title = " ".join([w.capitalize() for w in handle.split('-')])
    return best_title

def extract_prices(text):
    # Upgraded regex to catch QAR and perfectly handle numbers under 100
    matches = re.findall(r'(?:Rs\.?|₹|INR|QAR)\s*([\d,]+(?:\.\d{2})?)', text, re.I)
    prices = []
    for m in matches:
        try:
            val = float(m.replace(',', ''))
            prices.append((val, m))
        except ValueError:
            continue
    
    if not prices:
        matches = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b', text)
        for m in matches:
            try:
                val = float(m.replace(',', ''))
                if 1 <= val <= 100000:
                    prices.append((val, m))
            except ValueError:
                continue
                
    if not prices: return None, None
        
    unique_prices = []
    seen = set()
    for val, raw in prices:
        if val not in seen:
            seen.add(val)
            unique_prices.append((val, raw))
            
    if len(unique_prices) == 1:
        return unique_prices[0][0], None
    elif len(unique_prices) >= 2:
        sorted_prices = sorted(unique_prices, key=lambda x: x[0])
        return sorted_prices[0][0], sorted_prices[1][0]
    return None, None

def find_price_for_link(a_tag, handle):
    curr = a_tag
    for depth in range(5):
        parent = curr.parent
        if not parent: break
            
        other_product_links = 0
        for sibling_a in parent.find_all('a', href=True):
            s_href = sibling_a['href']
            if '/products/' in s_href:
                s_path = s_href.split('?')[0]
                s_handle = s_path.split('/products/')[-1]
                if s_handle and s_handle != handle:
                    other_product_links += 1
        
        if other_product_links > 0: break
            
        price_elems = parent.find_all(class_=re.compile(r'price|money|current|reduced|compare', re.I))
        for elem in price_elems:
            elem_text = clean_text(elem.get_text())
            sale, original = extract_prices(elem_text)
            if sale: return sale, original
                
        parent_text = clean_text(parent.get_text())
        sale, original = extract_prices(parent_text)
        if sale: return sale, original
        curr = parent
        
    return None, None

def scrape_offers():
    print("Starting Task-Based Extraction Engine...\n")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_sheet_results = {}
    
    # Process each task dynamically
    for task in TASKS:
        print(f"--- Running Task: {task['name']} ---")
        task_data = []
        
        for url in task["urls"]:
            print(f"Scraping: {url}")
            try:
                response = requests.get(url, headers=headers, timeout=CONFIG["TIMEOUT"])
                if response.status_code != 200:
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                products = {}
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    is_prod_link = False
                    handle = ""
                    if '/products/' in href:
                        is_prod_link = True
                        handle = href.split('?')[0].split('/products/')[-1]
                    elif '/product/' in href:
                        is_prod_link = True
                        handle = href.split('?')[0].split('/product/')[-1]
                    
                    if is_prod_link and handle and not any(x in href for x in ['/cart', '/checkout', '/search']):
                        if handle not in products:
                            products[handle] = {
                                'href': href if href.startswith('http') else f"{'/'.join(url.split('/')[:3])}{href}",
                                'titles': [],
                                'a_tag': a
                            }
                        if a.text: products[handle]['titles'].append(a.text)
                        img = a.find('img')
                        if img and img.get('alt'): products[handle]['titles'].append(img['alt'])
                
                # Filter results based on the current task's rules
                for handle, data in products.items():
                    title = extract_best_title(data['titles'], handle)
                    sale_price, original_price = find_price_for_link(data['a_tag'], handle)
                    
                    title_lower = title.lower()
                    handle_lower = handle.lower()
                    
                    # Rule 1: If it's a Keyword Task, ensure it matches
                    if task["type"] == "keyword":
                        if not any(kw in title_lower or kw in handle_lower for kw in task["keywords"]):
                            continue
                            
                    # Rule 2: If it's a Budget Task, ensure it's under the price limit
                    if task["type"] == "budget":
                        if sale_price is None or sale_price > task["max_price"]:
                            continue
                    
                    price_str = f"{task['currency']}{sale_price:,.2f}" if sale_price else "N/A"
                    if original_price:
                        price_str += f" (was {task['currency']}{original_price:,.2f})"
                    
                    task_data.append({
                        "Date Found": datetime.now().strftime("%Y-%m-%d"),
                        "Product": title,
                        "Price": price_str,
                        "Raw Price": sale_price if sale_price else float('inf'),
                        "Source URL": data['href']
                    })
                    
                time.sleep(CONFIG["DELAY_BETWEEN_SITES"])
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        # If data was found for this task, clean it, sort it, and stage it for export
        if task_data:
            df = pd.DataFrame(task_data).sort_values(by="Raw Price").drop(columns=["Raw Price"])
            all_sheet_results[task["name"]] = df
            print(f"> Found {len(task_data)} matching items.\n")
        else:
            print(f"> No matching items found.\n")

    # Final Export: Create a multi-sheet Excel file
    if all_sheet_results:
        filename = "daily_offers.xlsx"
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in all_sheet_results.items():
                df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        print(f"Success! Generated {filename} with {len(all_sheet_results)} sheets.")
    else:
        print("No items matched criteria across any task.")

if __name__ == "__main__":
    scrape_offers()