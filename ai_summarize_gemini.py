import os
import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Optional
import json
from langchain_core.output_parsers import StrOutputParser
import time

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
    # Load environment variables. Ensure GOOGLE_API_KEY is in your .env file
    load_dotenv()

    # --- Change: Instantiate the ChatGoogleGenerativeAI model ---
    # The API key is automatically read from the GOOGLE_API_KEY environment variable
    llm = ChatGoogleGenerativeAI(
        model="gemma-3-27b-it",
        temperature=0
    )

    # --- WORKAROUND ---
    # 1. Define the desired JSON structure in the prompt itself.
    json_schema = JobInfo.schema_json(indent=2)
    prompt = ChatPromptTemplate.from_template(
        """Extract the requested information from the following job details.
        Return your response as a valid JSON object that conforms to this JSON schema:
        
        ```json
        {json_schema}
        ```

        Job Details:
        {job_details}
        """
    )

    # 2. Create a chain that just returns the raw string output from the model.
    chain = prompt | llm | StrOutputParser()

    # --- Input/Output file handling ---
    dir_name = "_jobstreet_2025-09-13"
    base_path = f"data/csv/{dir_name}"

    # Loop from chunk 1 to a maximum of 14
    starting_chunk = 17
    ending_chunk = starting_chunk + 14 # Max free requests per day

    for chunk_number in range(starting_chunk, ending_chunk):
        print(f"\n{'='*20} Starting Chunk {chunk_number} {'='*20}")

        input_csv_file = f"{base_path}/{dir_name}_chunk_{chunk_number}.csv"
        
        # Stop if the next chunk file doesn't exist
        if not os.path.exists(input_csv_file):
            print(f"Chunk {chunk_number} not found. Ending process.")
            break

        # Construct the output filename
        input_filename = os.path.basename(input_csv_file)
        output_csv_file = f"{base_path}/ai_gemini_{input_filename}"
        
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
        for _, row in df.iterrows():
            job_details = row["job_details"]
            
            if not isinstance(job_details, str) or not job_details.strip():
                min_work_experiences.append(None)
                max_work_experiences.append(None)
                technical_skills_list.append(None)
                salary_types.append(None)
                min_salaries.append(None)
                max_salaries.append(None)
                fresh_graduate_friendly_list.append(None)
                industries.append(None)
                continue

            print(f"--- Processing Job: {row['job_title']} ---")
            
            try:
                # 3. Invoke the chain and manually parse the JSON output.
                response_str = chain.invoke({"job_details": job_details, "json_schema": json_schema})
                
                # Clean the response to extract only the JSON block
                json_str = response_str.strip().removeprefix("```json").removesuffix("```").strip()
                
                data = json.loads(json_str)
                result = JobInfo(**data) # Validate data with Pydantic model
                
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

            # Rate Limiting
            time.sleep(8)

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
        print(f"\nProcessed data for chunk {chunk_number} saved to {output_csv_file}")
        print(f"{'='*20} Finished Chunk {chunk_number} {'='*20}")


if __name__ == "__main__":
    main()
