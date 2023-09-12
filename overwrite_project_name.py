import argparse
import os

replace_in_files = ['README.md', '.env.example', 'pyproject.toml']
project_directory = 'project_template'


def replace_in_file(file, original, replace_with):
    with open(file, 'r') as f:
        filedata = f.read()

    filedata = filedata.replace(original, replace_with)

    with open(file, 'w') as f:
        f.write(filedata)


def rename_directory(directory_name, new_name):
    os.rename(directory_name, new_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('overwrite_project_name.py')
    parser.add_argument('-pn', '--projectname', required=True, help='Project name to be replaced with')

    args = parser.parse_args()
    project_name = args.projectname

    for file in replace_in_files:
        replace_in_file(file, '{template}', project_name)

    rename_directory(project_directory, f'project_{project_name}')
