from backend.apps.doc.models import Doc
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.conf import settings
from urllib.parse import urlparse
from loguru import logger
import time
import os
import io
import subprocess
import shutil

# 查找文档的下级文档
def find_doc_next(doc_id):
    doc = Doc.objects.get(id=int(doc_id))

    subdoc = Doc.objects.filter(parent_doc=doc.id, status=1)

    if subdoc.count() != 0:
        next_doc = subdoc.order_by('sort')[0]
    else:
        sibling_docs = Doc.objects.filter(parent_doc=doc.parent_doc, status=1).order_by('sort','create_time')
        sibling_list = [d.id for d in sibling_docs]
        if sibling_list.index(doc.id) != len(sibling_list) - 1:
            next_id = sibling_list[sibling_list.index(doc.id) + 1]
            next_doc = Doc.objects.get(id=next_id)
        else:
            if doc.parent_doc == 0:
                next_doc = None
            else:
                next_doc = find_doc_parent_sibling(doc.parent_doc)

    return next_doc


def find_doc_parent_sibling(doc_id):
    doc = Doc.objects.get(id=int(doc_id))
    sibling_docs = Doc.objects.filter(parent_doc=doc.parent_doc, status=1).order_by('sort', 'create_time')
    sibling_list = [d.id for d in sibling_docs]
    if sibling_list.index(doc.id) != len(sibling_list) - 1:
        next_id = sibling_list[sibling_list.index(doc.id) + 1]
        next_doc = Doc.objects.get(id=next_id)
    else:
        if doc.parent_doc == 0:
            next_doc = None
        else:
            next_doc = find_doc_parent_sibling(doc.parent_doc, sort)
    return next_doc


def find_doc_previous(doc_id):
    doc = Doc.objects.get(id=int(doc_id))
    sibling_docs = Doc.objects.filter(parent_doc=doc.parent_doc, status=1).order_by('sort', 'create_time')
    sibling_list = [d.id for d in sibling_docs]

    if sibling_list.index(doc.id) == 0:
        if doc.parent_doc == 0:
            previous_doc = None
        else:
            previous_doc = Doc.objects.get(id=doc.parent_doc)
    else:
        previous_id = sibling_list[sibling_list.index(doc.id) - 1]
        previous_doc = find_doc_sibling_sub(previous_id, 0)

    return previous_doc


def find_doc_sibling_sub(doc_id, sort):
    doc = Doc.objects.get(id=int(doc_id))
    if sort == 1:
        subdoc = Doc.objects.filter(parent_doc=doc.id, status=1).order_by('-create_time')
    else:
        subdoc = Doc.objects.filter(parent_doc=doc.id, status=1).order_by('sort', 'create_time')
    subdoc_list = [d.id for d in subdoc]
    if subdoc.count() == 0:
        previous_doc = doc
    else:
        previous_doc = find_doc_sibling_sub(subdoc_list[len(subdoc) - 1], sort)

    return previous_doc


def validate_url(url):
    try:
        validate = URLValidator()
        validate(url)
        parsed_url = urlparse(url)
        if parsed_url.hostname in ['localhost', '127.0.0.1']:
            return False
        return url
    except:
        return False


_wmf_extensions = {
    "image/x-wmf": ".wmf",
    "image/x-emf": ".emf",
}


def libreoffice_wmf_conversion(image, post_process=None):
    if post_process is None:
        post_process = lambda x: x

    wmf_extension = _wmf_extensions.get(image.content_type)
    if wmf_extension is None:
        return image
    else:
        temporary_directory = os.path.join(settings.MEDIA_ROOT, 'import_docx_imgs')
        if os.path.exists(temporary_directory) is False:
            os.mkdir(temporary_directory)
        try:
            timestamp = str(time.time())
            input_path = os.path.join(temporary_directory, "image_{}".format(timestamp) + wmf_extension)
            with open(input_path, "wb") as input_fileobj:
                with image.open() as image_fileobj:
                    shutil.copyfileobj(image_fileobj, input_fileobj)

            output_path = os.path.join(temporary_directory, "image_{}.png".format(timestamp))
            subprocess.check_call([
                settings.LIBREOFFICE_PATH,
                "--headless",
                "--convert-to",
                "png",
                input_path,
                "--outdir",
                temporary_directory,
            ])

            with open(output_path, "rb") as output_fileobj:
                output = output_fileobj.read()

            def open_image():
                return io.BytesIO(output)

            return post_process(image.copy(
                content_type="image/png",
                open=open_image,
            ))
        except:
            return image
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


def image_trim(old_image):
    from PIL import Image

    timestamp = str(time.time())
    temporary_directory = os.path.join(settings.MEDIA_ROOT, 'import_docx_imgs')
    output_path = os.path.join(temporary_directory, f"trim_image_{timestamp}.png")

    def open_image():
        try:
            with open(output_path, 'rb') as imgfile:
                return io.BytesIO(imgfile.read())
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    image = Image.open(old_image.open())
    width, height = image.size

    x_left, x_top = width, height
    x_right = x_bottom = 0

    for r in range(height):
        for c in range(width):
            pixel = image.getpixel((c, r))
            if pixel[0] < 255 and pixel[1] < 255 and pixel[2] < 255:
                x_top = min(x_top, r)
                x_bottom = max(x_bottom, r)
                x_left = min(x_left, c)
                x_right = max(x_right, c)

    if x_left < x_right and x_top < x_bottom:
        cropped = image.crop((x_left - 5, x_top - 5, x_right + 5, x_bottom + 5))
        cropped.save(output_path, format="PNG")
    else:
        image.save(output_path, format="PNG")

    new_image = old_image.copy(open=open_image)
    return new_image
