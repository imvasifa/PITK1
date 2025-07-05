import os
import re
from pathlib import Path

def update_logo_paths(directory):
    # Define the correct Flask URL path for the logo
    url_logo_path = "{{ url_for('static', filename='pitk-logo.svg') }}"
    
    # Compile regex patterns to match various logo path formats
    patterns = [
        # Match src attributes with different path formats
        (re.compile(r'src=["\']/static/pitk-logo\.svg["\']'), 'src'),
        (re.compile(r'src=["\']/static/img/pitk-logo\.svg["\']'), 'src'),
        (re.compile(r'src=["\']\.\./static/pitk-logo\.svg["\']'), 'src'),
        (re.compile(r'src=["\']static/pitk-logo\.svg["\']'), 'src'),
        (re.compile(r'src=["\']img/pitk-logo\.svg["\']'), 'src'),
        # Match href attributes (for favicons and links)
        (re.compile(r'href=["\']/static/pitk-logo\.svg["\']'), 'href'),
        (re.compile(r'href=["\']/static/img/pitk-logo\.svg["\']'), 'href'),
        (re.compile(r'href=["\']\.\./static/pitk-logo\.svg["\']'), 'href'),
        (re.compile(r'href=["\']static/pitk-logo\.svg["\']'), 'href'),
        (re.compile(r'href=["\']img/pitk-logo\.svg["\']'), 'href')
    ]
    
    # Walk through all files in the templates directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if any pattern matches
                    updated = False
                    for pattern, attr_type in patterns:
                        if pattern.search(content):
                            # Use the appropriate attribute type (src or href)
                            content = pattern.sub(f'{attr_type}="{url_logo_path}"', content)
                            updated = True
                    
                    # Check for any hardcoded paths that might have been missed
                    if 'pitk-logo.svg' in content and 'url_for' not in content:
                        # If we find the logo filename but no url_for, we should update it
                        # This is a simple check - the actual replacement is done by the patterns above
                        updated = True
                    
                    # Save the file if it was updated
                    if updated:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"Updated logo paths in: {file_path}")
                            
                except Exception as e:
                    print(f"Error processing {file_path}: {str(e)}")

if __name__ == "__main__":
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    update_logo_paths(templates_dir)
    print("Logo path update completed.")
