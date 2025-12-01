import time
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flipkart_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FlipkartScraper:
    """Advanced Flipkart scraper with anti-bot mechanisms"""
    
    def __init__(self):
        self.driver = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        
    def setup_driver(self):
        """Configure Chrome WebDriver with anti-detection settings"""
        try:
            options = webdriver.ChromeOptions()
            
            # Anti-bot detection settings
            options.add_argument(f'user-agent={random.choice(self.user_agents)}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Performance settings
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            
            # options.add_argument('--headless')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
            
            # Execute CDP commands to hide automation
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": random.choice(self.user_agents)
            })
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            logger.info("WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def human_delay(self, min_sec=2, max_sec=5):
        """Random delay to mimic human behavior"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def scroll_page(self):
        """Scroll page to load lazy-loaded content"""
        try:
            scroll_pause = 1.5
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for _ in range(3):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(scroll_pause)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
        except Exception as e:
            logger.warning(f"Scroll error: {e}")
    
    def scrape_product_list(self, url: str, max_products: int = 50) -> List[Dict]:
        """Scrape product listing page"""
        products = []
        
        try:
            logger.info(f"Accessing URL: {url}")
            self.driver.get(url)
            self.human_delay(3, 5)
            
            # Handle popup if present
            try:
                close_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '✕')]"))
                )
                close_button.click()
                logger.info("Closed popup")
            except TimeoutException:
                logger.info("No popup detected")
            
            self.scroll_page()
            
            # Get page source and parse
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Dynamic class name handling - multiple selectors
            product_containers = (
                soup.find_all('div', {'class': lambda x: x and 'cPHDOP' in str(x)}) or
                soup.find_all('div', {'class': lambda x: x and '_1AtVbE' in str(x)}) or
                soup.find_all('div', {'data-id': True})
            )
            
            logger.info(f"Found {len(product_containers)} product containers")
            
            for idx, container in enumerate(product_containers[:max_products]):
                try:
                    product_data = self.extract_product_details(container)
                    if product_data:
                        products.append(product_data)
                        logger.info(f"Scraped product {idx + 1}: {product_data['title'][:50]}")
                        
                except Exception as e:
                    logger.warning(f"Error extracting product {idx}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(products)} products")
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        
        return products
    
    def extract_product_details(self, container) -> Dict:
        """Extract individual product details"""
        product = {}
        
        try:
            # Title - multiple selector attempts
            title_tag = (
                container.find('div', {'class': lambda x: x and 'KzDlHZ' in str(x)}) or
                container.find('a', {'class': lambda x: x and 's1Q9rs' in str(x)}) or
                container.find('div', {'class': 'col-7-12'})
            )
            product['title'] = title_tag.get_text(strip=True) if title_tag else 'N/A'
            
            # Price
            price_tag = (
                container.find('div', {'class': lambda x: x and 'Nx9bqj' in str(x)}) or
                container.find('div', {'class': lambda x: x and '_30jeq3' in str(x)})
            )
            price_text = price_tag.get_text(strip=True) if price_tag else '₹0'
            product['price'] = price_text.replace('₹', '').replace(',', '').strip()
            
            # Rating
            rating_tag = container.find('div', {'class': lambda x: x and 'XQDdHH' in str(x)})
            product['rating'] = rating_tag.get_text(strip=True) if rating_tag else 'N/A'
            
            # Reviews count
            reviews_tag = container.find('span', {'class': lambda x: x and 'Wphh3N' in str(x)})
            product['reviews'] = reviews_tag.get_text(strip=True) if reviews_tag else '0'
            
            # Product URL
            link_tag = container.find('a', href=True)
            product['url'] = f"https://www.flipkart.com{link_tag['href']}" if link_tag else 'N/A'
            
            # Seller (if available)
            seller_tag = container.find('div', {'class': lambda x: x and 'seller' in str(x).lower()})
            product['seller'] = seller_tag.get_text(strip=True) if seller_tag else 'N/A'
            
            # Timestamp
            product['scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return product
            
        except Exception as e:
            logger.error(f"Error in extract_product_details: {e}")
            return None
    
    def save_to_excel(self, products: List[Dict], filename: str = 'flipkart_products.xlsx'):
        """Save data to Excel file"""
        try:
            df = pd.DataFrame(products)
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Excel save error: {e}")
            return False
    
    def save_to_csv(self, products: List[Dict], filename: str = 'flipkart_products.csv'):
        """Save data to CSV file"""
        try:
            df = pd.DataFrame(products)
            df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"CSV save error: {e}")
            return False
    
    def save_to_database(self, products: List[Dict], db_name: str = 'flipkart_data.db'):
        """Save data to SQLite database"""
        try:
            conn = sqlite3.connect(db_name)
            df = pd.DataFrame(products)
            df.to_sql('products', conn, if_exists='append', index=False)
            conn.commit()
            conn.close()
            logger.info(f"Data saved to database {db_name}")
            return True
        except Exception as e:
            logger.error(f"Database save error: {e}")
            return False
    
    def close(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")


def main():
    """Main execution function"""
    
    # Product categories to scrape
    categories = {
        'mobiles': 'https://www.flipkart.com/search?q=mobiles',
        'laptops': 'https://www.flipkart.com/search?q=laptops',
        'headphones': 'https://www.flipkart.com/search?q=headphones',
        'smartwatches': 'https://www.flipkart.com/search?q=smartwatches'
    }
    
    scraper = FlipkartScraper()
    
    try:
        if not scraper.setup_driver():
            logger.error("Failed to setup driver. Exiting.")
            return
        
        all_products = []
        
        for category_name, category_url in categories.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Scraping category: {category_name.upper()}")
            logger.info(f"{'='*50}")
            
            products = scraper.scrape_product_list(category_url, max_products=20)
            
            # Add category to each product
            for product in products:
                product['category'] = category_name
            
            all_products.extend(products)
            
            # Delay between categories
            scraper.human_delay(5, 10)
        
        # Save results
        if all_products:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            scraper.save_to_excel(all_products, f'flipkart_products_{timestamp}.xlsx')
            scraper.save_to_csv(all_products, f'flipkart_products_{timestamp}.csv')
            scraper.save_to_database(all_products)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Total products scraped: {len(all_products)}")
            logger.info(f"{'='*50}")
        else:
            logger.warning("No products scraped")
    
    except Exception as e:
        logger.error(f"Main execution error: {e}")
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()