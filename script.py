import subprocess
import sys
import os 

# for pattern finding and number modification
import re
import random

# for filesysytem exploring
from pathlib import Path 
import shutil

# ensure PyMuPDF is installed
try:
    import fitz  # PyMuPDF is imported as 'fitz'
except ImportError:
    print("PyMuPDF not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF"])
    import fitz


# initiate percentage
# If you would like to select a specific percentage value, replace 'round(random.random(), 2))' with your percentage.
# percentages should follow a decimal format. For example, if you want a 45% decrease, replace the text with "0.45"
percentage_changed = round(random.random(), 2)


# Get all PDF files from a given root directory
def find_all_pdfs(root_path):
    root = Path(root_path)
    return list(root.rglob("*.pdf"))

# Clone directory structure and build destination path
def get_redacted_output_path(original_path, input_root, output_root):
    relative_path = Path(original_path).relative_to(input_root)
    redacted_filename = f"REDACTED_{relative_path.name}"
    return Path(output_root) / relative_path.parent / redacted_filename

def create_output_dirs(output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

def process_all_pdfs(input_root, output_root):
    pdf_paths = find_all_pdfs(input_root)
    print(f"Found {len(pdf_paths)} PDF(s) to process in {input_root}.\n")

    for i, path in enumerate(pdf_paths, 1):
        try:
            doc = fitz.open(path)
        except Exception as e:
            print(f"Skipping {path} due to error: {e}")
            continue
        
        redact_first_page(doc)
        redact_contact_info(doc)
        modify_values(doc)

        output_path = get_redacted_output_path(path, input_root, output_root)
        create_output_dirs(output_path)
        doc.save(str(output_path))
        doc.close()

        print(f"Saved redacted PDF #{i} to: {output_path}\n")
    

# apply percentage to a vlaue
def alter_value(number_string):
    if isinstance(number_string, str):
        cleaned_price = re.sub(r'[^.0-9]', '', number_string)
        if cleaned_price == '' or cleaned_price == '.':
            return number_string
        
        # remove trailing period if price is at the end of a sentence
        if cleaned_price[-1] == ".":
            cleaned_price = cleaned_price[:-1]
        price_float = float(cleaned_price)
        
        value_symbol = ''
        if number_string[0] == '$':
            value_symbol = '$'
        elif number_string[0] == '+':
            value_symbol = '+'
        elif number_string[0] == '-':
            value_symbol = '-'
       
        # apply percentage and return price to the original format
        new_price_float = price_float - price_float * percentage_changed
        
        rounded_price = round(new_price_float)
        
        new_price = f"{value_symbol}{rounded_price:,}"
        return new_price
    
    return number_string


# function that takes the top-left coordinate of a box and outputs the coordinates of the top-left and bottom-right corners
def generate_rect_coordiante(document, page_number, start_x, start_y):
    page = document[page_number]
    pix = page.get_pixmap(dpi=200)  # Higher resolution helps with accuracy
    
    # Convert starting coordinates to match pixmap scale
    scale_x = pix.width / page.rect.width
    scale_y = pix.height / page.rect.height
    px_start_x = int(start_x * scale_x)
    px_start_y = int(start_y * scale_y)
    
    # Find right edge - move right until we hit a black pixel
    curr_px_x = px_start_x
    while curr_px_x < pix.width:
        r, g, b = pix.pixel(curr_px_x, px_start_y)
        if r + g + b < 100:  # Very dark pixel indicates a black line
            break
        curr_px_x += 1
    curr_px_x = curr_px_x - 4  # Move back some pixel to stay inside the box

    # Find bottom edge - move down until we hit a black pixel
    curr_px_y = px_start_y
    while curr_px_y < pix.height:
        r, g, b = pix.pixel(curr_px_x, curr_px_y)
        if r + g + b < 100:
            break
        curr_px_y += 1
    curr_px_y = curr_px_y - 4  # Move back some pixels to stay inside the box
    
    # Convert pixmap coordinates back to PDF coordinates
    end_x = curr_px_x / scale_x
    end_y = curr_px_y / scale_y

    return (start_x, start_y, end_x, end_y)


# redact confidential boxes of page one (document agnostic)
def redact_first_page(document):
    first_page = document[0]
    blocks_to_redact = ["7.", "8.", "15A.", "16.", "17A.", "18.", "19A.", "19B.", "20B.", "30A.", "30B.", "31A.", "31B."]
    rect_coordinates_to_redact = []
    for block in blocks_to_redact:
        instance = first_page.search_for(block)
        if instance:
            x0, y0, x1, y1 = instance[0]
            rect_coordinates_to_redact.append(generate_rect_coordiante(document, 0, x0, y1))

    # redact
    for rect_coordinate in rect_coordinates_to_redact:
        rect = fitz.Rect(rect_coordinate)  # Convert tuple to Rect object
        first_page.add_redact_annot(rect, fill=(0, 0, 0))
    first_page.apply_redactions()
    
    
# redact contact info on all pages
def redact_contact_info(document):
    search_targets = ["ATTN", "Telephone No", "Email Address", "POC Name", "POC Email", "POC Telephone"]
    for page_num, page in enumerate(document):
        pix = page.get_pixmap(dpi=300)
        for target in search_targets:
            text_instances = page.search_for(target)
            for inst in text_instances:
                
                # get coordinates of found text
                x0, y0, x1, y1 = inst
                
                # redact to the right end of the page
                redaction_rect = fitz.Rect(x1, y0, pix.width - 100, y1)
                page.add_redact_annot(redaction_rect, fill=(1, 1, 1))
    
    # redact
    for page in document:
        page.apply_redactions()


# modify amounts (avoid the patterns of numbers that we do not want to change)
def modify_values(document):
    
    price_pattern = re.compile(r'^[+\-]?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?$|^[+\-]?\$?\d+(?:\.\d{2})?$')
    
    alphanumeric_inside_pattern = re.compile(r'\d+[A-Za-z]+\d+') # avoid "123BN123" and so on
    letter_prefix_pattern = re.compile(r'^[A-Za-z]\d+') # avoid "N1234" and so on
    range_pattern = re.compile(r'\d+\s*[-–—]\s*\d+') # avoid "4 - 7" and so on
    page_pattern = re.compile(r'\b(pp?\.?|page)\s*\d+', re.IGNORECASE) # avoid "Page 5", etc.
    standalone_int = re.compile(r'^\d{1,3}$')  # avoid lone numbers like 2, 10
    four_digit_pattern = re.compile(r'^\d{4}$') # avoid years and addresses
    leading_zero_pattern = re.compile(r'^0{2,}\d+(\.\d+)?$') # avoid "00001", "0034"

    
    for page_num, page in enumerate(document):
        words = page.get_text("words")
        for w in words:
            x0, y0, x1, y1, word_text, *_ = w
            raw_text = word_text.strip()

            if not any(char.isdigit() for char in raw_text):
                continue

            if (
            price_pattern.fullmatch(raw_text)
            and not range_pattern.search(raw_text)
            and not page_pattern.search(raw_text)
            and not standalone_int.fullmatch(raw_text)
            and not four_digit_pattern.fullmatch(raw_text)
            and not leading_zero_pattern.fullmatch(raw_text)
            and not alphanumeric_inside_pattern.fullmatch(raw_text)
            and not letter_prefix_pattern.fullmatch(raw_text)
            ):
                new_price = alter_value(raw_text)
                rect = fitz.Rect(x0, y0, x1, y1)
                insertion_point = (x0, y1 - 2)

                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
                page.insert_text(insertion_point, new_price, fontsize=8, color=(0, 0, 0))


def main():
    input_root = Path("C:/Users") / "peter.fernando" / "Downloads" / "Awards"
    output_root = Path("ClonedRedactedFY")
    process_all_pdfs(input_root, output_root)
        
main()
