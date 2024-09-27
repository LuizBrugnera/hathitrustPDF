from bs4 import BeautifulSoup
import requests
import re
import os
from pathlib import Path
from PyPDF2 import PdfMerger
import progressbar

def PDFDownload(output_line, actual_page, path_folder):
    try:
        PDF_download = requests.get(output_line, stream=True, timeout=300)
        with open(os.path.join(path_folder, f'page{actual_page}.pdf'), 'wb') as f:
            f.write(PDF_download.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the page {actual_page}: {e}")

def merge_pdfs(path_folder, name_output):
    merger = PdfMerger()

    arquivos = os.listdir(path_folder)

    pdfs = sorted(
        [arquivo for arquivo in arquivos if arquivo.lower().endswith('.pdf')],
        key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0
    )

    for pdf in pdfs:
        caminho_pdf = os.path.join(path_folder, pdf)
        try:
            merger.append(caminho_pdf)
            print(f'Added: {pdf}')
        except Exception as e:
            print(f"Error adding {pdf}: {e}")

    caminho_output = os.path.join(path_folder, name_output)
    try:
        with open(caminho_output, 'wb') as arquivo_output:
            merger.write(arquivo_output)
        print(f'\nPDFs successfully merged into: {caminho_output}')
    except Exception as e:
        print(f"Error writing final PDF: {e}")
    finally:
        merger.close()

def main():
    link = "https://babel.hathitrust.org/cgi/pt?id=ufl.31262094199295&seq=7" ## insert the link to the book
    size_pages_pdf = 1122  ## insert the size of the pages you want to download
    id_book_match = re.findall(r'id=([\w\.]+)', link)
    if not id_book_match:
        raise ValueError("Invalid link format. Unable to extract book ID.")
    id_book = id_book_match[0]

    try:
        r = requests.get(link, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Error accessing the link: {e}")

    soup = BeautifulSoup(r.text, "html.parser")

    script_tag = soup.find("script", text=re.compile("HT.params.totalSeq"))
    if not script_tag:
        raise ValueError("Unable to find script with 'HT.params.totalSeq'")
    script_text = script_tag.string
    pages_match = re.search(r'HT.params.totalSeq\s*=\s*(\d+);', script_text)
    if not pages_match:
        raise ValueError("Unable to extract the total number of pages")
    pages_book = int(pages_match.group(1))

    name_meta = soup.find('meta', {'property': 'og:title'})
    if name_meta and 'content' in name_meta.attrs:
        name_book = name_meta['content']
    else:
        raise ValueError("Unable to find book title")

    if len(name_book) > 55:
        name_book = name_book[:40]

    remove_character = "[],/\\:.;\"'?!*"
    translation_table = str.maketrans({char: ' ' for char in remove_character})
    name_book = name_book.translate(translation_table).strip()

    local = os.getcwd()
    path_folder = os.path.join(local, name_book)
    Path(path_folder).mkdir(parents=True, exist_ok=True)

    begin_page = 1
    last_page = pages_book + 1

    bar = progressbar.ProgressBar(maxval=last_page - begin_page,
                                  widgets=[progressbar.Bar('=', '[', ']'), ' ',
                                           progressbar.Percentage()])
    bar.start()

    for actual_page in range(begin_page, last_page):
        output_line = f'https://babel.hathitrust.org/cgi/imgsrv/download/pdf?id={id_book};orient=0;size={size_pages_pdf};seq={actual_page};attachment=0'
        PDFDownload(output_line, actual_page, path_folder)

        pdf_path = os.path.join(path_folder, f'page{actual_page}.pdf')
        attempts = 0
        while os.path.getsize(pdf_path) < 6000 and attempts < 5:
            print(f"Insufficient size for page {actual_page}. Trying again...")
            PDFDownload(output_line, actual_page, path_folder)
            attempts += 1

        if os.path.getsize(pdf_path) < 6000:
            print(f"Fail to download {actual_page} after {attempts} trys.")

        bar.update(actual_page - begin_page + 1)

    bar.finish()

    name_pdf_output = f"{name_book}_output.pdf"
    merge_pdfs(path_folder, name_pdf_output)

if __name__ == "__main__":
    main()
