#!/usr/bin/env python3
import sys
import os
import traceback

# Add parent directory to Python path to find hdlparse module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hdlparse.verilog_parser import parse_verilog_file, VerilogModule, VerilogLexer

def debug_file_encoding(filename):
    """Try to read file with different encodings and show results"""
    print("\n=== File Encoding Debug ===")
    encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
    
    file_size = os.path.getsize(filename)
    print(f"File size: {file_size} bytes")
    
    for encoding in encodings:
        try:
            with open(filename, 'rt', encoding=encoding) as f:
                content = f.read()
                print(f"✓ {encoding}: Successfully read {len(content)} characters")
        except UnicodeDecodeError as e:
            print(f"✗ {encoding}: Failed at position {e.start} - {str(e)}")

def debug_lexer_tokens(text):
    """Show lexer tokens for debugging"""
    print("\n=== Lexer Token Debug ===")
    try:
        for pos, action, groups in VerilogLexer.run(text):
            if action:  # Skip None actions
                print(f"Position: {pos}, Action: {action}")
                if groups:
                    print(f"  Groups: {groups}")
    except Exception as e:
        print(f"Lexer error at position {pos}: {str(e)}")
        print(f"Context: {text[max(0, pos-50):pos]}>>>>{text[pos:min(len(text), pos+50)]}")

def print_module_detailed(module):
    """Print detailed information about a Verilog module"""
    print(f"\n=== Module: {module.name} ===")
    
    if module.desc:
        print("\nDescription:")
        print(f"  {module.desc}")
    
    print("\nParameters/Generics:")
    if module.generics:
        for param in module.generics:
            print(f"  Name: {param.name}")
            print(f"    Type: {param.data_type}")
            print(f"    Mode: {param.mode}")
            print(f"    Default: {param.default_value}")
            if param.desc:
                print(f"    Description: {param.desc}")
    else:
        print("  None")
    
    print("\nPorts:")
    if module.ports:
        for port in module.ports:
            print(f"  Name: {port.name}")
            print(f"    Mode: {port.mode}")
            print(f"    Type: {port.data_type}")
            if port.desc:
                print(f"    Description: {port.desc}")
    else:
        print("  None")
    
    print("\nSubmodules:")
    if module.submodules:
        for sub in module.submodules:
            print(f"  Instance: {sub.instance_name}")
            print(f"    Type: {sub.module_type}")
            if sub.port_connections:
                print("    Port Connections:")
                for port, conn in sub.port_connections.items():
                    print(f"      {port} => {conn}")
            if sub.desc:
                print(f"    Description: {sub.desc}")
    else:
        print("  None")
    
    if module.sections:
        print("\nSections:")
        for section, ports in module.sections.items():
            print(f"  {section}:")
            for port in ports:
                print(f"    {port}")

def debug_file_content(filename):
    """Show file content statistics and potential issues"""
    print("\n=== File Content Debug ===")
    with open(filename, 'rb') as f:
        content = f.read()
    
    print(f"File size: {len(content)} bytes")
    
    # Check for common special bytes that might cause issues
    special_bytes = {
        b'\x00': 'NULL',
        b'\xff': 'xFF',
        b'\xef\xbb\xbf': 'UTF-8 BOM',
        b'\xfe\xff': 'UTF-16 BE BOM',
        b'\xff\xfe': 'UTF-16 LE BOM'
    }
    
    for byte_seq, name in special_bytes.items():
        if byte_seq in content:
            print(f"Found {name} bytes at position(s):", end=' ')
            pos = -1
            while True:
                pos = content.find(byte_seq, pos + 1)
                if pos == -1:
                    break
                print(pos, end=' ')
            print()

def main():
    if len(sys.argv) != 2:
        print("Usage: python test/debug_verilog_file.py <verilog_file>")
        sys.exit(1)
    
    verilog_file = sys.argv[1]
    if not os.path.exists(verilog_file):
        print(f"Error: File '{verilog_file}' not found")
        sys.exit(1)
    
    try:
        print(f"\nDebugging Verilog file: {verilog_file}")
        print("=" * 60)
        
        # Debug file content and encoding
        debug_file_content(verilog_file)
        debug_file_encoding(verilog_file)
        
        # Read file content
        with open(verilog_file, 'rt', encoding='latin-1') as f:
            content = f.read()
            print(f"\nSuccessfully read {len(content)} characters")
        
        # Debug lexer tokens
        debug_lexer_tokens(content)
        
        # Parse modules
        print("\n=== Parsing Modules ===")
        modules = parse_verilog_file(verilog_file)
        print(f"\nFound {len(modules)} module(s)")
        
        # Print detailed module information
        for module in modules:
            print_module_detailed(module)
            
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 