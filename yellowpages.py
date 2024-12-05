def process_all_urls(file_path, column_name):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path, sheet_name=0)
        if column_name in df.columns:
            urls = df[column_name].dropna()  # Get all non-NaN URLs
            industries = df['Industry'].dropna()  # Get the corresponding industries
            job_titles = df['Job Title'].dropna()  # Get the corresponding job titles

            # Ensure there is a one-to-one correspondence for all rows
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
process_all_urls(excel_file, url_column)
