# annotate and merge PDF files

# import necessary modules  e.g. PyMuPDF
import os
import fitz


# Define the directory where the PDF files are located (use script's directory)
pdf_directory = os.path.dirname(os.path.abspath(__file__))

# Create a new folder to store the annotated PDF files
annotated_directory = os.path.join(pdf_directory, 'annotated')
os.makedirs(annotated_directory, exist_ok=True)

# Sort the PDF files in alphabetical order
def sort_key(s):
    import re
    try:
        # Match "Lecture" followed by a number (e.g., "Lecture 1", "Lecture 4a", "Lecture 7b")
        match = re.match(r'Lecture\s+(\d+)([a-z]?)', s, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            suffix = match.group(2) if match.group(2) else ''
            # Return tuple for proper sorting (e.g., 4a < 4b < 5)
            return (num, suffix)
        return (float('inf'), '')
    except (ValueError, IndexError):
        return (float('inf'), '')  # Return a large number for file names that don't follow the expected format

# Get a list of all PDF files in the directory
pdf_files = [file for file in os.listdir(pdf_directory) if file.endswith('.pdf')]
#pdf_files.sort(key=sort_key)  no need to sort the files

# Add text to each page of the PDF files with the file name
for file_name in pdf_files:
    file_path = os.path.join(pdf_directory, file_name)
    doc = fitz.open(file_path)

    for page in doc:
        page_width = page.rect.width
        text_location = fitz.Point(0, 15)  # position text 20 pixels from top, left-aligned
        text_length = fitz.get_text_length(file_name, fontsize=12)
        text_location.x = (page_width - text_length) / 2  # calculate the x-coordinate to center the text
        page.insert_text(text_location, file_name, fontsize=12, rotate=0, color=(0, 0, 0))  # black text


    # Save the annotated PDF file
    annotated_file_path = os.path.join(annotated_directory, f'annotated_{file_name}')
    doc.save(annotated_file_path)
    doc.close()



# Merge the annotated PDF files into a single PDF
annotated_pdf_files = [file for file in os.listdir(annotated_directory) if file.endswith('.pdf')]
annotated_pdf_files.sort(key=sort_key)
merged_pdf = fitz.open()
for file_name in annotated_pdf_files: # merge in the order of annotated_pdf_files
    file_path = os.path.join(annotated_directory, file_name)
    doc = fitz.open(file_path)
    merged_pdf.insert_pdf(doc)
    doc.close()

# Save the merged PDF
merged_pdf_path = os.path.join(pdf_directory, 'annotatedMerged.pdf')
merged_pdf.save(merged_pdf_path)
merged_pdf.close()
