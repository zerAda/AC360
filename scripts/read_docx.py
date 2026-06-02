import zipfile
import xml.etree.ElementTree as ET
import sys
import glob
import os

def extract_text_from_docx(docx_path):
    try:
        document = zipfile.ZipFile(docx_path)
        xml_content = document.read('word/document.xml')
        document.close()
        tree = ET.XML(xml_content)
        
        WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        PARA = WORD_NAMESPACE + 'p'
        TEXT = WORD_NAMESPACE + 't'
        
        paragraphs = []
        for paragraph in tree.iter(PARA):
            texts = [node.text for node in paragraph.iter(TEXT) if node.text]
            if texts:
                paragraphs.append(''.join(texts))
                
        return '\n'.join(paragraphs)
    except Exception as e:
        return f"Error reading {docx_path}: {e}"

if __name__ == '__main__':
    search_path = "c:/Users/adelz/OneDrive - GEREP/Bureau/Zeriri/AC360/*.docx"
    files = glob.glob(search_path)
    output_path = "c:/Users/adelz/OneDrive - GEREP/Bureau/Zeriri/AC360/docs_content.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for file in files:
            f.write(f"--- {os.path.basename(file)} ---\n")
            f.write(extract_text_from_docx(file))
            f.write("\n" + "="*40 + "\n")
    print(f"Extraction complete. Check {output_path}")
