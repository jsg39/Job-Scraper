from bs4 import BeautifulSoup
from seleniumbase import SB
import pandas as pd
from datetime import datetime
from ai_summarize_openrouter import summarize
import asyncio

def get_url (root_url, job_title, location, last_listed, job_type):
    template = '{}/jobs?q={}&l={}&fromage={}&sort=date&sc={}'
    url = template.format(root_url,job_title, location, last_listed, job_type)
    return url

def bypass_cloudflare(sb, url):
    """Bypass Cloudflare protection using SeleniumBase."""
    while True:
        sb.open(url)
        sb.uc_gui_click_captcha()
        sb.sleep(10)

        try:
            sb.assert_text("Find jobs", "button.yosegi-InlineWhatWhere-primaryButton[type='submit']")
            print("Bypassed Cloudflare")
            break
        except Exception:
            print("Bypassing Cloudflare...")
            continue

def main():
    root_url = "https://ph.indeed.com"
    title = 'Python'
    location = 'Philippines'
    last_listed = '7'
    # job_type = '0kf%3Aattr%287EQCZ%29%3B' # Fresh Grad
    job_type = '' # Any

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")

    df = pd.DataFrame()

    #  Initial url
    url = get_url(root_url, title, location, last_listed, job_type)

    with SB(uc_cdp=True, incognito=True) as sb:
        while True:
            bypass_cloudflare(sb, url)

            raw_html = sb.get_page_source()
            soup = BeautifulSoup(raw_html, 'lxml')
            cards = soup.find_all('div', 'job_seen_beacon')
            
            for card in cards:
                td_tag = card.table.tbody.tr.td
                
                # Job Title and URL
                try:
                    job_a = td_tag.find('a', {'class', 'jcs-JobTitle css-1baag51 eu4oa1w0'})
                    href = job_a.get('href')

                    # Click the card
                    selector = f'a[href="{href}"]'
                    sb.click(selector)
                    sb.sleep(2)

                    # Updated html
                    raw_html = sb.get_page_source()
                    soup = BeautifulSoup(raw_html, 'lxml')

                    job_title = job_a.span.get('title')
                    job_url = root_url + href
                except AttributeError:
                    job_title = None
                    job_url = None

                # Company Name
                try:
                    company_div = td_tag.find('div', {'class','company_location css-i375s1 e37uo190'})
                    company_name = company_div.find('div', {'class','css-1afmp4o e37uo190'}).span.text.strip()
                except AttributeError:
                    company_name = None

                # Company Location
                try:
                    company_location = company_div.find('div', {'class','css-1restlb eu4oa1w0'}).text.strip()
                except Exception:
                    company_location = None

                # Salary Range
                # try:
                #     metadata_div = td_tag.find('div', {'class','jobMetaDataGroup css-qspwa8 eu4oa1w0'}).ul
                #     salary_range = metadata_div.find('li', {'class','css-u74ql7 eu4oa1w0'}).div.div.text.strip()
                # except AttributeError:
                #     salary_range = None

                # Summary (quick preview)
                try:
                    summary = card.find('div',{'class', 'underShelfFooter'}).div.div.ul.li.text.strip()
                except AttributeError:
                    summary = None

                # Extract full job description
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        descriptions = soup.find('div', id='jobDescriptionText')
                        full_description = descriptions.get_text(separator=' ', strip=True) if descriptions else ""

                        ai_response = asyncio.run(summarize(full_description))
                        ai_summary = ai_response.get("summary")
                        hard_skills = ai_response.get("hard_skills")
                        soft_skills = ai_response.get("soft_skills")
                        required_experience = ai_response.get("required_experience")
                        work_arrangement = ai_response.get("work_arrangement")
                        salary_range = ai_response.get("salary_range")

                        break
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed to extract full description for job {job_title}: {e}")
                        try:
                            sb.click(selector)
                        except:
                            sb.js_click(selector)
                        sb.sleep(1)
                        if attempt == max_retries - 1:
                            print("Failed to extract. None detected.")
                            ai_summary = hard_skills = soft_skills = required_experience = None
                          
                new_data = pd.DataFrame({
                    'Job Title': [job_title], #
                    'Summary': [summary], #TODO
                    'AI Summary': [ai_summary], #TODO
                    'Hard Skills': [hard_skills], #TODO
                    'Soft Skills': [soft_skills], #TODO
                    'Required Experience': [required_experience], #TODO
                    'Company Name': [company_name], #
                    'Location': [company_location], #
                    'Link': [job_url], #
                    'Date Extracted': [today], #
                    'Salary Range': [salary_range], #TODO
                    'Work Arrangement': [work_arrangement] #TODO
                })
                df = pd.concat([df, new_data], ignore_index=True)

            # Move to next page
            try:
                url = root_url + soup.find('a', {'aria-label':'Next Page'}).get('href')
            except AttributeError:
                break
            
    title_filename = title.strip().replace(" ", "_")
    excel_filename = f"{title_filename}_indeed_{today}_{timestamp}.xlsx"
    df.to_excel(excel_filename, index=False)

if __name__ == '__main__':
    main()