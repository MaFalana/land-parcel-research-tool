import requests
import os
import shutil
import openpyxl
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BEACON_URL = 'https://beacon.schneidercorp.com/Application.aspx?AppID=173&LayerID=2165&PageTypeID=2&PageID=1119'
BEACON_BASE_URL = 'https://beacon.schneidercorp.com/Application.aspx?AppID=173&LayerID=2165&PageTypeID=4&PageID=1121&Q=2061740127&KeyValue='
parcel_ID = '90-08-04-539-122.000-004'  # Example parcel ID

pw = sync_playwright().start()

browser = pw.chromium.launch(headless=False)  # Set headless=True to run in the background

page = browser.new_page()
page.goto(BEACON_URL)
page.click('text=Agree') # Click agree button

def main():
    

    search_beacon(parcel_ID)
    browser.close()

    # Fill in the form

def search_beacon(parcel_ID):

    page.fill('input#ctlBodyPane_ctl03_ctl01_txtParcelID', parcel_ID) # Fill in the search form with the parcel ID
    
    page.press('input#ctlBodyPane_ctl03_ctl01_txtParcelID', 'Enter') # Press enter to submit the form
    
    legal_desc = page.inner_text('span#ctlBodyPane_ctl02_ctl01_lblLegalDescription') # Get Legal Description from Property Details page
  
	
    # Get the latest transfer info from the Transfers table (first row) (date, document number or book/page)
    latest_transfer_date = page.inner_text('table#ctlBodyPane_ctl09_ctl01_gvwTransferHistory tbody tr:nth-child(1) th') # Get latest transfer date
    document_number_or_book_page = page.inner_text('table#ctlBodyPane_ctl09_ctl01_gvwTransferHistory tbody tr:nth-child(1) td:nth-child(3)') # Get document number or book/page
	

    prc_link = page.get_attribute('a#ctlBodyPane_ctl17_ctl01_prtrFiles_ctl00_prtrFiles_Inner_ctl00_hlkName', 'href') # get latest Property Record Card link

    print(f'Property Record Card link: {prc_link}')
    print(f'Legal Description: {legal_desc}')
    print(f'Latest Transfer Date: {latest_transfer_date}')
    print(f'Document Number or Book/Page: {document_number_or_book_page}')

    return prc_link


def search_beacon2(parcel_ID):
    page.fill('input#topSearchControl', parcel_ID) # Fill in the search form with the parcel ID

    page.press('input#ctlBodyPane_ctl03_ctl01_txtParcelID', 'Enter') # Press enter to submit the form

    prc_link = page.get_attribute('a#ctlBodyPane_ctl17_ctl01_prtrFiles_ctl00_prtrFiles_Inner_ctl00_hlkName', 'href') # get latest Property Record Card link

    print(f'Property Record Card link: {prc_link}')

    return prc_link
    

if __name__ == "__main__":
    main()