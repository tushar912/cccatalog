import os
import logging
from common.requester import DelayedRequester
from common.storage.image import ImageStore
from util.loader import provider_details as prov

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s:  %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

LIMIT = 100
DELAY = 5
RETRIES = 3
PROVIDER = prov.FINNISH_DEFAULT_PROVIDER
ENDPOINT = "https://api.finna.fi/api/v1/search"
SUB_PROVIDERS = prov.FINNISH_SUB_PROVIDERS
FORMAT_TYPE = "0/Image/"
API_URL = "https://api.finna.fi"
LANDING_URL = "https://www.finna.fi/Record/"

BUILDINGS = ["0/Suomen kansallismuseo/",
             "0/Museovirasto/", "0/SATMUSEO/", "0/SA-kuva/"]

DEFAULT_QUERY_PARAMS = {
    "filter[]": [f'format:"{FORMAT_TYPE}"'],
    "limit": LIMIT,
    "page": 1,
}

delayed_requester = DelayedRequester(DELAY)
image_store = ImageStore(provider=PROVIDER)


def main():
    logger.info("Begin: Finnish museum provider script")
    for building in BUILDINGS:
        logger.info(f"Obtaining Images of building {building}")
        object_list = _get_object_list(building)
        _ = _process_object_list(object_list)

    total_images = image_store.commit()
    logger.info(f"Total Images received {total_images}")


def _get_object_list(building, endpoint=ENDPOINT, retries=RETRIES):
    page = 1
    obj_list = []
    condition = True
    while condition:
        query_params = _build_params(building=building, page=page)
        page += 1
        json_resp = delayed_requester.get_response_json(
            endpoint=endpoint, retries=retries, query_params=query_params
        )

        object_list = _get_object_list_from_json(json_resp)
        if object_list is None:
            break
        for obj in object_list:
            obj_list.append(obj)

    if len(obj_list) == 0:
        logger.warning("No more retries .Returning None")
        return None
    else:
        return obj_list


def _build_params(building, default_params=DEFAULT_QUERY_PARAMS, page=1):
    query_params = default_params.copy()
    query_params.update(
        {
            "page": page,
            "filter[]": [f'format:"{FORMAT_TYPE}"', f'building:"{building}"'],
        }
    )

    return query_params


def _get_object_list_from_json(json_resp):
    if (
        json_resp is None or
        json_resp.get("records") is None or
        len(json_resp.get("records")) == 0
    ):
        object_list = None
    else:
        object_list = json_resp.get("records")

    return object_list


def _process_object_list(object_list):
    total_images = 0
    if object_list is not None:
        for obj in object_list:
            total_images = _process_object(obj)

    return total_images


def _process_object(obj, sub_providers=SUB_PROVIDERS, provider=PROVIDER):
    license = obj.get("imageRights")
    license_url = license.get("link")
    foreign_identifier = obj.get("id")
    title = obj.get("title")
    building = obj.get("buildings")[0].get("value")
    source = next((s for s in sub_providers
                   if building in sub_providers[s]), provider)
    foreign_landing_url = _get_landing(obj)
    raw_tags = obj.get("subjects")
    image_list = obj.get("images")
    for img in image_list:
        image_url = _get_image_url(img)
        total_images = image_store.add_item(
            license_url=license_url,
            foreign_identifier=foreign_identifier,
            image_url=image_url,
            title=title,
            source=source,
            raw_tags=raw_tags,
        )
    return total_images


def _get_landing(obj, landing_url=LANDING_URL):
    l_url = None
    id = obj.get("id")
    if id:
        l_url = landing_url + id
    return l_url


def _get_image_url(img, image_url=API_URL):
    img_url = None
    if img:
        img_url = image_url + img
    return img_url


if __name__ == "__main__":
    main()