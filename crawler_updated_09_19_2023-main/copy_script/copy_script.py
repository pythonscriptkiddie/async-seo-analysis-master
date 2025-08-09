import os
import shutil

current_path = '/Users/thomassullivan/Documents/Github/crawler_experiments0'
new_path = '/Users/thomassullivan/Documents/Github/zcrawler_aug_6'
directories = ['crawler', 'formatter',
              'local_data_final','structures', 'reports', 'copy_script']

for item in directories:
    shutil.copytree(src=item, dst=f'{new_path}/{item}')