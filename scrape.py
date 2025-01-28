import json
import time
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Define product links
links = {
    "Apple iPhone 15": "https://www.amazon.in/dp/B0CHX3TW6X?ref=ods_ucc_kindle_BBCHX2WQLX&th=1",
    "Apple 2023 MacBook Pro (16-inch)": "https://amzn.in/d/2K038xa",
    "OnePlus Nord 456 (Mercurial Silver, 8GB RAM, 256GB Storage)": "https://amzn.in/d/2K038xa",
    "Sony WH-1000XM5 Wireless Headphones": "https://amzn.in/d/4LJ9XL",
}

def scrape_product_data(link):
    """
    Scrapes product data such as price, discount, ratings, and reviews from the given product link.
    
    Parameters:
        link (str): URL of the product page.

    Returns:
        dict: Product data containing price, discount, and reviews.
    """
    # Configure Chrome options for headless scraping
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=en")
    options.add_argument("--window-size=1920,1080")

    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1920, 1080)
    driver.get(link)

    product_data = {}
    product_data["reviews"] = []
    wait = WebDriverWait(driver, 10)

    # Retry logic in case of loading issues
    retry = 0
    while retry < 3:
        try:
            driver.save_screenshot("screenshot.png")  # Save screenshot for debugging
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "a-offscreen")))
            break
        except Exception:
            print("Retrying...")
            retry += 1
            driver.get(link)
            time.sleep(5)

    try:
        # Extract price
        price_elem = driver.find_element(By.XPATH, '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[3]/span[2]/span[2]')
        product_data["selling_price"] = int("".join(price_elem.text.strip().split(",")))
    except Exception:
        product_data["selling_price"] = 0

    try:
        # Extract discount
        discount_elem = driver.find_element(By.XPATH, '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[2]')
        product_data["discount"] = discount_elem.text.strip()
    except Exception:
        product_data["discount"] = "N/A"

    try:
        # Extract rating
        rating_elem = driver.find_element(By.CLASS_NAME, "a-icon-popover")
        full_rating_text = rating_elem.get_attribute("innerHTML").strip()
        if "out of 5 stars" in full_rating_text.lower():
            product_data["rating"] = full_rating_text.lower().split(" out of")[0].strip()
        else:
            product_data["rating"] = full_rating_text
    except Exception:
        product_data["rating"] = "N/A"

    try:
        # Extract reviews
        reviews_link = driver.find_element(By.XPATH, "//a[contains(text(), 'See customer reviews')]").get_attribute("href")
        driver.get(reviews_link)
        time.sleep(3)
        reviews_container = driver.find_element(By.ID, "cm_cr-review_list")
        reviews_elements = reviews_container.find_elements(By.TAG_NAME, "span")
        for review in reviews_elements:
            product_data["reviews"].append(review.get_attribute("innerText"))
    except Exception:
        product_data["reviews"] = []

    # Add timestamp
    product_data["date"] = datetime.now().strftime("%Y-%m-%d")

    driver.quit()
    return product_data


# Main script to scrape data for all products
reviews = json.loads(pd.read_csv("reviews.csv").to_json(orient="records"))
prices = json.loads(pd.read_csv("competitor_data.csv").to_json(orient="records"))

for product_name, link in links.items():
    product_data = scrape_product_data(link)
    
    # Add scraped data to the prices list
    prices.append({
        "product_name": product_name,
        "Price": product_data.get("selling_price", 0),
        "Discount": product_data.get("discount", "N/A"),
        "Date": product_data["date"],
    })

    # Add reviews to the reviews list
    for review in product_data["reviews"]:
        reviews.append({"product_name": product_name, "review": review})

# Save updated data to CSV files
pd.DataFrame(reviews).to_csv("reviews.csv", index=False)
pd.DataFrame(prices).to_csv("competitor_data.csv", index=False)
