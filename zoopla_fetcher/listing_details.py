import pandas as pd
import requests
import re
import numpy as np
import json
from zoopla_fetcher.config import requests_config
from zoopla_fetcher import floor_plan_utils
from zoopla_fetcher import graphql_utils
from typing import Union
import logging

_logger = logging.getLogger(__name__)


class ListingDetails:

    def __init__(self, url: str):
        """
        :param url: url of the listing
        """
        self._url = url
        self._raw_html = self._extract_raw_html()
        self._listing_details = self._extract_listing_details()

    def _extract_raw_html(self) -> str:
        """
        :return: Raw html of the page
        """
        return requests.get(self._url, headers=requests_config.HEADERS).text

    def _extract_listing_details(self) -> dict:
        """
        :return: Raw dict of all listing details
        """
        rgex = 'type="application\/json">({"props":{"pageProps":.*})<\/script>'
        try:
            raw_data = json.loads(re.search(rgex, self._raw_html)[1])["props"]["pageProps"]
            return raw_data["listingDetails"]
        except Exception as e:
            raise Exception(f"Could not extract raw data from url: {self._url}, error: {str(e)}")

    @property
    def listing_id(self) -> int:
        """
        :return: Get the listing id
        """
        return self._listing_details["listingId"]

    def extract_main_details(self) -> pd.Series:
        """
        :return: Main details of the listing
        """
        main_details = self._listing_details["adTargeting"]
        filtered_details = {k: v for k, v in main_details.items() if "__" not in k}
        return pd.Series(filtered_details)

    def extract_pois(self) -> pd.Series:
        """
        :return: Any POIs associated with the property
        """
        pois_df = pd.DataFrame(self._listing_details["pointsOfInterest"])
        pois_closest = pois_df.sort_values("distanceMiles").groupby("type").first()
        pois_closest_dict = pois_closest["title"].to_dict()
        pois_closest.index = pois_closest.index + "_distance_miles"
        pois_closest_dict.update(pois_closest["distanceMiles"].to_dict())
        return pd.Series(pois_closest_dict).sort_index()

    def extract_detailed_description(self) -> pd.Series:
        """
        :return: Detailed description of the property
        """
        return pd.Series({"detailedDescription": self._listing_details["detailedDescription"]})

    def extract_location(self) -> pd.Series:
        """
        :return: Lat/Long of the property
        """
        loc_details = self._listing_details["location"]["coordinates"]
        return pd.Series({"latitude": loc_details["latitude"], "longitude": loc_details["longitude"]})

    def extract_sq_footage(self) -> pd.Series:
        """
        :return: Total square footage of the property
        """
        floor_plans = self._listing_details["floorPlan"]["image"]
        if floor_plans is None:
            return pd.Series({"total_sq_footage": np.nan})
        all_urls = ["https://lid.zoocdn.com/u/2400/1800/" + fp["filename"] for fp in floor_plans]
        sq_footage = pd.Series(
            [floor_plan_utils.extract_total_sq_footage_from_floorplan(url) for url in all_urls]).dropna().replace(0,
                                                                                                                  np.nan)
        if sq_footage.empty:
            return pd.Series({"total_sq_footage": np.nan})
        return pd.Series({"total_sq_footage": sq_footage.max()})

    def extract_price_change_history(self, graphql_api_key: str, summarised: bool = True) -> Union[pd.Series, pd.DataFrame]:
        """
        :param summarised: If True, returns a summarised version of the price change history
        :return: Price change history summary of the property if summarised=True, else
                 Detailed df of price change history
        """
        price_history = graphql_utils.extract_price_history_and_view_counts(listing_id=self.listing_id,
                                                                            api_key=graphql_api_key)
        price_history = price_history["listingDetails"]["priceHistory"]
        first_listed = None
        data_records = []
        if price_history is None:
            return pd.Series(dtype="object") if summarised else pd.DataFrame(dtype="object")
        # First published
        if price_history.get("firstPublished") is not None:
            record = price_history["firstPublished"]
            first_listed = record["firstPublishedDate"]
            data_records.append({"date": record["firstPublishedDate"],
                                 "price": record["priceLabel"],
                                 "price_change_type": "listing_change"})
        # Last sold
        if price_history.get("lastSale") is not None:
            record = price_history["lastSale"]
            data_records.append({"date": record["date"],
                                 "price": record["priceLabel"],
                                 "price_change_type": "last_sold"})
        # Listing changes
        if price_history.get("priceChanges") is not None:
            records = price_history["priceChanges"]
            for record in records:
                data_records.append({"date": record["priceChangeDate"],
                                     "price": record["priceLabel"],
                                     "price_change_type": "listing_change"})

        out_df = pd.DataFrame(data_records)
        if out_df.empty:
            return pd.Series(dtype="object") if summarised else pd.DataFrame(dtype="object")

        out_df["date"] = pd.to_datetime(out_df["date"])
        out_df["price"] = out_df["price"].apply(lambda v: floor_plan_utils.numbers_from_string(v)[0])
        out_df["listingId"] = self.listing_id
        out_df = out_df.set_index("date")
        out_df = out_df.sort_index()

        if summarised:
            listing_changes = out_df[out_df["price_change_type"] == "listing_change"]["price"].pct_change().dropna()
            number_of_changes = len(listing_changes)
            avg_pct_change = listing_changes.mean()
            max_pct_change = listing_changes.max()
            min_pct_change = listing_changes.min()
            return pd.Series({"first_listed": first_listed,
                              "number_of_price_changes": number_of_changes,
                              "avg_pct_per_price_change": avg_pct_change,
                              "max_pct_per_price_change": max_pct_change,
                              "min_pct_per_price_change": min_pct_change})
        else:
            return out_df

    def extract_all(self, graphql_api_key: str) -> pd.Series:
        """
        :param graphql_api_key: Graph ql API key
        :return: All details in a series
        """
        property_data = []
        all_methods = [
            self.extract_main_details,
            self.extract_pois,
            self.extract_detailed_description,
            self.extract_location,
            self.extract_sq_footage,
        ]
        for method in all_methods:
            property_data.append(method())

        # Price History
        property_data.append(self.extract_price_change_history(graphql_api_key=graphql_api_key,
                                                               summarised=True))
        property_data_series = pd.concat(property_data)
        property_data_series.index.name = self.listing_id

        if pd.notnull(property_data_series["total_sq_footage"]):
            property_data_series["pounds_per_sq_foot"] = property_data_series["price"] / property_data_series["total_sq_footage"]
        return property_data_series
