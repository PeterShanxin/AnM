import os
import fitz
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess

# Function to annotate and optionally save PDF files
def annotate_and_merge(pdf_directory, save_intermediate, open_folder):
    # Create a new folder to store the annotated PDF files
    annotated_directory = os.path.join(pdf_directory, 'annotated')
    if save_intermediate:
        os.makedirs(annotated_directory, exist_ok=True)

    # Sort the PDF files in alphabetical order
    def sort_key(s):
        try:
            lecture_part = s.split(' - ')[0]
            return int(lecture_part.split(' ')[1])
        except (ValueError, IndexError):
            return float('inf')

    # Get a list of all PDF files in the directory
    pdf_files = [file for file in os.listdir(pdf_directory) if file.endswith('.pdf')]

    for file_name in pdf_files:
        file_path = os.path.join(pdf_directory, file_name)
        doc = fitz.open(file_path)

        for page in doc:
            page_width = page.rect.width
            text_location = fitz.Point(0, 15)
            text_length = fitz.get_text_length(file_name, fontsize=12)
            text_location.x = (page_width - text_length) / 2
            page.insert_text(text_location, file_name, fontsize=12, rotate=0, color=(0, 0, 0))

        if save_intermediate:
            annotated_file_path = os.path.join(annotated_directory, f'annotated_{file_name}')
            doc.save(annotated_file_path)
        doc.close()

    # Merge the annotated PDF files into a single PDF
    annotated_pdf_files = [file for file in os.listdir(annotated_directory) if file.endswith('.pdf')] if save_intermediate else pdf_files
    annotated_pdf_files.sort(key=sort_key)
    merged_pdf = fitz.open()
    for file_name in annotated_pdf_files:
        file_path = os.path.join(annotated_directory, file_name) if save_intermediate else os.path.join(pdf_directory, file_name)
        doc = fitz.open(file_path)
        merged_pdf.insert_pdf(doc)
        doc.close()

    merged_pdf_path = os.path.join(pdf_directory, 'annotatedMerged.pdf')
    merged_pdf.save(merged_pdf_path)
    merged_pdf.close()

    if open_folder:
        subprocess.Popen(f'explorer \"{pdf_directory}\"')

# GUI Application using tkinter
class PDFAnnotatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Annotator and Merger")
        self.geometry("400x250")
        
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
        self.directory_label = tk.Label(self, text=f"Current Directory: {self.pdf_directory}", wraplength=380, justify="left")
        self.directory_label.pack(pady=10)
        
        # Select Directory Button
        self.select_dir_button = tk.Button(self, text="Select Folder", command=self.select_directory)
        self.select_dir_button.pack(pady=5)
        
        # Begin Merge Button
        self.begin_merge_button = tk.Button(self, text="Begin Merge", command=self.begin_merge)
        self.begin_merge_button.pack(pady=5)
        
        # Save Intermediate Files Checkbox
        self.save_intermediate_checkbox = tk.Checkbutton(self, text="Save Intermediate Annotated Files", variable=self.save_intermediate)
        self.save_intermediate_checkbox.pack(pady=5)
        
        # Open Folder After Merge Checkbox
        self.open_folder_checkbox = tk.Checkbutton(self, text="Open Folder After Merge", variable=self.open_folder)
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
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = PDFAnnotatorApp()
    app.mainloop()
