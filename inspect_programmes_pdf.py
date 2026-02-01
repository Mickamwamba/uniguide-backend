import requests
from bs4 import BeautifulSoup
import pdfplumber
import io

URL = "https://tcu.go.tz/services/accreditation/academic-programmes-offered-universities-tanzania"

def inspect_pdf():
    print(f"Fetching {URL}...")
    try:
        response = requests.get(URL, verify=False)
        soup = BeautifulSoup(response.content, 'lxml')
        
        pdf_links = soup.find_all('a', href=lambda h: h and h.endswith('.pdf'))
        print(f"Found {len(pdf_links)} PDF links:")
        for link in pdf_links:
            print(f"- {link.get_text(strip=True)} -> {link['href']}")
            
        if not pdf_links:
            print("No PDF links found.")
            return

        # Don't download yet, just list them.

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_pdf()
