import os
import json
from typing import Union, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import cv2
import statistics
from upload_to_sheets import add_reciept_to_sheet
import spacy
from stopwords import STOPWORDS
import functools
from dateutil.parser import parse

PARSED_IMAGE_JSON_DIR = "./parsed_image_jsons"

NLP = spacy.load("en_core_web_sm")


def normalize_text(text: str) -> str:
    text = text.lower()
    doc = NLP(text)
    lemmatized = list()
    for word in doc:
        if not word.is_stop:
            lemmatized.append(word.lemma_.replace(" ", ""))
    return "".join(lemmatized)


def safe_parse_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except:
        return None


@dataclass(frozen=True)
class Item:
    name: str
    cost: Optional[str]


class Coordinate:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class ReceiptEntity:
    def __init__(self, entity: dict[str, Union[str, dict]]) -> None:
        self.text: str = entity["description"]  # type: ignore
        self.bounds = [
            Coordinate(x=float(coord["x"]), y=float(coord["y"]))
            for coord in entity["bounding_poly"]
        ]

    @functools.cached_property
    def upper_left(self) -> Coordinate:
        upper_left_coord = self.bounds[0]
        for coord in self.bounds[1:]:
            if coord.x < upper_left_coord.x and coord.y < upper_left_coord.y:
                upper_left_coord = coord
        return upper_left_coord

    @functools.cached_property
    def upper_right(self) -> Coordinate:
        upper_right_coord = self.bounds[0]
        for coord in self.bounds[1:]:
            if coord.x > upper_right_coord.x and coord.y < upper_right_coord.y:
                upper_right_coord = coord
        return upper_right_coord

    @functools.cached_property
    def lower_left(self) -> Coordinate:
        lower_left_coord = self.bounds[0]
        for coord in self.bounds[1:]:
            if coord.x < lower_left_coord.x and coord.y > lower_left_coord.y:
                lower_left_coord = coord
        return lower_left_coord

    @functools.cached_property
    def lower_right(self) -> Coordinate:
        lower_right_coord = self.bounds[0]
        for coord in self.bounds[1:]:
            if coord.x > lower_right_coord.x and coord.y > lower_right_coord.y:
                lower_right_coord = coord
        return lower_right_coord

    @functools.cached_property
    def upper_y(self) -> float:
        return min(self.upper_left.y, self.upper_right.y)

    @functools.cached_property
    def width(self) -> float:
        leftest = self.bounds[0].x
        rightest = self.bounds[0].x
        for coord in self.bounds[1:]:
            if coord.x < leftest:
                leftest = coord.x
            if coord.x > rightest:
                rightest = coord.x
        # print("width: ", rightest - leftest)
        return rightest - leftest

    @functools.cached_property
    def height(self) -> float:
        lowest = self.bounds[0].y
        highest = self.bounds[0].y
        for coord in self.bounds[1:]:
            if coord.y < lowest:
                lowest = coord.y
            if coord.y > highest:
                highest = coord.y
        # print("height: ", highest - lowest)
        return highest - lowest

    @functools.cached_property
    def center(self) -> Coordinate:
        x = [bound.x for bound in self.bounds]
        y = [bound.y for bound in self.bounds]
        centroid = Coordinate(x=sum(x) / len(self.bounds), y=sum(y) / len(self.bounds))
        return centroid

    def same_row_as(self, center_y: float, tolerance: float, image_filepath) -> bool:
        tolerance_threshold = 0.25
        self_tolerance = self.height * tolerance_threshold
        center_self = self.center.y
        self_min = center_self - self_tolerance
        self_max = center_self + self_tolerance
        entity_tolerance = tolerance
        center_entity = center_y
        entity_min = center_entity - entity_tolerance
        entity_max = center_entity + entity_tolerance

        return (
            (self_min >= entity_min and self_min <= entity_max)
            or (self_max >= entity_min and self_max <= entity_max)
            or (entity_min >= self_min and entity_min <= self_max)
            or (entity_max >= self_min and entity_max <= self_max)
        )

    def is_left_of(self, entity: "ReceiptEntity") -> bool:
        return self.center.x < entity.center.x


class Receipt:
    def __init__(
        self, receipt_entities: list[dict[str, Union[str, dict]]], image_filepath: str
    ) -> None:
        self.origin_entities = receipt_entities
        self.entities = [ReceiptEntity(entity=entity) for entity in receipt_entities]
        self.image_filepath = image_filepath

    def show_entities(self):
        plt.imshow(Image.open(self.image_filepath))
        # add rectangle
        for entity in self.entities:
            plt.gca().add_patch(
                Rectangle(
                    (entity.upper_left.x, entity.upper_left.y),
                    entity.width,
                    entity.height,
                    edgecolor="red",
                    facecolor="none",
                    lw=1,
                )
            )
        # display plot
        plt.show()

    @functools.cached_property
    def clean_entities(self) -> list[ReceiptEntity]:
        outlier = 0
        for i, entity in enumerate(self.entities[1:], start=1):
            if entity.upper_y < self.entities[outlier].upper_y:
                outlier = i
        return [e for i, e in enumerate(self.entities) if i != outlier]

    def build_grid(self) -> list[list[ReceiptEntity]]:
        ordered_height_entities = sorted(
            self.clean_entities,
            key=lambda x: x.center.y,
        )
        # insert each entity into the correct line
        last_entity = ordered_height_entities[0]
        lines: list[list[ReceiptEntity]] = [[last_entity]]
        current_row = 0
        for entity in ordered_height_entities:
            current_row_avg_center_y = statistics.mean(
                entity.center.y for entity in lines[current_row]
            )
            current_row_tolerance = statistics.mean(
                entity.height * 0.25 for entity in lines[current_row]
            )
            if entity.same_row_as(
                current_row_avg_center_y,
                current_row_tolerance,
                self.image_filepath,
            ):
                lines[current_row].append(entity)
            else:
                lines.append([entity])
                current_row += 1
            last_entity = entity

        # sort each line left to right
        sorted_lines = []
        for line in lines:
            sorted_lines.append(sorted(line, key=lambda x: x.center.x))

        return sorted_lines

    @functools.cached_property
    def lines(self) -> list[list[str]]:
        lines = [[entity.text for entity in line] for line in self.build_grid()]
        merged_lines = []
        for line in lines:
            doc = NLP(" ".join(line))
            noun_chunks = [chunk.text for chunk in doc.noun_chunks]
            current_chunk = 0
            chunk_added = False
            merged_line = []
            for cell in line:
                if (
                    current_chunk < len(noun_chunks)
                    and cell in noun_chunks[current_chunk]
                ):
                    if not chunk_added:
                        merged_line.append(noun_chunks[current_chunk])
                        chunk_added = True

                elif current_chunk < len(noun_chunks):
                    current_chunk += 1
                    chunk_added = False
                    merged_line.append(cell)
                else:
                    merged_line.append(cell)
            merged_lines.append(merged_line)

        return merged_lines

    @functools.cached_property
    def items(self) -> list[Item]:
        items: list[Item] = []
        items_list_started = False
        for line in self.lines:
            if any(
                normalize_text(stopword) in normalize_text(" ".join(line))
                for stopword in STOPWORDS
            ):
                break
            cost = None
            name = None

            for cell in line:
                doc = NLP(cell)
                for ent in doc.ents:
                    if ent.label_ in ("CARDINAL", "COST", "MONEY"):
                        if cost is None or len(cost) < len(ent.text):
                            cost = ent.text
            for cell in line:
                if safe_parse_float(cell) is not None:
                    if cost is None or len(cost) < len(cell):
                        cost = cell
                elif cost is None or not cost in cell:
                    if name is None:
                        name = cell
                    else:
                        name = f"{name} {cell}"
            if (
                name is not None
                and len(name) > 1
                and (items_list_started or cost is not None)
            ):
                items.append(Item(name=name.title(), cost=cost))
                items_list_started = True
        return items

    @property
    def name(self) -> Optional[str]:
        lines = self.lines
        for line in lines:
            for cell in line:
                if len(cell) > 2:
                    return " ".join(line).title()
        return None

    @property
    def datetime(self) -> Optional["Datetime"]:
        lines = self.lines
        for line in lines:
            for cell in line:
                try:
                    return parse(cell)
                except:
                    pass
        return None

    @property
    def date(self) -> Optional[str]:
        return self.datetime.strftime("%m/%d/%Y") if self.datetime is not None else None

    def save_entities(self):
        # blank_image = np.ones(shape=(512, 512, 3), dtype=np.int16)
        original_image = cv2.imread(self.image_filepath)
        (thresh, image_template) = cv2.threshold(
            original_image, 255, 1, cv2.THRESH_BINARY_INV
        )
        # cv2.imshow("Image Template", image_template)
        # plt.imshow()
        # add rectangle
        for entity in self.clean_entities:
            cv2.rectangle(
                image_template,
                pt1=(int(entity.lower_right.x), int(entity.lower_right.y)),
                pt2=(int(entity.upper_left.x), int(entity.upper_left.y)),
                color=(255, 255, 0),
                thickness=-1,
            )
        plt.imshow(image_template)
        # display plot
        plt.show()

    def print_grid(self) -> None:
        lines = self.lines
        for line in lines:
            print(line)

    @functools.cached_property
    def formatted_sheet(self) -> list[list[str]]:
        lines = []
        if self.name is not None:
            lines.append([self.name])
        if self.date is not None:
            lines.append([self.date])
        if len(lines) > 0:
            lines.append([])
        for item in self.items:
            lines.append(
                [item.name, item.cost] if item.cost is not None else [item.name]
            )

        return lines

    def upload_receipt_to_gsheet(self):
        sheet_name = (
            self.name
            if self.name is not None
            else os.path.splitext(os.path.basename(self.image_filepath))[0]
        )
        add_reciept_to_sheet(sheet_name, self)


def coords_to_csv(parsed_receipts_json_dir_path: str):
    file_paths = os.listdir(parsed_receipts_json_dir_path)
    receipts = []

    for path in file_paths:
        full_path = os.path.join(PARSED_IMAGE_JSON_DIR, path)
        with open(full_path, "r") as f:
            parsed_receipt: list[dict[str, Union[str, dict]]] = json.load(f)
            receipts.append(
                Receipt(
                    receipt_entities=parsed_receipt["entities"],
                    image_filepath=parsed_receipt["image_filepath"],
                )
            )

    for receipt in receipts:
        receipt.upload_receipt_to_gsheet()


if __name__ == "__main__":
    coords_to_csv(PARSED_IMAGE_JSON_DIR)
