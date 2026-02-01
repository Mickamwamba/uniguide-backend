import requests
from bs4 import BeautifulSoup
import logging
import time
from ..models import University

logger = logging.getLogger(__name__)

class UniversityMetadataScraper:
    BASE_URL = "https://tcu.go.tz/services/accreditation/universities-registered-tanzania"
    
    def __init__(self):
        self.session = requests.Session()
        retries = requests.adapters.Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

    def scrape_metadata(self):
        """
        Iterates through the registered universities list and fetches details for each.
        Updates existing University records or creates new ones.
        """
        page = 0
        has_next = True
        
        while has_next:
            url = f"{self.BASE_URL}?page={page}"
            logger.info(f"Scraping University List Page {page}: {url}")
            
            try:
                response = self.session.get(url, verify=False, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'lxml')
                
                table = soup.find('table')
                if not table:
                    logger.warning(f"No table on page {page}. Stopping.")
                    break
                
                # Rows with data
                rows = [r for r in table.find_all('tr') if r.find('td')]
                if not rows:
                    logger.info("No data rows found. Stopping.")
                    break

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 6:
                        continue
                        
                    # Extract List Data
                    # Col 1: Name
                    name = cols[1].get_text(strip=True)
                    # Col 2: Head Office
                    head_office = cols[2].get_text(strip=True)
                    # Col 3: Type
                    uni_type = cols[3].get_text(strip=True)
                    # Col 4: Status
                    status = cols[4].get_text(strip=True)
                    
                    # Col 5: Action (contains link to details)
                    view_link = cols[5].find('a')
                    detail_url = None
                    if view_link and 'href' in view_link.attrs:
                        # Construct full URL if relative
                        href = view_link['href']
                        if href.startswith('http'):
                            detail_url = href
                        elif href.startswith('/'):
                            detail_url = f"https://tcu.go.tz{href}"
                        else:
                            # Relative execution from current path, but safer to prepend base domain path
                            # The listing is at /services/accreditation/...
                            # The link is usually sibling or root relative.
                            # Browser agent showed link: https://tcu.go.tz/services/accreditation/academic-programmes...
                            # But wait, the href might be just "academic-programmes..."
                            # Let's verify base. The page is at /services/accreditation/universities-registered-tanzania
                            # So relative path "academic-programmes..." goes to /services/accreditation/academic-programmes...
                            # But simpler to just check if it's the expected path.
                            detail_url = f"https://tcu.go.tz/services/accreditation/{href}"
                            
                    # Get or Create University
                    # We accept that names might slightly differ from previous scrape, 
                    # but usually they are the same source.
                    university, created = University.objects.get_or_create(
                        name=name,
                        defaults={
                            'head_office': head_office,
                            'university_type': uni_type,
                            'status': status
                        }
                    )
                    
                    # If not created, update the basic list info
                    if not created:
                        university.head_office = head_office
                        university.university_type = uni_type
                        university.status = status
                        university.save()
                        
                    # Fetch Details if link exists
                    if detail_url:
                        self.fetch_university_details(university, detail_url)
                        
                # Pagination Check
                next_page = soup.find('a', title='Go to next page') or soup.find('li', class_='pager__item--next')
                if not next_page:
                    has_next = False
                else:
                    page += 1
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                break

    def fetch_university_details(self, university, url):
        """
        Visits the details page to extract Address, Email, etc.
        """
        logger.info(f"Fetching details for {university.name}...")
        try:
            response = self.session.get(url, verify=False, timeout=30)
            soup = BeautifulSoup(response.content, 'lxml')
            
            # The details are likely in the "Institution Details" section.
            # Based on browser agent, keys are labels like "Address:", "E-mail:", etc.
            # We can look for text nodes or specific markup.
            # A common pattern in Drupal/CMS sites is `div.field` or similar, 
            # but let's try searching by Label Text.
            
            def extract_field(label_text):
                # Find element containing the label
                # Note: The browser agent saw them "Next to" the label.
                # Could be a <strong>Label:</strong> Value pattern or table.
                # Regex might be safer if structure varies.
                label_node = soup.find(string=lambda t: t and label_text in t)
                if label_node:
                    # Try to find the value in the next sibling or parent's next sibling
                    # Inspecting the parent might be safer
                    parent = label_node.parent
                    
                    # Case 1: Label is in a <th> or <td>, value in next <td>
                    if parent.name in ['th', 'td', 'dt']:
                        next_sib = parent.find_next_sibling()
                        if next_sib:
                            return next_sib.get_text(strip=True)
                            
                    # Case 2: Label is <strong>Label:</strong> Value (inside same block or next text node)
                    # We might get the whole text of parent and split
                    full_text = parent.get_text(strip=True)
                    if ':' in full_text:
                        parts = full_text.split(':', 1)
                        if len(parts) > 1:
                            return parts[1].strip()
                            
                    # Case 3: Value follows the element immediately in DOM
                    next_text = label_node.find_next(string=True)
                    if next_text:
                         return next_text.strip()
                         
                return ""

            # Attempt extraction with specific labels
            address = ""
            email = ""
            website = ""
            accreditation = ""
            reg_no = ""
            
            # Since structure is unknown, let's try a generic text search strategy within the content area if possible
            # But let's assume the labels are relatively distinct.
            
            # Using find_next approach for robustness if markup varies
            # Address
            addr_label = soup.find(string=lambda t: t and "Address:" in t)
            if addr_label:
                # Usually address might be multiline or in a div next to it
                # Let's try to get the parent's next sibling text or the text after the label
                # Getting the whole text of the container might be easier?
                # Browser agent suggests "Next to 'Address:' label"
                # Let's assume standard field-label field-item structure
                container = addr_label.find_parent('div', class_='field') # Common in Drupal
                if container:
                    val_item = container.find(class_='field__item') or container.find(class_='field-item')
                    if val_item:
                       address = val_item.get_text(separator="\n", strip=True)

                if not address:
                    # Fallback
                    address = addr_label.parent.parent.get_text(strip=True).replace("Address:", "").strip()

            university.address = address

            # Email
            email_label = soup.find(string=lambda t: t and "E-mail:" in t)
            if email_label:
                # Value might be in a mailto link
                link = email_label.find_next('a', href=lambda h: h and 'mailto:' in h)
                if link:
                    email = link.get_text(strip=True)
                else:
                    email = email_label.parent.parent.get_text(strip=True).replace("E-mail:", "").strip()
            
            university.email = email

            # Website
            web_label = soup.find(string=lambda t: t and "Website:" in t)
            if web_label:
                link = web_label.find_next('a', href=True)
                if link:
                    website = link['href']
            
            if website:
                university.website = website
                
            # Accreditation
            acc_label = soup.find(string=lambda t: t and "Accreditation Status:" in t)
            if acc_label:
                 accreditation = acc_label.parent.parent.get_text(strip=True).replace("Accreditation Status:", "").strip()
            
            university.accreditation_status = accreditation

            # Registration No
            reg_label = soup.find(string=lambda t: t and "Registration No.:" in t)
            if reg_label:
                reg_no = reg_label.parent.parent.get_text(strip=True).replace("Registration No.:", "").strip()
                
            university.registration_no = reg_no
            
            university.save()
            logger.info(f"Updated metadata for {university.name}")
            
        except Exception as e:
            logger.error(f"Error fetching details for {university.name}: {e}")
