#!/usr/bin/env python3
"""
Maybank PDF Statement Parser - Final Optimized Version
Consolidated and improved version with better error handling and duplicate elimination.
"""

import os
import re
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import PyPDF2


class MaybankStatementParser:
    def __init__(self, pdf_folder: str = "./Drop"):
        self.pdf_folder = pdf_folder
        # Optimized regex pattern for Maybank statement format
        # Matches: Posting Date + Transaction Date + Description + Amount + Optional CR
        self.transaction_pattern = re.compile(
            r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(\d+\.\d{2})(CR)?\s*$', 
            re.MULTILINE
        )
        
        # Pattern for balance information
        self.balance_pattern = re.compile(r'BALANCE\s+(\d+\.\d{2})')
        
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extract text from a PDF file with error handling.
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page_num, page in enumerate(reader.pages):
                    try:
                        text += page.extract_text() + '\n'
                    except Exception as e:
                        print(f"Warning: Could not extract text from page {page_num + 1} of {pdf_path}: {e}")
                        continue
                return text
        except FileNotFoundError:
            print(f"Error: File not found: {pdf_path}")
            return None
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return None
    
    def parse_date_maybank(self, date_str: str) -> str:
        """
        Parse Maybank date format (DD/MM) and add appropriate year.
        """
        try:
            # Extract month and day
            day, month = map(int, date_str.split('/'))
            current_date = datetime.now()
            current_year = current_date.year
            
            # Create date with current year
            try:
                date_obj = datetime(current_year, month, day)
                # If the date is more than 6 months in the future, use previous year
                if (date_obj - current_date).days > 180:
                    date_obj = datetime(current_year - 1, month, day)
            except ValueError:
                # Invalid date, use previous year
                date_obj = datetime(current_year - 1, month, day)
            
            return date_obj.strftime('%Y-%m-%d')
        except Exception:
            print(f"Warning: Could not parse Maybank date: {date_str}")
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
                
                # Parse amount
                try:
                    amount_float = float(amount)
                except ValueError:
                    continue
                
                # Determine transaction type
                transaction_type = 'CREDIT' if cr_flag == 'CR' else 'DEBIT'
                
                # Parse dates
                parsed_posting_date = self.parse_date_maybank(posting_date)
                parsed_transaction_date = self.parse_date_maybank(transaction_date)
                
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
                print(f"Warning: Error parsing transaction {match}: {e}")
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
    
    def process_all_statements(self) -> List[Dict]:
        """
        Process all PDF files in the specified folder.
        """
        if not os.path.exists(self.pdf_folder):
            print(f"Error: Folder '{self.pdf_folder}' does not exist.")
            return []
        
        all_transactions = []
        processed_files = 0
        
        pdf_files = [f for f in os.listdir(self.pdf_folder) if f.endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in '{self.pdf_folder}'")
            return []
        
        print(f"Found {len(pdf_files)} PDF files to process...")
        
        for filename in sorted(pdf_files):
            pdf_path = os.path.join(self.pdf_folder, filename)
            print(f"Processing: {filename}")
            
            text = self.extract_text_from_pdf(pdf_path)
            if text:
                transactions = self.parse_transactions(text, filename)
                balance = self.extract_balance_info(text)
                
                print(f"  - Extracted {len(transactions)} transactions")
                if balance:
                    print(f"  - Balance found: {balance:.2f}")
                
                all_transactions.extend(transactions)
                processed_files += 1
            else:
                print(f"  - Failed to extract text")
        
        print(f"\nProcessed {processed_files} files successfully.")
        print(f"Total transactions extracted: {len(all_transactions)}")
        
        return all_transactions
    
    def save_to_csv(self, transactions: List[Dict], filename: str = "maybank_transactions.csv"):
        """
        Save transactions to CSV file.
        """
        if not transactions:
            print("No transactions to save.")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'posting_date', 'transaction_date', 'description', 'amount', 'type', 'source_file']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for transaction in transactions:
                    writer.writerow(transaction)
            
            print(f"Transactions saved to {filename}")
        except Exception as e:
            print(f"Error saving to CSV: {e}")
    
    def save_to_json(self, transactions: List[Dict], filename: str = "maybank_transactions.json"):
        """
        Save transactions to JSON file.
        """
        if not transactions:
            print("No transactions to save.")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(transactions, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Transactions saved to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")
    
    def print_summary(self, transactions: List[Dict]):
        """
        Print a summary of extracted transactions.
        """
        if not transactions:
            print("No transactions found.")
            return
        
        print("\n" + "="*50)
        print("TRANSACTION SUMMARY")
        print("="*50)
        
        total_amount = sum(t['amount'] for t in transactions)
        credit_amount = sum(t['amount'] for t in transactions if t['type'] == 'CREDIT')
        debit_amount = sum(t['amount'] for t in transactions if t['type'] == 'DEBIT')
        unique_descriptions = set(t['description'] for t in transactions)
        
        print(f"Total transactions: {len(transactions)}")
        print(f"Total amount: RM {total_amount:.2f}")
        print(f"Credit amount: RM {credit_amount:.2f}")
        print(f"Debit amount: RM {debit_amount:.2f}")
        print(f"Unique transaction types: {len(unique_descriptions)}")
        
        # Show first few transactions as examples
        print("\nSample transactions:")
        for i, transaction in enumerate(transactions[:5]):
            print(f"{i+1}. {transaction['date']} | {transaction['description'][:40]:<40} | RM {transaction['amount']:>8.2f} | {transaction['type']}")
        
        if len(transactions) > 5:
            print(f"... and {len(transactions) - 5} more transactions")


def main():
    """
    Main function to run the parser.
    """
    print("Maybank PDF Statement Parser - Final Version")
    print("============================================\n")
    
    # Initialize parser
    parser = MaybankStatementParser()
    
    # Process all statements
    transactions = parser.process_all_statements()
    
    if transactions:
        # Print summary
        parser.print_summary(transactions)
        
        # Save to files
        parser.save_to_csv(transactions)
        parser.save_to_json(transactions)
        
        print("\nProcessing completed successfully!")
    else:
        print("No transactions were extracted. Please check your PDF files and folder path.")


if __name__ == "__main__":
    main()