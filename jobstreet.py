from curl_cffi import requests
from bs4 import BeautifulSoup
import pandas as pd
import math
from datetime import datetime, timedelta
import re

def main():
    root_url = "https://ph.jobstreet.com"
    job_title = "Python"
    location = "Philippines"

    rows = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    # First page
    base_url = f"{root_url}/{job_title}-jobs/in-{location.replace(' ', '-')}"
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
    last_page = 1
    # last_page = math.ceil(total_jobs / jobs_per_page)
    print(f"Last Page: {last_page}")

    for page in range(1, last_page + 1):
        page_url = base_url + f"?page={page}"
        print(f"Scraping: {page_url}")

        # Fetch HTML
        response = requests.get(url, impersonate="chrome")
        soup = BeautifulSoup(response.text, 'lxml')

        # Find all job cards
        job_cards = soup.find_all("article", {"data-card-type": "JobCard"})

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
                "Date Listed": date,
                "Job Title": title,
                "Company": company,
                "Location": locations,
                "Work Arrangement": work_arrangement,
                "Link": job_details_url,
                "Job Details": job_details
            })

    df = pd.DataFrame(rows)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")

    title_filename = job_title.strip().replace(" ", "_")
    filename = f"{title_filename}_jobstreet_{today}_{timestamp}"
    # df.to_excel(filename, index=False)
    df.to_csv(f"data/csv/{filename}", index=False)
    print(f"File name: {filename}")

if __name__ == '__main__':
    main()
