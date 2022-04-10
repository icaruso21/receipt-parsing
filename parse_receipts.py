from google.cloud import vision
import io
from pdf2image import convert_from_path
import os
import uuid
import json

PDF_IN_PATH = "./scanned_pdfs"
GENERATED_IMAGES_PATH = "./images"
JSON_OUT_DIR = "./parsed_image_jsons"


def parse_receipts(
    pdf_dir_path: str, generated_images_path: str, json_out_dir: str
) -> None:

    file_paths = os.listdir(pdf_dir_path)

    for path in file_paths:
        full_path = os.path.join(pdf_dir_path, path)
        pages = convert_from_path(full_path, 501)
        client = vision.ImageAnnotatorClient()
        image_file_contents = []
        for page in pages:
            image_filepath = os.path.join(
                generated_images_path, str(uuid.uuid4()) + ".jpg"
            )
            page.save(image_filepath)
            with io.open(image_filepath, "rb") as image_file:
                image_file_contents.append((image_filepath, image_file.read()))

        for image_filepath, image_content in image_file_contents:
            image = vision.Image(content=image_content)
            response = client.text_detection(image=image)

            with open(
                os.path.join(json_out_dir, str(uuid.uuid4()) + ".json"), "w"
            ) as f:
                json.dump(
                    {
                        "image_filepath": image_filepath,
                        "entities": [
                            {
                                "description": ann.description,
                                "bounding_poly": [
                                    {"x": v.x, "y": v.y}
                                    for v in ann.bounding_poly.vertices
                                ],
                            }
                            for ann in response.text_annotations
                        ],
                    },
                    f,
                )


if __name__ == "__main__":
    parse_receipts(PDF_IN_PATH, GENERATED_IMAGES_PATH, JSON_OUT_DIR)
