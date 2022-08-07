import textract
import os
import tempfile
import re
import requests
import numpy as np
from zoopla_fetcher.config import requests_config
from typing import List, Union, Any
import logging

_logger = logging.getLogger(__name__)


def extract_text_from_image(img_url: str) -> str:
    """
    Extract all text from an image
    :param img_url: Image url
    :return: Image text
    """
    r = requests.get(img_url, headers=requests_config.HEADERS)
    image_extension = img_url.split('.')[-1]
    # Set up temporary file
    tmp_f = tempfile.NamedTemporaryFile(suffix="." + image_extension, delete=False)
    try:
        tmp_f.write(r.content)
        tmp_f.close()
        text = textract.process(tmp_f.name, extension=image_extension, method="tesseract").decode("utf-8").lower()
        return text
    finally:
        os.remove(tmp_f.name)


def numbers_from_string(inp_str: str) -> List[float]:
    """
    Parse out all numbers from a string
    :param inp_str: Input string
    :return: All numbers
    """
    pattern = "[\d]{1,}[\.\d]{0,}[\d]{0,}"
    all_numbers = re.findall(pattern, inp_str.replace(",", ""))
    float_numbers = []
    for number in all_numbers:
        if bool(re.search(r'\d', number)):
            float_numbers.append(float(number))
    return float_numbers


def extract_total_sq_footage_from_floorplan(floorplan_url: str) -> Union[float, Any]:
    """
    Get the total square footage from a floorplan
    :param floorplan_url: Floorplan url
    :return: Parsed out total square footage from the image
    """
    text = extract_text_from_image(floorplan_url)
    sq_feet_pattern = "[0-9\.\,]{1,}[sq|\.|\s|square|s@|,]{1,}ft|[0-9\.\,]{1,}[sq|\.|\s|square|s@|,]{1,}feet"
    matches = re.findall(sq_feet_pattern, text)
    all_sq_feet = []
    for match in matches:
        all_sq_feet.extend(numbers_from_string(match))
    if all_sq_feet:
        return np.nanmax(all_sq_feet)
    else:
        return np.NaN
