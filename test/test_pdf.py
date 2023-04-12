"""
Tests functions related to pdf manipulation
"""

from qlapi.pdf import pdf2im


def test_pdf2im(label_pdf):
    images = pdf2im(label_pdf)

    assert type(images) == list
    assert len(images) == 2
