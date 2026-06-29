import requests
import pandas as pd
from datetime import datetime
import time

def scan_entire_intertec_store(max_price=100.0):
    base_url = "https://shopintertec.com/products.json"
    page = 1
    limit = 250  # Shopify's maximum allowable items per JSON request
    all_deals = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Initializing full site scan for shopintertec.com... Target: Under {max_price} QAR\n")
    
    while True:
        print(f"Scanning catalog block {page} (Fetching up to {limit} items)...")
        
        # Request the raw data layer directly
        params = {"limit": limit, "page": page}
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                break
                
            data = response.json()
            products = data.get("products", [])
            
            # If the products list is empty, we have reached the absolute end of the website
            if not products:
                print("Reached the end of the product catalog.")
                break
                
            for product in products:
                title = product.get("title")
                handle = product.get("handle")
                product_type = product.get("product_type", "")
                
                # A single product listing might have multiple options (e.g., different sizes)
                for variant in product.get("variants", []):
                    price_raw = variant.get("price")
                    compare_at_price_raw = variant.get("compare_at_price")
                    available = variant.get("available", True)
                    
                    if not price_raw:
                        continue
                        
                    try:
                        price = float(price_raw)
                    except ValueError:
                        continue
                    
                    # Check our budget target threshold
                    if price <= max_price and available:
                        variant_title = variant.get("title", "")
                        display_name = title
                        if variant_title and variant_title != "Default Title":
                            display_name = f"{title} ({variant_title})"
                            
                        price_str = f"QAR {price:,.2f}"
                        if compare_at_price_raw:
                            try:
                                old_p = float(compare_at_price_raw)
                                if old_p > price:
                                    price_str += f" (was QAR {old_p:,.2f})"
                            except ValueError:
                                pass
                                
                        all_deals.append({
                            "Date Found": datetime.now().strftime("%Y-%m-%d"),
                            "Category": product_type,
                            "Product Name": display_name,
                            "Price": price_str,
                            "Raw Price": price,
                            "Product URL": f"https://shopintertec.com/products/{handle}"
                        })
            
            # Increment to next block page
            page += 1
            time.sleep(1) # Polite cooldown between heavy pagination blocks
            
        except Exception as e:
            print(f"An error occurred during execution: {e}")
            break

    # Process and save results
    if all_deals:
        df = pd.DataFrame(all_deals)
        # Sort deals lowest price first so the absolute best flash offers surface immediately
        df = df.sort_values(by="Raw Price").drop(columns=["Raw Price"])
        
        filename = "intertec_budget_deals.xlsx"
        df.to_excel(filename, index=False, sheet_name="Deals Under 100")
        print(f"\nScan complete! Found {len(all_deals)} total items matching your criteria.")
        print(f"Saved cleanly to {filename}")
    else:
        print("\nScan complete. No matching items found under your limit today.")

if __name__ == "__main__":
    scan_entire_intertec_store(max_price=100.0)