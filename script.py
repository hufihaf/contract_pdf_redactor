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

document_paths = ["Datalake-Code/N63394-16-D-0018 Award Synthesized 7.7.25 PF_Redacted v2_Redacted.pdf", "Datalake-Code/F01_21F0037_29_Executed Modification_Final_20250407_Synthesized 7.7.25 PF_Redacted v2_Redacted.pdf"]
    
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


# execute script
def main():
    i=1
    for path in document_paths:
        doc = fitz.open(path)
        print(f"REDACTING AND MODIFYING FILE #{i}...")
        redact_first_page(doc)
        redact_contact_info(doc)
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
        
main()
