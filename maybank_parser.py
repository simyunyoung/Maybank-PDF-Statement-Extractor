#!/usr/bin/env python3
"""
Maybank PDF Statement Parser - Final Optimized Version
Consolidated and improved version with better error handling and duplicate elimination.
"""

import os
import re
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional
import PyPDF2


class MaybankStatementParser:
    def __init__(self, pdf_folder: str = "./Drop", log_level: str = "INFO"):
        self.pdf_folder = pdf_folder
        
        # Configure logging
        self.setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        
        # Optimized regex pattern for Maybank statement format
        # Matches: Posting Date + Transaction Date + Description + Amount + Optional CR
        self.transaction_pattern = re.compile(
            r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2})(CR)?\s*$', 
            re.MULTILINE
        )
        
        # Pattern for balance information
        self.balance_pattern = re.compile(r'BALANCE\s+(\d+\.\d{2})')
        
        self.logger.info(f"Initialized Maybank Statement Parser with folder: {pdf_folder}")
    
    def setup_logging(self, log_level: str = "INFO"):
        """Setup logging configuration with proper formatting."""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Configure logging format - more concise
        log_format = "%(asctime)s [%(levelname)s] %(message)s"
        date_format = "%H:%M:%S"
        
        # Clear any existing handlers to avoid conflicts
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler("logs/maybank_parser.log", mode='a'),
                logging.StreamHandler()  # Console output
            ],
            force=True  # Force reconfiguration
        )
        
        # Set specific logger levels
        logging.getLogger("PyPDF2").setLevel(logging.WARNING)  # Reduce PyPDF2 noise
        
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from a PDF file with error handling.
        """
        try:
            self.logger.debug(f"Starting text extraction from: {pdf_path}")
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page_num, page in enumerate(reader.pages):
                    try:
                        text += page.extract_text() + '\n'
                    except Exception as e:
                        self.logger.warning(f"Could not extract text from page {page_num + 1} of {pdf_path}: {e}")
                        continue
                self.logger.debug(f"Successfully extracted {len(text)} characters from {pdf_path}")
                return text
        except FileNotFoundError:
            self.logger.error(f"File not found: {pdf_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading PDF {pdf_path}: {e}")
            return None
    
    def extract_statement_year(self, text: str) -> Optional[int]:
        """
        Extract the statement year from PDF content by looking for statement dates,
        payment due dates, statement periods, or year-end summaries.
        """
        try:
            # Look for Statement Date section followed by date pattern like "08 JUN 24"
            # The date appears after "Statement Date/Tarikh Penyata Payment Due Date/Tarikh Akhir Pembayaran"
            statement_section = re.search(r'Statement Date.*?Tarikh Penyata.*?Payment Due Date.*?Tarikh Akhir Pembayaran', text, re.IGNORECASE | re.DOTALL)
            if statement_section:
                # Look for the first date pattern after the statement section
                remaining_text = text[statement_section.end():statement_section.end() + 200]  # Look in next 200 chars
                date_pattern = re.search(r'(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{2})', remaining_text, re.IGNORECASE)
                if date_pattern:
                    year_2digit = int(date_pattern.group(3))
                    # Convert 2-digit year to 4-digit (assuming 20xx for years 00-99)
                    return 2000 + year_2digit
            
            # Look for payment due date patterns like "Payment Due Date / Tarikh Bayaran Perlu Dijelaskan 28 JANUARY 2024"
            due_date_pattern = re.search(r'Payment Due Date.*?\d{1,2}\s+[A-Z]+\s+(20\d{2})', text, re.IGNORECASE)
            if due_date_pattern:
                return int(due_date_pattern.group(1))
            
            # Look for year-end summary patterns like "2024 Year End Summary"
            year_summary_pattern = re.search(r'(20\d{2})\s+Year End Summary', text, re.IGNORECASE)
            if year_summary_pattern:
                return int(year_summary_pattern.group(1))
            
            # Look for statement period patterns
            period_pattern = re.search(r'Statement.*?Period.*?(20\d{2})', text, re.IGNORECASE)
            if period_pattern:
                return int(period_pattern.group(1))
            
            # Look for any 4-digit year in payment context
            payment_year_pattern = re.search(r'Payment.*?(20\d{2})', text, re.IGNORECASE)
            if payment_year_pattern:
                return int(payment_year_pattern.group(1))
            
            # Simple fallback - look for JANUARY/FEBRUARY etc followed by year
            month_year_pattern = re.search(r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(20\d{2})', text, re.IGNORECASE)
            if month_year_pattern:
                return int(month_year_pattern.group(2))
                
            return None
        except Exception as e:
            self.logger.error(f"Error in extract_statement_year: {e}")
            return None
    
    def parse_date_maybank(self, date_str: str, statement_year: int = None) -> str:
        """
        Parse Maybank date format (DD/MM) and add appropriate year.
        Uses statement year from PDF content if available, otherwise uses current year logic.
        """
        try:
            # Extract month and day
            day, month = map(int, date_str.split('/'))
            
            # Use statement year if provided, otherwise use current year logic
            if statement_year:
                target_year = statement_year
            else:
                current_date = datetime.now()
                target_year = current_date.year
                # If the date is more than 6 months in the future, use previous year
                try:
                    date_obj = datetime(target_year, month, day)
                    if (date_obj - current_date).days > 180:
                        target_year = target_year - 1
                except ValueError:
                    # Invalid date, use previous year
                    target_year = target_year - 1
            
            # Create final date object
            date_obj = datetime(target_year, month, day)
            return date_obj.strftime('%Y-%m-%d')
        except Exception:
            self.logger.warning(f"Could not parse Maybank date: {date_str}")
            return date_str
    
    def clean_description(self, description: str) -> str:
        """
        Clean and normalize transaction description.
        """
        # Remove extra whitespace and normalize
        cleaned = ' '.join(description.split())
        return cleaned.strip()
    
    def is_valid_transaction(self, description: str) -> bool:
        """
        Check if the description represents a valid transaction.
        """
        # Skip non-transaction lines
        skip_keywords = [
            'BALANCE', 'LIMIT', 'STATEMENT', 'PREVIOUS', 'CURRENT', 'MINIMUM',
            'RETAIL INTEREST RATE', 'YOUR COMBINED', 'KOMBINASI HAD',
            'JUMLAH PENYATA', 'TRANSACTED AMOUNT', 'USD', 'FOREIGN EXCHANGE'
        ]
        
        description_upper = description.upper()
        return not any(keyword in description_upper for keyword in skip_keywords)
    
    def parse_transactions(self, text: str, filename: str) -> List[Dict]:
        """
        Parse transactions from extracted text.
        """
        transactions = []
        seen_transactions = set()  # To avoid duplicates
        
        # Extract statement year from PDF content
        statement_year = self.extract_statement_year(text)
        if not statement_year:
            self.logger.warning(f"Could not detect statement year for {filename}")
        
        matches = self.transaction_pattern.findall(text)
        
        for match in matches:
            try:
                posting_date, transaction_date, description, amount, cr_flag = match
                
                # Clean and validate description
                description = self.clean_description(description)
                if not description or len(description) < 3:
                    continue
                
                # Skip non-transaction lines
                if not self.is_valid_transaction(description):
                    continue
                
                # Parse amount (remove commas first)
                try:
                    amount_float = float(amount.replace(',', ''))
                except ValueError:
                    continue
                
                # Determine transaction type
                transaction_type = 'CREDIT' if cr_flag == 'CR' else 'DEBIT'
                
                # Parse dates using statement year from PDF content
                parsed_posting_date = self.parse_date_maybank(posting_date, statement_year)
                parsed_transaction_date = self.parse_date_maybank(transaction_date, statement_year)
                
                # Create unique identifier to avoid duplicates
                transaction_id = f"{transaction_date}_{description}_{amount}"
                if transaction_id in seen_transactions:
                    continue
                seen_transactions.add(transaction_id)
                
                transaction = {
                    'date': parsed_transaction_date,
                    'posting_date': parsed_posting_date,
                    'transaction_date': parsed_transaction_date,
                    'description': description,
                    'amount': amount_float,
                    'type': transaction_type,
                    'source_file': filename
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                self.logger.warning(f"Error parsing transaction {match} in {filename}: {e}")
                continue
        
        return transactions
    
    def extract_balance_info(self, text: str) -> Optional[float]:
        """
        Extract balance information from the statement.
        """
        balance_match = self.balance_pattern.search(text)
        if balance_match:
            try:
                return float(balance_match.group(1))
            except ValueError:
                return None
        return None
    
    def extract_total_debit(self, text: str) -> Optional[float]:
        """
        Extract total debit amount from the statement for validation.
        Looks for "TOTAL DEBIT THIS MONTH (JUMLAH DEBIT)" and similar patterns.
        """
        # Pattern to match total debit amounts
        total_patterns = [
            r'\(JUMLAH DEBIT\)([\d,]+\.\d{2})',
            r'TOTAL DEBIT THIS MONTH\s*\(JUMLAH DEBIT\)\s*([\d,]+\.\d{2})',
            r'TOTAL DEBIT THIS MONTH\s+([\d,]+\.\d{2})',
            r'JUMLAH DEBIT\s*([\d,]+\.\d{2})',
            r'TOTAL DEBIT\s+([\d,]+\.\d{2})',
            r'Total Debit\s+([\d,]+\.\d{2})',
            r'DEBIT TOTAL\s+([\d,]+\.\d{2})',
            r'Debit Total\s+([\d,]+\.\d{2})'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Remove commas and convert to float
                    amount_str = match.group(1).replace(',', '')
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def validate_debit_transactions(self, transactions: List[Dict], text: str, filename: str) -> bool:
        """
        Validate debit transactions for the month.
        Compares the sum of parsed debit transactions against the PDF total debit amount.
        """
        # Calculate sum of debit transactions
        debit_transactions = [t for t in transactions if t['type'] == 'DEBIT']
        calculated_debit_sum = sum(t['amount'] for t in debit_transactions)
        
        if not debit_transactions:
            return True
        
        # Extract total debit from PDF
        pdf_total_debit = self.extract_total_debit(text)
        
        if pdf_total_debit is not None:
            # Compare with tolerance for floating point precision
            tolerance = 0.01
            is_valid = abs(calculated_debit_sum - pdf_total_debit) <= tolerance
            
            if not is_valid:
                self.logger.error(f"✗ Validation failed: {filename} - Expected RM{pdf_total_debit:.2f}, got RM{calculated_debit_sum:.2f}")
                self.logger.warning(f"⚠️  Please manually check {filename} for transaction accuracy")
            
            return is_valid
        else:
            # No PDF total found - cannot validate
            self.logger.warning(f"⚠️  No validation total found in {filename} - please verify transactions manually")
            return True  # Cannot validate, but don't fail
    
    def process_all_statements(self) -> List[Dict]:
        """
        Process all PDF files in the specified folder.
        """
        if not os.path.exists(self.pdf_folder):
            self.logger.error(f"Folder '{self.pdf_folder}' does not exist.")
            return []
        
        all_transactions = []
        processed_files = 0
        
        pdf_files = [f for f in os.listdir(self.pdf_folder) if f.endswith('.pdf')]
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found in '{self.pdf_folder}'")
            return []
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process...")
        
        for filename in sorted(pdf_files):
            pdf_path = os.path.join(self.pdf_folder, filename)
            
            text = self.extract_text_from_pdf(pdf_path)
            if text:
                transactions = self.parse_transactions(text, filename)
                balance = self.extract_balance_info(text)
                
                # Create summary message
                balance_info = f", Balance: RM{balance:.2f}" if balance else ""
                self.logger.info(f"✓ {filename}: {len(transactions)} transactions{balance_info}")
                
                # Validate debit transactions
                self.validate_debit_transactions(transactions, text, filename)
                
                all_transactions.extend(transactions)
                processed_files += 1
            else:
                self.logger.error(f"✗ Failed to extract text from {filename}")
        
        self.logger.info(f"Processed {processed_files} files successfully.")
        self.logger.info(f"Total transactions extracted: {len(all_transactions)}")
        
        return all_transactions
    
    def save_to_csv(self, transactions: List[Dict], filename: str = "maybank_transactions.csv"):
        """
        Save transactions to CSV file.
        """
        if not transactions:
            self.logger.warning("No transactions to save to CSV.")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'posting_date', 'transaction_date', 'description', 'amount', 'type', 'source_file']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for transaction in transactions:
                    writer.writerow(transaction)
            
            self.logger.info(f"Transactions saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {e}")
    
    def save_to_json(self, transactions: List[Dict], filename: str = "maybank_transactions.json"):
        """
        Save transactions to JSON file.
        """
        if not transactions:
            self.logger.warning("No transactions to save to JSON.")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(transactions, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Transactions saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving to JSON: {e}")
    
    def print_summary(self, transactions: List[Dict]):
        """
        Log a summary of extracted transactions.
        """
        if not transactions:
            self.logger.warning("No transactions found.")
            return
        
        credit_amount = sum(t['amount'] for t in transactions if t['type'] == 'CREDIT')
        debit_amount = sum(t['amount'] for t in transactions if t['type'] == 'DEBIT')
        
        self.logger.info(f"📊 Summary: {len(transactions)} transactions | Credits: RM{credit_amount:.2f} | Debits: RM{debit_amount:.2f}")
        
        # Show sample transactions
        self.logger.info("📋 Sample transactions:")
        for i, transaction in enumerate(transactions[:3]):
            desc = transaction['description'][:35] + "..." if len(transaction['description']) > 35 else transaction['description']
            self.logger.info(f"   {transaction['date']} | {desc:<38} | RM{transaction['amount']:>8.2f}")
        
        if len(transactions) > 3:
            self.logger.info(f"   ... and {len(transactions) - 3} more transactions")


def main():
    """
    Main function to run the Maybank statement parser.
    """
    # Initialize parser with INFO level logging
    parser = MaybankStatementParser(log_level="INFO")
    
    parser.logger.info("Starting Maybank PDF Statement Parser...")
    
    # Process all statements
    transactions = parser.process_all_statements()
    
    if transactions:
        # Print summary
        parser.print_summary(transactions)
        
        # Save to files
        parser.save_to_csv(transactions)
        parser.save_to_json(transactions)
        
        parser.logger.info("✓ Processing completed successfully!")
    else:
        parser.logger.error("✗ No transactions extracted. Check PDF files and folder path.")


if __name__ == "__main__":
    main()