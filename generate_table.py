import sys
import argparse
import os

def parse_and_generate(input_path, output_path):
    with open(input_path, 'r') as f:
        lines = f.readlines()
        
    table_lines = []
    table_lines.append("| Hostname | IP Address | Type |")
    table_lines.append("|---|---|---|")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split('\t')
        if len(parts) < 3:
            continue
            
        ip_host_part = parts[0]
        if ' / ' in ip_host_part:
            ip_part, host_part = ip_host_part.split(' / ', 1)
        else:
            ip_part = ip_host_part
            host_part = "Unknown"
            
        ip = ip_part.strip()
        hostname = host_part.strip()
        
        raw_type = parts[2].strip()
        if 'Wi-Fi' in raw_type:
            device_type = 'Wi-Fi'
        elif 'Ethernet' in raw_type:
            device_type = 'Ethernet'
        else:
            device_type = raw_type
            
        table_lines.append(f"| {hostname} | {ip} | {device_type} |")
        
    # Ensure output dir exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write('\n'.join(table_lines) + '\n')

def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate markdown table from device list')
    parser.add_argument('--input', '-i', default='device_list.txt', help='Input device list path')
    parser.add_argument('--output', '-o', default='device_table.md', help='Output markdown path')
    args = parser.parse_args(argv)
    parse_and_generate(args.input, args.output)

if __name__ == '__main__':
    main()
