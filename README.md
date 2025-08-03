# Maybank PDF Statement Parser

Python application to extract and organize transaction data from **Maybank Credit Card and Current Account PDF statements** into structured spreadsheets.

## Quick Start

1. Download this project and install Python
2. Put your PDF statements in a `Drop/` folder
3. Run the program and select your statement type
4. Get organized CSV and JSON files automatically

## Overview

This tool processes **both Maybank Credit Card and Current Account PDF statements** and converts them into structured data formats. It addresses the challenge of working with PDF statements by:

- 🔍 **Auto-detecting** statement types (Credit Card vs Current Account)
- 📊 Extracting transaction data automatically
- 💾 Converting to CSV and JSON formats
- 📈 Organizing data for analysis and reporting
- 🔒 Supporting encrypted PDF files
- ⚠️ Warning about unexpected formats

**Use cases:** Personal budgeting, expense tracking, tax preparation, financial analysis, account reconciliation

## Features

### 🏦 Statement Type Support
- **Credit Card Statements**: Full support for Maybank credit card PDF statements
- **Current Account Statements**: Complete support for Maybank current account PDF statements
- **Manual Selection**: Choose specific statement type based on your PDFs
- **Format Validation**: Warns about unexpected or unsupported formats

### 📊 Data Processing
- **Optimized PDF Processing**: Extract transaction data from Maybank PDF statements with improved efficiency
- **Enhanced Transaction Parsing**: Parse transaction details including posting date, transaction date, description, amount, and type (DEBIT/CREDIT)
- **Smart Date Handling**: Automatically infer correct year for DD/MM date format
- **Duplicate Prevention**: Advanced duplicate detection using unique transaction identifiers
- **Balance Extraction**: Extract balance information from statements
- **Transaction Filtering**: Skip non-transaction lines and system messages
- **Clean Data Output**: Normalized descriptions and proper data formatting

### 💾 Export & Security
- **Multiple Export Formats**: Export data to both CSV and JSON formats
- **Encrypted PDF Support**: Handle password-protected and encrypted PDFs
- **Batch Processing**: Process multiple PDF files in one run

### 🔧 User Experience
- **Interactive Interface**: User-friendly prompts for statement type selection
- **Robust Error Handling**: Comprehensive error handling and informative feedback
- **Progress Feedback**: Clear status updates and processing summaries
- **Troubleshooting Tips**: Helpful guidance when issues occur

## Requirements

- Python 3.7 or newer ([Download here](https://www.python.org/downloads/))
- Maybank PDF statements downloaded from Maybank2u (M2U) online banking
- Required Python libraries (installed automatically via requirements.txt)

### Important: Statement Source

**Download statements directly from Maybank2u (M2U) online banking** rather than using statements received via email. Email statements are typically password-protected and may have formatting differences that could affect parsing accuracy.

**For Credit Card Statements:**
1. Log into your Maybank2u account
2. Navigate to Credit Card > Statements
3. Select the desired statement period
4. Download as PDF

**For Current Account Statements:**
1. Log into your Maybank2u account
2. Navigate to Accounts > Account Statement
3. Select your current account
4. Choose the desired statement period
5. Download as PDF

This ensures you get the standard format that the parser is optimized for both statement types.

## Installation

### Step 1: Download the Project
- Download ZIP from the repository and extract
- Or clone using Git: `git clone [repository-url]`

### Step 2: Open Terminal/Command Prompt
- **Mac:** Press `Cmd + Space`, type "Terminal", press Enter
- **Windows:** Press `Win + R`, type "cmd", press Enter
- Navigate to project folder: `cd path/to/Maybank_app`

### Step 3: Set Up Python Environment

**For Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**For Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

The virtual environment will be activated when you see `(venv)` in your terminal prompt.

## Usage

### Step 1: Prepare Your PDF Files
1. Download your Maybank statements from M2U online banking (PDF format)
   - Credit Card statements from Credit Card > Statements
   - Current Account statements from Accounts > Account Statement
2. Create a folder called `Drop` in the project directory
3. Copy all your PDF files into the `Drop/` folder

```
Project structure:
Maybank_app/
├── Drop/
│   ├── cc_statement_jan.pdf      # Credit Card
│   ├── ca_statement_jan.pdf      # Current Account
│   ├── cc_statement_feb.pdf      # Credit Card
│   └── ca_statement_feb.pdf      # Current Account
└── maybank_parser.py
```

### Step 2: Run the Parser
```bash
# Ensure virtual environment is active (you should see "(venv)" in terminal)
python maybank_parser.py
```

### Step 3: Select Statement Type
The program will prompt you to choose:

```
🏦 MAYBANK PDF STATEMENT PARSER
============================================================

Please select the type of Maybank statement to process:

1. 💳 Credit Card Statement
2. 🏛️  Current Account Statement

------------------------------------------------------------
Enter your choice (1-2): 1

✅ Selected: Credit Card Statement
```

**Note:** Choose the statement type that matches your PDF files in the Drop folder.

### Step 4: Review Results
The program creates two output files:
- `maybank_transactions.csv` - Spreadsheet format for Excel/Google Sheets
- `maybank_transactions.json` - JSON format for data processing

### Expected Output
```
============================================================
🚀 Starting Maybank PDF Statement Parser...
📁 Processing PDFs from: ./Drop/

⚠️  Note: Unexpected formats will trigger warnings
------------------------------------------------------------

📄 Processing: cc_statement_jan.pdf
📄 Processing: cc_statement_feb.pdf
📄 Processing: cc_statement_mar.pdf

============================================================
📊 PROCESSING SUMMARY
============================================================

✅ Processed 3 files successfully
📊 Total transactions extracted: 67
💳 Credit Card transactions: 34
🏛️  Current Account transactions: 33

============================================================
✅ Processing completed successfully!
📄 Files saved: maybank_transactions.csv, maybank_transactions.json
============================================================
```

### Output Features
- **Unified Format**: Both statement types use the same output structure
- **Statement Type Column**: Identifies whether each transaction is from Credit Card or Current Account
- **Standardized Columns**: Date, Description, Amount, Transaction Type, and Statement Type
- **Excel Compatible**: Ready to import into Excel, Google Sheets, or other tools
- **JSON Format**: Perfect for data analysis, APIs, and programming applications

## Output Format

The parser extracts the following information for each transaction:

- **date**: Standardized date (YYYY-MM-DD)
- **raw_date**: Original date from PDF
- **posting_date**: When transaction was posted
- **transaction_date**: When transaction occurred
- **description**: Transaction description
- **amount**: Transaction amount
- **type**: CREDIT or DEBIT
- **source_file**: Source PDF filename
- **pattern_used**: Which regex pattern matched



## Project Structure

```
Maybank_app/
├── Drop/                     # PDF statements directory
│   ├── statement1.pdf        # Maybank PDF files
│   ├── statement2.pdf
│   └── ...
├── venv/                    # Python virtual environment
├── maybank_parser.py        # Main parser script
├── requirements.txt         # Python dependencies
├── README.md               # Documentation
├── maybank_transactions.csv # Output: CSV format
└── maybank_transactions.json # Output: JSON format
```

## Improvements Made

This project has evolved through multiple iterations with significant improvements:

### Version 1 (Original)
- Basic PDF text extraction
- Simple regex patterns
- Hardcoded paths
- No error handling

### Version 2 (Improved)
- Added dependency management
- Enhanced error handling
- Better regex patterns
- Duplicate detection
- Multiple output formats

### Version 3 (Final Optimized) ⭐
- **Streamlined Processing**: Reduced from 216 to 102 transactions by eliminating duplicates
- **Optimized Regex**: Single, efficient pattern for better performance
- **Smart Duplicate Detection**: Uses unique transaction identifiers
- **Enhanced Data Quality**: Better description cleaning and validation
- **Improved Date Handling**: More accurate year inference
- **Performance Optimization**: Faster processing with reduced memory usage
- **Clean Output**: Consistent field structure without redundant data

### Key Technical Improvements
1. **Dependency Management**: Virtual environment with pinned versions
2. **Code Consolidation**: Single, optimized parser class
3. **Advanced Error Handling**: Comprehensive exception handling
4. **Encrypted PDF Support**: Full support for protected documents
5. **Data Validation**: Robust filtering and validation logic
6. **Memory Efficiency**: Optimized for large statement processing

## Sample Output

The optimized parser extracts transactions in a clean, consistent format:

```csv
date,posting_date,transaction_date,description,amount,type,source_file
2024-01-15,2024-01-15,2024-01-15,PAYMENT RECEIVED,500.00,CREDIT,statement_202401.pdf
2024-01-16,2024-01-16,2024-01-16,RETAIL PURCHASE,150.00,DEBIT,statement_202401.pdf
2024-01-18,2024-01-18,2024-01-18,ONLINE SUBSCRIPTION,25.99,DEBIT,statement_202401.pdf
```

### Processing Summary
```
Processed X files successfully.
Total transactions extracted: XXX
Total amount: RM X,XXX.XX
Credit amount: RM X,XXX.XX
Debit amount: RM X,XXX.XX
```

## Troubleshooting

### "Command not found" or "Python not recognized"
- Install Python from [python.org](https://www.python.org/downloads/)
- Windows: Ensure "Add Python to PATH" is checked during installation

### "No such file or directory"
- Verify you're in the correct directory
- Use `ls` (Mac/Linux) or `dir` (Windows) to list files
- Navigate to project folder: `cd path/to/Maybank_app`

### "No transactions extracted"
- Confirm PDFs are in the `Drop/` folder
- Verify files are Maybank credit card statements
- Test with a single PDF file first
- Check that PDFs contain readable transaction data

### "PyCryptodome is required"
- Indicates password-protected PDF files
- Install manually if needed: `pip install pycryptodome`
- Consider using M2U downloaded statements instead

### "Permission denied"
- Close any applications using the output files
- Run terminal as administrator (Windows) or with appropriate permissions

### General Troubleshooting Steps
1. Verify Python installation: `python --version`
2. Confirm you're in the project directory (should contain `maybank_parser.py`)
3. Check virtual environment is active (look for `(venv)` in terminal)
4. Reinstall dependencies: `pip install -r requirements.txt`

## Security and Safety

This tool operates locally on your computer and:
- Only reads PDF files from the specified directory
- Creates output files locally
- Does not modify original PDF statements
- Does not access external networks or bank accounts
- Does not transmit data anywhere

Your financial data remains secure on your local machine.

## License

This project is for personal use. Please ensure compliance with your bank's terms of service when processing financial documents.