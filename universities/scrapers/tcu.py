import requests
from bs4 import BeautifulSoup
import logging
import time

logger = logging.getLogger(__name__)

class TCUScraper:
    PROGRAMMES_URL = "https://tcu.go.tz/services/accreditation/academic-programmes-offered-universities-tanzania"
    METADATA_URL = "https://tcu.go.tz/services/accreditation/universities-registered-tanzania"

    def __init__(self):
        self.session = requests.Session()
        retries = requests.adapters.Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

    def fetch_universities_metadata(self):
        """
        Fetches university metadata and their details page urls.
        Returns a generator of dictionaries with full university metadata.
        """
        page = 0
        has_next = True
        
        while has_next:
            url = f"{self.METADATA_URL}?page={page}"
            logger.info(f"Scraping University Metadata List Page {page}: {url}")
            
            try:
                response = self.session.get(url, verify=False, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'lxml')
                
                table = soup.find('table')
                if not table:
                    logger.warning(f"No table on page {page}. Stopping.")
                    break
                
                rows = [r for r in table.find_all('tr') if r.find('td')]
                if not rows:
                    logger.info("No data rows found. Stopping.")
                    break

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue
                        
                    name = cols[1].get_text(strip=True)
                    head_office = cols[2].get_text(strip=True)
                    uni_type = cols[3].get_text(strip=True)
                    status = cols[4].get_text(strip=True)
                    
                    view_link = cols[5].find('a')
                    detail_url = None
                    if view_link and 'href' in view_link.attrs:
                        href = view_link['href']
                        if href.startswith('http'):
                            detail_url = href
                        elif href.startswith('/'):
                            detail_url = f"https://tcu.go.tz{href}"
                        else:
                            detail_url = f"https://tcu.go.tz/services/accreditation/{href}"

                    # Base metadata structure
                    uni_data = {
                        'name': name,
                        'head_office': head_office,
                        'university_type': uni_type,
                        'status': status,
                        'address': '',
                        'email': '',
                        'website': '',
                        'accreditation_status': '',
                        'registration_no': ''
                    }

                    if detail_url:
                        details = self._fetch_university_details(detail_url)
                        uni_data.update(details)

                    yield uni_data

                next_page = soup.find('a', title='Go to next page') or soup.find('li', class_='pager__item--next')
                if not next_page:
                    has_next = False
                else:
                    page += 1
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error on metadata page {page}: {e}")
                break

    def _fetch_university_details(self, url):
        """
        Helper method to scrape specific details.
        Returns a dict of additional metadata.
        """
        details = {
            'address': '',
            'email': '',
            'website': '',
            'accreditation_status': '',
            'registration_no': ''
        }
        try:
            response = self.session.get(url, verify=False, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Address
            addr_label = soup.find(string=lambda t: t and "Address:" in t)
            if addr_label:
                container = addr_label.find_parent('div', class_='field')
                if container:
                    val_item = container.find(class_='field__item') or container.find(class_='field-item')
                    if val_item:
                       details['address'] = val_item.get_text(separator="\\n", strip=True)
                if not details['address']:
                    details['address'] = addr_label.parent.parent.get_text(strip=True).replace("Address:", "").strip()

            # Email
            email_label = soup.find(string=lambda t: t and "E-mail:" in t)
            if email_label:
                link = email_label.find_next('a', href=lambda h: h and 'mailto:' in h)
                if link:
                    details['email'] = link.get_text(strip=True)
                else:
                    details['email'] = email_label.parent.parent.get_text(strip=True).replace("E-mail:", "").strip()

            # Website
            web_label = soup.find(string=lambda t: t and "Website:" in t)
            if web_label:
                link = web_label.find_next('a', href=True)
                if link:
                    details['website'] = link['href']
                
            # Accreditation Status
            acc_label = soup.find(string=lambda t: t and "Accreditation Status:" in t)
            if acc_label:
                 details['accreditation_status'] = acc_label.parent.parent.get_text(strip=True).replace("Accreditation Status:", "").strip()
            
            # Registration No
            reg_label = soup.find(string=lambda t: t and "Registration No.:" in t)
            if reg_label:
                details['registration_no'] = reg_label.parent.parent.get_text(strip=True).replace("Registration No.:", "").strip()

        except Exception as e:
            logger.error(f"Error fetching detail page at {url}: {e}")
            
        return details

    def fetch_programmes(self):
        """
        Fetches all programmes by iterating through pagination.
        Yields a list of dictionaries (batch) with programme details for each page.
        """
        page = 0
        has_next = True
        consecutive_errors = 0
        
        while has_next:
            url = f"{self.PROGRAMMES_URL}?page={page}"
            logger.info(f"Fetching programmes page {page}: {url}")
            
            try:
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
                
                data_rows = [r for r in table.find_all('tr') if r.find('td')]
                
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
                
                next_page_exists = soup.find('a', title='Go to next page') or soup.find('li', class_='pager__item--next')
                
                if page > 200: 
                    logger.warning("Reached page limit 200. Stopping.")
                    break
                    
                page += 1
                consecutive_errors = 0
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                consecutive_errors += 1
                if consecutive_errors > 3:
                     logger.error("Too many consecutive errors. Stopping.")
                     break
                time.sleep(5)
