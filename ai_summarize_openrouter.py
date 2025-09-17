import os
import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from typing import List, Optional

# Define the structured output
class JobInfo(BaseModel):
    """Information to extract from a job posting."""
    min_work_experience: Optional[int] = Field(description="Minimum years of work experience required, if any")
    max_work_experience: Optional[int] = Field(description="Maximum years of work experience required, if any")
    technical_skills: Optional[List[str]] = Field(description="List of technical skills mentioned")
    salary_type: Optional[List[str]] = Field(description="Type of salary, e.g., monthly, yearly, hourly")
    min_salary: Optional[int] = Field(description="Minimum salary if mentioned, otherwise null")
    max_salary: Optional[int] = Field(description="Maximum salary if mentioned, otherwise null")
    fresh_graduate_friendly: Optional[bool] = Field(description="True if the job is open to fresh graduates, otherwise False")
    industry: str = Field(description="The industry of the job, e.g., Information Technology, Finance. This field must always contain a value and not be empty.")

def main():
    load_dotenv()
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # LLM
    llm = ChatOpenAI(
        model="deepseek/deepseek-chat-v3.1:free",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0
    )

    # Create a structured output chain
    structured_llm = llm.with_structured_output(JobInfo)

    # Create the prompt
    prompt = ChatPromptTemplate.from_template(
        """Extract the requested information from the following job details:
        
        {job_details}
        """
    )

    # Create the chain
    chain = prompt | structured_llm

    # Hardcoded CSV file
    dir_name = "_jobstreet_2025-09-13"
    base_path = f"data/csv/{dir_name}"
    chunk_number = 27

    input_csv_file = f"{base_path}/{dir_name}_chunk_{chunk_number}.csv"
    
    # Construct the output filename
    input_filename = os.path.basename(input_csv_file)
    output_csv_file = f"{base_path}/ai_openrouter_{input_filename}"
    
    if not os.path.exists(input_csv_file):
        print(f"CSV file not found: {input_csv_file}")
        return

    print(f"Processing file: {input_csv_file}")
    df = pd.read_csv(input_csv_file)

    # Lists to store extracted data
    min_work_experiences = []
    max_work_experiences = []
    technical_skills_list = []
    salary_types = []
    min_salaries = []
    max_salaries = []
    fresh_graduate_friendly_list = []
    industries = []

    # Process each job detail
    for index, row in df.iterrows():
        job_details = row["job_details"]
        
        # Skip if job_details is empty or not a string
        if not isinstance(job_details, str) or not job_details.strip():
            min_work_experiences.append(None)
            max_work_experiences.append(None)
            technical_skills_list.append(None)
            min_salaries.append(None)
            max_salaries.append(None)
            fresh_graduate_friendly_list.append(None)
            industries.append(None)
            continue

        print(f"--- Processing Job: {row['job_title']} ---")
        
        try:
            # Invoke the chain
            result = chain.invoke({"job_details": job_details})
            
            # Append results to lists
            min_work_experiences.append(result.min_work_experience)
            max_work_experiences.append(result.max_work_experience)
            technical_skills_list.append(result.technical_skills)
            salary_types.append(result.salary_type)
            min_salaries.append(result.min_salary)
            max_salaries.append(result.max_salary)
            fresh_graduate_friendly_list.append(result.fresh_graduate_friendly)
            industries.append(result.industry)

            # Print the structured output
            print(f"Min Work Experience: {result.min_work_experience}")
            print(f"Max Work Experience: {result.max_work_experience}")
            print(f"Technical Skills: {result.technical_skills}")
            print(f"Salary Type: {result.salary_type}")
            print(f"Min Salary: {result.min_salary}")
            print(f"Max Salary: {result.max_salary}")
            print(f"Fresh Graduate Friendly: {result.fresh_graduate_friendly}")
            print(f"Industry: {result.industry}")
            print("-" * 20)

        except Exception as e:
            print(f"Could not process job details for '{row['job_title']}': {e}")
            min_work_experiences.append(None)
            max_work_experiences.append(None)
            technical_skills_list.append(None)
            salary_types.append(None)
            min_salaries.append(None)
            max_salaries.append(None)
            fresh_graduate_friendly_list.append(None)
            industries.append(None)

    # Add new columns to the DataFrame
    df['min_work_experience'] = min_work_experiences
    df['max_work_experience'] = max_work_experiences
    df['technical_skills'] = technical_skills_list
    df['salary_type'] = salary_types
    df['min_salary'] = min_salaries
    df['max_salary'] = max_salaries
    df['fresh_graduate_friendly'] = fresh_graduate_friendly_list
    df['industry'] = industries

    # Save to a new CSV file
    df.to_csv(output_csv_file, index=False, encoding="utf-8-sig")
    print(f"\nProcessed data saved to {output_csv_file}")


if __name__ == "__main__":
    main()
