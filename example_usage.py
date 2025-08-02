#!/usr/bin/env python3
"""
Example usage of the Maybank Statement Parser with different logging levels.
"""

from maybank_parser import MaybankStatementParser

def main():
    print("Maybank Parser - Example Usage")
    print("==============================\n")
    
    # Example 1: Default INFO level logging
    print("1. Running with INFO level logging (default):")
    parser_info = MaybankStatementParser(log_level="INFO")
    transactions = parser_info.process_all_statements()
    
    if transactions:
        parser_info.print_summary(transactions)
        print(f"\nProcessed {len(transactions)} transactions with INFO logging.\n")
    
    # Example 2: DEBUG level logging (more verbose)
    print("\n" + "="*50)
    print("2. Running with DEBUG level logging (verbose):")
    parser_debug = MaybankStatementParser(log_level="DEBUG")
    # Process just one file for demo
    import os
    pdf_files = [f for f in os.listdir(parser_debug.pdf_folder) if f.endswith('.pdf')]
    if pdf_files:
        filename = pdf_files[0]
        pdf_path = os.path.join(parser_debug.pdf_folder, filename)
        text = parser_debug.extract_text_from_pdf(pdf_path)
        if text:
            transactions_debug = parser_debug.parse_transactions(text, filename)
            print(f"\nProcessed {len(transactions_debug)} transactions with DEBUG logging.\n")
    
    # Example 3: WARNING level logging (minimal output)
    print("\n" + "="*50)
    print("3. Running with WARNING level logging (minimal):")
    parser_warning = MaybankStatementParser(log_level="WARNING")
    transactions_warning = parser_warning.process_all_statements()
    print(f"\nProcessed {len(transactions_warning)} transactions with WARNING logging.\n")
    
    print("\nCheck the log file at: logs/maybank_parser.log")
    print("The log file contains all messages from all runs.")

if __name__ == "__main__":
    main()