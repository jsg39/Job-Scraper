from curl_cffi import requests
from bs4 import BeautifulSoup
import pandas as pd
import math
from datetime import datetime, timedelta
import re
import time
import os

def clean_text(text):
    if not isinstance(text, str):
        return text
    return text.replace("\n", " ").replace("\r", " ").strip()

def main():
    root_url = "https://ph.jobstreet.com"
    job_title = "" # 
    location = "Philippines"

    # Prepare filename
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    title_filename = job_title.strip().replace(" ", "_")
    filename = f"data/csv/{title_filename}_jobstreet_{today}.csv"

    # First page
    base_url = f"{root_url}/{job_title}jobs/in-{location.replace(' ', '-')}"
    url = base_url + "?page=1"
    response = requests.get(url, impersonate="chrome")
    soup = BeautifulSoup(response.text, 'lxml')

    # Find total number of jobs
    total_jobs_tag = soup.find("div", {"data-automation": "totalJobsMessage"})
    if total_jobs_tag:
        total_jobs = int(total_jobs_tag.get_text(strip=True).split()[0].replace(",", ""))
    else:
        total_jobs = 0

    # Calculate last page
    jobs_per_page = 32 # Check HTML
    last_page = math.ceil(total_jobs / jobs_per_page)
    print(f"Last Page: {last_page}")

    for page in range(1, last_page + 1):
        page_url = base_url + f"?page={page}"
        print(f"Scraping: {page_url}")

        # Fetch HTML
        response = requests.get(page_url, impersonate="chrome")
        soup = BeautifulSoup(response.text, 'lxml')

        # Find all job cards
        job_cards = soup.find_all("article", {"data-card-type": "JobCard"})

        rows = []
        # Parse inside each card
        for card in job_cards:
            title_tag = card.find("a", {"data-automation": "jobTitle"})
            company_tag = card.find("a", {"data-automation": "jobCompany"})
            location_tags = card.find_all("a", {"data-automation": "jobLocation"})
            work_arrangement_tag = card.find("span", {"data-testid": "work-arrangement"})
            date_tag = card.find("span", {"data-automation": "jobListingDate"})

            title = title_tag.get_text(strip=True) if title_tag else None
            company = company_tag.get_text(strip=True) if company_tag else None
            locations = [loc.get_text(strip=True) for loc in location_tags] if location_tags else None
            work_arrangement = work_arrangement_tag.get_text(strip=True) if work_arrangement_tag else None
            
            # Find date
            text = date_tag.get_text(strip=True)
            match = re.search(r"\d+", text)
            if match:
                days_ago = int(match.group())
                date = (datetime.today() - timedelta(days=days_ago)).date()
            
            # Job details
            job_details_url = root_url + title_tag["href"]

            # Fetch job detail
            job_details_response = requests.get(job_details_url, impersonate="chrome")
            job_details_soup = BeautifulSoup(job_details_response.text, 'lxml')

            # Find job details
            job_details_tag = job_details_soup.find_all("div", {"data-automation": "jobAdDetails"})
            job_details = [details.get_text(strip=True) for details in job_details_tag]

            # Data Structuring
            rows.append({
                "date_listed": clean_text(date),
                "job_title": clean_text(title),
                "company": clean_text(company),
                "location": clean_text(locations),
                "work_arrangement": clean_text(work_arrangement),
                "link": clean_text(job_details_url),
                "job_details": clean_text(job_details)
            })

        # Create a DataFrame for the current page
        df_page = pd.DataFrame(rows)
        if df_page.empty:
            print(f"No jobs found on page {page}")
            continue

        # If file exists, load existing data then combine and drop duplicates; otherwise use new data.
        if os.path.exists(filename):
            df_existing = pd.read_csv(filename, encoding="utf-8-sig")
            df_combined = pd.concat([df_existing, df_page], ignore_index=True)
            # Assuming each job card is unique by its link
            df_combined = df_combined.drop_duplicates(subset=["link"])
        else:
            df_combined = df_page.drop_duplicates(subset=["link"])
        
        # Write the deduplicated DataFrame back to CSV
        df_combined.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Page {page} processed and saved to {filename}")

if __name__ == '__main__':
    start = time.perf_counter()
    main()
    end = time.perf_counter()
    print(f"Execution time: {end - start:.6f} seconds")