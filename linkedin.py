from lxml import etree
from datetime import datetime
import pandas as pd
from seleniumbase import SB
from ai_summarize_openrouter import summarize
import asyncio

def get_url (title, location, last_listed, work_type, experience):
    template = 'https://www.linkedin.com/jobs/search?keywords={}&location={}&geoId=103121230&f_TPR={}&f_WT={}&f_E={}&position=1&pageNum=0'
    url = template.format(title, location, last_listed, work_type, experience)
    return url

def main():
    title = 'Python'
    location = 'Philippines'
    tpr = 'r2592000' # Last listed Month: r2592000, Week: r604800, Day: r86400
    work_type = '3%2C2' # Hybrid + Remote
    experience = '2' # Entry level

    url = get_url (title, location, tpr, work_type, experience)

    with SB(uc_cdp=True, incognito=True) as sb:
        sb.open(url)
        sb.sleep(1)

        # Close login popup if it exists
        if sb.is_element_present("#base-contextual-sign-in-modal > div > section > button"):
            sb.click("#base-contextual-sign-in-modal > div > section > button")
            sb.sleep(0.25)

        end_message = "You've viewed all jobs for this search"

        while True:
            # Scroll to bottom with smooth behavior (more human-like)
            sb.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")
            sb.sleep(0.25)
            
            # Check if we've reached the end (no more content loaded)
            if sb.is_text_visible(end_message):
                break
                
            # Try to click "See More" button if it appears
            see_more_button = 'button:contains("See more jobs")'
            if sb.is_element_present(see_more_button):
                try:
                    sb.scroll_to(see_more_button)
                    sb.click(see_more_button)
                    sb.sleep(0.25)
                    continue
                except:
                    pass

        raw_html = sb.get_page_source()
        tree = etree.HTML(raw_html)
        cards = tree.xpath('//*[@id="main-content"]/section[2]/ul/li[*]/div')
        print(f"Number of jobs: {len(cards)}")

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H%M%S")

        df = pd.DataFrame()
        for i, card in enumerate (cards, start=1):
            try:
                job_title = card.xpath('.//*[@class="base-search-card__title"]')[0].text.strip()
            except Exception:
                job_title = None

            try:
                company_name = card.xpath('.//*[@class="base-search-card__subtitle"]/a')[0].text.strip()
            except Exception:
                company_name = None

            try:
                location = card.xpath('.//*[@class="job-search-card__location"]')[0].text.strip()
            except Exception:
                location = None

            try:
                date_listed = card.xpath('.//time[contains(@class, "job-search-card__listdate")]/@datetime')[0].strip()
            except Exception:
                date_listed = None

            try:
                job_url = card.xpath('.//a[@href]/@href')[0].strip()
            except Exception:
                job_url = None

            try:
                # Click job posting
                job_link_selector = f'//*[@id="main-content"]/section[2]/ul/li[{i}]//a'
                
                sb.wait_for_element_visible(job_link_selector, timeout=10)
                sb.wait_for_element_clickable(job_link_selector, timeout=10)
                sb.scroll_to(job_link_selector)
                
                try:
                    sb.click(job_link_selector)
                except:
                    sb.js_click(job_link_selector)
                
                sb.sleep(0.5)

                raw_html = sb.get_page_source()
                tree = etree.HTML(raw_html)

                # Extract full job description with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        descriptions = tree.xpath('//div[contains(@class, "show-more-less-html__markup")]//text()')
                        full_description = ' '.join(descriptions)

                        ai_response = asyncio.run(summarize(full_description))
                        ai_summary = ai_response.get("summary")
                        hard_skills = ai_response.get("hard_skills")
                        soft_skills = ai_response.get("soft_skills")
                        required_experience = ai_response.get("required_experience")
                        work_arrangement = ai_response.get("work_arrangement") 
                        break

                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed to extract full description for job {job_title}: {e}")
                        try:
                            sb.click(job_link_selector)
                        except:
                            sb.js_click(job_link_selector)
                        sb.sleep(1)
                        if attempt == max_retries - 1:
                            print("Failed to extract. None detected.")
                            ai_summary = hard_skills = soft_skills = required_experience = None

                try:
                    descriptions = tree.xpath('//div[contains(@class, "show-more-less-html__markup")]//text()')
                    full_description = ' '.join(descriptions)
                    ai_response = asyncio.run(summarize(full_description))

                    ai_summary = ai_response.get("summary")
                    hard_skills = ai_response.get("hard_skills")
                    soft_skills = ai_response.get("soft_skills")
                    required_experience = ai_response.get("required_experience")
                    work_arrangement = ai_response.get("work_arrangement")

                except Exception:
                    ai_summary = None

            except Exception as e:
                print(f"Failed to click job {i}: {str(e)}")
                continue  # Skip to next job if this one fails

            new_data = pd.DataFrame({
                'Date Listed': [date_listed],
                'Job Title': [job_title],
                'AI Summary': [ai_summary],
                'Hard Skills': [hard_skills],
                'Soft Skills': [soft_skills],
                'Required Experience': [required_experience],
                'Company Name': [company_name],
                'Location': [location],
                'Link': [job_url],
                'Date Extracted': [today],
                'Work Arrangement': [work_arrangement]
            })
            df = pd.concat([df, new_data], ignore_index=True)

    title_filename = title.strip().replace(" ", "_")
    excel_filename = f"{title_filename}_linkedin_{today}_{timestamp}.xlsx"
    df.to_excel(excel_filename, index=False)

if __name__ == '__main__':
    main()


