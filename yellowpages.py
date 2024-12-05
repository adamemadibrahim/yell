import pandas as pd
import requests
import csv
import re
from bs4 import BeautifulSoup

# Function to extract all contact details with correct formatting
def extract_contact_details(soup):
    try:
        contact_container = soup.select_one('div.primary-contacts-container')
        if not contact_container: 
            return 'No contact details found'
        
        contacts = []
        # Extract all contact methods from div.contact and a.contact
        contact_methods = contact_container.select('div.contact, a.contact')

        for method in contact_methods:
            contact_type = method.get('title', 'Unknown').strip()
            contact_value = method.select_one('div.desktop-display-value')

            if contact_value:
                contact_value_text = contact_value.get_text(strip=True)
                
                # Handle special cases for email and website
                if contact_type.lower() == 'fax':
                    contacts.append(f"Fax: {contact_value_text}")
                elif 'email' in contact_type.lower():
                    # Extract email from the title attribute
                    email_address = method.get('title', '').split(' ')[-1]
                    if email_address:
                        contacts.append(f"Email: {email_address}")
                elif 'phone' in contact_type.lower():
                    contacts.append(f"Phone: {contact_value_text}")
                else:
                    contacts.append(f"{contact_value_text}: {contact_type}")
        
        return '; '.join(contacts) if contacts else 'No contact details found'
    except Exception as e:
        return f"Error occurred: {e}"

# Function to extract location
def extract_location(soup):
    try:
        location_tag = soup.select_one('div.listing-address.mappable-address')
        return location_tag.get_text(strip=True) if location_tag else 'No location found'
    except Exception as e:
        return f"Error occurred: {e}"

# Function to extract category
def extract_category(soup):
    try:
        category_tag = soup.select_one('h2.listing-heading a')
        return category_tag.get_text(strip=True) if category_tag else 'No category found'
    except Exception as e:
        return f"Error occurred: {e}"

def extract_about_and_products(soup):
    about_us = "No information available"
    products_services = "No information available"

    try:
        # Extract 'About Us' content
        about_us_section = soup.select_one("div.about-us-content")
        if about_us_section:
            # Get all text content from the section
            about_us = about_us_section.get_text(separator="\n", strip=True)

        # Extract 'Products and Services' content
        products_section = soup.select_one("div.products-and-services")
        if products_section:
            # Get all text content from the section
            products_services = products_section.get_text(separator="\n", strip=True)

    except Exception as e:
        print(f"Error extracting About Us or Products and Services: {e}")

    return about_us, products_services


# Function to parse business data from a single page
def parse_business_data(soup):
    data = []
    business_cards = soup.select('div.Box__Div-sc-dws99b-0.fYIHHU > a > h3')  # CSS selector for business name

    for card in business_cards:
        name = card.get_text(strip=True) if card else None
        parent_link = card.find_parent('a', href=True)
        link = parent_link['href'] if parent_link else None

        if link:
            if not link.startswith(('http://', 'https://')):
                link = 'https://www.yellowpages.com.au' + link  # Prepend base URL
            
            # Visit business detail page
            response = requests.get(link)
            if response.status_code == 200:
                detail_soup = BeautifulSoup(response.text, 'html.parser')
                contact_details = extract_contact_details(detail_soup)
                location = extract_location(detail_soup)
                category = extract_category(detail_soup)
                about_us, products_services = extract_about_and_products(detail_soup)

                data.append({
                    'Business Name': name,
                    'Link': link,
                    'Contact Details': contact_details,
                    'Location': location,
                    'Category': category,
                    'About Us': about_us,
                    'Products and Services': products_services
                })
    
    return data

# Function to scrape a single page and return soup
def fetch_page_soup(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        print(f"Failed to fetch {url}: Status code {response.status_code}")
        return None

def scrape_pages(base_url):
    all_data = []
    current_url = base_url
    page = 1  # Start at page 1

    while True:
        print(f"Scraping page {page}")
        soup = fetch_page_soup(current_url)
        if soup:
            # Scrape the current page
            all_data.extend(parse_business_data(soup))

            # Look for the div with display="flex" that contains the "Next" button
            next_button_div = soup.find('div', {'display': 'flex'})
            
            if next_button_div:
                # Within that div, look for the "Next" button with the text "Next"
                next_button = next_button_div.find('span', class_='MuiButton-label', string="Next")

                if next_button:
                    # Find the parent 'a' tag with the href attribute for the next page
                    next_page_tag = next_button.find_parent('a', href=True)
                    if next_page_tag:
                        # Update the current URL to the next page
                        current_url = 'https://www.yellowpages.com.au' + next_page_tag['href']
                        page += 1  # Increment page counter
                        print(f"Moving to page {page}")
                    else:
                        print("Error: Next page URL is missing.")
                        break  # Exit if the "Next" button link is not found
                else:
                    print("No 'Next' button found within the flex container.")
                    break  # Exit if no "Next" button is found inside the flex container
            else:
                print("No 'flex' container found with the 'Next' button.")
                break  # Exit if no flex container is found

        else:
            print("Failed to fetch the page.")
            break  # Stop if the page cannot be fetched

    return all_data

# Function to parse contact details and extract specific contact types dynamically
def split_contact_details_dynamic(row):
    details = row.get("Contact Details", "")
    contact_types = {}
    
    for detail in details.split(';'):
        detail = detail.strip()
        if ':' in detail:
            key, value = detail.split(':', 1)
            contact_types[key.strip()] = value.strip()
    
    return pd.Series(contact_types)

# Function to check and split the location dynamically
def split_location(location):
    # If no location is found, return all parts as 'N/A'
    if location == 'No location found' or pd.isna(location):
        return ['N/A', 'N/A', 'N/A', 'N/A']
    
    # Regular expression for handling full address (Street, Suburb, State, Postcode)
    location_pattern = r'^(.*?),\s*([A-Za-z\s]+)\s+([A-Za-z]{2,3})\s*(\d{4})$'
    match = re.match(location_pattern, location.strip())
    
    if match:
        # If full address is matched, return all parts
        street = match.group(1).strip()
        suburb = match.group(2).strip()
        state = match.group(3).strip()
        postcode = match.group(4).strip()
        return [street, suburb, state, postcode]
    
    # Handle case where only Suburb, State, and Postcode are provided (no Street)
    location_pattern_no_street = r'^[A-Za-z\s]+,\s*([A-Za-z\s]+)\s+([A-Za-z]{2,3})\s*(\d{4})$'
    match_no_street = re.match(location_pattern_no_street, location.strip())
    
    if match_no_street:
        suburb = match_no_street.group(1).strip()
        state = match_no_street.group(2).strip()
        postcode = match_no_street.group(3).strip()
        return ['N/A', suburb, state, postcode]
    
    # Handle case where only Suburb and State are present (missing Postcode)
    location_pattern_suburb_state = r'^[A-Za-z\s]+,\s*([A-Za-z\s]+)\s+([A-Za-z]{2,3})$'
    match_suburb_state = re.match(location_pattern_suburb_state, location.strip())
    
    if match_suburb_state:
        suburb = match_suburb_state.group(1).strip()
        state = match_suburb_state.group(2).strip()
        return ['N/A', suburb, state, 'N/A']
    
    # Handle case where only Suburb and Postcode are present (missing State)
    location_pattern_suburb_postcode = r'^[A-Za-z\s]+,\s*([A-Za-z\s]+)\s*(\d{4})$'
    match_suburb_postcode = re.match(location_pattern_suburb_postcode, location.strip())
    
    if match_suburb_postcode:
        suburb = match_suburb_postcode.group(1).strip()
        postcode = match_suburb_postcode.group(2).strip()
        return ['N/A', suburb, 'N/A', postcode]
    
    # If none of the patterns match, return the location as Street and N/A for others
    return ["N/A", 'N/A', 'N/A', 'N/A']

# Function to save data to CSV
def save_to_csv(data, industry, job_title, file_name='output.csv'):
    try:
        # Adding Industry and Job Title to each row at the beginning
        for row in data:
            row['Industry'] = industry
            row['Job Title'] = job_title

        # Convert to DataFrame and dynamically split contact details into separate columns
        df = pd.DataFrame(data)
        contact_columns = df.apply(split_contact_details_dynamic, axis=1)
        df = pd.concat([df.drop(columns=["Contact Details"]), contact_columns], axis=1)
        
        # Ensure email, website, and phone columns exist even if not present in the data
        contact_types = ['Email', 'Website', 'Phone']
        for col in contact_types:
            if col not in df.columns:
                df[col] = None

        # Filter website column to remove unwanted text (e.g., "(opens in a new window)")
        df['Website'] = df['Website'].apply(lambda x: re.sub(r'\s*\(.*\)\s*', '', str(x)))

        # Replace pd.NA, 'nan', or empty strings with "N/A"
        df['Website'] = df['Website'].apply(lambda x: "N/A" if pd.isna(x) or str(x).lower() == 'nan' or x.strip() == "" else x)

        # Replace NaN values in Email, Website, and Phone with "N/A"
        df[contact_types] = df[contact_types].fillna("N/A")

        # Keep only the 'Full Location' column
        df['Full Location'] = df['Location']
        df = df.drop(columns=['Location'])  # Drop the 'Location' column if unnecessary

        # Define the desired order of columns
        column_order = [
            'Industry', 'Job Title', 'Business Name', 'Link',
            'Email', 'Website', 'Phone', 'Full Location',
            'Category', 'About Us', 'Products and Services'
        ]
        # Include any other dynamic columns that may exist
        column_order += [col for col in df.columns if col not in column_order]

        # Reorder columns
        df = df.reindex(columns=column_order)

        # Writing to CSV
        df.to_csv(file_name, index=False, encoding='utf-8')
        print(f"Data saved to {file_name}")
    except Exception as e:
        print(f"An error occurred while saving to CSV: {e}")


        
def process_first_two_urls(file_path, column_name):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path, sheet_name=0)
        if column_name in df.columns:
            urls = df[column_name].dropna().iloc[:2]  # Get the first two non-NaN URLs
            industries = df['Industry'].dropna().iloc[:2]  # Get the corresponding industries
            job_titles = df['Job Title'].dropna().iloc[:2]  # Get the corresponding job titles
            
            for idx, (url, industry, job_title) in enumerate(zip(urls, industries, job_titles), start=1):
                print(f"Processing URL {idx}: {url}")
                data = scrape_pages(url)  # Scrape data for the current URL
                output_file = f"output_{idx}.csv"  # Generate a file name for each URL
                save_to_csv(data, industry, job_title, file_name=output_file)
        else:
            print(f"Column '{column_name}' not found in the Excel file.")
    except Exception as e:
        print(f"An error occurred while processing the Excel file: {e}")

# Example usage
excel_file = "Copy of Yellow Pages Phase 1 Links Adam.xlsx"  # Update with your Excel file path
url_column = "Yellow Pages Links"  # Update with the column name containing URLs
process_first_two_urls(excel_file, url_column)
