from __future__ import annotations

import re
from datetime import date
from io import BytesIO
from typing import Any

from pypdf import PdfReader


class OCRUnavailableError(RuntimeError):
    pass


class OCRService:
    LAB_PATTERNS = (
        (r"\b(?:Hemoglobin|Hgb)\b", "Hemoglobin"),
        (r"\b(?:LDL(?:-C)?|Low[- ]density lipoprotein)\b", "LDL Cholesterol"),
        (r"\b(?:Total Cholesterol|Cholesterol)\b", "Cholesterol"),
        (r"\b(?:Hemoglobin A1c|HbA1c)\b", "HbA1c"),
        (r"\b(?:Platelets?|Platelet Count)\b", "Platelets"),
        (r"\b(?:HDL(?:-C)?|High[- ]density lipoprotein)\b", "HDL Cholesterol"),
        (r"\b(?:Triglycerides?)\b", "Triglycerides"),
        (r"\b(?:Glucose|Blood Sugar)\b", "Glucose"),
        (r"\b(?:Creatinine)\b", "Creatinine"),
        (r"\b(?:WBC|White Blood Cell Count)\b", "White Blood Cell Count"),
    )
    NUMBER_PATTERN = r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:[.,]\d+)?"
    RANGE_PATTERN = (
        rf"(?:{NUMBER_PATTERN}\s*(?:-|–|—|−|to)\s*{NUMBER_PATTERN}"
        rf"|<\s*{NUMBER_PATTERN}|>\s*{NUMBER_PATTERN})"
    )
    RANGE_SEARCH_PATTERN = re.compile(RANGE_PATTERN, re.IGNORECASE)
    UNIT_PATTERN = re.compile(
        r"[a-zA-Zµμ/%^][a-zA-Zµμ0-9.%^]*(?:\s*/\s*[a-zA-Zµμ0-9^]+)?"
    )
    LAB_ROW_PATTERN = re.compile(
        r"^\s*(?P<name>[\w][\w\s./()+-]*?)\s*[:=]\s*(?P<result>.+?)\s*$"
    )
    RESULT_PATTERN = re.compile(
        rf"^\s*(?P<value>{NUMBER_PATTERN})\s*"
        r"(?P<unit>[a-zA-Zµμ/%^0-9.]+(?:\s*/\s*[a-zA-Zµμ0-9^]+)?)?"
        r"(?P<details>.*)$"
    )
    REFERENCE_PATTERN = re.compile(
        rf"\b(?:ref(?:erence)?(?:\s+range)?|normal\s+range)\b\s*[:=]?\s*"
        rf"(?P<range>{RANGE_PATTERN})",
        re.IGNORECASE,
    )
    BRACKETED_RANGE_PATTERN = re.compile(
        rf"[\[(]\s*(?P<range>{RANGE_PATTERN})\s*[\])]",
        re.IGNORECASE,
    )

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        for mojibake, separator in (
            ("â€“", "-"),
            ("â€”", "-"),
            ("â\u0080\u0093", "-"),
            ("â\u0080\u0094", "-"),
            ("â\u0096", "-"),
            ("â\u0097", "-"),
        ):
            text = text.replace(mojibake, separator)
        text = re.sub(r"[ \t]+", " ", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    @classmethod
    def extract_lab_candidates(cls, text: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        normalized_text = cls.normalize_text(text)
        lines = normalized_text.splitlines()
        for line in lines:
            range_match = cls.RANGE_SEARCH_PATTERN.search(line)
            if range_match:
                result_matches = list(
                    re.finditer(cls.NUMBER_PATTERN, line[: range_match.start()])
                )
                if not result_matches:
                    continue
                value_match = result_matches[-1]
                raw_name = line[: value_match.start()].strip(" \t:=,-")
                if not raw_name:
                    continue
                reference_range = range_match.group(0).strip()
                unit_text = (
                    line[value_match.end() : range_match.start()]
                    + " "
                    + line[range_match.end() :]
                )
                unit_text = re.sub(
                    r"\b(?:ref(?:erence)?(?:\s+range)?|normal\s+range)\b",
                    " ",
                    unit_text,
                    flags=re.IGNORECASE,
                )
                unit_match = cls.UNIT_PATTERN.search(unit_text)
                raw_value = cls._parse_number(value_match.group(0))
                known_name = cls._canonical_test_name(raw_name)
                candidates.append(
                    {
                        "name": known_name or raw_name,
                        "value": raw_value,
                        "unit": unit_match.group(0).strip() if unit_match else "",
                        "reference_range": reference_range,
                        "status": cls._compare_to_reference(raw_value, reference_range),
                        "source_text": line.strip(),
                    }
                )
                continue

            row = cls.LAB_ROW_PATTERN.match(line)
            if row:
                raw_name = row.group("name").strip()
                result_text = row.group("result")
            else:
                matched_label = None
                for pattern, test_name in cls.LAB_PATTERNS:
                    label = re.search(pattern, line, flags=re.IGNORECASE)
                    if label:
                        matched_label = (label, test_name)
                        break
                if not matched_label:
                    continue
                label, _ = matched_label
                raw_name = label.group(0)
                result_text = line[label.end() :]

            value_match = cls.RESULT_PATTERN.match(result_text)
            if not value_match:
                continue
            reference_range = cls._extract_reference_range(value_match.group("details"))
            known_name = cls._canonical_test_name(raw_name)
            if known_name is None and reference_range is None:
                continue

            raw_value = cls._parse_number(value_match.group("value"))
            status = (
                cls._compare_to_reference(raw_value, reference_range)
                if reference_range
                else "unknown"
            )
            candidates.append(
                {
                    "name": known_name or raw_name,
                    "value": raw_value,
                    "unit": (value_match.group("unit") or "").strip(),
                    "reference_range": reference_range,
                    "status": status,
                    "source_text": line.strip(),
                }
            )
        candidates.extend(cls._extract_multiline_table_candidates(lines))
        return candidates

    @classmethod
    def _extract_multiline_table_candidates(
        cls, lines: list[str]
    ) -> list[dict[str, Any]]:
        lines = [line.strip() for line in lines if line.strip()]
        headers = (
            {"test", "test name", "tests", "investigation", "parameter"},
            {"result", "value", "observed value"},
            {"reference range", "ref range", "normal range"},
            {"unit", "units"},
        )
        header_labels = {label for column in headers for label in column}
        candidates: list[dict[str, Any]] = []
        for index in range(max(0, len(lines) - 3)):
            if not all(
                lines[index + offset].strip().casefold() in header
                for offset, header in enumerate(headers)
            ):
                continue

            row_index = index + 4
            while row_index + 3 < len(lines):
                raw_name, raw_value, reference_range, unit = (
                    line.strip() for line in lines[row_index : row_index + 4]
                )
                if (
                    not raw_name
                    or raw_name.casefold() in header_labels
                    or not re.fullmatch(cls.NUMBER_PATTERN, raw_value)
                    or not re.fullmatch(cls.RANGE_PATTERN, reference_range, re.IGNORECASE)
                    or not cls.UNIT_PATTERN.fullmatch(unit)
                ):
                    break

                value = cls._parse_number(raw_value)
                candidates.append(
                    {
                        "name": cls._canonical_test_name(raw_name) or raw_name,
                        "value": value,
                        "unit": unit,
                        "reference_range": reference_range,
                        "status": cls._compare_to_reference(value, reference_range),
                        "source_text": " | ".join(
                            (raw_name, raw_value, reference_range, unit)
                        ),
                    }
                )
                row_index += 4
        return candidates

    @classmethod
    def _canonical_test_name(cls, raw_name: str) -> str | None:
        for pattern, test_name in cls.LAB_PATTERNS:
            if re.search(pattern, raw_name, flags=re.IGNORECASE):
                return test_name
        return None

    @staticmethod
    def _parse_number(raw_number: str) -> float:
        if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw_number):
            return float(raw_number.replace(",", ""))
        return float(raw_number.replace(",", "."))

    @classmethod
    def _extract_reference_range(cls, details: str) -> str | None:
        match = (
            cls.REFERENCE_PATTERN.search(details)
            or cls.BRACKETED_RANGE_PATTERN.search(details)
        )
        return match.group("range").strip() if match else None

    @classmethod
    def _compare_to_reference(cls, value: float, reference_range: str) -> str:
        normalized = (
            reference_range.replace("–", "-")
            .replace("—", "-")
            .replace("−", "-")
            .strip()
        )
        if normalized.startswith("<"):
            return "high" if value >= cls._parse_number(normalized[1:].strip()) else "normal"
        if normalized.startswith(">"):
            return "low" if value <= cls._parse_number(normalized[1:].strip()) else "normal"
        range_match = re.fullmatch(
            rf"({cls.NUMBER_PATTERN})\s*(?:-|to)\s*({cls.NUMBER_PATTERN})",
            normalized,
            flags=re.IGNORECASE,
        )
        if not range_match:
            return "unknown"
        lower, upper = map(cls._parse_number, range_match.groups())
        return "low" if value < lower else "high" if value > upper else "normal"

    @classmethod
    def extract_text(cls, content: bytes, mime_type: str) -> tuple[str, str]:
        if mime_type == "application/pdf":
            reader = PdfReader(BytesIO(content))
            text = cls.normalize_text("\n".join(page.extract_text() or "" for page in reader.pages))
            if not text:
                raise OCRUnavailableError(
                    "This PDF has no extractable text. Scanned PDF OCR is not available yet; export each page as an image or use a text-based PDF."
                )
            return text, "pdf-text"
        if mime_type.startswith("image/"):
            try:
                from PIL import Image
                import pytesseract
            except ImportError as exc:
                raise OCRUnavailableError("Image OCR dependencies are missing; install backend requirements.") from exc
            try:
                image = Image.open(BytesIO(content))
                if image.width * image.height > 25_000_000:
                    raise OCRUnavailableError("This image's dimensions exceed the supported OCR limit.")
                image.verify()
                image = Image.open(BytesIO(content))
                text = pytesseract.image_to_string(image, lang="eng+hin", config="--psm 6")
            except OCRUnavailableError:
                raise
            except pytesseract.TesseractNotFoundError as exc:
                raise OCRUnavailableError(
                    "Tesseract OCR is not installed. Install Tesseract with English and Hindi language data to process images."
                ) from exc
            except pytesseract.TesseractError as exc:
                raise OCRUnavailableError(
                    "Bilingual OCR failed. Confirm Tesseract is installed with both eng and hin language data."
                ) from exc
            except Exception as exc:
                raise OCRUnavailableError("The uploaded image could not be read as a valid image.") from exc
            text = cls.normalize_text(text)
            if not text:
                raise OCRUnavailableError(
                    "No text was recognized. Image OCR is imperfect, especially for handwriting; enter the text manually or upload a clearer image."
                )
            return text, "tesseract-eng-hin"
        raise OCRUnavailableError("Only PDF, JPEG, PNG, and WebP documents can be processed.")

    @classmethod
    def process_document(cls, text: str) -> dict[str, Any]:
        cleaned = cls.normalize_text(text)
        candidates = cls.extract_lab_candidates(cleaned)
        return {
            "status": "processed" if cleaned else "failed",
            "clean_text": cleaned,
            "detected_tests": candidates,
            "summary": (
                f"Extracted text from the document and found {len(candidates)} possible laboratory value(s). "
                "Please verify every extracted item against the original report."
                if cleaned
                else "No text could be extracted from this document."
            ),
            "date": date.today().isoformat(),
            "review_required": True,
        }
