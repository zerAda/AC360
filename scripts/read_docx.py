import zipfile
import xml.etree.ElementTree as ET
import sys
import glob
import os

def extract_text_from_docx(docx_path):
    try:
        document = zipfile.ZipFile(docx_path)
        xml_file = document.open('word/document.xml')
        
        WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        PARA = WORD_NAMESPACE + 'p'
        TEXT = WORD_NAMESPACE + 't'
        
        paragraphs = []
        current_para = []
        
        # [PATCH HATER] iterparse évite de charger tout l'arbre en mémoire et mitige
        # partiellement les attaques XXE/Billion Laughs comparé à ET.XML()
        for event, elem in ET.iterparse(xml_file, events=('start', 'end')):
            if event == 'start' and elem.tag == PARA:
                current_para = []
            elif event == 'end' and elem.tag == TEXT:
                if elem.text:
                    current_para.append(elem.text)
            elif event == 'end' and elem.tag == PARA:
                if current_para:
                    paragraphs.append(''.join(current_para))
                elem.clear() # Libérer la mémoire
                
        document.close()
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
