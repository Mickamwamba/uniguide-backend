import requests
from bs4 import BeautifulSoup
import logging
import time

logger = logging.getLogger(__name__)

class TCUScraper:
    BASE_URL = "https://tcu.go.tz/services/accreditation/academic-programmes-offered-universities-tanzania"

    def __init__(self):
        self.session = requests.Session()
        retries = requests.adapters.Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

    def fetch_programmes(self):
        """
        Fetches all programmes by iterating through pagination.
        Yields a list of dictionaries (batch) with programme details for each page.
        """
        page = 0
        has_next = True
        consecutive_errors = 0
        
        while has_next:
            url = f"{self.BASE_URL}?page={page}"
            logger.info(f"Fetching page {page}: {url}")
            
            try:
                # Add headers to mimic browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
                }
                response = self.session.get(url, headers=headers, verify=False, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'lxml')
                
                table = soup.find('table')
                if not table:
                    logger.warning(f"No table found on page {page}. Stopping.")
                    break
                
                rows = table.find_all('tr')
                # Skip header row (checking if it contains 'S/N' or just standard td check)
                data_rows = [r for r in rows if r.find('td')]
                
                if not data_rows:
                    logger.info("No more data rows found. Stopping.")
                    break

                batch = []
                page_count = 0
                
                for row in data_rows:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue
                    
                    try:
                        programme_name = cols[1].get_text(strip=True)
                        university_name = cols[2].get_text(strip=True)
                        award_level = cols[3].get_text(strip=True)
                        duration_str = cols[4].get_text(strip=True)
                        framework = cols[5].get_text(strip=True)
                        study_mode = cols[6].get_text(strip=True)
                        
                        try:
                            duration_months = int(''.join(filter(str.isdigit, duration_str)))
                        except ValueError:
                            duration_months = 0

                        batch.append({
                            'programme_name': programme_name,
                            'university_name': university_name,
                            'award_level': award_level,
                            'duration_months': duration_months,
                            'qualification_framework': framework,
                            'study_mode': study_mode
                        })
                        page_count += 1
                        
                    except IndexError as e:
                        logger.error(f"Error parsing row: {e}")
                        continue
                
                logger.info(f"Extracted {page_count} programmes from page {page}")
                yield batch
                
                # Check for "Next" link
                next_page_exists = soup.find('a', title='Go to next page') or soup.find('li', class_='pager__item--next')
                
                if page > 200: 
                    logger.warning("Reached page limit 200. Stopping.")
                    break
                    
                page += 1
                consecutive_errors = 0 # Reset error count
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                consecutive_errors += 1
                if consecutive_errors > 3:
                     logger.error("Too many consecutive errors. Stopping.")
                     break
                time.sleep(5) # Wait a bit before retrying the same page (or next page logic needs adjustment if we want to retry SAME page)
                # Currently this loop increments page even on error if we don't handle it.
                # Actually, if we get an exception, we hit 'break' in the old code.
                # Here we should probably continue to retry the *current* page or just skip? 
                # Simplest is to just skip for now or try to retry the loop.
                # Let's just log and continue to allow next pages if it's a specific page error, 
                # BUT if it's connection error the iterator moves to next page which is wrong.
                # Correct logic for retry of SAME page is complex without refactoring loop.
                # For now, let's rely on `requests.adapters.Retry` to handle connection glitches.
                # If `requests` raises after retries, we likely can't access the site.
                if "Read timed out" in str(e):
                     # If requests retry didn't fix it, we might be blocked.
                     pass 

    def fetch_universities(self):
        # We now extract universities dynamically from the programmes list
        return []
