import pandas as pd

from zoopla_fetcher.listing_details import ListingDetails
from zoopla_fetcher import graphql_utils
from tqdm import tqdm
from bs4 import BeautifulSoup
import requests
import re
from zoopla_fetcher.config import requests_config
import logging
from multiprocessing.pool import ThreadPool
from typing import List

_logger = logging.getLogger(__name__)


class ListingsQuery:
    """
    Manage the full data fetch for a query
    """
    MAX_RESULTS = 10000

    def __init__(self,
                 query_string: str,
                 query_type: str = "for-sale",
                 price_min: int = None,
                 price_max: int = None,
                 beds_min: int = None,
                 beds_max: int = None,
                 radius_miles: float = 0.0,
                 property_type: str = None,
                 shared_ownership: bool = False,
                 new_homes: bool = True,
                 include_auctions: bool = True,
                 include_sold: bool = False,
                 retirement_homes: bool = True,
                 include_shared_accommodation: bool = False):
        """
        :param query_string: The location name (postcode of a city name)
        :param query_type: Either for-sale or to-rent
        :param price_min: Min price filter
        :param price_max: Max price filter
        :param beds_min: Min beds filter
        :param beds_max: Max beds filter
        :param radius_miles: How many miles radius from the queried location
        :param property_type: One of ["houses", "flats", "farms_land", None]
        :param shared_ownership: Whether shared ownership results should be returned
        :param new_homes: Whether new home results should be returned
        :param include_auctions: Whether auctions should be returned
        :param include_sold: Whether already sold properties should be returned
        :param retirement_homes: Whether retirement should be returned
        :param include_shared_accommodation: Whether sjared accommodation results should be returned
        """

        if query_type not in ["for-sale", "to-rent"]:
            raise ValueError("Query type must be either 'for-sale' or 'to-rent'")

        if property_type not in ["houses", "flats", "farms_land", None]:
            raise ValueError("Property type must be either None (i.e. All), 'houses', 'flats' or 'farms_land'")

        self.q = query_string
        self.query_type = query_type
        self.price_min = price_min
        self.price_max = price_max
        self.beds_min = beds_min
        self.beds_max = beds_max
        self.radius = radius_miles
        self.property_type = property_type
        self.shared_ownership = shared_ownership
        self.new_homes = new_homes
        self.include_auctions = include_auctions
        self.include_sold = include_sold
        self.retirement_homes = retirement_homes
        self.include_shared_accommodation = include_shared_accommodation
        self._query_url = self._gen_query_url()
        self.listing_urls = self.get_all_listing_urls()
        self.graphql_api_key = self.get_graphql_api_key()

    def gen_query_params(self) -> dict:
        """
        Set up the query params for the request
        """
        return {
            "q": self.q,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "property_type": self.property_type,
            "beds_min": self.beds_min,
            "beds_max": self.beds_max,
            "category": "residential",
            "price_frequency": "per_month",
            "furnished_state": None,
            "radius": self.radius,
            "added": None,
            "results_sort": "newest_listings",
            "keywords": None,
            "new_homes": "include" if self.new_homes else "exclude",
            "retirement_homes": "true" if self.retirement_homes else "false",
            "shared_ownership": "true" if self.shared_ownership else "false",
            "include_auctions": "true" if self.include_auctions else "false",
            "include_sold": "true" if self.include_sold else "false",
            "include_shared_accommodation": "true" if self.include_shared_accommodation else "false",
            "include_rented": None,
            "search_source": self.query_type,
            "section": self.query_type,
            "view_type": "list"
        }

    def _gen_query_url(self) -> str:
        """
        Gen full query url. Only generated once, then only page number is replaced in the url as we
        loop through to get all property urls
        """
        query_params = self.gen_query_params()
        r = requests.get(requests_config.BASE_URL + "/search/", params=query_params, headers=requests_config.HEADERS,
                         allow_redirects=False)
        new_endpoint = r.headers["location"]
        additional_params = [
            "page_size=100",
            "pn=1",
        ]
        return requests_config.BASE_URL + new_endpoint + "&" + "&".join(additional_params)

    def _get_page_property_urls(self, page_number: int) -> List[str]:
        """
        For one page of property listings, parse out all property urls
        :param page_number: Page number of the query results
        :return: List of all listing urls in the page
        """
        new_url = self._query_url.replace("pn=1", "pn=" + str(page_number))
        r = requests.get(new_url, headers=requests_config.HEADERS)
        souped = BeautifulSoup(r.text, 'html.parser')
        prop_url_tags = souped.findAll('a', {'data-testid': 'listing-details-link'})
        prop_urls = [requests_config.BASE_URL + re.sub('\?search_identifier=.{1,}', '', a['href']) for a in prop_url_tags]
        return prop_urls

    def get_all_listing_urls(self) -> List[str]:
        """
        Loop through all query pages, and return all listings urls
        :return: List of all listing urls for the query
        """
        _logger.info("Getting all listing urls for given query...")
        first_request = requests.get(self._query_url, headers=requests_config.HEADERS)
        souped = BeautifulSoup(first_request.text, 'html.parser')
        total_results_element = souped.findAll('p', {'data-testid': 'total-results'})
        if len(total_results_element) > 0:
            total_results_str = re.search('([\d]{1,})', total_results_element[0].text).group(1)
            total_results = int(total_results_str)
        else:
            raise Exception("Could not get page data")

        if total_results >= self.MAX_RESULTS:
            _logger.warning("Too many results, only returning first {}".format(self.MAX_RESULTS))

        pages_divmod = divmod(total_results, 100)
        total_pages = pages_divmod[0] + 1 if pages_divmod[1] > 0 else pages_divmod[0]
        listing_urls = []
        for page_number in tqdm(range(1, total_pages + 1)):
            listing_urls.extend(self._get_page_property_urls(page_number))

        return listing_urls

    def get_graphql_api_key(self) -> str:
        """
        Get GraphQl API key, used for price history data
        :return: GraphQl API key
        """
        _logger.info("Extracting graph ql API key for price history queries...")
        api_key = graphql_utils.extract_api_key(any_property_url=self.listing_urls[0])
        _logger.info(f"API key found: {api_key}")
        return api_key

    @property
    def total_listings(self) -> int:
        """
        :return: Total listings for this query
        """
        return len(self.listing_urls)

    def get_listing_details(self, listing_url: str) -> pd.Series:
        """
        Extract details for 1 property listing
        :param listing_url: Listing url
        :return: All details for the listing
        """
        try:
            p = ListingDetails(listing_url)
            return p.extract_all(graphql_api_key=self.graphql_api_key)
        except Exception as e:
            _logger.error(f"Error extracting property details {listing_url}: Exception {e}")
            return pd.Series(dtype="object")

    def get_listing_price_history(self, listing_url) -> pd.DataFrame:
        """
        Extract a more detailed breakdown of price change history for the listing
        :param listing_url: Listing url
        :return: Detailed price history
        """
        try:
            p = ListingDetails(listing_url)
            return p.extract_price_change_history(summarised=False,
                                                  graphql_api_key=self.graphql_api_key)
        except Exception as e:
            _logger.error(f"Error extracting property price history {listing_url}: Exception {e}")
            return pd.DataFrame()

    def extract_all_properties_details(self, threads: int = 10) -> pd.DataFrame:
        """
        Loop over all listing urls in parallel, and generate the full results
        :param threads: How many threads should be used for the parallel process
        :return: Full result of the query
        """
        with ThreadPool(threads) as pool:
            all_results = list(tqdm(pool.imap(self.get_listing_details, self.listing_urls), total=self.total_listings))
        return pd.DataFrame(all_results).set_index("listingId")

    def extract_all_properties_price_history(self, threads: int = 10):
        """
        Loop over all listing urls in parallel, and generate the price change history for all listings
        :param threads: How many threads should be used for the parallel process
        :return: Price history of all properties
        """
        with ThreadPool(threads) as pool:
            all_results = list(
                tqdm(pool.imap(self.get_listing_price_history, self.listing_urls), total=self.total_listings))
        return pd.concat(all_results)
