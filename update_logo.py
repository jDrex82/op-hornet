import re

with open('/app/hornet/dashboard/index.html', 'r') as f:
    html = f.read()

# Replace [H] text logos with image
html = re.sub(
    r'<span class="text-5xl font-bold text-amber-500">\[H\]</span>',
    '<img src="/dashboard/static/logo.png" alt="HORNET" class="h-16 w-16">',
    html
)

html = re.sub(
    r'<span class="text-3xl font-bold text-amber-500">\[H\]</span>',
    '<img src="/dashboard/static/logo.png" alt="HORNET" class="h-10 w-10">',
    html
)

with open('/app/hornet/dashboard/index.html', 'w') as f:
    f.write(html)

print('Dashboard updated with logo!')
