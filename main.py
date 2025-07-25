import random
import subprocess
import sys
import os
import re
# ensure PyMuPDF is installed
try:
    import fitz  # PyMuPDF is imported as 'fitz'
except ImportError:
    print("PyMuPDF not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF"])
    import fitz

# initiate percentage
percentage_changed = round(random.random(), 2)

# identify if document is a mod or not (returns a bool)
def is_mod(document):
    output = False
    first_page = document[0]
    instance = first_page.search_for("SOLICITATION/MODIFICATION")
    if instance:
        output = True
    return output
    

document_paths = ["Datalake-Code/N63394-16-D-0018 Award Synthesized 7.7.25 PF_Redacted v2_Redacted.pdf", "Datalake-Code/F01_21F0037_29_Executed Modification_Final_20250407_Synthesized 7.7.25 PF_Redacted v2_Redacted.pdf"]

# Numbers to avoid modifying (add patterns you want to exclude)
NUMBERS_TO_AVOID = [
    r'\b\d{4}\b',  # 4-digit years (e.g., 2024, 2025)
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # dates (MM/DD/YYYY or similar)
    r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # dates with dashes
    r'\b[A-Z]\d+[A-Z]*\d*\b',  # contract numbers like N63394-16-D-0018
    r'\b\d{1,2}:\d{2}\b',  # time format (HH:MM)
    r'\bpage\s+\d+\b',  # page numbers
    r'\bsection\s+\d+\b',  # section numbers
    r'\bitem\s+\d+\b',  # item numbers
]

def should_avoid_number(text_context, number_match):
    """
    Check if a number should be avoided based on context and patterns
    """
    # Check against predefined patterns
    for pattern in NUMBERS_TO_AVOID:
        if re.search(pattern, text_context, re.IGNORECASE):
            return True
    
    # Additional context-based checks
    context_lower = text_context.lower()
    
    # Avoid numbers in specific contexts
    avoid_contexts = [
        'page', 'section', 'item', 'paragraph', 'line',
        'version', 'revision', 'amendment', 'modification',
        'contract', 'solicitation', 'award', 'number',
        'date', 'year', 'month', 'day', 'time'
    ]
    
    for context in avoid_contexts:
        if context in context_lower:
            return True
    
    return False

# apply percentage to a price
def alter_price(number_string):
    cleaned_price = re.sub(r'[^.0-9]', '', number_string)
    if cleaned_price == '' or cleaned_price == '.':
        return number_string
    
    # remove trailing period if price is at the end of a sentence
    if cleaned_price[-1] == ".":
        cleaned_price = cleaned_price[:-1]
    price_float = float(cleaned_price)
    
    # apply percentage and return price to the original format
    new_price_float = price_float - price_float * percentage_changed
    new_price = "${:,.2f}".format(new_price_float)
    
    price_float = "${:,.2f}".format(price_float)
    print(f"Modifying {price_float} to {new_price} (decreased by {int(percentage_changed * 100)}%)")
    return new_price

# apply percentage to any number (not just prices)
def alter_number(number_string):
    cleaned_number = re.sub(r'[^.0-9]', '', number_string)
    if cleaned_number == '' or cleaned_number == '.':
        return number_string
    
    # remove trailing period if number is at the end of a sentence
    if cleaned_number[-1] == ".":
        cleaned_number = cleaned_number[:-1]
    
    try:
        number_float = float(cleaned_number)
        
        # apply percentage change
        new_number_float = number_float - number_float * percentage_changed
        
        # Format the number (preserve decimal places if original had them)
        if '.' in cleaned_number:
            decimal_places = len(cleaned_number.split('.')[1])
            new_number = "{:.{}f}".format(new_number_float, decimal_places)
        else:
            new_number = "{:.0f}".format(new_number_float)
        
        print(f"Modifying {number_float} to {new_number} (decreased by {int(percentage_changed * 100)}%)")
        return new_number
    except ValueError:
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
    
    
# redact contact info on all pages of award file
def redact_contact_info(document):
    search_targets = ["ATTN:", "Telephone No.", "Email Address:"]
    for page_num, page in enumerate(document):
        for target in search_targets:
            text_instances = page.search_for(target)
            for inst in text_instances:
                
                # get coordinates of found text
                x0, y0, x1, y1 = inst
                
                # redact to the right
                redaction_rect = fitz.Rect(x1, y0, x1 + 115, y1)
                page.add_redact_annot(redaction_rect, fill=(1, 1, 1))
                print(f"Redacting {target[:-1]} on page {page_num + 1}")
    
    # redact
    for page in document:
        page.apply_redactions()
    print("Redaction complete.")


# modify amounts found to the right of dollar signs
def modify_prices(document):
    for page_num, page in enumerate(document):
        text_instances = page.search_for("$")
        for inst in text_instances:
            # redact a rectangle to the right of the dollar sign and add new price
            x0, y0, x1, y1 = inst[0], inst[1], inst[2] + 100, inst[3]
            price = page.get_text("text", clip=(x0, y0, x1, y1)).strip()
            new_price = alter_price(price)
            page.add_redact_annot((x0, y0, x1, y1), fill=(1, 1, 1))
            page.apply_redactions()
            page.insert_text((x0, y1), new_price, fontsize=9, color=(0, 0, 0))
    print(f"Modification complete.")
    
# mod documents have weird formats. This function is for mod documents
def modify_prices_from_mod(document):
    """
    Modify all numbers in the document while avoiding specific patterns
    """
    # Pattern to find numbers (including decimals and currency)
    number_pattern = r'\$?[\d,]+\.?\d*'
    
    for page_num, page in enumerate(document):
        print(f"Processing page {page_num + 1} for number modifications...")
        
        # Get all text blocks with their positions
        text_dict = page.get_text("dict")
        
        modifications_made = 0
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        bbox = span["bbox"]  # (x0, y0, x1, y1)
                        
                        # Find all numbers in this text span
                        for match in re.finditer(number_pattern, text):
                            number_text = match.group()
                            
                            # Get surrounding context for decision making
                            start_context = max(0, match.start() - 20)
                            end_context = min(len(text), match.end() + 20)
                            context = text[start_context:end_context]
                            
                            # Check if we should avoid this number
                            if should_avoid_number(context, match):
                                print(f"Skipping number '{number_text}' in context: '{context.strip()}'")
                                continue
                            
                            # Calculate position of the number within the span
                            char_width = (bbox[2] - bbox[0]) / len(text) if len(text) > 0 else 10
                            number_x0 = bbox[0] + match.start() * char_width
                            number_x1 = bbox[0] + match.end() * char_width
                            
                            # Create rectangle for the number
                            number_rect = fitz.Rect(number_x0, bbox[1], number_x1, bbox[3])
                            
                            # Modify the number
                            if number_text.startswith('$'):
                                new_number = alter_price(number_text)
                            else:
                                new_number = alter_number(number_text)
                            
                            # Only proceed if the number actually changed
                            if new_number != number_text:
                                # Redact the old number
                                page.add_redact_annot(number_rect, fill=(1, 1, 1))
                                page.apply_redactions()
                                
                                # Insert the new number
                                page.insert_text(
                                    (number_x0, bbox[3]), 
                                    new_number, 
                                    fontsize=span.get("size", 9), 
                                    color=(0, 0, 0)
                                )
                                modifications_made += 1
        
        print(f"Made {modifications_made} number modifications on page {page_num + 1}")
    
    print("Modification complete for mod document.")


# execute script
def main():
    i=1
    for path in document_paths:
        doc = fitz.open(path)
        print(f"REDACTING AND MODIFYING FILE #{i}...")
        redact_first_page(doc)
        redact_contact_info(doc)
        
        if is_mod(doc):
            modify_prices_from_mod(doc)
        else:
            modify_prices(doc)
        
        # save the modified PDF with "REDACTED_" prefix
        input_filename = os.path.basename(path)
        output_filename = f"REDACTED_{input_filename}"
        output_dir = os.path.dirname(path)
        output_path = os.path.join(output_dir, output_filename)
        doc.save(output_path)
        doc.close()
        print(f"Modified PDF saved to: {output_path}\n")
        i+=1
        
if __name__ == "__main__":
    main()