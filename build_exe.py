import PyInstaller.__main__
import os

if __name__ == '__main__':
    PyInstaller.__main__.run([
        'annotate_and_merge.py',
        '--onefile',
        '--noconsole',
        '--name=PDFAnnotator',
        '--clean',
    ])
