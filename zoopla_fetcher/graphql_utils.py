"""
Any details that require graphql can be done using this module
"""
import re
import requests
from typing import Union
from zoopla_fetcher.config import requests_config


API_URL = "https://api-graphql-lambda.prod.zoopla.co.uk/graphql"


def extract_api_key(any_property_url: str) -> str:
    """
    :param any_property_url: URL of any property currently live on Zoopla
    :return: Graphql api key
    """
    raw_html = requests.get(any_property_url, headers=requests_config.HEADERS).text
    # Extract all the javascript urls, as one of them includes the graphql api key
    rgex = 'script src="https://r.zoocdn.com/_next/static/chunks/[^\s]*\.js'
    js_script_urls = re.findall(rgex, raw_html)
    for js_url in js_script_urls:
        url = js_url.replace('script src="', '')
        r = requests.get(url, headers=requests_config.HEADERS)
        rgex = '"X-Api-Key":"([\w]{1,})"'
        api_key_hits = re.findall(rgex, r.text)
        if api_key_hits:
            return api_key_hits[0]
    raise Exception("No API key found")

def extract_price_history_and_view_counts(listing_id: Union[int, str], api_key: str) -> dict:
    """
    Query graph ql to extract a listing's price history, and its view counts
    :param listing_id: Id of the zoopla listing
    :param api_key: Zoopla's graphql API key
    :return: Query result
    """
    payload = f'{{"operationName":"ListingHistory","variables":{{"listingId":{listing_id}}},"query":"query ListingHistory($listingId: Int\u0021) {{\\n  listingDetails(id: $listingId) {{\\n    ... on ListingData {{\\n      priceHistory {{\\n        ...History\\n        __typename\\n      }}\\n      viewCount {{\\n        ...ViewCount\\n        __typename\\n      }}\\n      __typename\\n    }}\\n    ... on ListingResultError {{\\n      errorCode\\n      __typename\\n    }}\\n    __typename\\n  }}\\n}}\\n\\nfragment History on PriceHistory {{\\n  firstPublished {{\\n    firstPublishedDate\\n    priceLabel\\n    __typename\\n  }}\\n  lastSale {{\\n    date\\n    newBuild\\n    price\\n    priceLabel\\n    recentlySold\\n    __typename\\n  }}\\n  priceChanges {{\\n    isMinorChange\\n    isPriceDrop\\n    isPriceIncrease\\n    percentageChangeLabel\\n    priceChangeDate\\n    priceChangeLabel\\n    priceLabel\\n    __typename\\n  }}\\n  __typename\\n}}\\n\\nfragment ViewCount on ViewCount {{\\n  viewCount30day\\n  __typename\\n}}\\n"}}'
    headers = dict(requests_config.HEADERS)
    headers["content-type"] = "application/json"
    headers["x-api-key"] = api_key
    raw_price_history_r = requests.post(url=API_URL,
                                        data=payload,
                                        headers=headers)
    raw_price_history_r.raise_for_status()
    return raw_price_history_r.json()["data"]





