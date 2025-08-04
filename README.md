# PDF Redaction and Value Modification Script

This script processes a folder of PDF files, redacts their sensitive fields, and modifies dollar and hour values using a random or user-defined percentage.

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
   - [Install Requirements](#install-requirements)
   - [Set File Paths (Line 236)](#set-file-paths-line-236)
   - [Set Percentage Change (Line 23)](#set-percentage-change-line-23)
3. [How It Works](#️-how-it-works)
4. [Function Reference](#-how-it-works-function-by-function)
   - [`find_all_pdfs`](#find_all_pdfs)
   - [`get_redacted_output_path`](#get_redacted_output_path)
   - [`create_output_dirs`](#create_output_dirs)
   - [`process_all_pdfs`](#process_all_pdfs)
   - [`alter_value`](#alter_value)
   - [`generate_rect_coordiante`](#generate_rect_coordiante)
   - [`redact_first_page`](#redact_first_page)
   - [`redact_contact_info`](#redact_contact_info)
   - [`modify_values`](#modify_values)
   - [`main`](#main)
5. [Notes](#notes)

---

## 🧾 Overview

This script will:

- Traverse a folder and find all `.pdf` files.
- Clone the original folder structure to a new directory.
- Redact form fields and contact information on each PDF.
- Modify sensitive values by a percentage (random by default).

All output PDFs will be saved to a new folder with `REDACTED_` prefixed in their filenames.

---

## 🚀 Getting Started

### ✅ Install Requirements

Python will attempt to install the required `PyMuPDF` library if it's not found. You don't need to do anything unless you encounter errors.

### 📂 Set File Paths (Line 236)

Modify line **236** in the `main()` function to point to the folder you want to process. For example:

```python
input_root = Path.home() / "Awarded Contracts" / "FY16"
```

Replace with a path to your folder:

```python
input_root = Path("C:/Users/YourName/Documents/YourFolder")
```

The output will be saved to a folder named `ClonedRedactedFY` in the same location where the script runs.

---

### 🎯 Set Percentage Change (Line 23)

By default, the script randomly selects a percentage. You can change line **23**:

```python
percentage_changed = round(random.random(), 2)
```

Replace with a fixed value (e.g., 45% decrease → `0.45`):

```python
percentage_changed = 0.45
```

---

## ⚙️ How It Works

The script performs the following steps:

1. **Scans** the input folder and finds all `.pdf` files.
2. **Redacts** standard form blocks and contact information.
3. **Identifies** dollar and hour amounts and modifies them.
4. **Saves** the modified file to a new location with the same folder structure.

---

## 🧠 How it Works, Function by Function

### `find_all_pdfs`

Finds all `.pdf` files recursively in a given directory.

```python
def find_all_pdfs(root_path):
```

---

### `get_redacted_output_path`

Creates a new path for the redacted PDF that mirrors the original structure.

```python
def get_redacted_output_path(original_path, input_root, output_root):
```

---

### `create_output_dirs`

Ensures the directory exists before saving the new PDF.

```python
def create_output_dirs(output_path):
```

---

### `process_all_pdfs`

The main engine of the script. It reads PDFs, applies redactions and modifications, then saves them.

```python
def process_all_pdfs(input_root, output_root):
```

---

### `alter_value`

Takes a value as a string, modifies it by the chosen percentage, and returns a formatted string.

```python
def alter_value(number_string):
```

---

### `generate_rect_coordiante`

Given the top-left corner of a block, it computes the bounding rectangle of a form field box.

```python
def generate_rect_coordiante(document, page_number, start_x, start_y):
```

---

### `redact_first_page`

Redacts standardized field blocks (like "7.", "16.") found on the first page.

```python
def redact_first_page(document):
```

---

### `redact_contact_info`

Redacts fields such as email addresses, phone numbers, and POCs across all pages.

```python
def redact_contact_info(document):
```

---

### `modify_values`

Searches for numeric values and modifies them unless they are page numbers, years, ranges, etc.

```python
def modify_values(document):
```

---

### `main`

This is the entry point of the script. It defines input/output folders and begins processing.

```python
def main():
```

---

## 📝 Notes

- Certain numbers are **excluded**: page numbers, years (4-digit), short integers (like "12"), and zero-padded IDs.
- Redactions are **visible**—they replace content with white or black boxes.
- The script preserves the original directory layout when saving output PDFs.
- PDFs with read errors will be skipped with a warning.

---

Feel free to ask someone familiar with Python if you want to modify the logic further, or reach out for assistance if needed.
