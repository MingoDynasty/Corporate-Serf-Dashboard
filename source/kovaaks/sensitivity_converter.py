"""
TODO
"""

import logging
import sys
from source.kovaaks.sensitivity_converter_model import SensitivityAPIResponse

RESOURCE_FILE = "../../resources/sensitivity converter/response.json"
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def convert_sensitivity_to_cm360(
    sens_scale: str, sensitivity: float, dpi: int
) -> float:
    return 0.0


def load_sensitivity_file() -> None:
    logger.debug("Loading sensitivity file.")
    logger.info("Loading sensitivity file.")
    logger.warning("Loading sensitivity file.")
    with open(RESOURCE_FILE, "r", encoding="utf-8") as file:
        json_data = file.read()
    response = SensitivityAPIResponse.model_validate_json(json_data)
    # print(response)

    for sensitivity_scale in response.SensitivityAndFov:
        sens = sensitivity_scale.Sens
        if not sens:
            # logger.debug(f"Skipping sensitivity_scale: %s", sensitivity_scale)
            continue

        increment_formula = sens.IncrementFormula
        logger.debug(f"{sensitivity_scale.ScaleName}\t: {increment_formula}")
        logger.debug(f"    sens.InchesFormula : {sens.InchesFormula}")


load_sensitivity_file()
