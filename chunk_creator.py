import pandas as pd
import os

def create_csv_chunks(input_csv_file: str, chunk_size: int = 1000):
    """
    Reads a CSV file and splits it into smaller chunks of a specified size.

    Args:
        input_csv_file (str): The path to the input CSV file.
        chunk_size (int): The number of rows each chunk should have. Defaults to 1000.
    """
    # 1. Validate that the input file exists
    if not os.path.exists(input_csv_file):
        print(f"Error: Input file not found at '{input_csv_file}'")
        return

    try:
        # 2. Read the source CSV file
        df = pd.read_csv(input_csv_file)
        print(f"Successfully read '{input_csv_file}' with {len(df)} rows.")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # 3. Get the base name and directory for the output files
    input_dir = os.path.dirname(input_csv_file)
    base_filename = os.path.splitext(os.path.basename(input_csv_file))[0]
    
    # Create a new directory for the chunks named after the base filename
    output_dir = os.path.join(input_dir, base_filename)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory set to: '{output_dir}'")

    num_rows = len(df)

    # 4. Loop through the DataFrame and create chunks
    for i in range(0, num_rows, chunk_size):
        # Get the chunk of the DataFrame
        df_chunk = df.iloc[i:i+chunk_size]
        
        # Calculate the chunk number (starting from 1)
        chunk_num = i // chunk_size + 1
        
        # 5. Construct the new filename
        output_filename = f"{base_filename}_chunk_{chunk_num}.csv"
        output_path = os.path.join(output_dir, output_filename)
        
        # 6. Save the chunk to a new CSV file
        try:
            df_chunk.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"Successfully created chunk {chunk_num}: '{output_path}'")
        except Exception as e:
            print(f"Error saving chunk {chunk_num}: {e}")

if __name__ == '__main__':
    # Example usage:
    source_file = 'data\csv\_jobstreet_2025-09-13.csv'
    create_csv_chunks(source_file)
