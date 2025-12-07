import os
import fitz
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import re

# Function to annotate and optionally save PDF files
def annotate_and_merge(pdf_directory, save_intermediate, open_folder):
    
    # Sort the PDF files in alphabetical order
    def sort_key(s):
        chunks = re.split(r'(\d+)', s)
        return [int(chunk) if chunk.isdigit() else chunk for chunk in chunks]


    # Get a list of all PDF files in the directory
    pdf_files = [file for file in os.listdir(pdf_directory) if file.endswith('.pdf')]
    pdf_files.sort(key=sort_key)

    if not pdf_files:
        raise FileNotFoundError("No PDF files found in the selected directory.")

    annotated_files = []

    if save_intermediate:
        annotated_directory = os.path.join(pdf_directory, 'annotated')
        os.makedirs(annotated_directory, exist_ok=True)

    for file_name in pdf_files:
        file_path = os.path.join(pdf_directory, file_name)
        doc = fitz.open(file_path)

        for page in doc:
            page_width = page.rect.width
            page_height = page.rect.height
            text = file_name
            font_size = 12
            text_length = fitz.get_text_length(text, fontsize=font_size)
            text_location = fitz.Point((page_width - text_length) / 2, 25)
            rect = fitz.Rect(text_location.x - 5, text_location.y - font_size - 2, text_location.x + text_length + 5, text_location.y + 2)

            # Draw semi-transparent rectangle manually
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), stroke_opacity=0.5, fill_opacity=0.5)
            
            # Insert text over the rectangle
            page.insert_text(text_location, text, fontsize=font_size, rotate=0, color=(0, 0, 0))

        if save_intermediate:
            annotated_file_path = os.path.join(annotated_directory, f'annotated_{file_name}')
            doc.save(annotated_file_path)
            annotated_files.append(annotated_file_path)
        else:
            temp_annotated_path = os.path.join(pdf_directory, f'annotated_{file_name}')
            doc.save(temp_annotated_path)
            annotated_files.append(temp_annotated_path)
        doc.close()

    # Merge the annotated PDF files into a single PDF
    merged_pdf = fitz.open()
    for file_name in annotated_files:
        doc = fitz.open(file_name)
        merged_pdf.insert_pdf(doc)
        doc.close()

    merged_pdf_path = os.path.join(pdf_directory, 'annotatedMerged.pdf')
    merged_pdf.save(merged_pdf_path)
    merged_pdf.close()

    # Clean up intermediate files if not saved
    if not save_intermediate:
        for file_path in annotated_files:
            os.remove(file_path)

    if open_folder:
        subprocess.Popen(f'explorer \"{os.path.realpath(pdf_directory)}\"')

# GUI Application using tkinter
class PDFAnnotatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Annotator and Merger")
        self.geometry("500x250")
        
        # High DPI Awareness to fix blurriness
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            print(f"Failed to set DPI awareness: {e}")
        
        self.pdf_directory = os.getcwd()
        self.save_intermediate = tk.BooleanVar(value=False)
        self.open_folder = tk.BooleanVar(value=True)
        
        # Directory Label
        self.directory_label = tk.Label(self, text=f"Current Directory: {self.pdf_directory}", wraplength=480, justify="left", font=("Arial", 16))
        self.directory_label.pack(pady=10)
        
        # Select Directory Button
        self.select_dir_button = tk.Button(self, text="Select Folder", command=self.select_directory, font=("Arial", 16))
        self.select_dir_button.pack(pady=5)
        
        # Begin Merge Button
        self.begin_merge_button = tk.Button(self, text="Begin Merge", command=self.begin_merge, font=("Arial", 16))
        self.begin_merge_button.pack(pady=5)
        
        # Save Intermediate Files Checkbox
        self.save_intermediate_checkbox = tk.Checkbutton(self, text="Save Intermediate Annotated Files", variable=self.save_intermediate, font=("Arial", 16))
        self.save_intermediate_checkbox.pack(pady=5)
        
        # Open Folder After Merge Checkbox
        self.open_folder_checkbox = tk.Checkbutton(self, text="Open Folder After Merge", variable=self.open_folder, font=("Arial", 16))
        self.open_folder_checkbox.pack(pady=5)
    
    def select_directory(self):
        selected_directory = filedialog.askdirectory(initialdir=self.pdf_directory)
        if selected_directory:
            self.pdf_directory = selected_directory
            self.directory_label.config(text=f"Current Directory: {self.pdf_directory}")
    
    def begin_merge(self):
        try:
            annotate_and_merge(self.pdf_directory, self.save_intermediate.get(), self.open_folder.get())
            messagebox.showinfo("Success", "PDF files have been annotated and merged successfully!")
        except FileNotFoundError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = PDFAnnotatorApp()
    app.mainloop()
