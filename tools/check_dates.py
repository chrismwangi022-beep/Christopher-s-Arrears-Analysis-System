import sys, os
from importlib import import_module

# Ensure project root is on sys.path so we can import `src` as a package
sys.path.insert(0, os.getcwd())
mod = import_module('src.data_loader')
extract_date_from_filename = mod.extract_date_from_filename

files = [f for f in os.listdir('data') if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
print('Found', len(files), 'files')
for f in sorted(files):
    print(f, '->', extract_date_from_filename(f))
