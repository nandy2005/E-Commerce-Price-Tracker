from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import sys
import pandas as pd
from datetime import datetime


def get_product_data(url):
    options=webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver=webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        WebDriverWait(driver,10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,"span.VU-ZEz")))
        html=driver.page_source
        soup=BeautifulSoup(html, "lxml")
    
        def extract(selector):
            elem=soup.select_one(selector)
            return elem.text if elem else None
    
        Ratings_Count = extract("span.Wphh3N > span:first-child")
        ratings_count_final=Ratings_Count.split()[0] if Ratings_Count else None
        data={
            "Title": extract("span.VU-ZEz"),
            "Current Price": extract("div.Nx9bqj.CxhGGd"),
            "Original Price":extract("div.yRaY8j.A6\+E6v"),
            "Overall Rating":extract("div.XQDdHH"),
            "Ratings Count":ratings_count_final
            
        }
        return data
    
    except TimeoutException:
        print("Timeout: Page took too long to load",file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error:{e}",file=sys.stderr)
        return None
    finally:
        driver.quit()

with open("./data/seed_urls.txt","r") as file:
    urls=[url.strip() for url in file.readlines() if url.strip()]
    products=[]
    for url in urls:
        product=get_product_data(url)
        if product:
            product["url"]=url
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            product["timestamp"]=timestamp
            products.append(product)
        else:
            print(f"Skipping {url} due to errors", file=sys.stderr)
            
    df=pd.DataFrame(products)
    df.to_csv("./data/scraped_products.csv", index=False, encoding="utf-8")
    print("Data saved to ./data/scraped_products.csv")

