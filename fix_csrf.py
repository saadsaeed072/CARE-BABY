import os
import re

template_dir = r"d:\CARE BABY\templates"

for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith(".html"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find <form ... method="POST" ... > and insert the hidden input right after
            # Be careful that re.sub doesn't replace the same ones twice if already run!
            if 'csrf_token()' not in content:
                # Add after forms that use method POST
                new_content = re.sub(
                    r'(<form[^>]*method\s*=\s*["\']POST["\'][^>]*>)',
                    r'\1\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>',
                    content,
                    flags=re.IGNORECASE
                )
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated {path}")
