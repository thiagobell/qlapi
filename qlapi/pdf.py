from typing import List, BinaryIO

import pypdfium2
import pypdfium2 as pdfium
from PIL import Image


class CouldNotLoadPDFError(Exception):
    pass


def pdf2im(pdf_file: BinaryIO) -> List[Image.Image]:
    """
    Renders the PDF at 300dpi into Pillow Image instances
    Args:
        pdf_file: A file like object containing the pdf data

    Returns: a list of pillow images. one for each page in the pdf

    Raises: CouldNotLoadPdfError if file could not open. e.g. file is not a pdf
    """
    try:
        pdf = pdfium.PdfDocument(pdf_file.read())
    except pypdfium2.PdfiumError:
        raise CouldNotLoadPDFError

    # convert all pages to PIL images
    # returns a generator of PIL image objects
    # cannot use pdf.render directly because it does not support PdfDocument
    # instances initialized with bytes
    pil_pages = []
    for page in pdf:
        pil_pages.append(
            page.render(
                scale=300/72
            ).to_pil()
        )
    return pil_pages
