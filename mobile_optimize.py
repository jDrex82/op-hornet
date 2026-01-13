import re

with open('/app/hornet/dashboard/index.html', 'r') as f:
    html = f.read()

# 1. Fix viewport meta (ensure it's there)
if 'viewport' not in html:
    html = html.replace('<head>', '<head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">')

# 2. Make stat cards responsive: 5 cols -> 2 on mobile, 3 on tablet
html = html.replace('grid grid-cols-5 gap-4 p-6', 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 p-4 lg:p-6')

# 3. Make main content responsive: 3 cols -> stack on mobile
html = html.replace('grid grid-cols-3 gap-6', 'grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6')

# 4. Make incident queue full width on mobile
html = html.replace('col-span-2 bg-black/30', 'col-span-1 lg:col-span-2 bg-black/30')

# 5. Make header responsive
html = html.replace(
    '<header class="bg-black/40 border-b border-gray-800 px-6 py-3">',
    '<header class="bg-black/40 border-b border-gray-800 px-3 sm:px-6 py-3">'
)

# 6. Make modal responsive
html = html.replace('w-4/5 max-w-4xl', 'w-[95%] sm:w-4/5 max-w-4xl')

# 7. Make table scroll horizontally on mobile
html = html.replace(
    '<div class="overflow-y-auto" style="max-height: 500px;">',
    '<div class="overflow-x-auto overflow-y-auto" style="max-height: 500px;">'
)

# 8. Hide some columns on mobile (add responsive classes to table)
# Make ID column smaller on mobile
html = html.replace(
    '<th class="text-left p-3 font-medium">ID</th>',
    '<th class="text-left p-2 sm:p-3 font-medium">ID</th>'
)

# 9. Responsive padding on content area
html = html.replace('px-6 pb-6 grid', 'px-3 sm:px-6 pb-4 sm:pb-6 grid')

# 10. Make login modal responsive
html = html.replace('p-8 rounded-lg shadow-2xl w-96', 'p-6 sm:p-8 rounded-lg shadow-2xl w-[90%] sm:w-96')

# 11. Smaller text on mobile for stats
html = html.replace('text-3xl font-bold text-amber-500 mono', 'text-2xl sm:text-3xl font-bold text-amber-500 mono')
html = html.replace('text-3xl font-bold text-cyan-400 mono', 'text-2xl sm:text-3xl font-bold text-cyan-400 mono')
html = html.replace('text-3xl font-bold text-green-500 mono', 'text-2xl sm:text-3xl font-bold text-green-500 mono')
html = html.replace('text-3xl font-bold text-purple-400 mono', 'text-2xl sm:text-3xl font-bold text-purple-400 mono')
html = html.replace('text-3xl font-bold text-amber-300 mono', 'text-2xl sm:text-3xl font-bold text-amber-300 mono')

with open('/app/hornet/dashboard/index.html', 'w') as f:
    f.write(html)

print('Mobile optimization complete!')
