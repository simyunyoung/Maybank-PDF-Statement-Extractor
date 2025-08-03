#!/usr/bin/env python3
"""
Maybank PDF Statement Parser - Enhanced Multi-Format Version
Supports both Maybank Credit Card and Current Account statements.
"""

import os
import re
import json
import csv
import getpass
from datetime import datetime
from typing import List, Dict, Optional, Literal
import PyPDF2
from enum import Enum

class StatementType(Enum):
    CREDIT_CARD = "credit_card"
    CURRENT_ACCOUNT = "current_account"
    AUTO_DETECT = "auto_detect"


class MaybankStatementParser:
    def __init__(self, pdf_folder: str = "./Drop", statement_type: StatementType = StatementType.CREDIT_CARD):
        self.pdf_folder = pdf_folder
        self.statement_type = statement_type
        self.validation_results = []  # Track validation results
        self.password_cache = {}  # Cache passwords for files
        self.use_same_password = None  # User preference for password handling
        self.common_password = None  # Common password if user chooses same for all
        
        # Credit Card regex pattern (original)
        # Matches: Posting Date + Transaction Date + Description + Amount + Optional CR
        self.credit_card_pattern = re.compile(
            r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2})(CR)?\s*$', 
            re.MULTILINE
        )
        
        # Current Account regex patterns
        # Pattern 1: Maybank current account format - Date + Description + Amount + Balance
        # Format: DD/MM DESCRIPTION AMOUNT+/- BALANCE
        self.current_account_pattern1 = re.compile(
            r'(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2}[+-])\s+([\d,]+\.\d{2})',
            re.MULTILINE
        )
        
        # Pattern 2: Alternative format with separate debit/credit columns
        self.current_account_pattern2 = re.compile(
            r'(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s+(DR|CR)\s+([\d,]+\.\d{2})',
            re.MULTILINE
        )
        
        # Pattern for balance information
        self.balance_pattern = re.compile(r'BALANCE\s+([\d,]+\.\d{2})')
        
        # Statement type detection patterns
        self.credit_card_indicators = [
            r'CREDIT CARD STATEMENT',
            r'MAYBANK CREDIT CARD',
            r'CARD NUMBER',
            r'CREDIT LIMIT',
            r'MINIMUM PAYMENT'
        ]
        
        self.current_account_indicators = [
            r'ACCOUNT TRANSACTIONS',
            r'URUSNIAGA AKAUN',
            r'CURRENT ACCOUNT STATEMENT',
            r'SAVINGS ACCOUNT STATEMENT', 
            r'ACCOUNT NUMBER',
            r'OPENING BALANCE',
            r'CLOSING BALANCE',
            r'BEGINNING BALANCE',
            r'STATEMENT BALANCE',
            r'CDM CASH DEPOSIT',
            r'TRANSFER TO A/C'
        ]
        

    
    def detect_statement_type(self, text: str) -> StatementType:
        """Detect whether the PDF is a credit card or current account statement."""
        text_upper = text.upper()
        
        credit_card_score = 0
        current_account_score = 0
        
        # Check for credit card indicators
        for indicator in self.credit_card_indicators:
            if re.search(indicator, text_upper):
                credit_card_score += 1
        
        for indicator in self.current_account_indicators:
            if re.search(indicator, text_upper):
                current_account_score += 1
        
        if credit_card_score > current_account_score:
            return StatementType.CREDIT_CARD
        elif current_account_score > credit_card_score:
            return StatementType.CURRENT_ACCOUNT
        else:
            # Default to credit card if unclear
            print("⚠️  Could not clearly detect statement type, defaulting to credit card")
            return StatementType.CREDIT_CARD
        
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from a PDF file with error handling and password support.
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Check if PDF is encrypted
                if reader.is_encrypted:
                    print(f"🔒 Encrypted PDF detected: {os.path.basename(pdf_path)}")
                    
                    # First try empty password (some Maybank PDFs use this)
                    try:
                        empty_result = reader.decrypt("")
                        if empty_result > 0:
                            print(f"✅ Successfully decrypted PDF with empty password: {os.path.basename(pdf_path)}")
                        else:
                            # Empty password failed, try with user-provided password
                            max_password_attempts = 3
                            for attempt in range(max_password_attempts):
                                password = self._get_password_for_file(pdf_path, attempt)
                                if password is None:
                                    print(f"❌ No password provided for encrypted PDF: {pdf_path}")
                                    return None
                                
                                try:
                                    decrypt_result = reader.decrypt(password)
                                    if decrypt_result == 0:
                                        print(f"❌ Failed to decrypt PDF: {os.path.basename(pdf_path)} - Incorrect password (attempt {attempt + 1}/{max_password_attempts})")
                                        # Clear the cached password so user can try again
                                        filename = os.path.basename(pdf_path)
                                        if filename in self.password_cache:
                                            del self.password_cache[filename]
                                        # If using same password for all, clear that too
                                        if self.use_same_password:
                                            self.common_password = None
                                        
                                        # If this was the last attempt, return None
                                        if attempt == max_password_attempts - 1:
                                            print(f"❌ Maximum password attempts exceeded for {os.path.basename(pdf_path)}")
                                            return None
                                        # Otherwise, continue to next attempt
                                        continue
                                    elif decrypt_result == 1:
                                        print(f"✅ Successfully decrypted PDF: {os.path.basename(pdf_path)}")
                                        break
                                    elif decrypt_result == 2:
                                        print(f"✅ Successfully decrypted PDF with owner password: {os.path.basename(pdf_path)}")
                                        break
                                except Exception as e:
                                    print(f"❌ Error during decryption of {os.path.basename(pdf_path)}: {e}")
                                    if attempt == max_password_attempts - 1:
                                        return None
                    except Exception as e:
                        print(f"❌ Error trying empty password for {os.path.basename(pdf_path)}: {e}")
                        return None
                
                text = ''
                for page_num, page in enumerate(reader.pages):
                    try:
                        text += page.extract_text() + '\n'
                    except Exception as e:
                        continue
                return text
        except FileNotFoundError:
            print(f"❌ File not found: {pdf_path}")
            return None
        except Exception as e:
            print(f"❌ Error reading PDF {pdf_path}: {e}")
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
        Parse transactions from extracted text based on statement type.
        """
        transactions = []
        seen_transactions = set()  # To avoid duplicates
        
        # Extract statement year from PDF content
        statement_year = self.extract_statement_year(text)
        
        # Parse based on statement type
        if self.statement_type == StatementType.CREDIT_CARD:
            transactions = self._parse_credit_card_transactions(text, filename, statement_year, seen_transactions)
        elif self.statement_type == StatementType.CURRENT_ACCOUNT:
            transactions = self._parse_current_account_transactions(text, filename, statement_year, seen_transactions)
        else:
            print(f"⚠️  Unknown statement format detected in {filename}. Please check the file manually.")
            return []
        
        return transactions
    
    def _parse_credit_card_transactions(self, text: str, filename: str, statement_year: int, seen_transactions: set) -> List[Dict]:
        """
        Parse credit card transactions using the original pattern.
        """
        transactions = []
        matches = self.credit_card_pattern.findall(text)
        
        if not matches:
            print(f"⚠️  No credit card transactions found in {filename}. Format may be unexpected.")
        
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
                    continue
        
        return transactions
    
    def _parse_current_account_transactions(self, text: str, filename: str, statement_year: int, seen_transactions: set) -> List[Dict]:
        """
        Parse current account transactions with multi-line descriptions.
        """
        transactions = []
        lines = text.split('\n')
        
        # Main transaction pattern: DD/MM DESCRIPTION AMOUNT+/- BALANCE
        transaction_pattern = re.compile(r'^(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2}[+-])\s+([\d,]+\.\d{2})\s*$')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            match = transaction_pattern.match(line)
            
            if match:
                try:
                    date_str, base_description, amount_with_sign, balance_str = match.groups()
                    
                    # Collect multi-line description
                    full_description = base_description.strip()
                    detail_lines = []
                    
                    # Look ahead for detail lines (lines that start with spaces or specific patterns)
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        # Stop if we hit another transaction or empty line
                        if (transaction_pattern.match(next_line.strip()) or 
                            not next_line.strip() or
                            next_line.strip().startswith('BEGINNING BALANCE') or
                            next_line.strip().startswith('ENDING BALANCE')):
                            break
                        
                        # Collect detail lines (usually indented or contain specific info)
                        if (next_line.startswith('   ') or 
                            re.match(r'^\s+[A-Z0-9*\s]+$', next_line) or
                            'DUITNOW' in next_line or
                            re.match(r'^\s+\d+Q?$', next_line)):
                            detail_lines.append(next_line.strip())
                        j += 1
                    
                    # Combine description with details
                    if detail_lines:
                        # Filter out lines that are just '*' but keep account numbers and meaningful details
                        meaningful_details = []
                        for detail in detail_lines:
                            if (detail and detail != '*' and len(detail) > 1):
                                # Keep account numbers (long numeric strings) and other meaningful text
                                if (re.match(r'^\d{10,}', detail) or  # Account numbers (10+ digits)
                                    re.match(r'^\d+Q$', detail) or      # Reference codes ending with Q
                                    re.match(r'^[A-Z][A-Z0-9\s*]+$', detail) or  # Names and text
                                    'DUITNOW' in detail or
                                    len(detail) > 3):  # Other meaningful text
                                    meaningful_details.append(detail)
                        
                        if meaningful_details:
                            full_description += ' | ' + ' | '.join(meaningful_details)
                    
                    # Clean and validate description
                    full_description = self.clean_description(full_description)
                    if not full_description or len(full_description) < 3:
                        i = j
                        continue
                    
                    # Skip non-transaction lines
                    if not self.is_valid_transaction(full_description):
                        i = j
                        continue
                    
                    # Parse amount and determine type
                    amount_float = 0.0
                    transaction_type = 'UNKNOWN'
                    
                    if amount_with_sign.endswith('+'):
                        try:
                            amount_float = float(amount_with_sign[:-1].replace(',', ''))
                            transaction_type = 'CREDIT'
                        except ValueError:
                            i = j
                            continue
                    elif amount_with_sign.endswith('-'):
                        try:
                            amount_float = float(amount_with_sign[:-1].replace(',', ''))
                            transaction_type = 'DEBIT'
                        except ValueError:
                            i = j
                            continue
                    else:
                        i = j
                        continue  # Skip if no amount found
                    
                    # Parse date (current account uses DD/MM format)
                    parsed_date = self._parse_current_account_date(date_str, statement_year)
                    
                    # Create unique identifier to avoid duplicates
                    # Include detail lines and balance to distinguish between similar transactions
                    detail_summary = '|'.join(detail_lines[:3]) if detail_lines else ''
                    transaction_id = f"{date_str}_{full_description}_{amount_float}_{detail_summary}_{balance_str}"
                    if transaction_id in seen_transactions:
                        i = j
                        continue
                    seen_transactions.add(transaction_id)
                    
                    transaction = {
                        'date': parsed_date,
                        'posting_date': parsed_date,
                        'transaction_date': parsed_date,
                        'description': full_description,
                        'amount': amount_float,
                        'type': transaction_type,
                        'source_file': filename
                    }
                    
                    transactions.append(transaction)
                    i = j
                    
                except Exception as e:
                    i += 1
                    continue
            else:
                i += 1
        
        return transactions
    
    def _parse_current_account_date(self, date_str: str, statement_year: int = None) -> str:
        """
        Parse current account date format (DD/MM) and add year.
        """
        try:
            # Handle DD/MM format
            if '/' in date_str and len(date_str.split('/')) == 2:
                day, month = date_str.split('/')
                year = statement_year or datetime.now().year
                date_obj = datetime(year, int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            # Handle DD/MM/YYYY format (fallback)
            elif '/' in date_str and len(date_str.split('/')) == 3:
                date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                return date_obj.strftime('%Y-%m-%d')
            else:
                return date_str
        except ValueError:
            return date_str
    
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
        Looks for "TOTAL DEBIT : amount" and similar patterns.
        """
        # Pattern to match total debit amounts
        total_patterns = [
            r'TOTAL DEBIT\s*:\s*([\d,]+\.\d{2})',
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
            self.validation_results.append({
                'filename': filename,
                'status': 'NO_DEBITS',
                'calculated_sum': 0.0,
                'pdf_total': None,
                'difference': 0.0
            })
            return True
        
        # Extract total debit from PDF
        pdf_total_debit = self.extract_total_debit(text)
        
        if pdf_total_debit is not None:
            # Compare with tolerance for floating point precision
            tolerance = 0.01
            difference = abs(calculated_debit_sum - pdf_total_debit)
            is_valid = difference <= tolerance
            
            # Store validation result
            self.validation_results.append({
                'filename': filename,
                'status': 'PASS' if is_valid else 'FAIL',
                'calculated_sum': calculated_debit_sum,
                'pdf_total': pdf_total_debit,
                'difference': difference
            })
            
            if not is_valid:
                print(f"✗ Validation failed: {filename} - Expected RM{pdf_total_debit:.2f}, got RM{calculated_debit_sum:.2f}")
                print(f"⚠️  Please manually check {filename} for transaction accuracy")
            
            return is_valid
        else:
            # No PDF total found - cannot validate
            self.validation_results.append({
                'filename': filename,
                'status': 'NO_TOTAL',
                'calculated_sum': calculated_debit_sum,
                'pdf_total': None,
                'difference': None
            })
            print(f"⚠️  No validation total found in {filename} - please verify transactions manually")
            return True  # Cannot validate, but don't fail
    
    def process_all_statements(self) -> List[Dict]:
        """
        Process all PDF files in the specified folder.
        """
        if not os.path.exists(self.pdf_folder):
            print(f"❌ Folder '{self.pdf_folder}' does not exist.")
            return []
        
        all_transactions = []
        processed_files = 0
        
        pdf_files = [f for f in os.listdir(self.pdf_folder) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"⚠️  No PDF files found in '{self.pdf_folder}'")
            return []
        
        print(f"📁 Found {len(pdf_files)} PDF files to process...")
        
        for filename in sorted(pdf_files):
            pdf_path = os.path.join(self.pdf_folder, filename)
            
            text = self.extract_text_from_pdf(pdf_path)
            if text:
                transactions = self.parse_transactions(text, filename)
                balance = self.extract_balance_info(text)
                
                # Create summary message
                balance_info = f", Balance: RM{balance:.2f}" if balance else ""
                print(f"✓ {filename}: {len(transactions)} transactions{balance_info}")
                
                # Validate debit transactions
                self.validate_debit_transactions(transactions, text, filename)
                
                all_transactions.extend(transactions)
                processed_files += 1
            else:
                print(f"✗ Failed to extract text from {filename}")
        
        print(f"📊 Processed {processed_files} files successfully.")
        print(f"📊 Total transactions extracted: {len(all_transactions)}")
        
        return all_transactions
    
    def save_to_csv(self, transactions: List[Dict], filename: str = "maybank_transactions.csv"):
        """
        Save transactions to CSV file.
        """
        if not transactions:
            print("⚠️  No transactions to save to CSV.")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'posting_date', 'transaction_date', 'description', 'amount', 'type', 'source_file']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for transaction in transactions:
                    writer.writerow(transaction)
            
            print(f"💾 Transactions saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
    
    def save_to_json(self, transactions: List[Dict], filename: str = "maybank_transactions.json"):
        """
        Save transactions to JSON file.
        """
        if not transactions:
            print("⚠️  No transactions to save to JSON.")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(transactions, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"💾 Transactions saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")
    
    def print_summary(self, transactions: List[Dict]):
        """
        Log a summary of extracted transactions.
        """
        if not transactions:
            print("⚠️  No transactions found.")
            return
        
        credit_amount = sum(t['amount'] for t in transactions if t['type'] == 'CREDIT')
        debit_amount = sum(t['amount'] for t in transactions if t['type'] == 'DEBIT')
        
        print(f"📊 Summary: {len(transactions)} transactions | Credits: RM{credit_amount:.2f} | Debits: RM{debit_amount:.2f}")
        
        # Show sample transactions
        print("📋 Sample transactions:")
        for i, transaction in enumerate(transactions[:3]):
            desc = transaction['description'][:35] + "..." if len(transaction['description']) > 35 else transaction['description']
            print(f"   {transaction['date']} | {desc:<38} | RM{transaction['amount']:>8.2f}")
        
        if len(transactions) > 3:
            print(f"   ... and {len(transactions) - 3} more transactions")
    
    def _get_password_for_file(self, pdf_path: str, attempt: int = 0) -> Optional[str]:
         """
         Get password for a specific PDF file, with caching and user preference handling.
         """
         filename = os.path.basename(pdf_path)
         
         # Check if we already have a password for this file
         if filename in self.password_cache:
             return self.password_cache[filename]
         
         # Check if user wants to use same password for all files
         if self.use_same_password is None:
             print(f"\n🔒 Password required for: {filename}")
             while True:
                 choice = input("Do you want to use the same password for all PDFs? (y/n): ").strip().lower()
                 if choice in ['y', 'yes']:
                     self.use_same_password = True
                     break
                 elif choice in ['n', 'no']:
                     self.use_same_password = False
                     break
                 else:
                     print("Please enter 'y' for yes or 'n' for no.")
         
         # If using same password for all and we have it, return it
         if self.use_same_password and self.common_password:
             self.password_cache[filename] = self.common_password
             return self.common_password
         
         # Prompt for password
         try:
             if attempt > 0:
                 print(f"\n⚠️  Previous password was incorrect. Attempt {attempt + 1} of 3")
             
             if self.use_same_password and not self.common_password:
                 password = getpass.getpass(f"Enter password for all PDFs: ")
                 if password:
                     self.common_password = password
             else:
                 password = getpass.getpass(f"Enter password for {filename}: ")
             
             if password:
                 self.password_cache[filename] = password
                 return password
             else:
                 print("Empty password entered.")
                 return None
                 
         except KeyboardInterrupt:
             print("\n\nPassword input cancelled.")
             return None
         except Exception as e:
            print(f"❌ Error getting password: {e}")
            return None
    
    def print_validation_summary(self):
        """
        Print a summary of validation results.
        """
        if not self.validation_results:
            return
        
        print(f"\n🔍 Validation Summary:")
        print("-" * 80)
        
        passed = 0
        failed = 0
        no_total = 0
        no_debits = 0
        
        for result in self.validation_results:
            filename = result['filename']
            status = result['status']
            
            if status == 'PASS':
                passed += 1
                print(f"   ✅ {filename:<35} PASS    (Diff: RM{result['difference']:.2f})")
            elif status == 'FAIL':
                failed += 1
                print(f"   ❌ {filename:<35} FAIL    (Expected: RM{result['pdf_total']:.2f}, Got: RM{result['calculated_sum']:.2f})")
            elif status == 'NO_TOTAL':
                no_total += 1
                print(f"   ⚠️  {filename:<35} NO_TOTAL (Cannot validate - no PDF total found)")
            elif status == 'NO_DEBITS':
                no_debits += 1
                print(f"   ℹ️  {filename:<35} NO_DEBITS (No debit transactions found)")
        
        print("-" * 80)
        print(f"   📊 Summary: {passed} passed, {failed} failed, {no_total} no total, {no_debits} no debits")
        
        if failed > 0:
            print(f"   ⚠️  {failed} file(s) failed validation - please review manually")
        elif passed > 0:
            print(f"   ✅ All {passed} file(s) passed validation!")


def get_user_statement_type() -> StatementType:
    """
    Get user's preferred statement type through interactive prompt.
    """
    print("\n" + "="*60)
    print("🏦 MAYBANK PDF STATEMENT PARSER")
    print("="*60)
    print("\nPlease select the type of Maybank statement to process:")
    print("\n1. 💳 Credit Card Statement")
    print("2. 🏛️  Current Account Statement")
    print("\n" + "-"*60)
    
    while True:
        try:
            choice = input("Enter your choice (1-2): ").strip()
            
            if choice == '1':
                print("\n✅ Selected: Credit Card Statement")
                return StatementType.CREDIT_CARD
            elif choice == '2':
                print("\n✅ Selected: Current Account Statement")
                return StatementType.CURRENT_ACCOUNT
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n\n👋 Process interrupted by user. Goodbye!")
            exit(0)
        except Exception as e:
            print(f"❌ Error: {e}. Please try again.")

def main():
    """
    Main function to run the Maybank statement parser.
    """
    try:
        # Get user's statement type preference
        statement_type = get_user_statement_type()
        
        # Initialize parser with selected statement type
        parser = MaybankStatementParser(statement_type=statement_type)
        
        print("\n" + "="*60)
        print("🚀 Starting Maybank PDF Statement Parser...")
        print("📁 Processing PDFs from: ./Drop/")
        
        print("\n⚠️  Note: Unexpected formats will trigger warnings")
        print("-"*60)
        
        # Process all statements
        transactions = parser.process_all_statements()
        
        if transactions:
            print("\n" + "="*60)
            print("📊 PROCESSING SUMMARY")
            print("="*60)
            
            # Print summary
            parser.print_summary(transactions)
            
            # Save to files
            parser.save_to_csv(transactions)
            parser.save_to_json(transactions)
            
            # Print validation summary
            parser.print_validation_summary()
            
            print("\n" + "="*60)
            print("✅ Processing completed successfully!")
            print("📄 Files saved: maybank_transactions.csv, maybank_transactions.json")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("❌ No transactions extracted.")
            print("\n💡 Troubleshooting tips:")
            print("   • Check if PDF files are in the ./Drop/ folder")
            print("   • Verify PDFs are valid Maybank statements")
            print("   • Try different statement type if auto-detect failed")
            print("="*60)
            
    except KeyboardInterrupt:
        print("\n\n👋 Process interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("Please check the error message above for more details.")


if __name__ == "__main__":
    main()