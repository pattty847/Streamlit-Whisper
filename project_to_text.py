import os
from pathlib import Path
from typing import Set, TextIO
from datetime import datetime

def write_project_to_file(
    startpath: str = '.',
    output_file: str = 'project_contents.txt',
    ignore_dirs: Set[str] = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv'},
    ignore_files: Set[str] = {'.gitignore', '.env', '*.pyc'},
    indent: str = '    '
) -> None:
    """
    Write the entire project structure and file contents to a text file.
    
    Args:
        startpath: Root directory to start from
        output_file: Name of the output file
        ignore_dirs: Directories to ignore
        ignore_files: File patterns to ignore
        indent: Indentation string
    """
    # Convert startpath to absolute path
    startpath = os.path.abspath(startpath)
    
    def should_ignore(path: str, patterns: Set[str]) -> bool:
        """Check if path matches any of the ignore patterns."""
        name = os.path.basename(path)
        return any(
            name == pattern or 
            (pattern.startswith('*') and name.endswith(pattern[1:]))
            for pattern in patterns
        )
    
    def write_file_contents(file_path: str, f: TextIO, indent_level: int) -> None:
        """Write the contents of a file with proper indentation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as source_file:
                f.write(f"{indent * indent_level}File Contents:\n")
                f.write(f"{indent * indent_level}" + "=" * 50 + "\n")
                for line in source_file:
                    f.write(f"{indent * indent_level}{line}")
                f.write(f"{indent * indent_level}" + "=" * 50 + "\n\n")
        except Exception as e:
            f.write(f"{indent * indent_level}[Error reading file: {str(e)}]\n\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header information
        f.write(f"Project Export - {os.path.basename(startpath)}\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        
        # Write project structure and contents
        for root, dirs, files in os.walk(startpath):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if not should_ignore(d, ignore_dirs)]
            
            # Calculate level for indentation
            level = root[len(startpath):].count(os.sep)
            
            # Write directory name
            indent_str = indent * level
            folder_name = os.path.basename(root)
            if level == 0:
                f.write('📁 .\n')
            else:
                f.write(f'{indent_str}📁 {folder_name}\n')
            
            # Write files and their contents
            for file in sorted(files):
                if not should_ignore(file, ignore_files):
                    file_path = os.path.join(root, file)
                    f.write(f'{indent_str}{indent}📄 {file}\n')
                    
                    # Only write contents of text-based files
                    if file.endswith(('.py', '.txt', '.md', '.json', '.yml', '.yaml', '.ini', '.cfg')):
                        write_file_contents(file_path, f, level + 2)

if __name__ == '__main__':
    # Get the project root directory (assuming this script is in the project)
    project_root = str(Path(__file__).parent)
    dir_ = ""
    
    write_project_to_file(
        startpath=dir_ or project_root,
        output_file='full-project.txt',
        ignore_dirs={
            '.git', '__pycache__', '.pytest_cache',
            '.venv', 'venv', 'node_modules', '.idea',
            'workspace', 'docker_workspace','reference',
            'docs', 'tools'
        },
        ignore_files={
            '.gitignore', '.env', '*.pyc', '.DS_Store',
            '*.pyo', '*.pyd', '.Python', '*.so'
        }
    )